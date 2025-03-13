import re
from _Tools import _Tools_
import _Log
import _G
import sys
import importlib
from typing import Dict, Tuple, Callable, Optional, List
import os
import json


class _CmdMgr_:
    """命令管理器"""
    
    _instance = None  # 单例实例
    
    # 直接使用类属性
    cmdRegistry: Dict[str, Tuple[Callable, Optional[str]]] = {}
    
    @classmethod
    def reg(cls, cmd_pattern=None, param_pattern=None):
        """注册命令
        
        Args:
            cmd_pattern: 命令模式或函数
            param_pattern: 参数匹配模式，默认为None
        """
        # 如果第一个参数是函数，说明装饰器没有参数
        if callable(cmd_pattern):
            func = cmd_pattern
            # 清除同名或同模块同函数名的旧命令
            cls._clearOldCommand(func.__name__, func.__module__, func.__name__)
            # 使用函数名作为命令名
            cls.cmdRegistry[func.__name__] = (func, None, func.__doc__)
            return func
        
        # 如果第一个参数不是函数，说明装饰器有参数
        def decorator(func):
            # 清除同名或同模块同函数名的旧命令
            cls._clearOldCommand(cmd_pattern, func.__module__, func.__name__)
            # 使用命令模式作为键
            cmd_tuple = (func, param_pattern, func.__doc__)
            cls.cmdRegistry[cmd_pattern] = cmd_tuple
            return func
        return decorator
    
    @classmethod
    def _clearOldCommand(cls, pattern, module_name, func_name):
        """清除旧命令
        
        Args:
            pattern: 命令模式
            module_name: 模块名
            func_name: 函数名
        """
        # 清除同名命令
        if pattern in cls.cmdRegistry:
            del cls.cmdRegistry[pattern]
        
        # 清除同模块同函数名的命令
        for p, (f, _, _) in list(cls.cmdRegistry.items()):
            if f.__module__ == module_name and f.__name__ == func_name:
                del cls.cmdRegistry[p]
    
    @classmethod
    def clear(cls):
        """清除命令"""
        _CmdMgr_.cmdRegistry.clear()
    
    @classmethod
    def do(cls, command, deviceID=None, data=None):
        """执行命令"""
        cmd = command.strip()
        if not cmd:
            return "w->空命令", None
            
        cmdParts = cmd.split(None, 1)
        cmdName = cmdParts[0].lower()
        cmdArgs = cmdParts[1] if len(cmdParts) > 1 else None
        if cmdArgs and cmdArgs.strip() == '':
            cmdArgs = None
    
        # _Log._Log_.d(f'执行命令: {cmdName} {cmdArgs}')
        try:
            func = param_pattern = None
            # 按正则表达式匹配命令别名
            for pattern, (f, p, _) in cls.cmdRegistry.items():
                if re.match(f"^{pattern}$", cmdName):
                    func, param_pattern = f, p
                    # _Log._Log_.d(f'按命令别名匹配到命令: {pattern} => {f.__name__}')
                    break
            # 再精确匹配函数名
            if not func:
                for _, (f, p, _) in cls.cmdRegistry.items():
                    if f.__name__.lower() == cmdName:
                        func, param_pattern = f, p
                        # _Log._Log_.d(f'按命令名精确匹配到命令: {f.__name__}')
                        break
            # 3. 如果前两个都没匹配上，输出命令名匹配不成功
            if not func:
                return "w->未知命令", None
            
            # _Log._Log_.d(f'执行函数: {func.__name__}, 参数模式: {param_pattern}, 参数: {cmdArgs}')
            
            # 4. 如果匹配成功，继续正则表达式匹配参数模式
            # 如果命令不支持参数但提供了参数，返回错误
            if not param_pattern:
                return (func() if not cmdArgs else "w##该命令不支持参数"), func.__name__
            
            # 如果没有参数，则使用空字符串
            if cmdArgs is None:
                cmdArgs = ""
            
            # 匹配参数
            match = re.match(f"^{param_pattern}$", cmdArgs)
            if not match:
                _Log._Log_.e(f'参数格式错误: {cmdArgs} {param_pattern}')
                return "w->参数格式错误", func.__name__
            
            # 将 data 参数添加到 match.groupdict() 中
            params = match.groupdict()
            import inspect
            sig = inspect.signature(func)
            if 'data' in sig.parameters:
                params['data'] = data
            if 'deviceID' in sig.parameters:
                params['deviceID'] = deviceID
            
            # 执行命令并返回结果
            _Log._Log_.d(f'执行函数: {func.__name__}, 参数: {params}')
            return func(**params), func.__name__
        except Exception as e:
            _Log._Log_.ex(e, f'{cmd}命令执行错误')
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
            log.d(f'重新加载模块: {moduleName}')
            # 检查模块是否已加载
            if moduleName in sys.modules:
                module = sys.modules[moduleName]
                oldCls = g.getClass(moduleName)
                # 获取模块对应的类（假设类名为模块名加下划线）
                if hasattr(oldCls, 'OnPreload'):
                    oldCls.OnPreload()
                # 获取所有引用了该模块的模块
                referrers = [m for m in sys.modules.values() 
                            if m and hasattr(m, '__dict__') and moduleName in m.__dict__]
                # _Log._Log_.d(f'获取所有引用了该模块的模块: {referrers}')
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
                # 打印模块所有成员
                # _Log._Log_.d(f'模块 {module_name} 的成员:::: {dir(module)}')
                # 清除全局引用
                g.clear()
                log.d(f'清除全局引用: {moduleName}')    
                g.CallMethod(module, 'Clone', oldCls)
                g.CallMethod(module, 'OnReload')
            else:
                # 首次加载直接使用import_module
                try:
                    module = importlib.import_module(moduleName)
                    # _Log._Log_.d(f"首次加载模块成功: {module_name}")
                except ImportError as e:
                    log.e(f"找不到模块: {moduleName}, 错误: {e}")
                    return False
            
            return True
        except Exception as e:
            log.ex(e, "模块重载失败")
            return False

    @classmethod
    def _reset(cls):
        g = _G._G_
        log = g.Log()
        """重新加载所有脚本并重启脚本引擎"""
        try:
            log.i("开始全量重载脚本...")
            if g.IsServer():
                return "e->当前是服务器，无法全量重载"
            # 创建一个事件来等待脚本更新完成
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
            g.getClass('CFileServer').update(onUpdateCompleted)
            
            # 等待更新完成，最多等待30秒
            if not update_completed.wait(30):
                log.e("脚本更新超时")
                return "e->脚本更新超时，重载失败"
            
            # 2. 清除Python中所有脚本模块并重新加载
            log.i("正在清除模块缓存...")
            import sys
            import importlib

            client = _G._G_.getClass('CClient')()
            # 缓存必要的状态
            deviceID = client.deviceID if client else None
            server = client.server if client else None
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
            
            # _Log._Log_.d(f"已清除{len(modules_to_reload)}个模块缓存")
            # 3. 重新执行入口函数，重启脚本
            # _Log._Log_.i("正在重启脚本引擎...")
            # 先结束当前客户端
            if client:
                try:
                    client.End()
                except Exception as e:
                    _Log._Log_.ex(e, "结束客户端失败")
            
            # 重新导入CMain模块并执行Begin
            try:
                import importlib
                CMain = importlib.import_module("CMain")
                importlib.reload(CMain)            
                # 获取当前设备ID和服务器地址
                from CClient import client
                if deviceID and server:
                    # print(f"#################重新初始化客户端: deviceID={deviceID} server={server}")
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
        
        这个方法会:
        1. 清除所有命令注册
        2. 首先注册自己的命令
        3. 扫描脚本目录，找到所有包含registerCommands方法的模块
        4. 加载这些模块并执行它们的命令注册函数
        
        Returns:
            bool: 是否成功重新注册
        """
        g = _G._G_
        log = g.Log()
        log.i("开始重新注册命令...")
        try:
            # 1. 清除所有命令注册
            cls.clear()            
            # 3. 扫描脚本目录，找到所有包含registerCommands方法的模块
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
            log.i(f"命令重新注册完成，成功注册{success_count}/{len(modules)}个模块，共{cmd_count}个命令")
            return success_count == len(modules)
        except Exception as e:
            log.ex(e, "命令重新注册失败")
            return False
    
 
        
    @classmethod
    def registerCommands(cls):
        """注册命令管理器自身的命令"""
        # _Log._Log_.i("注册CmdMgr模块命令...")
        @cls.reg(r"重启")
        def reloadAll():
            """重新加载所有命令"""
            return cls._reset()
        
        @cls.reg(r"加载", r"(?P<moduleName>\S+)")
        def reload(moduleName):
            """重新加载指定模块"""
            g = _G._G_
            log = g.Log()
            log.i(f"重新加载模块: {moduleName}")
            moduleName = g.getScriptName(moduleName)
            if not moduleName:
                return "e->找不到模块"
            # 检查是否需要下载最新版本
            moduleFile = f"scripts/{moduleName}.py"
            if not g.IsServer():
                # 先下载最新版本，然后在回调中重新加载
                g.CFileServer().download(moduleFile, lambda success: cls._reloadModule(moduleName))
                return f"i->正在下载并重载{moduleName}..."
            else:
                # 如果没有文件服务器，直接重载
                ret = cls._reloadModule(moduleName)
                return f"i->重载{moduleName}{ret}"
        
        @cls.reg(r"命令列表")
        def cmdList():
            """列出所有可用命令"""
            result = "可用命令:\n"
            for pattern, (_, _, desc) in sorted(cls.cmdRegistry.items()):
                result += f"{pattern}: {desc or '无描述'}\n"
            return result
        

        @cls.reg(r"帮助")
        def help():
            """显示所有可用命令的帮助信息"""
            # 创建命令信息字典
            commands_info = {
                "commands": [],
                "filters": [
                    {"name": "@设备名", "description": "按设备名过滤日志"},
                    {"name": ":TAG", "description": "按TAG标签过滤日志"},
                    {"name": "*正则", "description": "使用正则表达式匹配日志"},
                    {"name": "文本", "description": "按包含文本过滤日志"}
                ]
            }
            
            # 获取所有注册的命令
            commands = cls.cmdRegistry.copy()
            
            # 按命令名称排序
            sorted_commands = sorted(commands.items(), key=lambda x: x[0])
            
            # 命令别名映射
            command_aliases = {}
            
            # 首先收集所有命令的别名
            for cmd_name, cmd_info in sorted_commands:
                _, func, _ = cmd_info
                for alias, (_, alias_func, _) in sorted_commands:
                    if alias != cmd_name and alias_func == func:
                        if cmd_name not in command_aliases:
                            command_aliases[cmd_name] = []
                        command_aliases[cmd_name].append(alias)
            
            # 然后构建命令信息
            for cmd_name, cmd_info in sorted_commands:
                _, func, desc = cmd_info
                
                # 检查这个命令是否是其他命令的别名
                is_alias = False
                for main_cmd, aliases in command_aliases.items():
                    if cmd_name in aliases:
                        is_alias = True
                        break
                
                # 如果是别名，跳过，避免重复
                if is_alias:
                    continue
                
                # 构建命令信息
                cmd_data = {
                    "name": cmd_name,
                    "description": desc or ""
                }
                # 添加别名
                if cmd_name in command_aliases:
                    cmd_data["aliases"] = command_aliases[cmd_name]
                commands_info["commands"].append(cmd_data)            
            # 转换为JSON字符串，使用缩进美化输出
            return json.dumps(commands_info, ensure_ascii=False, indent=2)
        # _Log._Log_.d("CmdMgr模块命令注册完成")


    @classmethod
    def OnReload(cls):
        _Log._Log_.i("CmdMgr模块热更新 重新注册命令")
        # 使用全局命令重新注册机制
        cls.regAllCmds()

# 创建全局单例实例
regCmd = _CmdMgr_.reg
