from enum import Enum
from typing import Dict, Any
import _G
import datetime
import os
import json
import threading
import time

g = _G.g
log = g.Log()


class CSchedule_:
    """调度器类，用于按照策略执行检查器"""
    
    # 导入eDoRet枚举类型，与CChecker_保持一致
    class eDoRet(Enum):
        # 无操作
        none = ''
        # 结束schedule
        endSchedule = 'endSchedule'
        # 结束本次check，继续schedule
        end = 'end'
        # 出错
        error = 'error'
    
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
    def batchRun(cls, checker, policy) -> threading.Thread:
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
    def _runSchedule(cls, checker, schedule):
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
    def _onOneTime(cls, checker, config):
        """处理一次性执行的配置项
        Args:
            checker: 要执行的检查器对象
            config: 执行配置
        Returns:
            bool: 是否有一次性执行项并成功完成
        """
        log = g.Log()
        
        log.i(f"一次性执行检查器 {checker.name}")
        ret = cls._run(checker, config)
        if ret == cls.eDoRet.endSchedule or ret == cls.eDoRet.end:
            return True
        
        log.w(f"一次性执行失败，返回：{ret}")
        return False
    
    @classmethod
    def _onInterval(cls, checker, minutes, config):
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
            if ret == cls.eDoRet.endSchedule:
                log.i("间隔执行收到终止信号，停止执行")
                return True
                
            # 等待到下一个间隔
            log.i(f"等待 {intervalSeconds} 秒后执行下一次检查")
            time.sleep(intervalSeconds)
    
    @classmethod
    def _onTimePoint(cls, checker, timePointSchedule):
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
                
                if ret == cls.eDoRet.endSchedule:
                    log.i(f"时间点 {timeStr} 执行收到终止信号，停止后续执行")
                    return True
                
                # 更新基准时间为当前时间
                now = datetime.datetime.now()
                
            except Exception as e:
                log.ex(e, f"执行时间点 {timeStr} 出错")
                
        return executed

    @classmethod
    def _run(cls, checker, config) -> eDoRet:
        """按照次数或时长执行
        Args:
            checker: 要执行的检查器对象
            config: 配置字典，包含以下可选参数：
                - t/tim/times: 执行次数
                - d/dur/duration: 执行时长（秒）
                - i/int/interval: 执行间隔（秒）
        Returns:
            eDoRet: 执行结果
        """
        log = g.Log()
        
        try:
            # 从配置中提取参数
            times = cls._getConfigValue(config, 't', 'tim', 'times', defaultValue=1)
            duration = cls._getConfigValue(
                config, 'd', 'dur', 'duration', defaultValue=0)
            interval = cls._getConfigValue(
                config, 'i', 'int', 'interval', defaultValue=5)
            
            log.i(f"执行配置: times={times}, duration={duration}, interval={interval}")
            
            # 记录开始时间
            startTime = time.time()
            count = 0
            
            while True:
                ret = checker.begin()
                count += 1
                log.i(f"执行检查器 {checker.name} 第 {count} 次")
                if ret == cls.eDoRet.endSchedule:
                    log.i(f"检查器 {checker.name} 返回终止schedule信号，停止执行")
                    return ret
                # 判断是否达到次数限制
                if times > 0 and count >= times:
                    log.i(f"已完成指定次数 {times} 次执行")
                    break
                # 判断是否达到时长限制
                elif (times <= 0 and duration > 0 and 
                      (time.time() - startTime) >= duration):
                    log.i(f"已完成指定时长 {duration} 秒执行")
                    break
                # 如果既没有指定次数也没有指定时长，执行一次就退出
                elif times <= 0 and duration <= 0:
                    break
                time.sleep(interval)
            return cls.eDoRet.end
            
        except Exception as e:
            log.ex(e, f"执行检查器 {checker.name} 出错")
            return cls.eDoRet.error

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