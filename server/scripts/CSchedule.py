# import _G
# import datetime
# import os
# import json
# import threading
# import time
# from typing import TYPE_CHECKING, Optional, Dict
# if TYPE_CHECKING:
#     from _Tools import _Tools_
#     from _Page import _Page_
#     from _App import _App_


# class CSchedule_:
#     """调度器类，用于按照策略执行检查器"""
    
#     # 定义类变量
#     policies = []
   
#     @classmethod
#     def loadConfig(cls) -> bool:
#         """加载调度策略配置文件
        
#         Args:
#             policyFile: 策略文件路径，默认为 config/Schedule.json
            
#         Returns:
#             bool: 是否成功加载策略文件
#         """
#         g = _G._G_
#         log = g.Log()
#         try:
#             # 如果没有指定策略文件，使用默认路径
#             policyFile = os.path.join(
#                 g.rootDir(), 'config', 'Schedule.json')
#             # 检查策略文件是否存在
#             if not os.path.exists(policyFile):
#                 log.e(f"策略文件 {policyFile} 不存在")
#                 return False
            
#             # 加载策略文件
#             with open(policyFile, 'r', encoding='utf-8') as f:
#                 cls.policies = json.load(f)
#             log.i(f"加载策略文件成功，策略数量: {len(cls.policies)}")
#             return True
#         except Exception as e:
#             log.ex(e, "加载策略文件失败")
#             return False
    
#     def __init__(self, app: "_App_"):
#         """初始化调度器，关联应用实例
        
#         Args:
#             app: 关联的应用实例
#         """
#         self.app = app
#         self.threads = []
#         self.running = True
#         g = _G._G_
#         self.log = g.Log()
#         self.log.i(f"创建应用 {app.name} 的调度器")
    
#     def runAll(self) -> bool:
#         """根据策略文件批量执行该应用下所有配置的页面
            
#         Returns:
#             bool: 是否成功启动批量执行
#         """
#         try:
#             # 加载策略文件
#             if not CSchedule_.loadConfig():
#                 return False
            
#             # 创建线程列表
#             self.threads = []
            
#             # 按照策略顺序创建并执行检查器
#             for policy in CSchedule_.policies:
#                 page_name = policy.get('page')
#                 if not page_name:
#                     self.log.w(f"策略中缺少页面名称: {policy}")
#                     continue
                
#                 # 获取页面
#                 page = self.app.getPage(page_name, create=True)
#                 if not page:
#                     self.log.w(f"页面 {page_name} 不存在或创建失败")
#                     continue
                
#                 # 创建线程执行批量运行方法
#                 thread = self.run(page, policy)
#                 self.threads.append(thread)
#                 self.log.i(f"启动页面 {page_name} 的批量执行线程")
            
#             self.log.i(f"成功启动 {len(self.threads)} 个页面批量执行线程")
#             return True
            
#         except Exception as e:
#             self.log.ex(e, "批量执行所有页面失败")
#             return False
    
#     def run(self, page: "_Page_", config: dict = None) -> threading.Thread:
#         """批量执行页面
#         根据策略参数执行页面，只通过schedule配置支持定时执行、指定次数或指定时长
#         Args:
#             page: 要执行的页面对象
#             policy: 执行策略字典，包含以下字段:
#                 - s/sch/schedule: 定时计划，支持以下格式:
#                   - {"HH:MM"|整数|"": {"t": 次数, "i": 间隔, "d": 时长}, ...}
#         Returns:
#             threading.Thread: 执行线程
#         """
#         def _run():
#             try:
#                 # 优先使用外部配置，没有则使用页面配置
#                 schedule = config or page.schedule
#                 if not schedule:
#                     self.log.w(f"页面 {page.name} 没有配置执行计划")
#                     return False
                
#                 self.log.i(f"启动批量执行页面 {page.name}, 计划: {schedule}")
#                 return self._runSchedule(page, schedule)
#             except Exception as e:
#                 self.log.ex(e, f"批量执行页面 {page.name} 失败")
#                 return False
                
#         thread = threading.Thread(
#             target=_run,
#             daemon=True
#         )
#         thread.start()
#         return thread
    
#     def _runSchedule(self, page: "_Page_", schedule: dict) -> bool:
#         """按照时间表执行
#         Args:
#             page: 要执行的页面对象
#             schedule: 定时计划字典
#                      - 字典格式: {"HH:MM"|整数|"": {"t": 次数, "i": 间隔, "d": 时长}, ...}
#         Returns:
#             bool: 是否成功执行
#         """
#         # 处理一次性执行
#         if "" in schedule:
#             if self._onOneTime(page, schedule[""]):
#                 return True
            
