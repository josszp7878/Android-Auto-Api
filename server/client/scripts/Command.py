import re
from functools import wraps
from datetime import datetime
# 条件导入 Java 相关模块
try:
    from java import jclass
    PythonServices = jclass("cn.vove7.andro_accessibility_api.demo.script.PythonServices")
    IN_APP = True
except ImportError:
    IN_APP = False
    
class Command:
    """命令处理类"""
    
    def __init__(self):
        self.registry = {}  # 命令注册表
        self._register_commands()
    
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
            if match:
                try:
                    params = match.groupdict()
                    if IN_APP:
                        return func(**params) if params else func()
                    else:
                        return self.testCall(func, params)
                except Exception as e:
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

        @self.reg(r"点击\s+(?P<x>\d+)\s+(?P<y>\d+)")
        def click(x, y):
            try:
                x, y = int(x), int(y)
                result = PythonServices.clickPosition(x, y)
                return f"点击位置 ({x}, {y}) 结果: {result}"
            except Exception as e:
                return f"Error calling clickPosition: {e}"

        @self.reg(r"屏幕内容")
        def getScreenText():
            try:
                screen_text = PythonServices.getScreenText()
                return f"屏幕文本: {screen_text}"
            except Exception as e:
                return f"Error calling getScreenText: {e}"

        @self.reg(r"返回")
        def go_back():
            return PythonServices.goBack()

        @self.reg(r"主屏幕")
        def go_home():
            return PythonServices.goHome()

        @self.reg(r"检查安装\s+(?P<pkgName>\S+)")
        def is_app_installed(pkgName):
            return PythonServices.isAppInstalled(pkgName)

        @self.reg(r"打开\s+(?P<appName>\S+)")
        def open_app(appName):
            return PythonServices.openApp(appName)

        @self.reg(r"关闭\s+(?P<appName>\S+)")
        def close_app(appName):
            return PythonServices.closeApp(appName)


        @self.reg(r"安装\s+(?P<appName>\S+)")
        def install_app(appName):
            return PythonServices.installApp(appName)

        @self.reg(r"卸载\s+(?P<appName>\S+)")
        def uninstall_app(appName):
            return PythonServices.uninstallApp(appName)

        @self.reg(r"截屏")
        def take_screenshot():
            try:
                result = PythonServices.takeScreenshot()
                return f"截屏结果: {result}"
            except Exception as e:
                return f"Error calling takeScreenshot: {e}"

# 创建全局命令处理器实例
command = Command()
do = command.do

