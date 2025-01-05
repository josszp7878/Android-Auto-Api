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
            self.cmdRegistry = {}     # 命令注册表 {cmd_pattern: (func, param_pattern)}
            self.nameRegistry = {}    # 方法名匹配表 {method_name: (func, param_pattern)}
            self.initialized = True
    
    def init(self):
        self.RunFromApp = False
        try:
            from java import jclass
            self._android = jclass("cn.vove7.andro_accessibility_api.demo.script.PythonServices")
            self.RunFromApp = True
        except ImportError:
            self._android = None
        Log.d(f"初始化命令管理器... RunFromApp: {self.RunFromApp}")  # 调试输出
            
    @property 
    def Android(self):
        return self._android

    def reg(self, cmd_pattern, param_pattern=None):
        """注册命令"""
        # 如果第一个参数是函数，说明装饰器没有参数
        if callable(cmd_pattern):
            func = cmd_pattern
            self.cmdRegistry[func.__name__] = (func, None)
            self.nameRegistry[func.__name__.lower()] = (func, None)
            # print(f"注册命令: {func.__name__} -> {func.__name__}, 无参数")
            return func
        
        def decorator(func):
            cmd_tuple = (func, param_pattern)
            self.cmdRegistry[cmd_pattern] = cmd_tuple
            self.nameRegistry[func.__name__.lower()] = cmd_tuple
            # print(f"注册命令: {cmd_pattern} -> {func.__name__}, 参数模式: {param_pattern}")
            # print(f"命令注册表: {self.cmdRegistry}")
            # print(f"方法名注册表: {self.nameRegistry}")
            return func
        return decorator
    
    def do(self, cmd):
        """执行命令"""
        cmd = cmd.strip()
        if not cmd:
            return "w##空命令"
            
        # 分割命令名和参数
        cmdParts = cmd.split(None, 1)
        cmdName = cmdParts[0].lower()
        cmdArgs = cmdParts[1] if len(cmdParts) > 1 else ""

        try:
            # print("\n当前命令注册表:")
            # for k, v in self.cmdRegistry.items():
            #     print(f"  {k}: ({v[0].__name__}, {v[1]})")
            # print("\n当前方法名注册表:")
            # for k, v in self.nameRegistry.items():
            #     print(f"  {k}: ({v[0].__name__}, {v[1]})")

            # 1. 查找匹配的命令
            func = param_pattern = None
            
            # 先尝试正则命令名匹配
            for pattern, (f, p) in self.cmdRegistry.items():
                if re.match(f"^{pattern}$", cmdName):
                    func, param_pattern = f, p
                    print(f"模式匹配到命令名: {cmdName} -> {f.__name__} param_pattern: {p}")
                    break
                
            # 再尝试方法名模糊匹配
            if not func:
                for name, (f, p) in self.nameRegistry.items():
                    if name.startswith(cmdName):
                        func, param_pattern = f, p
                        # print(f"模糊匹配到命令名: {cmdName} -> {f.__name__} param_pattern: {p}")
                        break
            
            if not func:
                return "w##未知命令"
            # 2. 验证参数
            if not param_pattern:
                return func() if not cmdArgs else "w##该命令不支持参数"
            
            match = re.match(f"^{param_pattern}$", cmdArgs)
            if not match:
                return "w##参数格式错误"
            
            return func(**match.groupdict())

        except AttributeError as e:
            if not self.RunFromApp:
                return f"w##当前客户端是测试模式，不支持设备接口调用：{cmd}"
            Log.ex(e, '命令执行错误')
            return "e##命令执行错误"
        except Exception as e:
            Log.ex(e, '命令执行错误')
            return "e##命令执行错误"


# 创建全局单例实例
cmdMgr = CmdMgr()
regCmd = cmdMgr.reg


# 命令定义
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
def click(x, y):
    x, y = int(x), int(y)
    result = cmdMgr.Android.clickPosition(x, y)
    return f"点击位置 ({x}, {y}) 结果: {result}"

@regCmd(r'返回')
def goBack():
    return cmdMgr.Android.goBack()
    
@regCmd(r'屏幕内容')
def screenText():
    return cmdMgr.Android.getScreenText()
    
@regCmd(r'主屏幕')
def goHome():
    return cmdMgr.Android.goHome()
    
@regCmd(r'检查安装\s+(?P<pkgName>\S+)')
def isInstalled(pkgName):
    return cmdMgr.Android.isAppInstalled(pkgName)
    
@regCmd(r'安装\s+(?P<pkgName>\S+)')
def install(pkgName):
    return cmdMgr.Android.installApp(pkgName)
    
@regCmd(r'卸载\s+(?P<pkgName>\S+)')
def uninstall(pkgName):
    return cmdMgr.Android.uninstallApp(pkgName)
    
@regCmd(r'启动', r'(?P<pkgName>\S+)')
def startApp(pkgName):
    return cmdMgr.Android.startApp(pkgName)
    
@regCmd(r'停止', r'(?P<pkgName>\S+)')
def stopApp(pkgName):
    return cmdMgr.Android.stopApp(pkgName)
    
@regCmd(r'重启', r'(?P<pkgName>\S+)')
def restartApp(pkgName):
    return cmdMgr.Android.restartApp(pkgName)

@regCmd(r'截图')
def captureScreen():
    return cmdMgr.Android.captureScreen()

