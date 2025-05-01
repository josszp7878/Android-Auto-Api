import _G
import datetime
import os
import json
import threading
import time
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from _Tools import _Tools_
    from _Page import _Page_


class CSchedule_:
    """调度器类，用于按照策略执行检查器"""
    
    # 定义类变量
    policies = []
   
    @classmethod
    def loadConfig(cls) -> bool:
        """加载调度策略配置文件
        
        Args:
            policyFile: 策略文件路径，默认为 config/Schedule.json
            
        Returns:
            bool: 是否成功加载策略文件
        """
        g = _G._G_
        log = g.Log()
        try:
            # 如果没有指定策略文件，使用默认路径
            policyFile = os.path.join(
                g.rootDir(), 'config', 'Schedule.json')
            # 检查策略文件是否存在
            if not os.path.exists(policyFile):
                log.e(f"策略文件 {policyFile} 不存在")
                return False
            
            # 加载策略文件
            with open(policyFile, 'r', encoding='utf-8') as f:
                cls.policies = json.load(f)
            log.i(f"加载策略文件成功，策略数量: {len(cls.policies)}")
            return True
        except Exception as e:
            log.ex(e, "加载策略文件失败")
            return False
    
    @classmethod
    def runAll(cls, policyFile: str = None):
        """根据策略文件批量执行所有配置的检查器
        
        Args:
            policyFile: 策略文件路径，默认为 config/Schedule.json
            
        Returns:
            bool: 是否成功启动批量执行
        """
        g = _G._G_
        log = g.Log()
        try:
            # 加载策略文件
            if not cls.loadConfig(policyFile):
                return False
            
            # 创建线程列表
            threads = []
            
            # 按照策略顺序创建并执行检查器
            for policy in cls.policies:
                page_name = policy.get('page')
                if not page_name:
                    log.w(f"策略中缺少页面名称: {policy}")
                    continue
                
                # 获取页面
                Page = g.Page()
                page = Page.getInst(page_name, create=True)
                if not page:
                    log.w(f"页面 {page_name} 不存在或创建失败")
                    continue
                
                # 创建线程执行批量运行方法
                thread = cls.batchRun(page, policy)
                threads.append(thread)
                log.i(f"启动页面 {page_name} 的批量执行线程")
            
            log.i(f"成功启动 {len(threads)} 个页面批量执行线程")
            return True
            
        except Exception as e:
            log.ex(e, "批量执行所有页面失败")
            return False
    
    @classmethod
    def batchRun(cls, page: "_Page_", config: dict = None) -> threading.Thread:
        """批量执行页面
        根据策略参数执行页面，只通过schedule配置支持定时执行、指定次数或指定时长
        Args:
            page: 要执行的页面对象
            policy: 执行策略字典，包含以下字段:
                - s/sch/schedule: 定时计划，支持以下格式:
                  - {"HH:MM"|整数|"": {"t": 次数, "i": 间隔, "d": 时长}, ...}
        Returns:
            threading.Thread: 执行线程
        """
        g = _G._G_
        log = g.Log()
        
        def _run():
            try:
                # 优先使用外部配置，没有则使用页面配置
                schedule = config or page.schedule
                if not schedule:
                    log.w(f"页面 {page.name} 没有配置执行计划")
                    return False
                
                log.i(f"启动批量执行页面 {page.name}, 计划: {schedule}")
                return cls._runSchedule(page, schedule)
            except Exception as e:
                log.ex(e, f"批量执行页面 {page.name} 失败")
                return False
                
        thread = threading.Thread(
            target=_run,
            daemon=True
        )
        thread.start()
        return thread
    
    @classmethod
    def _runSchedule(cls, page: "_Page_", schedule: dict) -> bool:
        """按照时间表执行
        Args:
            page: 要执行的页面对象
            schedule: 定时计划字典
                     - 字典格式: {"HH:MM"|整数|"": {"t": 次数, "i": 间隔, "d": 时长}, ...}
        Returns:
            bool: 是否成功执行
        """
        # 处理一次性执行
        if "" in schedule:
            if cls._onOneTime(page, schedule[""]):
                return True
            
        # 处理间隔分钟执行项
        intervalKeys = [k for k in schedule 
                        if isinstance(k, (int, str)) and str(k).isdigit()]
        for key in intervalKeys:
            minutes = int(key)
            if minutes > 0:
                if cls._onInterval(page, minutes, schedule[key]):
                    return True
            
        # 处理时间点执行
        timePointKeys = [k for k in schedule if isinstance(k, str) and ":" in k]
        if timePointKeys:
            return cls._onTimePoint(
                page,
                {k: schedule[k] for k in timePointKeys}
            )
        
        return False
    
    @classmethod
    def _onOneTime(cls, page: "_Page_", config: dict) -> bool:
        """处理一次性执行的配置项
        Args:
            page: 要执行的页面对象
            config: 执行配置
        Returns:
            bool: 是否有一次性执行项并成功完成
        """
        g = _G._G_
        log = g.Log()
        
        log.i(f"一次性执行页面 {page.name}")
        cls._run(page, config)
        return True
    
    @classmethod
    def _onInterval(cls, page: "_Page_", minutes: int, config: dict) -> bool:
        """处理间隔执行的配置项
        Args:
            page: 要执行的页面对象
            minutes: 间隔分钟数
            config: 执行配置
        
        Returns:
            bool: 是否有间隔执行项并成功启动
        """
        g = _G._G_
        log = g.Log()
        
        log.i(f"间隔执行页面 {page.name}, 每{minutes}分钟一次")
        
        # 转换为秒
        intervalSeconds = minutes * 60
        tools = g.Tools()
        while True:
            ret = cls._run(page, config)
            if ret == tools.eRet.exit:
                log.i("间隔执行收到终止信号，停止执行")
                return True
            # 等待到下一个间隔
            log.i(f"等待 {intervalSeconds} 秒后执行下一次检查")
            time.sleep(intervalSeconds)
    
    @classmethod
    def _onTimePoint(cls, page: "_Page_", timePointSchedule: dict) -> bool:
        """执行时间点计划
        
        Args:
            page: 要执行的页面对象
            timePointSchedule: 时间点执行计划字典
            
        Returns:
            bool: 是否执行了任务
        """
        g = _G._G_
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
        tools = g.Tools()
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
                ret = cls._run(page, config)
                executed = True
                
                if ret == tools.eRet.exit:
                    log.i(f"时间点 {timeStr} 执行收到终止信号，停止后续执行")
                    return True
                # 更新基准时间为当前时间
                now = datetime.datetime.now()
            except Exception as e:
                log.ex(e, f"执行时间点 {timeStr} 出错")
        return executed

    @classmethod
    def _run(cls, page: "_Page_", config: dict) -> '_Tools_.eRet':
        """执行页面并处理结果
        
        Args:
            page: 要执行的页面对象
            config: 执行配置参数
            
        Returns:
            '_Tools_.DoRet': 执行结果
        """
        g = _G._G_
        log = g.Log()
        tools = g.Tools()
        try:
            # 获取执行参数（支持多种键名和简写）
            times = cls._getConfigValue(
                config, 't', 'tim', 'times', defaultValue=1)
            interval = cls._getConfigValue(
                config, 'i', 'int', 'interval', defaultValue=0)
            duration = cls._getConfigValue(
                config, 'd', 'dur', 'duration', defaultValue=0)
            
            # 处理参数
            times = int(times) if times else 1
            interval = int(interval) if interval else 0
            duration = int(duration) if duration else 0
            # 如果指定了times，优先按次数执行
            if times > 0:
                for i in range(times):
                    log.i(f"执行第 {i+1}/{times} 次")
                    page.begin()
                    # 等待结果
                    while page.ret == _Tools_.eRet.none:
                        # 如果有返回值，根据返回值处理
                        time.sleep(1)
                    if page.ret == tools.eRet.exit:
                        log.i("执行收到终止信号，停止后续执行")
                        return page.ret
                    # 执行间隔
                    if i < times - 1 and interval > 0:
                        log.i(f"等待 {interval} 秒后执行下一次")
                        time.sleep(interval)
                return page.ret
            
            # 时长优先级低于次数，只有未指定次数时才按时长执行
            elif duration > 0:
                end_time = time.time() + duration
                i = 0
                while time.time() < end_time:
                    i += 1
                    log.i(f"按时长执行第 {i} 次，剩余时间: {int(end_time - time.time())} 秒")
                    page.begin()
                    # 等待结果
                    while page.ret == _Tools_.eRet.none:
                        # 如果有返回值，根据返回值处理
                        time.sleep(1)
                    if page.ret == tools.eRet.exit:
                        log.i("执行收到终止信号，停止后续执行")
                        return page.ret
                    # 执行间隔
                    if time.time() + interval < end_time and interval > 0:
                        log.i(f"等待 {interval} 秒后执行下一次")
                        time.sleep(interval)
                    else:
                        # 如果剩余时间不足以执行下一次，结束循环
                        break
                return page.ret
            
            # 没有设置次数和时长，执行一次
            else:
                log.i("执行一次")
                page.begin()
                # 等待结果
                while page.ret == _Tools_.eRet.none:
                    # 如果有返回值，根据返回值处理
                    time.sleep(1)
                return page.ret
                
        except Exception as e:
            log.ex(e, f"执行页面 {page.name} 失败")
            return tools.eRet.error

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