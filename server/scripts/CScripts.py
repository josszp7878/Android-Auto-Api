import time
import _Log
import _G
from CCmds import CCmds_

class CScripts_:


    @classmethod
    def registerCommands(cls):
        from _CmdMgr import regCmd
        # 注册复合命令
        @regCmd(r"#打开快手极速版")
        def runCC():
            from  _App import App_
            App_.goHome()
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
