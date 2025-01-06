import re
from logger import Log
from tools import Tools


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
                    #print(f"模式匹配到命令名: {cmdName} -> {f.__name__} param_pattern: {p}")
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

        except Exception as e:
            Log.ex(e, f'{cmd}命令执行错误')
            return "e##Error"
        
############################################################
#工具方法
############################################################
    def isHarmonyOS(self) -> bool:
        """检查是否是鸿蒙系统"""
        try:
            # 检查系统属性中是否包含鸿蒙特征
            manufacturer = Build.MANUFACTURER.lower()
            return "huawei" in manufacturer or "honor" in manufacturer
        except Exception as e:
            print(e, '检查系统类型失败')
            return False

    def openApp(self, app_name: str) -> bool:
        """智能打开应用，根据系统类型选择不同的打开方式
        
        Args:
            app_name: 应用名称
            go_back: 是否在打开后返回
            
        Returns:
            bool: 是否成功打开
        """
        Log.i(Tools.TAG, f"Opening app: {app_name}")
        
        try:
            # 检查系统类型
            if self.isHarmonyOS():
                Log.i(Tools.TAG, "Using HarmonyOS method (click)")
                return self._openAppByClick(app_name)
            else:
                Log.i(Tools.TAG, "Using Android method (service)")
                return PythonServices.openApp(app_name)
        except Exception as e:
            Log.ex(e, '打开应用失败')
            return False

    def _openAppByClick(self, app_name: str) -> bool:
        """通过点击方式打开应用（原来的实现移到这里）"""
        try:
            if not PythonServices.goHome():
                Log.ex(e, '返回主页失败')
                return False
                
            time.sleep(0.5)
            
            nodes = PythonServices.findTextNodes()
            targetNode = next((node for node in nodes if app_name in node.getText()), None)
            
            if not targetNode:
                Log.e(Tools.TAG, f"App icon not found: {app_name}")
                return False
            
            bounds = targetNode.getBounds()
            if not PythonServices.clickPosition(bounds.centerX(), bounds.centerY()):
                Log.e(Tools.TAG, "Failed to click app icon")
                return False
            return True
            
        except Exception as e:
            Log.ex(e, '通过点击打开应用失败')
            return False        


# 创建全局单例实例
cmdMgr = CmdMgr()
regCmd = cmdMgr.reg

