from tasktemplate import TaskTemplate
from task import Task
from checker import Checker
from logger import Log
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

class AdTemplate(TaskTemplate):
    """广告任务模板"""
    
    def init(self, task: Task):
        """初始化广告任务的检查器"""
        # 添加启动阶段检查
        task.addStartCheck(
            Checker.create("观看广告|点击观看")
        )
        
        # 添加执行阶段检查
        task.addDoCheck(
            Checker.create([
                r"广告剩余(?P<seconds>\d+)秒",
                r"正在播放广告"
            ])
        )
        
        # 添加结束阶段检查
        task.addEndCheck(
            Checker.create("领取成功|观看完成")
        )
        
    def start(self, task: Task) -> bool:
        return task.startCheckList[0].check(handleAdStart)
        
    def do(self, task: Task) -> bool:
        while True:
            if task.doCheckList[0].check(handleAdProgress):
                break
        return True
        
    def end(self, task: Task) -> bool:
        return task.endCheckList[0].check(handleAdEnd) 