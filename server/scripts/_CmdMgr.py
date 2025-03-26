import re
import _Log
import _G
import sys
import importlib
from typing import List

class Cmd:
    """命令类，存储命令信息"""
    
    def __init__(self, func, param=None, alias=None, doc=None):
        self.func = func      # 命令函数
        self.param = param    # 参数匹配模式
        self.alias = alias or func.__name__  # 命令别名，默认为函数名
        self.doc = doc or func.__doc__      # 命令文档
        self.module = func.__module__       # 命令所属模块
        self.name = func.__name__           # 函数名
        
        # 解析别名中的拼音首字母缩写（格式：别名-缩写）
        self.sAlias = ""
        if self.alias and "-" in self.alias:
            parts = self.alias.split("-", 1)
            if len(parts) == 2:
                self.alias = parts[0].strip()
                self.sAlias = parts[1].strip().lower()
        
        # 生成函数名首字母+大写字母缩写
        self.sName = self._getNameShortcut(self.name).lower()
    
    def _getNameShortcut(self, name):
        """获取函数名首字母+大写字母缩写"""
        if not name:
            return ""
        
        try:
            # 获取首字母
            shortcut = name[0]
            # 添加其他大写字母
            for char in name[1:]:
                if char.isupper():
                    shortcut += char.lower()
            return shortcut
        except Exception as e:
            _Log._Log_.ex(e, f"获取函数名缩写失败: {name}")
            return ""


