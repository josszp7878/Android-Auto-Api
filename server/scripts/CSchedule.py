from enum import Enum
import _G
import datetime
import os
import json
import threading
import time
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from CChecker import CChecker_

g = _G.g
log = g.Log()


class CSchedule_:
    """调度器类，用于按照策略执行检查器"""
    
   
    @classmethod
    def runAll(cls, policyFile: str = None):
        """根据策略文件批量执行所有配置的检查器
        
        Args:
            policyFile: 策略文件路径，默认为 config/Schedule.json
            
        Returns:
            bool: 是否成功启动批量执行
        """
        log = g.Log()
        try:
            # 如果没有指定策略文件，使用默认路径
            if not policyFile:
                policyFile = os.path.join(g.rootDir(), 'config', 'Schedule.json')
            # 检查策略文件是否存在
            if not os.path.exists(policyFile):
                log.e(f"策略文件 {policyFile} 不存在")
                return False
            
            # 加载策略文件
            with open(policyFile, 'r', encoding='utf-8') as f:
                policies = json.load(f)
            log.i(f"加载策略文件 {policyFile} 成功，策略数量: {len(policies)}")
            # 创建线程列表
            threads = []
            
            # 按照策略顺序创建并执行检查器
            for policy in policies:
                checker_name = policy.get('checker')
                if not checker_name:
                    log.w(f"策略中缺少检查器名称: {policy}")
                    continue
                
                # 获取检查器
                Checker = g.Checker()
                checker = Checker.get(checker_name, create=True)
                if not checker:
                    log.w(f"检查器 {checker_name} 不存在或创建失败")
                    continue
                # 创建线程执行批量运行方法
                thread = cls.batchRun(checker, policy)
                threads.append(thread)
                log.i(f"启动检查器 {checker_name} 的批量执行线程")
            
            log.i(f"成功启动 {len(threads)} 个检查器批量执行线程")
            return True
            
        except Exception as e:
            log.ex(e, "批量执行所有检查器失败")
            return False
    
    @classmethod
    def batchRun(cls, checker: "CChecker_", policy: dict) -> threading.Thread:
        """批量执行检查器
        根据策略参数执行检查器，只通过schedule配置支持定时执行、指定次数或指定时长
        Args:
            checker: 要执行的检查器对象
            policy: 执行策略字典，包含以下字段:
                - s/sch/schedule: 定时计划，支持以下格式:
                  - {"HH:MM"|整数|"": {"t": 次数, "i": 间隔, "d": 时长}, ...}
        Returns:
            threading.Thread: 执行线程
        """
        def _run():
            try:
                # 提取策略参数（支持简化的key）
                schedule = cls._getConfigValue(
                    policy, 's', 'sch', 'schedule', defaultValue={})
                # 转换为字典格式方便处理
                if isinstance(schedule, str):
                    schedule = {schedule: {}}
                elif isinstance(schedule, list):
                    schedule = {item: {} for item in schedule}
                
                # 如果schedule为空，无法执行
                if not schedule:
                    log.w(f"未找到有效的执行计划配置，无法执行检查器 {checker.name}")
                    return False
                log.i(f"启动批量执行检查器 {checker.name}, 计划: {schedule}")
                # 根据schedule执行定时任务
                return cls._runSchedule(checker, schedule)
            except Exception as e:
                log.ex(e, f"批量执行检查器 {checker.name} 失败")
                return False
                
        thread = threading.Thread(
            target=_run,
            daemon=True
        )
        thread.start()
        return thread
    
    @classmethod
    def _runSchedule(cls, checker: "CChecker_", schedule: dict) -> bool:
        """按照时间表执行
        Args:
            checker: 要执行的检查器对象
            schedule: 定时计划字典
                     - 字典格式: {"HH:MM"|整数|"": {"t": 次数, "i": 间隔, "d": 时长}, ...}
        Returns:
            bool: 是否成功执行
        """
        # 处理一次性执行
        if "" in schedule:
            if cls._onOneTime(checker, schedule[""]):
                return True
            
        # 处理间隔分钟执行项
        intervalKeys = [k for k in schedule 
                        if isinstance(k, (int, str)) and str(k).isdigit()]
        for key in intervalKeys:
            minutes = int(key)
            if minutes > 0:
                if cls._onInterval(checker, minutes, schedule[key]):
                    return True
            
        # 处理时间点执行
        timePointKeys = [k for k in schedule if isinstance(k, str) and ":" in k]
        if timePointKeys:
            return cls._onTimePoint(
                checker,
                {k: schedule[k] for k in timePointKeys}
            )
        
        return False
    
    @classmethod
    def _onOneTime(cls, checker: "CChecker_", config: dict) -> bool:
        """处理一次性执行的配置项
        Args:
            checker: 要执行的检查器对象
            config: 执行配置
        Returns:
            bool: 是否有一次性执行项并成功完成
        """
        log = g.Log()
        
        log.i(f"一次性执行检查器 {checker.name}")
        cls._run(checker, config)
    
    @classmethod
    def _onInterval(cls, checker: "CChecker_", minutes: int, config: dict) -> bool:
        """处理间隔执行的配置项
        Args:
            checker: 要执行的检查器对象
            minutes: 间隔分钟数
            config: 执行配置
        
        Returns:
            bool: 是否有间隔执行项并成功启动
        """
        log = g.Log()
        
        log.i(f"间隔执行检查器 {checker.name}, 每{minutes}分钟一次")
        
        # 转换为秒
        intervalSeconds = minutes * 60
        
        while True:
            ret = cls._run(checker, config)
            if ret == CChecker_.eDoRet.exit.value:
                log.i("间隔执行收到终止信号，停止执行")
                return True
            # 等待到下一个间隔
            log.i(f"等待 {intervalSeconds} 秒后执行下一次检查")
            time.sleep(intervalSeconds)
    
    @classmethod
    def _onTimePoint(cls, checker: "CChecker_", timePointSchedule: dict) -> bool:
        """执行时间点计划
        
        Args:
            checker: 要执行的检查器对象
            timePointSchedule: 时间点执行计划字典
            
        Returns:
            bool: 是否执行了任务
        """
        log = g.Log()
        executed = False
        now = datetime.datetime.now()
        
        # 如果没有时间点项，返回False
        if not timePointSchedule:
            log.i("没有时间点执行项")
            return False 
            
        # 按时间排序处理
        timePoints = sorted(timePointSchedule.keys())
        validTimePoints = []
        
        # 找出所有未过期的时间点
        for timeStr in timePoints:
            try:
                # 解析时间字符串
                hour, minute = map(int, timeStr.split(':'))
                scheduleTime = now.replace(
                    hour=hour, minute=minute, second=0, microsecond=0)
                
                # 如果时间已过，跳过此时间点
                if scheduleTime < now:
                    log.i(f"时间点 {timeStr} 已过期，跳过")
                    continue
                    
                validTimePoints.append((timeStr, scheduleTime))
            except Exception as e:
                log.ex(e, f"解析时间点 {timeStr} 出错")
        
        # 没有有效的时间点
        if not validTimePoints:
            log.i("没有有效的时间点，所有时间点已过期")
            return False
            
        # 按时间排序
        validTimePoints.sort(key=lambda x: x[1])
        
        # 执行有效的时间点任务
        for timeStr, scheduleTime in validTimePoints:
            config = timePointSchedule[timeStr]
            try:
                # 计算到下一个执行时间的秒数
                secondsToWait = (scheduleTime - now).total_seconds()
                log.i(f"将在 {timeStr} 执行，等待 {int(secondsToWait)} 秒")
                
                # 等待到执行时间
                time.sleep(secondsToWait)
                
                # 执行指定次数或时长
                ret = cls._run(checker, config)
                executed = True
                
                if ret == CChecker_.eDoRet.exit.value:
                    log.i(f"时间点 {timeStr} 执行收到终止信号，停止后续执行")
                    return True
                # 更新基准时间为当前时间
                now = datetime.datetime.now()
            except Exception as e:
                log.ex(e, f"执行时间点 {timeStr} 出错")
        return executed

    @classmethod
    def _run(cls, checker: "CChecker_", config: dict) -> str:
        """执行检查器并处理结果
        
        Args:
            checker: 要执行的检查器对象
            config: 执行配置参数
            
        Returns:
            str: 执行结果，如果是特殊结果则返回对应的字符串
        """
        log = g.Log()
        try:
            # 获取执行参数（支持多种键名和简写）
            times = cls._getConfigValue(config, 't', 'tim', 'times', 
                                      defaultValue=1)
            interval = cls._getConfigValue(config, 'i', 'int', 'interval', 
                                         defaultValue=0)
            duration = cls._getConfigValue(config, 'd', 'dur', 'duration', 
                                         defaultValue=0)
            
            # 处理参数
            times = int(times) if times else 1
            interval = int(interval) if interval else 0
            duration = int(duration) if duration else 0
            
            # 如果指定了times，优先按次数执行
            if times > 0:
                for i in range(times):
                    log.i(f"执行第 {i+1}/{times} 次")
                    checker.begin()
                    ret = ''
                    # 等待结果
                    while ret == '':
                        # 如果有返回值，根据返回值处理
                        if hasattr(checker, 'ret') and checker.ret:
                            ret = checker.ret
                        time.sleep(1)
                    if ret == CChecker_.eDoRet.exit.value:
                        log.i("执行收到终止信号，停止后续执行")
                        return ret
                    # 执行间隔
                    if i < times - 1 and interval > 0:
                        log.i(f"等待 {interval} 秒后执行下一次")
                        time.sleep(interval)
                return ret
            
            # 时长优先级低于次数，只有未指定次数时才按时长执行
            elif duration > 0:
                end_time = time.time() + duration
                i = 0
                while time.time() < end_time:
                    i += 1
                    log.i(f"按时长执行第 {i} 次，剩余时间: {int(end_time - time.time())} 秒")
                    checker.begin()
                    ret = ''
                    # 等待结果
                    while ret == '':
                        # 如果有返回值，根据返回值处理
                        if hasattr(checker, 'ret') and checker.ret:
                            ret = checker.ret
                        time.sleep(1)
                    if ret == CChecker_.eDoRet.exit.value:
                        log.i("执行收到终止信号，停止后续执行")
                        return ret
                    # 执行间隔
                    if time.time() + interval < end_time and interval > 0:
                        log.i(f"等待 {interval} 秒后执行下一次")
                        time.sleep(interval)
                    else:
                        # 如果剩余时间不足以执行下一次，结束循环
                        break
                return ret
            
            # 没有设置次数和时长，执行一次
            else:
                log.i("执行一次")
                checker.begin()
                ret = ''
                # 等待结果
                while ret == '':
                    # 如果有返回值，根据返回值处理
                    if hasattr(checker, 'ret') and checker.ret:
                        ret = checker.ret
                    time.sleep(1)
                return ret
                
        except Exception as e:
            log.ex(e, f"执行检查器 {checker.name} 失败")
            return CChecker_.eDoRet.error.value

    @classmethod
    def _getConfigValue(cls, config, *keys, defaultValue=None):
        """从配置中获取值，支持多个候选键名
        Args:
            config: 配置字典
            *keys: 要查找的键名列表，按优先级排序
            defaultValue: 默认值，当所有键名都不存在时返回

        Returns:
            找到的值或默认值
        """
        if not config:
            return defaultValue            
        for key in keys:
            if key in config:
                return config[key]                
        return defaultValue 