from datetime import datetime
from logger import Log, requireAndroid
from CDevice import CDevice
from tools import Tools
from CmdMgr import regCmd


@regCmd(r'aa')
def cmdAa():
    """获取设备信息"""
    Log.d("cmdAa")


@regCmd(r'信息')
def info():
    """获取设备信息"""
    return {
        'device': 'Android Device',
        'version': '1.0.0',
        'timestamp': str(datetime.now())
    }


@regCmd(r'时间')
def time():
    """获取当前时间"""
    return str(datetime.now())


@regCmd(r'状态')
def status():
    """查看设备状态"""
    device = CDevice.instance()
    status = "已连接" if device.connected else "未连接"
    return f'设备状态: {status}'


@regCmd(r'断开')
def disconnect():
    """断开连接"""
    device = CDevice.instance()
    device.disconnect()
    return "已断开连接"


@regCmd(r'连接(?:\s+(?P<server_url>\S+))?')
def connect(server_url=None):
    """连接服务器"""
    device = CDevice.instance()
    if device.connect(server_url):
        return "连接成功"
    return "连接失败"


@regCmd(r'日志', r'(?P<level>[iwe])\s+(?P<content>.+)')
def log(level, content):
    if level not in ['i', 'w', 'e']:
        return "日志级别必须是 i/w/e 之一"
    if level == 'i':
        Log.i(content)
    elif level == 'w':
        Log.w(content)
    else:
        Log.e(content)


@regCmd(r'登录')
def login():
    """登录设备"""
    device = CDevice.instance()
    if device.login():
        return "登录成功"
    return "登录失败"


@regCmd(r'登出')
def logout():
    """登出设备"""
    device = CDevice.instance()
    device.logout()
    return "已登出"


@regCmd(r'连接状态')
def isConnect():
    """检查连接状态"""
    device = CDevice.instance()
    if device.connected:
        return f"已连接到服务器，设备ID: {device.deviceID}"
    return "未连接到服务器"


@regCmd(r'点击', r'(?P<x>\d+)\D+(?P<y>\d+)')
@requireAndroid
def click(x, y):
    x, y = int(x), int(y)
    result = Log().Android().clickPosition(x, y)
    return f"点击位置 ({x}, {y}) 结果: {result}"


@regCmd(r'返回')
@requireAndroid
def goBack():
    return Log().Android().goBack()


@regCmd(r'屏幕内容')
@requireAndroid
def screenText():
    return Log().Android().getScreenText()


@regCmd(r'主屏幕')
@requireAndroid
def goHome():
    return Log().Android().goHome()


@regCmd(r'检查安装\s+(?P<pkgName>\S+)')
@requireAndroid
def isInstalled(pkgName):
    return Log().Android().isAppInstalled(pkgName)


@regCmd(r'安装\s+(?P<pkgName>\S+)')
@requireAndroid
def install(pkgName):
    return Log().Android().installApp(pkgName)


@regCmd(r'卸载\s+(?P<pkgName>\S+)')
@requireAndroid
def uninstall(pkgName):
    return Log().Android().uninstallApp(pkgName)


@regCmd(r'启动', r'(?P<pkgName>\S+)')
@requireAndroid
def startApp(pkgName):
    return Log().Android().startApp(pkgName)


@regCmd(r'停止', r'(?P<pkgName>\S+)')
@requireAndroid
def stopApp(pkgName):
    return Log().Android().stopApp(pkgName)


@regCmd(r'重启', r'(?P<pkgName>\S+)')
@requireAndroid
def restartApp(pkgName):
    return Log().Android().restartApp(pkgName)


@regCmd(r'截图')
@requireAndroid
def captureScreen():
    return Log().Android().captureScreen()


@regCmd(r'热加载', r'(?P<module_name>\w+)')
def reload(module_name):
    """热加载指定模块
    用法: reload <module_name>
    示例: 
        reload Cmds  # 重新加载命令模块
        reload CmdMgr  # 重新加载命令管理器
    """
    print(f"热加载模块: {module_name}")
    try:
        if Tools().reloadModule(module_name):
            return f"模块 {module_name} 重新加载成功ee"
        return f"模块 {module_name} 重新加载失败"
    except Exception as e:
        Log.ex(e, f"重新加载模块失败: {module_name}")
        return f"重新加载失败: {str(e)}"


def OnReload():
    Log.w("Cmds模块热更新 OnReload")

def OnPreload():
    Log.w("Cmds模块热更新 onPreload")


