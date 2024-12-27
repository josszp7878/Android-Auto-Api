from CmdMgr import cmdMgr, regCmd

@regCmd(r"点击\s+(?P<x>\d+)\s+(?P<y>\d+)")
def click(x, y):
    cmdMgr.click(x, y)

@regCmd(r"返回")
def go_back():
    cmdMgr.goBack()
    
@regCmd(r"屏幕内容")
def getScreenText():
    cmdMgr.getScreenText()
    
@regCmd(r"主屏幕")
def go_home():
    cmdMgr.goHome()
    
@regCmd(r"检查安装\s+(?P<pkgName>\S+)")
def isInstalled(pkgName):
    cmdMgr.isInstalled(pkgName)
    
@regCmd(r"安装\s+(?P<pkgName>\S+)")
def install(pkgName):
    cmdMgr.install(pkgName)
    
@regCmd(r"卸载\s+(?P<pkgName>\S+)")
def uninstall(pkgName):
    cmdMgr.uninstall(pkgName)
    
@regCmd(r"启动\s+(?P<pkgName>\S+)")
def start_app(pkgName):
    cmdMgr.startApp(pkgName)
    
@regCmd(r"停止\s+(?P<pkgName>\S+)")
def stop_app(pkgName):
    cmdMgr.stopApp(pkgName)
    
@regCmd(r"重启\s+(?P<pkgName>\S+)")
def restart_app(pkgName):
    cmdMgr.restartApp(pkgName)

@regCmd(r"截图")
def captureScreen():
    cmdMgr.captureScreen()
