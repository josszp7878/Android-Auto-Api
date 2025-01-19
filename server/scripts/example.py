from checker import Checker
import time
from logger import Log
from CmdMgr import CmdMgr
from tasktemplate import AdTemplate
from task import Task

def handleMatch(checker: Checker) -> bool:
    """处理匹配成功的回调"""
    # 可以根据匹配到的pattern执行不同操作
    if checker.matchedPattern.pattern == r"领取(?P<amount>\d+)金币":
        amount = checker.matchParams.get('amount')
        Log.i(f"领取了{amount}金币")
        return CmdMgr.instance().androidServices.click("确定")
    elif "广告" in checker.matchText:
        Log.i("检测到广告")
        return True
    return False

# 创建支持多模式的检查器
checker = Checker.create([
    r"领取(?P<amount>\d+)金币",
    r"广告剩余(?P<seconds>\d+)秒",
    r"观看广告"
], handleMatch)

# 或者使用|分隔的字符串
checker2 = Checker.create(
    r"领取(?P<amount>\d+)金币|广告剩余(?P<seconds>\d+)秒|观看广告",
    handleMatch
)

# 在指定区域内检查
region = [100, 200, 500, 800]  # [left, top, right, bottom]
checker3 = Checker.create(
    r"确定|取消", 
    handleMatch,
    region
)

def checkScreen():
    if checker.check():
        Log.i(f"匹配成功: {checker.matchText}")
        Log.i(f"匹配参数: {checker.matchParams}")
        return True
    return False

def waitAd(checker: Checker) -> bool:
    """等待广告结束的操作"""
    seconds = int(checker.matchParams.get('seconds', 0))
    Log.i(f"等待{seconds}秒广告结束")
    time.sleep(seconds)
    return True

# 创建检查器
successChecker = Checker.create(r"领取(?P<amount>\d+)金币成功").action(clickConfirm)
adChecker = Checker.create(r"广告剩余(?P<seconds>\d+)秒").action(waitAd)

def checkAd():
    if successChecker.check():
        return True
        
    if adChecker.check():
        return True
        
    return False 

# 创建任务模板
adTemplate = AdTemplate()

# 创建任务实例时传入模板
task = Task.create("抖音", "广告任务", adTemplate)

# 运行任务
task.run() 