import re
from datetime import datetime
from logger import Log
from CDevice import CDevice


class CmdMgr:
    """命令管理器"""
    
    _instance = None  # 单例实例
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CmdMgr, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.registry = {}
            # Android服务初始化
            try:
                from java import jclass
                self._android = jclass("cn.vove7.andro_accessibility_api.demo.script.PythonServices")
            except ImportError:
                self._android = None
            self.initialized = True
            
    @property 
    def Android(self):
        return self._android

    def reg(self, pattern):
        """注册命令"""
        def decorator(func):
            self.registry[pattern] = func
            return func
        return decorator
    
    def do(self, cmd):
        """执行命令"""
        cmd = cmd.strip().lower()
        for pattern, func in self.registry.items():
            match = re.match(pattern, cmd)
            if match:
                try:
                    params = match.groupdict()
                    return func(**params) if params else func()
                except Exception as e:
                    Log.ex(e, '命令执行错误')
                    return "e##命令执行错误"
        return "w##未知命令"


# 创建全局命令处理器实例
cmdMgr = CmdMgr()
regCmd = cmdMgr.reg


# 命令定义
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

@regCmd(r'status')
def cmd_status():
    """查看设备状态"""
    device = CDevice.instance()
    status = "已连接" if device.connected else "未连接"
    return f'设备状态: {status}'

@regCmd(r'disconnect')
def cmd_disconnect():
    """断开连接"""
    device = CDevice.instance()
    device.disconnect()
    return "已断开连接"

@regCmd(r'connect(?:\s+(?P<server_url>\S+))?')
def cmd_connect(server_url=None):
    """连接服务器"""
    device = CDevice.instance()
    if device.connect(server_url):
        return "连接成功"
    return "连接失败"

@regCmd(r'log\s+(?P<level>[iwe])\s+(?P<content>.+)')
def cmd_log(level, content):
    """手动打印日志
    用法: log <level> <content>
    level: i/w/e (info/warning/error)
    """
    if level not in ['i', 'w', 'e']:
        return "日志级别必须是 i/w/e 之一"
        
    if level == 'i':
        Log.i(content)
    elif level == 'w':
        Log.w(content)
    else:
        Log.e(content)
    return f"日志已打印: [{level}] {content}"

@regCmd(r'login')
def cmd_login():
    """登录设备"""
    device = CDevice.instance()
    if device.login():
        return "登录成功"
    return "登录失败"

@regCmd(r'logout')
def cmd_logout():
    """登出设备"""
    device = CDevice.instance()
    device.logout()
    return "已登出"

@regCmd(r'isconnect')
def cmd_isconnect():
    """检查连接状态"""
    device = CDevice.instance()
    if device.connected:
        return f"已连接到服务器，设备ID: {device.deviceID}"
    return "未连接到服务器"

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
