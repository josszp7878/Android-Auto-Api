# from task import Task
# from tools import LogD, LogE
# from Cmds import Cmds

from task import Task
from checker import Checker
from logger import Log
from CmdMgr import CmdMgr
import time

def handleAdStart(checker: Checker) -> bool:
    """处理广告开始"""
    for _, item in checker.matched:
        if "观看广告" in item['t']:
            return CmdMgr.instance().androidServices.click("观看")
    return False

def handleAdProgress(checker: Checker) -> bool:
    """处理广告进度"""
    for pattern, item in checker.matched:
        if pattern.pattern == r"广告剩余(?P<seconds>\d+)秒":
            match = pattern.search(item['t'])
            if match:
                seconds = int(match.group('seconds'))
                Log.i(f"等待{seconds}秒广告结束")
                time.sleep(seconds)
                return True
    return False

def handleAdEnd(checker: Checker) -> bool:
    """处理广告结束"""
    for _, item in checker.matched:
        if "领取成功" in item['t']:
            return CmdMgr.instance().androidServices.click("确定")
    return False

class AdTask(Task):
    """广告任务类,用于执行广告观看任务"""
    
    def __init__(self, appName: str):
        super().__init__(appName, "广告任务")
        
        # 添加启动阶段检查
        self.addStartCheck(
            Checker.create("观看广告|点击观看")
        )
        
        # 添加执行阶段检查
        self.addDoCheck(
            Checker.create([
                r"广告剩余(?P<seconds>\d+)秒",
                r"正在播放广告"
            ])
        )
        
        # 添加结束阶段检查
        self.addEndCheck(
            Checker.create("领取成功|观看完成")
        )

    def start(self) -> bool:
        return self.startCheckList[0].check(handleAdStart)
        
    def do(self) -> bool:
        while True:
            if self.doCheckList[0].check(handleAdProgress):
                break
        return True
        
    def end(self) -> bool:
        return self.endCheckList[0].check(handleAdEnd)

#     def start(self) -> bool:
#         """
#         开始广告任务:
#         1. 打开指定应用
#         2. 等待广告入口出现
#         3. 点击广告入口
#         """
#         try:
#             if not super().start():
#                 return False
            
#             # 打开应用
#             if not Cmds.openApp(self.appName):
#                 LogE("AdTask", f"Failed to open app: {self.appName}")
#                 return False
                
#             # 等待并点击广告入口
#             if not self._findAndClickAdEntry():
#                 LogE("AdTask", "Failed to find ad entry")
#                 return False
                
#             LogD("AdTask", "Ad task started successfully")
#             return True
            
#         except Exception as e:
#             LogE("AdTask", f"Start ad task failed: {str(e)}")
#             return False
    
#     def do(self) -> bool:
#         """
#         执行广告任务:
#         1. 等待广告加载
#         2. 检测广告播放状态
#         3. 等待指定时长
#         """
#         try:
#             if not super().do():
#                 return False
            
#             LogD("AdTask", "Watching ad...")
            
#             # 等待广告加载
#             if not self._waitForAdLoading():
#                 return False
                
#             # 等待广告播放完成
#             if not self._waitForAdComplete():
#                 return False
                
#             LogD("AdTask", "Ad watching completed")
#             return True
            
#         except Exception as e:
#             LogE("AdTask", f"Do ad task failed: {str(e)}")
#             return False
    
#     def end(self) -> bool:
#         """
#         结束广告任务:
#         1. 关闭广告
#         2. 领取奖励
#         3. 返回主界面
#         """
#         try:
#             if not super().end():
#                 return False
#             # 关闭广告
#             if not self._closeAd():
#                 return False
                
#             # 领取奖励
#             if not self._claimReward():
#                 return False
                
#             # 返回主界面
#             self.tools.back()
            
#             LogD("AdTask", "Ad task ended successfully")
#             return True
            
#         except Exception as e:
#             LogE("AdTask", f"End ad task failed: {str(e)}")
#             return False
    
#     def _findAndClickAdEntry(self) -> bool:
#         """查找并点击广告入口"""
#         # TODO: 实现查找广告入口的逻辑
#         # 1. 等待广告入口文本/图标出现
#         # 2. 点击广告入口
#         return True
    
#     def _waitForAdLoading(self) -> bool:
#         """等待广告加载完成"""
#         # TODO: 实现等待广告加载的逻辑
#         # 1. 检测加载提示
#         # 2. 等待加载完成
#         return True
    
#     def _waitForAdComplete(self) -> bool:
#         """等待广告播放完成"""
#         # TODO: 实现等待广告完成的逻辑
#         # 1. 检测广告进度
#         # 2. 等待指定时长
#         return True
    
#     def _closeAd(self) -> bool:
#         """关闭广告"""
#         # TODO: 实现关闭广告的逻辑
#         # 1. 查找关闭按钮
#         # 2. 点击关闭按钮
#         return True
    
#     def _claimReward(self) -> bool:
#         """领取广告奖励"""
#         # TODO: 实现领取奖励的逻辑
#         # 1. 等待奖励界面
#         # 2. 点击领取按钮
#         return True 