import re
from datetime import datetime
from logger import Log

class CmdMgr:
    """封装与手机APP交互的基础功能"""
    
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
            self._reg_commands()
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
        for pattern, func in self.registry.items():
            match = re.match(pattern, cmd)
            Log.i(f"匹配: {pattern} =>{cmd} 结果:{match}")
            if match:
                try:
                    params = match.groupdict()
                    return func(**params) if params else func()
                except Exception as e:
                    Log.ex(e, '命令执行错误')
                    return f"命令执行错误: {str(e)}"
        return "未知命令"
        
    def _reg_commands(self):
        """注册基础命令"""
        @self.reg(r'help(?:\s+(?P<cmd>\w+))?$')
        def cmd_help(cmd=None):
            """显示所有命令和对应的匹配字段"""
            if cmd:
                matched_cmds = []
                for pattern, func in self.registry.items():
                    if cmd.lower() in func.__name__.lower() or cmd.lower() in pattern.lower():
                        matched_cmds.append(f"{func.__name__}: {pattern}")
                if matched_cmds:
                    return "\r\n".join(matched_cmds)  # 使用\r\n确保跨平台兼容
                return f"未找到包含 '{cmd}' 的命令"
            else:
                cmds = []
                for pattern, func in self.registry.items():
                    cmds.append(f"{func.__name__}: {pattern}")
                return "\n".join(cmds)  # 使用\r\n确保跨平台兼容

# 创建全局命令处理器实例
cmdMgr = CmdMgr()
doCmd = cmdMgr.do
regCmd = cmdMgr.reg