class _CmdMgr_:
    """命令管理器"""
    
    _instance = None  # 单例实例
    
    # 使用列表存储命令
    cmdRegistry: List[Cmd] = []
    
    @classmethod
    def reg(cls, alias=None, param=None):
        """注册命令
        
        Args:
            alias: 命令别名，可以使用 "别名-缩写" 格式指定拼音首字母缩写
            param: 参数匹配模式，默认为None
        """
        # 如果第一个参数是函数，说明装饰器没有参数
        if callable(alias):
            func = alias
            # 清除同名或同模块同函数名的旧命令
            cls._clearOldCommand(func.__name__, func.__module__, func.__name__)
            # 创建命令对象并添加到注册表
            cmd = Cmd(func)
            cls.cmdRegistry.append(cmd)
            return func
        
        # 如果第一个参数不是函数，说明装饰器有参数
        def decorator(func):
            # 清除同名或同模块同函数名的旧命令
            cls._clearOldCommand(alias, func.__module__, func.__name__)
            # 创建命令对象并添加到注册表
            cmd = Cmd(func, param, alias, func.__doc__)
            cls.cmdRegistry.append(cmd)
            return func
        return decorator
    
    @classmethod
    def _clearOldCommand(cls, alias, module_name, func_name):
        """清除旧命令
        
        Args:
            alias: 命令别名
            module_name: 模块名
            func_name: 函数名
        """
        # 处理别名中可能包含的缩写
        if alias and "-" in alias:
            alias = alias.split("-", 1)[0]
            
        # 使用列表推导式过滤掉要删除的命令
        cls.cmdRegistry = [
            cmd for cmd in cls.cmdRegistry 
            if not (cmd.alias == alias or 
                   (cmd.module == module_name and cmd.name == func_name))
        ]
    
    @classmethod
    def clear(cls):
        """清除命令"""
        cls.cmdRegistry.clear()

    @classmethod
    def _findCommand(cls, cmdName):
        """查找命令
        
        Args:
            cmdName: 命令名称
            
        Returns:
            Cmd: 找到的命令对象，如果未找到则返回None
        """
        cmdName = cmdName.lower()
        # 1. 先按别名正则匹配
        for cmd in cls.cmdRegistry:
            if re.match(f"^{cmd.alias}$", cmdName):
                return cmd
        
        # 2. 再按函数名精确匹配
        for cmd in cls.cmdRegistry:
            if cmd.name.lower() == cmdName:
                return cmd
        
        # 3. 按拼音首字母缩写匹配
        for cmd in cls.cmdRegistry:
            if cmd.sAlias and cmd.sAlias == cmdName:
                return cmd
        
        # 4. 按函数名首字母+大写字母缩写匹配
        for cmd in cls.cmdRegistry:
            if cmd.sName and cmd.sName == cmdName:
                return cmd
                
        return None
    
    @classmethod
    def do(cls, command, deviceID=None, data=None):
        """执行命令"""
        cmd_text = command.strip()
        if not cmd_text:
            return "w->空命令", None
            
        log = _G._G_.Log()            
        cmdParts = cmd_text.split(None, 1)
        cmdName = cmdParts[0].lower()
        cmdArgs = cmdParts[1] if len(cmdParts) > 1 else None
        if cmdArgs and cmdArgs.strip() == '':
            cmdArgs = None
            
        try:
            # 查找匹配的命令
            cmd = cls._findCommand(cmdName)
            
            # 如果没有找到匹配的命令，返回错误
            if not cmd:
                return "w->未知命令", None
                
            # 如果命令不支持参数但提供了参数，返回错误
            if not cmd.param:
                return (cmd.func() if not cmdArgs else "w##该命令不支持参数"), cmd.name
            
            # 如果没有参数，则使用空字符串
            if cmdArgs is None:
                cmdArgs = ""
            
            # 匹配参数
            match = re.match(f"^{cmd.param}$", cmdArgs, re.DOTALL)
            if not match:
                log.e(f'参数格式错误: {cmdArgs} {cmd.param}')
                return "w->参数格式错误", cmd.name
            
            # 将 data 参数添加到 match.groupdict() 中
            params = match.groupdict()
            import inspect
            sig = inspect.signature(cmd.func)
            if 'data' in sig.parameters:
                params['data'] = data
            if 'deviceID' in sig.parameters:
                params['deviceID'] = deviceID
            
            # 执行命令并返回结果
            log.d(f'执行函数: {cmd.name}, 参数: {params}')
            ret = cmd.func(**params)
            if not isinstance(ret, str):
                ret = str(ret)
            return ret, cmd.name
        except Exception as e:
            log.ex(e, f'{cmd_text}命令执行错误')
            return f"e->{str(e)}", None
        
    @classmethod
    def _reloadModule(cls, moduleName: str) -> bool:
        """处理模块重新加载
        Args:
            module_name: 模块名称，支持带路径的形式(如scripts._Tools)
        Returns:
            bool: 是否重载成功
        """
        g = _G._G_
        log = g.Log()
        try:
            # log.d(f'重新加载模块: {moduleName}')
            # 检查模块是否已加载
            if moduleName in sys.modules:
                module = sys.modules[moduleName]
                oldCls = g.getClass(moduleName)
                # 获取模块对应的类（假设类名为模块名加下划线）
                if hasattr(oldCls, 'OnPreload'):
                    oldCls.OnPreload()
                # 获取所有引用了该模块的模块
                referrers = [
                    m for m in sys.modules.values() 
                    if m and hasattr(m, '__dict__') and moduleName in m.__dict__
                ]
                # 重新加载模块
                del sys.modules[moduleName]
                
                # 强制重新从文件加载模块
                spec = importlib.util.find_spec(moduleName)
                if not spec:
                    log.e(f"找不到模块: {moduleName}")
                    return False
                module = importlib.util.module_from_spec(spec)
                sys.modules[moduleName] = module
                spec.loader.exec_module(module)
                # 更新引用
                for referrer in referrers:
                    if hasattr(referrer, '__dict__'):
                        referrer.__dict__[moduleName] = module
                # 清除全局引用
                g.clear()
                # log.d(f'清除全局引用: {moduleName}')    
                g.CallMethod(module, 'Clone', oldCls)
                g.CallMethod(module, 'OnReload')
            else:
                # 首次加载直接使用import_module
                try:
                    module = importlib.import_module(moduleName)
                except ImportError as e:
                    log.e(f"找不到模块: {moduleName}, 错误: {e}")
                    return False
            
            # 6. 返回成功
            return True
        except Exception as e:
            _Log._Log_.ex(e, f"重新加载模块 {moduleName} 失败")
            return False

    @classmethod
    def _reset(cls):
        g = _G._G_
        log = g.Log()
        """重新加载所有脚本并重启脚本引擎"""
        try:
            if g.isServer():
                return "e->当前是服务器，无需重载脚本"
            # 创建一个事件来等待脚本更新完成
            log.i("开始重载所有脚本...")
            import threading
            update_completed = threading.Event()
            
            def onUpdateCompleted(success):
                if success:
                    _Log._Log_.i("脚本更新完成")
                else:
                    _Log._Log_.e("脚本更新失败")
                update_completed.set()
            
            # 调用更新脚本方法
            log.i("正在更新脚本...")
            g.getClass('CFileServer').downAll(onUpdateCompleted)
            
            # 等待更新完成，最多等待30秒
            if not update_completed.wait(30):
                log.e("脚本更新超时")
                return "e->脚本更新超时，重载失败"
            
            # 2. 清除Python中所有脚本模块并重新加载
            log.i("正在清除模块缓存...")
            # 保存需要重新加载的模块名
            modules_to_reload = []
            for module_name in list(sys.modules.keys()):
                # 只处理我们自己的脚本模块，不处理系统模块
                if (not module_name.startswith('_') and 
                    not module_name.startswith('sys') and 
                    not module_name.startswith('builtins') and
                    not module_name.startswith('java') and
                    not module_name.startswith('importlib') and
                    not module_name.startswith('threading')):
                    
                    # 记录模块名并从sys.modules中移除
                    modules_to_reload.append(module_name)
                    
            # 从sys.modules中移除所有自定义模块
            for module_name in modules_to_reload:
                if module_name in sys.modules:
                    del sys.modules[module_name]
            
            # 3. 重新执行入口函数，重启脚本
            # 先结束当前客户端
            client = _G._G_.getClass('CClient')()
            if client:
                try:
                    client.End()
                except Exception as e:
                    _Log._Log_.ex(e, "结束客户端失败")
            
            # 重新导入CMain模块并执行Begin
            try:
                # 获取当前设备ID和服务器地址
                deviceID = client.deviceID if client else None
                server = client.server if client else None
                
                CMain = importlib.import_module("CMain")
                importlib.reload(CMain)            
                
                if deviceID and server:
                    # 重新初始化客户端
                    CMain.Begin(deviceID, server)
                    return "i->脚本全量重载完成"
                else:
                    _Log._Log_.e("无法获取设备ID或服务器地址")
            except Exception as e:
                _Log._Log_.ex(e, "重启脚本引擎失败")
        except Exception as e:
            _Log._Log_.ex(e, "脚本全量重载失败")
       

    @classmethod
    def regAllCmds(cls):
        """清除已注册的命令并重新注册所有命令
        
        Returns:
            bool: 是否成功
        """
        g = _G._G_
        log = g.Log()
        log.i("开始重新注册命令...")
        try:
            # 1. 清除所有命令注册
            cls.clear()            
            modules = g.getScriptNames()
            success_count = 0
            for module in modules:
                try:
                    # 直接使用模块名，不添加前缀
                    full_module_name = module                    
                    # 加载模块
                    try:
                        if full_module_name not in sys.modules:
                            module = importlib.import_module(full_module_name)
                        else:
                            module = sys.modules[full_module_name]
                    except Exception as e:
                        log.ex(e, f"加载模块失败: {full_module_name}")
                        continue
                    # 查找模块中的registerCommands类方法
                    g.CallMethod(module, 'registerCommands')
                    success_count += 1
                except Exception as e:
                    log.ex(e, f"注册模块 {module} 的命令失败")
            
            # 5. 输出重新注册结果
            cmd_count = len(cls.cmdRegistry)
            log.i(f"命令重新注册完成，成功注册{success_count}/{len(modules)}个模块，"
                 f"共{cmd_count}个命令")
            return success_count == len(modules)
        except Exception as e:
            log.ex(e, "命令重新注册失败")
            return False
    
    @classmethod
    def registerCommands(cls):
        """注册命令管理器自身的命令"""
        @cls.reg(r"重启-cq")
        def reloadAll():
            """功能：重新加载所有脚本并重启脚本引擎
            指令名：reloadAll
            中文名：重启
            参数：无
            示例：重启
            """
            return cls._reset()
        
        @cls.reg(r"加载-jz", r"(?P<moduleName>\S+)")
        def reload(moduleName):
            """功能：重新加载指定模块
            指令名：reload
            中文名：加载
            参数：
              moduleName - 要重载的模块名
            示例：加载 _CmdMgr
            """
            g = _G._G_
            log = g.Log()
            # log.i(f"重新加载模块: {moduleName}")
            moduleName = g.getScriptName(moduleName)
            if not moduleName:
                return "e->找不到模块"
            # 检查是否需要下载最新版本
            moduleFile = f"scripts/{moduleName}.py"
            if not g.isServer():
                # 先下载最新版本，然后在回调中重新加载
                g.CFileServer().download(
                    moduleFile, 
                    lambda success: cls._reloadModule(moduleName)
                )
                ret = True
            else:
                # 如果没有文件服务器，直接重载
                ret = cls._reloadModule(moduleName)
            return ret
        
        @cls.reg(r"命令列表-mllb")
        def cmdList():
            """功能：列出所有可用命令
            指令名：cmdList
            中文名：命令列表
            参数：无
            示例：命令列表
            """
            result = "可用命令:\n"
            for cmd in sorted(cls.cmdRegistry, key=lambda x: x.name):
                result += f"{cmd.name}-{cmd.sName}\t\t: {cmd.alias}-{cmd.sAlias}\n"
            return result
        
        @cls.reg(r"帮助-bz", r"(?P<command>\S+)?")
        def help(command=None):
            """功能：显示命令帮助信息
            指令名：help
            中文名：帮助
            参数：
              command - 要查询的命令名称
            示例：帮助 重启
            """
            if not command:
                return """
                指令使用说明：

                格式：[设备ID][>]指令名 [参数] 
                说明：
                1. 指令名：可以是中文，英文和缩写，统一小写。
                   可用命令列表见下文
                2. 参数：空格于指令名隔开，不同指令有不同参数，
                   具体请调用：help 命令 进行查看
                3. 客户端指令格式：
                   [设备ID]>命令 [参数]
                   其中:设备ID为执行指令的目标设备ID或者分组ID,
                   如果没提供，就表示当前设备
                4. 服务端指令：
                    命令 [参数]
                5. 可用命令:
                    客户端指令列表用：>cl 查询
                    服务端指令列表用：cl 查询
                """
            # 获取命令信息
            cmd_info = cls._findCommand(command)
            if not cmd_info:
                return "e->无效指令"
            # 获取命令的描述
            desc = cmd_info.doc
            return desc


    @classmethod
    def OnReload(cls):
        _Log._Log_.i("CmdMgr模块热更新 重新注册命令")
        # 使用全局命令重新注册机制
        cls.regAllCmds()


# 创建全局单例实例
regCmd = _CmdMgr_.reg