#         # 处理间隔分钟执行项
#         intervalKeys = [k for k in schedule 
#                         if isinstance(k, (int, str)) and str(k).isdigit()]
#         for key in intervalKeys:
#             minutes = int(key)
#             if minutes > 0:
#                 if self._onInterval(page, minutes, schedule[key]):
#                     return True
            
#         # 处理时间点执行
#         timePointKeys = [k for k in schedule if isinstance(k, str) and ":" in k]
#         if timePointKeys:
#             return self._onTimePoint(
#                 page,
#                 {k: schedule[k] for k in timePointKeys}
#             )
        
#         return False
    
#     def _onOneTime(self, page: "_Page_", config: dict) -> bool:
#         """处理一次性执行的配置项
#         Args:
#             page: 要执行的页面对象
#             config: 执行配置
#         Returns:
#             bool: 是否有一次性执行项并成功完成
#         """
#         self.log.i(f"一次性执行页面 {page.name}")
#         self._run(page, config)
#         return True
    
#     def _onInterval(self, page: "_Page_", minutes: int, config: dict) -> bool:
#         """处理间隔执行的配置项
#         Args:
#             page: 要执行的页面对象
#             minutes: 间隔分钟数
#             config: 执行配置
        
#         Returns:
#             bool: 是否有间隔执行项并成功启动
#         """
#         self.log.i(f"间隔执行页面 {page.name}, 每{minutes}分钟一次")
        
#         # 转换为秒
#         intervalSeconds = minutes * 60
#         g = _G._G_
#         tools = g.Tools()
#         while self.running:
#             ret = self._run(page, config)
#             if ret == tools.eRet.exit:
#                 self.log.i("间隔执行收到终止信号，停止执行")
#                 return True
#             # 等待到下一个间隔
#             self.log.i(f"等待 {intervalSeconds} 秒后执行下一次检查")
#             time.sleep(intervalSeconds)
    
#     def _onTimePoint(self, page: "_Page_", timePointSchedule: dict) -> bool:
#         """执行时间点计划
        
#         Args:
#             page: 要执行的页面对象
#             timePointSchedule: 时间点执行计划字典
            
#         Returns:
#             bool: 是否执行了任务
#         """
#         executed = False
#         now = datetime.datetime.now()
        
#         # 如果没有时间点项，返回False
#         if not timePointSchedule:
#             self.log.i("没有时间点执行项")
#             return False 
            
#         # 按时间排序处理
#         timePoints = sorted(timePointSchedule.keys())
#         validTimePoints = []
        
#         # 找出所有未过期的时间点
#         for timeStr in timePoints:
#             try:
#                 # 解析时间字符串
#                 hour, minute = map(int, timeStr.split(':'))
#                 scheduleTime = now.replace(
#                     hour=hour, minute=minute, second=0, microsecond=0)
                
#                 # 如果时间已过，跳过此时间点
#                 if scheduleTime < now:
#                     self.log.i(f"时间点 {timeStr} 已过期，跳过")
#                     continue
                    
#                 validTimePoints.append((timeStr, scheduleTime))
#             except Exception as e:
#                 self.log.ex(e, f"解析时间点 {timeStr} 出错")
        
#         if not validTimePoints:
#             self.log.i("所有时间点已过期，无需执行")
#             return False
        
#         g = _G._G_
#         tools = g.Tools()
        
#         # 按时间顺序执行
#         for timeStr, scheduleTime in validTimePoints:
#             # 计算需要等待的时间
#             waitSeconds = (scheduleTime - datetime.datetime.now()).total_seconds()
#             if waitSeconds > 0:
#                 self.log.i(f"等待到时间点 {timeStr} ({int(waitSeconds/60)} 分钟后)")
                
#                 # 分段等待，便于中断
#                 while waitSeconds > 0 and self.running:
#                     sleepTime = min(waitSeconds, 10)  # 最多等待10秒
#                     time.sleep(sleepTime)
#                     waitSeconds -= sleepTime
            
#             if not self.running:
#                 self.log.i("收到停止信号，终止时间点执行计划")
#                 break
                
