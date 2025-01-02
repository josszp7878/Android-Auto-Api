from CmdMgr import cmdMgr, regCmd
from datetime import datetime
from logger import Log


@regCmd(r'getinfo')
def cmd_getinfo():
    """获取设备信息"""
    return {
        'device': 'Android Device',
        'version': '1.0.0',
        'timestamp': str(datetime.now())
    }

@regCmd(r'time')
def cmd_time():
    """获取当前时间"""
    return str(datetime.now())


@regCmd(r"点击\s+(?P<x>\d+)\s+(?P<y>\d+)")
def click(x, y):
    x, y = int(x), int(y)
    result = cmdMgr.Android.clickPosition(x, y)
    return f"点击位置 ({x}, {y}) 结果: {result}"


@regCmd(r"返回")
def go_back():
    return cmdMgr.Android.goBack()
    
@regCmd(r"屏幕内容")
def getScreenText():
    return cmdMgr.Android.getScreenText()
    
@regCmd(r"主屏幕")
def go_home():
    return cmdMgr.Android.goHome()
    
@regCmd(r"检查安装\s+(?P<pkgName>\S+)")
def isInstalled(pkgName):
    return cmdMgr.Android.isAppInstalled(pkgName)
    
@regCmd(r"安装\s+(?P<pkgName>\S+)")
def install(pkgName):
    return cmdMgr.Android.installApp(pkgName)
    
@regCmd(r"卸载\s+(?P<pkgName>\S+)")
def uninstall(pkgName):
    return cmdMgr.Android.uninstallApp(pkgName)
    
@regCmd(r"启动\s+(?P<pkgName>\S+)")
def start_app(pkgName):
    return cmdMgr.Android.startApp(pkgName)
    
@regCmd(r"停止\s+(?P<pkgName>\S+)")
def stop_app(pkgName):
    return cmdMgr.Android.stopApp(pkgName)
    
@regCmd(r"重启\s+(?P<pkgName>\S+)")
def restart_app(pkgName):
    return cmdMgr.Android.restartApp(pkgName)

@regCmd(r"截图")
def captureScreen():
    return cmdMgr.Android.captureScreen()
