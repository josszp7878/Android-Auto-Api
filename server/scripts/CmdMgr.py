import re
from datetime import datetime
from logger import Log

# 条件导入 Java 相关模块
try:
    from java import jclass
    PythonServices = jclass("cn.vove7.andro_accessibility_api.demo.script.PythonServices")
except ImportError:
    pass

class CmdMgr:
    """封装与手机APP交互的基础功能"""
    
    _instance = None  # 单例实例

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CmdMgr, cls).__new__(cls, *args, **kwargs)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):  # 确保初始化只执行一次
            self.registry = {}  # 命令注册表
            self._register_commands()
            self.initialized = True
    
    def reg(self, pattern):
        """注册命令"""
        def decorator(func):
            self.registry[pattern] = func
            return func
        return decorator
    
    def do(self, cmd):
        """执行命令"""
        for pattern, func in self.registry.items():
            match = re.match(pattern, cmd)
            Log.i(f"匹配: {pattern} =>{cmd} 结果:{match}")
            if match:
                try:
                    params = match.groupdict()
                    if Log.instance().RunFromApp:
                        return func(**params) if params else func()
                    else:
                        return self.testCall(func, params)
                except Exception as e:
                    Log.e(f"命令执行错误: {str(e)}")
                    return f"命令执行错误: {str(e)}"
        return "未知命令"
    
    def testCall(self, func, params):
        """模拟调用函数"""
        return f"模拟调用函数: {func.__name__} 参数: {params}"
    
    def _register_commands(self):
        """注册所有基础命令"""
        
        @self.reg(r'help')
        def cmd_help():
            """显示帮助信息"""
            return '''可用命令:
- help: 显示本帮助
- getinfo: 获取设备信息
- status: 获取设备状态
- time: 获取当前时间
- echo <message>: 回显消息
- add <x> <y>: 计算两数之和
- screenshot: 获取设备截图'''

        @self.reg(r'getinfo')
        def cmd_getinfo():
            """获取设备信息"""
            return {
                'device': 'Android Device',
                'version': '1.0.0',
                'timestamp': str(datetime.now())
            }

        @self.reg(r'time')
        def cmd_time():
            """获取当前时间"""
            return str(datetime.now())

        def click(x, y):
            try:
                x, y = int(x), int(y)
                result = PythonServices.clickPosition(x, y)
                return f"点击位置 ({x}, {y}) 结果: {result}"
            except Exception as e:
                return f"Error calling clickPosition: {e}"

        def getScreenText():
            try:
                screen_text = PythonServices.getScreenText()
                return f"屏幕文本: {screen_text}"
            except Exception as e:
                return f"Error calling getScreenText: {e}"

        def goBack():
            return PythonServices.goBack()

        def goHome():
            return PythonServices.goHome()

        def isInstalled(pkgName):
            return PythonServices.isAppInstalled(pkgName)

        def startApp(appName):
            return PythonServices.openApp(appName)

        def closeApp(appName):
            return PythonServices.closeApp(appName)

        def install(appName):
            return PythonServices.installApp(appName)

        def uninstall(appName):
            return PythonServices.uninstallApp(appName)

        def captureScreen():
            try:
                result = PythonServices.takeScreenshot()
                return f"截屏结果: {result}"
            except Exception as e:
                return f"Error calling takeScreenshot: {e}"

# 创建全局命令处理器实例
doCmd = CmdMgr().do
regCmd = CmdMgr().reg
cmdMgr = CmdMgr()