#             # 时间到，执行页面
#             self.log.i(f"时间点 {timeStr} 到达，执行页面 {page.name}")
#             config = timePointSchedule[timeStr]
#             ret = self._run(page, config) 
#             if ret == tools.eRet.exit:
#                 self.log.i("时间点执行收到终止信号，停止执行")
#                 return True
            
#             executed = True
            
#         return executed
    
#     def _run(self, page: "_Page_", config: dict) -> '_Tools_.eRet':
#         """执行页面
#         Args:
#             page: 要执行的页面
#             config: 执行配置，包含以下可选字段:
#                 t/times: 执行次数
#                 i/interval: 间隔时间(秒)
#                 d/duration: 执行时长(分钟)
        
#         Returns:
#             eRet: 执行结果
#                 exit: 请求退出
#                 ok: 执行完成
#                 fail: 执行失败
#         """
#         g = _G._G_
#         tools = g.Tools()
        
#         # 获取配置参数
#         times = self._getConfigValue(config, 't', 'times', defaultValue=1)
#         interval = self._getConfigValue(config, 'i', 'interval', defaultValue=1)
#         durationMinutes = self._getConfigValue(config, 'd', 'duration', defaultValue=0)
        
#         # 初始化计时器和计数器
#         startTime = time.time()
#         durationSeconds = durationMinutes * 60
#         count = 0
#         failCount = 0
#         maxFailCount = 3  # 允许的最大连续失败次数
        
#         # 确定执行条件
#         hasTimeLimit = durationSeconds > 0
#         hasCountLimit = times > 0
        
#         # 执行页面
#         self.log.i(f"执行页面 {page.name}, 次数={times}, 间隔={interval}秒, 时长={durationMinutes}分钟")
#         while self.running:
#             # 检查是否超过指定执行次数
#             if hasCountLimit and count >= times:
#                 self.log.i(f"已完成 {count}/{times} 次执行，执行完毕")
#                 break
                
#             # 检查是否超过指定执行时长
#             if hasTimeLimit:
#                 elapsed = time.time() - startTime
#                 if elapsed >= durationSeconds:
#                     self.log.i(f"已执行 {int(elapsed/60)} 分钟，达到指定时长，执行完毕")
#                     break
            
#             # 执行页面
#             try:
#                 # 启动页面，使用app的start方法而不是page.begin()
#                 self.log.i(f"执行第 {count+1} 次")
#                 page = self.app.goPage(page.name)
#                 ret = page is not None
#                 if ret is False:
#                     failCount += 1
#                     self.log.w(f"执行失败，连续失败次数: {failCount}/{maxFailCount}")
#                     if failCount >= maxFailCount:
#                         self.log.e(f"连续失败 {maxFailCount} 次，停止执行")
#                         return tools.eRet.fail
#                 else:
#                     # 成功执行，重置失败计数
#                     failCount = 0
                
#                 # 计数累加
#                 count += 1
                
#                 # 判断是否继续执行
#                 shouldContinue = (not hasCountLimit or count < times) and \
#                                  (not hasTimeLimit or (time.time() - startTime) < durationSeconds)
                
#                 if not shouldContinue:
#                     self.log.i("达到执行限制，执行完毕")
#                     break
                    
#                 # 等待指定的间隔时间
#                 if interval > 0 and shouldContinue:
#                     self.log.i(f"等待 {interval} 秒后执行下一次")
#                     for _ in range(interval):
#                         if not self.running:
#                             return tools.eRet.exit
#                         time.sleep(1)
                        
#             except Exception as e:
#                 self.log.ex(e, f"执行页面 {page.name} 出错")
#                 failCount += 1
#                 if failCount >= maxFailCount:
#                     self.log.e(f"连续失败 {maxFailCount} 次，停止执行")
#                     return tools.eRet.fail
        
#         if not self.running:
#             return tools.eRet.exit
            
#         return tools.eRet.ok

#     def stop(self):
#         """停止调度器所有任务"""
#         self.running = False
#         self.log.i(f"停止应用 {self.app.name} 的调度器")

#     def _getConfigValue(self, config, *keys, defaultValue=None):
#         """从配置中获取值，支持多个备选键名
#         Args:
#             config: 配置字典
#             *keys: 可能的键名列表
#             defaultValue: 默认值，当所有键名都不存在时返回
            
#         Returns:
#             任意: 找到的值或默认值
#         """
#         if not config:
#             return defaultValue
            
#         for key in keys:
#             if key in config:
#                 return config[key]
                
#         return defaultValue 