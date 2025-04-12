import time
import _Log
import _G
from _CmdMgr import regCmd
from CCmds import CCmds_

class CScripts_:

    @classmethod
    def onUnload(cls):
        log = _G._G_.Log()
        log.i("CScripts_模块预加载")
        cls.registerCommands()

    @classmethod
    def registerCommands(cls):
        # 注册复合命令
        @regCmd(r"#打开快手极速版")
        def runCC():
            from CApp import CApp_
            CApp_.goHome()
            time.sleep(1)
            tools = _G._G_.Tools()
            if not tools.click("快手极速版"):
                _Log._Log_.e("点击快手极速版失败")
                return
            time.sleep(1)
            if not tools.click("钱", (0, 100)):
                _Log._Log_.e("点击钱失败")
                return
            time.sleep(1)
            if not tools.inRect("任务中心", (-1, 0, 100, 300)):
                _Log._Log_.e("打开任务中心失败")
                return
            return "打开快手极速版完成"
