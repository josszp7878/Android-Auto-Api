import re
import _Log
import _G
import sys
import importlib
from typing import List, Any, Tuple

class Cmd:
    """命令类，存储命令信息"""
    
    def __init__(self, func, alias=None, sAlias=None, param=None, doc=None, is_full_pattern=False):
        self.func = func      # 命令函数
        self.param = param    # 参数匹配模式
        self.alias = alias or func.__name__  # 命令别名，默认为函数名
        self.sAlias = sAlias  # 命令缩写别名
        self.doc = doc or func.__doc__      # 命令文档
        self.module = func.__module__       # 命令所属模块
        self.name = func.__name__           # 函数名
        self.is_full_pattern = is_full_pattern  # 是否为完整正则模式
        
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
    def reg(cls, alias=None, param=None, sAlias=None):
        """注册命令
        
        Args:
            alias: 命令别名或完整正则表达式
            sAlias: 命令缩写别名
            param: 参数匹配模式，默认为None
        
        支持两种模式：
        1. 传统模式：alias为命令前缀，param为参数正则
        2. 完整模式：当alias以"(?P<"开头时，视为完整正则表达式
        """
        # 如果第一个参数是函数，说明装饰器没有参数
        if callable(alias):
            func = alias
            # 清除同名或同模块同函数名的旧命令
            cls._clearOldCommand(func.__name__, func.__module__, func.__name__)
            # 创建命令对象并添加到注册表
            cmd = Cmd(func=func)
            cls.cmdRegistry.append(cmd)
            return func
        
        # 如果第一个参数不是函数，说明装饰器有参数
        def decorator(func):
            # 清除同名或同模块同函数名的旧命令
            cls._clearOldCommand(alias, func.__module__, func.__name__)
            
            # 判断是否为完整正则模式
            is_full_pattern = alias and alias.startswith("(?P<")
            
            # 创建命令对象并添加到注册表
            cmd = Cmd(
                func=func, 
                alias=alias, 
                sAlias=sAlias,
                param=param, 
                doc=func.__doc__, 
                is_full_pattern=is_full_pattern
            )
            
            # 完整正则模式的命令放在前面，优先匹配
            if is_full_pattern:
                cls.cmdRegistry.insert(0, cmd)
            else:
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
        if not cmdName:
            return None
        
        cmdName = cmdName.lower()
        
        # 1. 精确匹配别名
        for cmd in cls.cmdRegistry:
            if cmd.alias.lower() == cmdName:
                return cmd
        
        # 2. 匹配缩写别名
        for cmd in cls.cmdRegistry:
            if cmd.sAlias and cmd.sAlias.lower() == cmdName:
                return cmd
        
        # 3. 匹配函数名
        for cmd in cls.cmdRegistry:
            if cmd.name.lower() == cmdName:
                return cmd
        
        # 4. 匹配函数名缩写
        for cmd in cls.cmdRegistry:
            if cmd.sName.lower() == cmdName:
                return cmd
        
        return None
    
    @classmethod
    def do(cls, cmdStr, data=None)->Tuple[Any, str]:
        """执行命令
        
        Args:
            cmdStr: 命令字符串
            data: 额外的数据参数
        
        Returns:
            Tuple[Any, str]: 命令执行结果和命令名称
        """
        g = _G._G_
        log = g.Log()
        
        try:
            # 先尝试完整正则模式匹配
            for cmd in cls.cmdRegistry:
                if cmd.is_full_pattern:
                    match = re.fullmatch(cmd.alias, cmdStr)
                    if match:
                        # 提取命名捕获组作为参数
                        kwargs = match.groupdict()
                        if data:
                            kwargs['data'] = data
                        return cmd.func(**kwargs), cmd.name
            
            # 再尝试传统模式匹配
            for cmd in cls.cmdRegistry:
                if not cmd.is_full_pattern:
                    # 匹配命令前缀
                    pattern = rf"^({cmd.alias}|{cmd.sAlias})\b" if cmd.sAlias else rf"^{cmd.alias}\b"
                    match = re.match(pattern, cmdStr)
                    if match:
                        # 提取参数部分
                        paramPart = cmdStr[match.end():].strip()
                        
                        # 如果有参数模式，则匹配参数
                        if cmd.param:
                            paramMatch = re.fullmatch(cmd.param, paramPart)
                            if not paramMatch:
                                return f"参数格式错误，正确格式：{cmd.param}", cmd.name
                            
                            # 提取参数
                            kwargs = paramMatch.groupdict()
                            if data:
                                kwargs['data'] = data   
                            return cmd.func(**kwargs), cmd.name
                        else:
                            # 无参数
                            return cmd.func(), cmd.name
            
            return "未知命令", None
        except Exception as e:
            log.ex(e, f"执行命令出错: {cmdStr}")
            return f"执行出错: {str(e)}", None
        
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
                if hasattr(oldCls, 'onUnload'):
                    oldCls.onUnload()
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
    def _reset(cls)->bool:
        g = _G._G_
        log = g.Log()
        """重新加载所有脚本并重启脚本引擎"""
        try:
            if g.isServer():
                log.i("当前是服务器，不支持RESET")
                return False
            # 创建一个事件来等待脚本更新完成
            log.i("开始重载所有脚本...")
            
            # 调用更新脚本方法
            log.i("正在更新脚本...")
            downAll = g.CFileServer().downAll()
            downAll.join()
            log.i("脚本更新完成")
            
            log.i("正在结束客户端...")
            CDevice = g.CDevice()
            Client = g.CClient()
            if Client:
                try:
                    Client.End()
                except Exception as e:
                    _Log._Log_.ex(e, "结束客户端失败")
            
            # 获取当前设备ID和服务器地址
            deviceID = CDevice.deviceID()
            server = CDevice.server()
            log.i(f"当前设备ID: {deviceID}, 服务器地址: {server}")

            log.i("正在清除模块缓存...")
            cls.clearModules()

            CMain = importlib.import_module("CMain")
            importlib.reload(CMain)            
            log.i(f"222当前设备ID: {deviceID}, 服务器地址: {server}")
            if deviceID:
                # 重新初始化客户端
                log.i("重启客户端...")
                CMain.Begin(deviceID, server)
            else:
                _Log._Log_.e("无法获取设备ID或服务器地址")
        except Exception as e:
            _Log._Log_.ex(e, "脚本全量重载失败")

    @classmethod
    def clearModules(cls):
        try:
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
        except Exception as e:
            _Log._Log_.ex(e, "清除模块缓存失败")

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
        @cls.reg(r"重启", sAlias="cq")
        def reset():
            """功能：重新加载所有脚本并重启脚本引擎
            指令名：reloadAll
            中文名：重启
            参数：无
            示例：重启
            """
            return cls._reset()
        
        @cls.reg(r"加载", r"(?P<moduleName>\S+)", sAlias="jz")
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
                return "e-找不到模块"
            # 检查是否需要下载最新版本
            moduleFile = f"scripts/{moduleName}.py"
            if not g.isServer():
                # 先下载最新版本，然后在回调中重新加载
                try:
                    g.CFileServer().download(
                        moduleFile, 
                        lambda success: cls._reloadModule(moduleName)
                    )
                except Exception as e:
                    log.ex(e, f"下载模块失败: {moduleFile}")
                    cls._reloadModule(moduleName)
            else:
                # 如果没有文件服务器，直接重载
                cls._reloadModule(moduleName)
        
        @cls.reg(r"命令列表", sAlias="mllb")
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
        
        @cls.reg(r"帮助", r"(?P<command>\S+)?", sAlias="bz")
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
