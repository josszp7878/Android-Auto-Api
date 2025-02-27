from logger import Log
from CmdMgr import cmdMgr, regCmd
from CCmds import *

# 注册复合命令
@regCmd(r"打开快手极速版")
def runCC():
    goHome()
    time.sleep(1)
    if not click("快手极速版"):
        Log.e("点击快手极速版失败")
        return
    time.sleep(1)
    if not click("钱", (0, 100)):
        Log.e("点击钱失败")
        return
    time.sleep(1)
    if not inRect("任务中心", (-1, 0, 100, 300)):
        Log.e("打开任务中心失败")
        return
    return "打开快手极速版完成"
