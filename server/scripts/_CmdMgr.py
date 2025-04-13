import re
import _Log
import _G
import sys
import importlib
from typing import List, Any, Tuple

class Cmd:
    """命令类，存储命令信息"""
    
    def __init__(self, func, alias=None, doc=None):
        self.func = func      # 命令函数
        self.alias = alias or func.__name__  # 命令别名，默认为函数名
        self.doc = doc or func.__doc__      # 命令文档
        self.module = func.__module__       # 命令所属模块
        self.name = func.__name__           # 函数名


class _CmdMgr_:
    """命令管理器"""
    
    _instance = None  # 单例实例
    
    # 使用列表存储命令
    cmdRegistry: List[Cmd] = []
    
    # 预编译正则表达式
    _SPACE_PATTERN = re.compile(r'\s+')
    _PUNCT_QUOTE_PATTERN = re.compile(r'[,，。.、?？!！;；:：]$|["""'']')
    

    @classmethod
    def processParamSpaces(cls, cmdStr):
        """处理参数之间的空格"""
        # 查找所有命名捕获组 (?P<name>pattern) 包括可选参数
        param_groups = list(re.finditer(r'\(\?P<([^>]+)>[^)]+\)\??', cmdStr))
        
        # 过滤掉命令关键字参数，并按出现顺序记录参数位置
        params = []
        for match in param_groups:
            param_name = match.group(1)
            if param_name != cls.CmdKey:
                params.append((match.start(), match.end()))
        
        # 在参数之间添加\s+（最后一个参数不添加）
        modified = cmdStr
        offset = 0  # 用于跟踪插入空格后的位置偏移
        for i in range(len(params)-1):
            current_end = params[i][1] + offset
            next_start = params[i+1][0] + offset
            
            # 检查当前参数结束到下一个参数开始之间是否有其他字符
            between = modified[current_end:next_start]
            if not re.search(r'\\s', between):  # 如果没有已有的空格匹配
                # 在当前位置插入\s+
                modified = modified[:current_end] + r'\s*' + modified[current_end:]
                offset += 4  # 插入4个字符(\s+)
        
        return modified

    
    @classmethod
    def reg(cls, pattern=None):
        """注册命令
        
        Args:
            pattern: 命令模式，支持以下格式:
                1. 包含 "#命令名|别名" 的模式 - 自动替换为 "(?P<CC>命令名|别名|函数名|缩写)"
                2. 完整的正则表达式 - 直接使用
            
        注意: 系统会自动将函数名和函数名缩写添加到命令别名中
        函数名缩写规则: 取函数名第一个字母和所有大写字母组合
        """
        log = _G._G_.Log()
        
        # 如果第一个参数是函数，说明装饰器没有参数
        if callable(pattern):
            func = pattern
            # 获取函数名和函数名缩写
            func_name = func.__name__
            # 生成函数名缩写: 取第一个字母和所有大写字母
            abbr = func_name[0] + ''.join(c for c in func_name[1:] if c.isupper())
            
            # 创建命令模式，使用函数名和缩写
            cmd_pattern = f"(?P<{cls.CmdKey}>{func_name}|{abbr.lower()})"
            
            # 清除同名或同模块同函数名的旧命令
            cls._clearOldCommand(cmd_pattern, func.__module__, func.__name__)
            
            # 创建命令对象并添加到注册表
            cmd = Cmd(func=func, alias=cmd_pattern)
            cls.cmdRegistry.append(cmd)
            return func
        
        # 如果第一个参数不是函数，说明装饰器有参数
        def decorator(func):
            nonlocal pattern  # 声明pattern为非局部变量，引用外部作用域的pattern
            
            # 获取函数名和函数名缩写
            func_name = func.__name__
            # 生成函数名缩写: 取第一个字母和所有大写字母
            abbr = func_name[0] + ''.join(c for c in func_name[1:] if c.isupper())
            
            # 处理参数之间的空格
            pattern = cls.processParamSpaces(pattern)
            
            if '#' in pattern:
                # 使用正则表达式查找 #命令名|别名 格式
                m = re.search(r'\s*#([^\s\(]+)\s*', pattern)
                if m:
                    cmd_pattern = m.group(0)
                    cmdName = m.group(1)
                    # 始终添加函数名和缩写到命令别名中，不考虑是否已有别名
                    cmdName = f"{cmdName}|{func_name}|{abbr.lower()}"
                    # 在替换命令名时添加忽略大小写标记
                    pattern = pattern.replace(
                        cmd_pattern, 
                        f'(?P<{cls.CmdKey}>{cmdName})(?i)\s*'  # 添加(?i)忽略大小写
                    )
                else:
                    log.e(f"{pattern} 没有匹配指令名")
                    return func
            # 如果pattern结尾是\s+,应该去掉
            if pattern.endswith(r'\s+'):
                pattern = pattern[:-3]
            # 记录日志，帮助调试
            # log.i(f"{pattern}<=>\n{new_pattern}")
            # 清除同名或同模块同函数名的旧命令
            cls._clearOldCommand(pattern, func.__module__, func.__name__)

            # 创建命令对象并添加到注册表
            cmd = Cmd(
                func=func, 
                alias=pattern,
                doc=func.__doc__
            )
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
        
        # 2. 匹配函数名
        for cmd in cls.cmdRegistry:
            if cmd.name.lower() == cmdName:
                return cmd
        
        return None
    
    @classmethod
    def _cleanParam(cls, value:str)->str:
        """清理参数值，去除多余空格和标点符号"""
        if value is not None:
            # 去除前后空格
            value = value.strip()        
            # 替换多余空格为单个空格
            value = cls._SPACE_PATTERN.sub(' ', value)
            # 去除末尾标点符号和所有引号
            value = cls._PUNCT_QUOTE_PATTERN.sub('', value)
        return value
    
    CmdKey = "CC"
    DataKey = 'DD'

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
        cmdStr = cmdStr.strip() if cmdStr else ''
        if cmdStr == '':
            return None, None
        cmdStr = cmdStr.lower()
        try:
            findCmd = None
            m = None
            # 尝试匹配所有命令的正则表达式，找到最长的匹配
            bestMatch = None
            bestMatchLength = -1
            for cmd in cls.cmdRegistry:
                try:
                    match = re.fullmatch(cmd.alias, cmdStr)
                except Exception as e:
                    log.ex(e, f"命令: {cmdStr} 正则表达式错误: {cmd.alias}")
                    continue
                if match:
                    cmdMatch = match.groupdict().get(cls.CmdKey)
                    matchLength = len(cmdMatch) if cmdMatch else 0
                    if matchLength > bestMatchLength:
                        bestMatch = cmd
                        m = match
                        bestMatchLength = matchLength
            findCmd = bestMatch
            if findCmd is None:
                log.e(f"找不到命令: {cmdStr}")
                return "", None
            # 提取命名捕获组作为参数
            kwargs = {}
            for key, value in m.groupdict().items():
                # 跳过命令关键字,这个不能作为参数
                if key != cls.CmdKey:
                    kwargs[key] = cls._cleanParam(value)
            if data:
                kwargs[cls.DataKey] = data
            result = findCmd.func(**kwargs)
            log.log_(f'cmdStr<{findCmd.name.lower()}>', '', 'c', result or '')
            return result, findCmd.name
        except Exception as e:
            log.ex(e, f'执行命令出错: {cmdStr}')
            return None, None
        
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
                g.CallMethod(module, 'onLoad', oldCls)
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
            
            # 调用更新脚本方法
            # log.i("正在更新脚本...")
            downAll = g.CFileServer().downAll()
            downAll.join()
            log.i("脚本更新完成")
            
            # log.i("正在结束客户端...")
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

            # log.i("正在清除模块缓存...")
            cls.clearModules()

            CMain = importlib.import_module("CMain")
            importlib.reload(CMain)            
            # log.i(f"222当前设备ID: {deviceID}, 服务器地址: {server}")
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
    def regAllCmds_(cls):
        g = _G._G_
        log = g.Log()
        log.i("开始重新注册命令...")
        try:
            # 1. 清除所有命令注册
            cls.clear()            
            modules = g.getScriptNames()
            success_count = 0
            # 加载所有为加载的模块，加载模块时模块本身会执行registerCommands方法
            for module in modules:
                try:
                    # 直接使用模块名，不添加前缀
                    full_module_name = module                    
                    # 加载模块
                    try:
                        if full_module_name not in sys.modules:
                            module = importlib.import_module(full_module_name)
                    except Exception as e:
                        log.ex(e, f"加载模块失败: {full_module_name}")
                        continue
                    success_count += 1
                except Exception as e:
                    log.ex(e, f"注册模块 {module} 的命令失败")
        except Exception as e:
            log.ex(e, "命令重新注册失败")
            return False
       
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
        @cls.reg(r"#重启")
        def reset():
            """功能：重新加载所有脚本并重启脚本引擎
            指令名：reloadAll
            中文名：重启
            参数：无
            示例：重启
            """
            return cls._reset()
        
        @cls.reg(r"#加载|jz (?P<moduleName>.+)")
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
                return "e~找不到模块"
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
        
        @cls.reg(r"#命令列表|mjlb|cl") 
        def cmdList():
            """功能：列出所有可用命令
            指令名：cmdList
            中文名：命令列表
            参数：无
            示例：命令列表
            """
            result = "可用命令:\n"
            for cmd in sorted(cls.cmdRegistry, key=lambda x: x.name):
                result += f"{cmd.name}\t\t: {cmd.alias}\n"
            return result
        
        @cls.reg(r"#帮助|bz|help (?P<command>\S+)?")
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
                return "e~无效指令"
            # 获取命令的描述
            desc = cmd_info.doc
            return desc



    @classmethod
    def onLoad(cls, clone):
        log = _G._G_.Log()
        log.i("注册指令 _CmdMgr_")
        cls.registerCommands()
        return True
    
_CmdMgr_.onLoad(None)
# 创建全局单例实例
regCmd = _CmdMgr_.reg