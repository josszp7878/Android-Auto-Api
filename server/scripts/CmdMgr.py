import re
try:
    from logger import Log
except:
    from scripts.logger import Log
import sys
import importlib
from typing import Dict, Tuple, Callable, Optional


class CmdMgr:
    """命令管理器"""
    
    _instance = None  # 单例实例
    
    # 直接使用类属性
    cmdRegistry: Dict[str, Tuple[Callable, Optional[str]]] = {}
    nameRegistry: Dict[str, Tuple[Callable, Optional[str]]] = {}
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CmdMgr, cls).__new__(cls)
        return cls._instance
    
    def reg(self, cmd_pattern, param_pattern=None, description=None):
        """注册命令
        
        Args:
            cmd_pattern: 命令模式或函数
            param_pattern: 参数匹配模式，默认为None
            description: 命令描述，默认为None
        """
        # 如果第一个参数是函数，说明装饰器没有参数
        if callable(cmd_pattern):
            func = cmd_pattern
            CmdMgr.cmdRegistry[func.__name__] = (func, None, None)
            CmdMgr.nameRegistry[func.__name__.lower()] = (func, None, None)
            return func
        
        def decorator(func):
            cmd_tuple = (func, param_pattern, description)
            CmdMgr.cmdRegistry[cmd_pattern] = cmd_tuple
            CmdMgr.nameRegistry[func.__name__.lower()] = cmd_tuple
            return func
        return decorator
    
    def clear(self):
        """清除命令"""
        CmdMgr.cmdRegistry.clear()
        CmdMgr.nameRegistry.clear()
    
    def do(self, command, sender=None, data=None):
        """执行命令"""
        cmd = command.strip()
        if not cmd:
            return "w##空命令", None
            
        cmdParts = cmd.split(None, 1)
        cmdName = cmdParts[0].lower()
        cmdArgs = cmdParts[1] if len(cmdParts) > 1 else ""
        
        try:
            func = param_pattern = None
            # 按命令模式匹配
            for pattern, (f, p, _) in CmdMgr.cmdRegistry.items():
                if re.match(f"^{pattern}$", cmdName):
                    func, param_pattern = f, p
                    break
            # 按命令名称匹配
            Log.d(f'按命令名称匹配: {cmdName}=> {func} {param_pattern}')
            if not func:
                for name, (f, p, _) in CmdMgr.nameRegistry.items():
                    if name.startswith(cmdName):
                        func, param_pattern = f, p
                        break
            Log.d(f'按命令名称匹配: {cmdName}=> {func} {param_pattern}')
            if not func:
                return "w##未知命令", None
            if not param_pattern:
                return (func(data) if not cmdArgs else "w##该命令不支持参数"), func.__name__
            
            match = re.match(f"^{param_pattern}$", cmdArgs)
            if not match:
                return "w##参数格式错误", func.__name__
            
            # 将 data 参数添加到 match.groupdict() 中
            params = match.groupdict()
            if data is not None:
                params['data'] = data
            
            return func(**params), func.__name__
            
        except Exception as e:
            Log.ex(e, f'{cmd}命令执行错误')
            return "e##Error", None


# 创建全局单例实例
cmdMgr = CmdMgr()
regCmd = cmdMgr.reg


#热加载
@classmethod
def loadModule(cls, module_name: str) -> bool:
    """处理模块重新加载
    Args:
        module_name: 模块名称
        log: 日志实例
    Returns:
        bool: 是否重载成功
    """
    try:
        if module_name in sys.modules:
            module = sys.modules[module_name]
            # 执行预加载
            if hasattr(module, 'OnPreload'):
                module.OnPreload()
            
            # 获取所有引用了该模块的模块
            referrers = [m for m in sys.modules.values() 
                        if m and hasattr(m, '__dict__') and module_name in m.__dict__]
            
            # 重新加载模块
            del sys.modules[module_name]
            # 强制重新从文件加载模块
            spec = importlib.util.find_spec(module_name)
            if not spec:
                Log.e(f"找不到模块: {module_name}")
                return False
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 更新引用
            for referrer in referrers:
                if hasattr(referrer, '__dict__'):
                    referrer.__dict__[module_name] = module
            
            # 执行重载后回调
            if hasattr(module, 'OnReload'):
                module.OnReload()
            Log.i(f"重新加载模块成功: {module_name}")
        else:
            # 首次加载直接使用import_module
            module = importlib.import_module(module_name)
            Log.i(f"首次加载模块成功: {module_name}")
        
        return True
    except Exception as e:
        Log.ex(e, f"加载模块失败: {module_name}")
        return False

# 添加reload命令
@regCmd(r"加载", r"(?P<module_name>\w+)?")
def reload(module_name):
    print(f"热加载模块1: {module_name}")
    modules = []
    
    import os
    import importlib.util
    # 获取客户端和服务器端脚本路径
    scriptsDir = os.path.dirname(__file__)    
    # 尝试获取CCmds模块路径(客户端)
    try:
        ccmds_spec = importlib.util.find_spec('SCmds' if Log.IsServer else 'CCmds')
        if ccmds_spec:
            scriptsDir.append(os.path.dirname(ccmds_spec.origin))
    except:
        pass
    # 获取所有脚本文件
    files = [f for f in os.listdir(scriptsDir) if f.endswith('.py') and f != '__init__.py']
    if not module_name:
        modules = files
    else:
        # 使用 next 和生成器表达式来查找模块
        module = next((x for x in files if x.lower() == module_name.lower() + '.py'), None)
        if module:
            modules.append(module)
    
    if not modules:
        return "e##未找到热加载模块"

    for script in modules:
        module_name = script[:-3]  # 去掉 .py 后缀
        if Log.IsServer:
            CmdMgr.loadModule(module_name)
        else:
            def onComplete(success):
                if success:
                    CmdMgr.loadModule(module_name)
                else:
                    Log.e(f"下载失败: {module_name}")
            from CFileServer import fileServer
            return fileServer.download(f"{module_name}.py", onComplete)
       
# 模块级别的热更新回调函数
def OnPreload():
    """热更新前保存当前命令注册状态到sys.modules"""
    try:
        # 保存到sys.modules['__main__']中
        main = sys.modules['__main__']
        if not hasattr(main, 'cmds'):
            main.cmds = {}
            main.names = {}
        
        # 保存当前注册表
        main.cmds.update(CmdMgr.cmdRegistry)
        main.names.update(CmdMgr.nameRegistry)
        Log.i("CmdMgr保存命令注册状态到sys.modules")
        return True
    except Exception as e:
        Log.ex(e, "保存命令注册状态失败")
        return False

def OnReload():
    """热更新后从sys.modules恢复命令注册状态"""
    try:
        # 从sys.modules['__main__']恢复
        main = sys.modules['__main__']
        if hasattr(main, 'cmds'):
            CmdMgr.cmdRegistry.update(main.cmds)
            CmdMgr.nameRegistry.update(main.names)
            Log.i("CmdMgr从sys.modules恢复命令注册状态")
            
            # 清理保存的状态
            delattr(main, 'cmds')
            delattr(main, 'names')
        return True
    except Exception as e:
        Log.ex(e, "恢复命令注册状态失败")
        return False 