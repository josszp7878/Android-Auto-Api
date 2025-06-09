from datetime import datetime
import re
import _Log
import _G
import sys
import importlib
from typing import Any, Tuple
import inspect
import json

class Cmd:
    """命令类，存储命令信息"""
    
    def __init__(self, func, match=None, doc=None):
        self.func = func      # 命令函数
        self.match = match    # 命令匹配，默认为函数名
        self.doc = doc or func.__doc__      # 命令文档
        self.module = func.__module__       # 命令所属模块
        self.name = func.__name__           # 函数名
        
        # 预编译完整正则表达式，添加IGNORECASE标志
        self.matchRegex = re.compile(match, re.IGNORECASE) if match else None
        
        # 预编译命令名正则表达式(从match中提取)
        self.nameRegex = None
        if match:
            try:
                from _CmdMgr import _CmdMgr_
                # 提取命令名部分
                key = _CmdMgr_.CmdKey
                cmdMatches = re.search(fr'\(\?P<{key}>(.*?)\)', match)
                if cmdMatches:
                    searchPattern = cmdMatches.group(1)
                    # 创建搜索正则，用于_findCommand
                    self.nameRegex = re.compile(
                        f"({searchPattern})", 
                        re.IGNORECASE
                    )
            except Exception:
                pass


class _CmdMgr_:
    """命令管理器"""
    
    _instance = None  # 单例实例
    
    # 按模块存储命令，格式: [(模块名, {命令名: Cmd对象}), ...]
    cmdModules = []
    
    # 模块优先级，数字越小优先级越高
    modulePriority = {
        "_CmdMgr": 10,
        "_G": 20,
        "_Log": 30
    }
    
    # 预编译正则表达式
    _SPACE_PATTERN = re.compile(r'\s+')

    @classmethod
    def processParamSpaces(cls, pattern):
        """简化版的参数间空格处理：只处理参数间的简单空格
        
        Args:
            pattern: 命令模式字符串
        Returns:
            str: 处理后的命令模式字符串
        """
        # 查找所有命名捕获组
        param_pattern = r'\(\?P<([^>]+)>([^)]+)\)(\??)'
        matches = list(re.finditer(param_pattern, pattern))
        
        if len(matches) <= 1:  # 如果只有一个或没有参数，不需要处理
            return pattern
            
        # 构建结果
        result = ""
        last_end = 0
        
        # 处理每个匹配项
        for i, match in enumerate(matches):
            # 获取当前参数的信息
            full_match = match.group(0)  # 整个匹配
            param_start = match.start()
            param_end = match.end()
            
            # 添加上一个参数结束到当前参数开始之间的部分
            between = pattern[last_end:param_start]
            # 如果是参数之间的部分(不是开头部分)，且只包含空白
            if i > 0 and between.strip() == '':
                # 替换为\s*
                result += r'\s*'
            else:
                result += between
                
            # 添加当前参数
            result += full_match
            last_end = param_end
            
        # 添加最后一个参数后的部分
        result += pattern[last_end:]
        
        return result

    
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
        
        # 存储所有已注册的模式项，用于检测雷同
        if not hasattr(cls, 'registered_patterns'):
            cls.registered_patterns = {}
        
        # 如果第一个参数是函数，说明装饰器没有参数
        if callable(pattern):
            log.e(f"目前不支持没有参数的装饰器: {pattern.__name__}")
            return None
        # 如果第一个参数不是函数，说明装饰器有参数
        def decorator(func):
            nonlocal pattern  # 声明pattern为非局部变量，引用外部作用域的pattern
            
            # 获取函数名和函数名缩写
            func_name = func.__name__
            # 生成函数名缩写: 取第一个字母和所有大写字母
            abbr = func_name[0] + ''.join(c for c in func_name[1:] if c.isupper())
            
            if '#' in pattern:
                # 使用正则表达式查找 #命令名|别名 格式
                m = re.search(r'\s*#([^\s\(]+)\s*', pattern)
                if m:
                    cmd_pattern = m.group(0)
                    cmdName = m.group(1)
                    # 提取命令名的每个部分进行雷同检查
                    cmd_parts = cmdName.split('|')
                    # 添加函数名和缩写到检查列表
                    cmd_parts.extend([func_name.lower(), abbr.lower()])
                    
                    # 检查是否有雷同匹配
                    for item in cmd_parts:
                        item = item.strip().lower()
                        if item in cls.registered_patterns:
                            existing_cmd = cls.registered_patterns[item]
                            # 避免与自己比较
                            if existing_cmd != func_name:
                                log.e(f"命令匹配模式雷同: '{item}' 在 {func_name} 和 {existing_cmd} 之间重复")
                        else:
                            cls.registered_patterns[item] = func_name
                    
                    # 始终添加函数名和缩写到命令别名中，不考虑是否已有别名
                    cmdName = f"{cmdName}|{func_name}|{abbr.lower()}"
                    namePattern = f"(?P<{cls.CmdKey}>{cmdName})\s*"
                    # 在替换命令名时添加忽略大小写标记
                    pattern = pattern.replace(
                        cmd_pattern, 
                        namePattern
                    )
                else:
                    log.e(f"{pattern} 没有匹配指令名")
                    return func
            
            # 处理参数之间的空格
            # 查找所有命名捕获组
            param_pattern = r'\(\?P<([^>]+)>[^)]+\)(\??)'
            param_matches = list(re.finditer(param_pattern, pattern))
            
            # 如果找到参数，处理它们之间的空格
            if len(param_matches) > 1:
                # 使用已有的processParamSpaces方法处理参数间空格
                pattern = cls.processParamSpaces(pattern)
            
            # 如果pattern结尾是\s+或者\s*,应该去掉
            if pattern.endswith(r'\s*'):
                pattern = pattern[:-3]

            # 创建命令对象并添加到注册表
            cmd = Cmd(
                func=func, 
                match=pattern,
                doc=func.__doc__
            )
            cls._addCommand(cmd)
            return func
        return decorator
    
    @classmethod
    def _addCommand(cls, cmd):
        """添加命令到模块命令集合
        
        Args:
            cmd: 命令对象
        """
        module_name = cmd.module
        func_name = cmd.name
        
        # 查找模块在列表中的位置
        cmdMap = None
        for i, (name, cmds) in enumerate(cls.cmdModules):
            if name == module_name:
                cmdMap = cmds
                break
                
        # 如果模块不存在，创建新的模块命令集合
        if cmdMap is None:
            cmdMap = {}
            cls.cmdModules.append((module_name, cmdMap))
            
        # 添加命令到模块命令集合
        cmdMap[func_name] = cmd
    
    
    @classmethod
    def clear(cls):
        """清除所有命令"""
        cls.cmdModules.clear()
        cls.modulePriority.clear()

    @classmethod
    def _sort(cls):
        """按优先级对模块进行排序"""
        # 更新所有模块的默认优先级
        for module_name, _ in cls.cmdModules:
            if module_name not in cls.modulePriority:
                cls.modulePriority[module_name] = 100
        
        # 按优先级排序模块
        cls.cmdModules.sort(key=lambda x: cls.modulePriority.get(x[0], 999))

    @classmethod
    def _findCommand(cls, cmdName, moduleName=None):
        """查找命令
        
        Args:
            cmdName: 命令名称
            moduleName: 模块名称
        Returns:
            Cmd: 找到的命令对象，如果未找到则返回None
        """
        if not cmdName:
            return None
        
        cmdName = cmdName.lower()
        
        # 尝试匹配所有命令的正则表达式，找到最长的匹配
        bestMatch = None
        bestMatchLength = -1
        
        log = _G._G_.Log()        
        # 使用已排序的模块列表
        for module_name, module_cmds in cls.cmdModules:
            if moduleName and module_name != moduleName:
                continue
            # 遍历模块中的所有命令
            for cmd in module_cmds.values():
                # 使用预编译的正则表达式
                if cmd.nameRegex:
                    try:
                        cmdMatches = cmd.nameRegex.search(cmdName)
                        if cmdMatches:
                            matchLength = len(cmdMatches.group(0))
                            if matchLength > bestMatchLength:
                                bestMatch = cmd
                                bestMatchLength = matchLength
                    except Exception as e:
                        log.ex(e, f"命令名匹配失败: {cmd.name}")
                else:
                    # 如果没有预编译的正则表达式，尝试匹配函数名
                    if cmd.name.lower() == cmdName:
                        matchLength = len(cmd.name)
                        if matchLength > bestMatchLength:
                            bestMatch = cmd
                            bestMatchLength = matchLength
        
        return bestMatch
    
    @classmethod
    def _cleanParam(cls, value: str) -> str:
        """清理参数值，去除多余空格"""
        if value is not None:
            # 去除前后空格
            value = value.strip()        
            # 替换多余空格为单个空格
            value = cls._SPACE_PATTERN.sub(' ', value)
        return value
    
    CmdKey = "CC"
    @classmethod
    def do(cls, cmd:dict):
        """执行命令
        Args:
            cmd: dict 成员如下：
                id: 命令ID
                name: 命令名称
                data: 命令数据
                cmd: 命令字符串
        """
        if cmd is None:
            return None
        g = _G._G_
        log = g.Log()
        cmdStr = cmd.get('cmd')
        cmdStr = cmdStr.strip() if cmdStr else ''
        if cmdStr == '':
            return
        # 不再转换为小写，保持原始大小写
        try:
            find = None
            m = None
            # 尝试匹配所有命令的正则表达式，找到最长的匹配
            bestMatch = None
            bestMatchLength = -1
            
            # 使用已排序的模块列表
            for module_name in cls.cmdModules:
                module_cmds = module_name[1]
                
                # 遍历模块中的所有命令
                for cmdObj in module_cmds.values():
                    try:
                        # 使用预编译的正则表达式
                        match = cmdObj.matchRegex.fullmatch(cmdStr)
                    except Exception as e:
                        log.ex(e, f"命令: {cmdStr} 正则表达式错误: {cmdObj.match}")
                        continue
                    if match:
                        cmdMatch = match.groupdict().get(cls.CmdKey)
                        matchLength = len(cmdMatch) if cmdMatch else 0
                        if matchLength > bestMatchLength:
                            bestMatch = cmdObj
                            m = match
                            bestMatchLength = matchLength
            find = bestMatch
            if find is None:
                log.w(f"{cmdStr} 不是命令: 当成脚本执行")
                tools = g.Tools()
                tools.do(cmdStr)
                return
            # 提取命名捕获组作为参数
            kwargs = {}
            for key, value in m.groupdict().items():
                # 跳过命令关键字,这个不能作为参数
                if key != cls.CmdKey:
                    kwargs[key] = cls._cleanParam(value)
            cmdName = find.name.lower()
            cmd['name'] = cmdName
            # 检查目标函数是否有cmd参数
            sig = inspect.signature(find.func)
            if 'cmd' in sig.parameters:
                kwargs['cmd'] = cmd 
            log.c_(f'<{cmdName}>:{cmdStr}', '')
            result = find.func(**kwargs)
            try:
                # 检查是否能被json序列化
                json.dumps(result)
            except TypeError:
                raise Exception(f"命令返回值不支持JSON序列化: {type(result)}，请检查实现")
            if result:
                cmd['result'] = result
                # 解析结果中可能包含的级别信息
                level, result = log._parseLevel(result)
                if isinstance(result, str):
                    # 如果result是字符串，则直接当结果打印
                    log.log_(f'  => {result}', '', level)
                else:
                    # 如果result不是字符串，则转换为字符串并当结果打印
                    log.log_(f'  => {str(result)}', '', level)
        except Exception as e:
            log.ex(e, f'执行命令出错: {cmdStr}')
        
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
                oldCls = g.getClassLazy(moduleName)
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
                # 重新注册命令
                cls._regCmd(module, log)
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
            g = _G._G_
            log = g.Log()
            # 获取所有用户脚本模块名称
            script_modules = g.getScriptNames()
            modules_cleared = 0
            
            # 遍历sys.modules中的所有模块
            for module_name in list(sys.modules.keys()):
                # 检查是否是用户脚本模块（以任一脚本模块名结尾）
                for script_name in script_modules:
                    if module_name.endswith(script_name):
                        del sys.modules[module_name]
                        modules_cleared += 1
                        break
            
            log.i(f"已清理{modules_cleared}个脚本模块")
        except Exception as e:
            _Log._Log_.ex(e, "清除模块缓存失败")

    @classmethod
    def regAllCmds(cls):
        g = _G._G_
        log = g.Log()
        log.i("注册所有命令...")
        try:
            cls.cmdMap = {}
            modules = g.getScriptNames()
            # 加载所有未加载的模块，加载模块时模块本身会执行registerCommands方法
            for moduleName in modules:
                try:
                    # 直接使用模块名，不添加前缀
                    if moduleName not in sys.modules:
                        module = importlib.import_module(moduleName)
                    else:
                        module = sys.modules[moduleName]
                    cls._regCmd(module, log)
                except Exception as e:
                    log.ex(e, f"导入模块 {moduleName} 出错")
            
            # 对模块进行排序
            cls._sort()
            return True
        except Exception as e:
            log.ex(e, "注册命令失败")
            return False
        
    @classmethod
    def _regCmd(cls, module, log):
        if not module:
            return
        # 尝试查找模块中的类并调用类的registerCommands方法
        moduleName = module.__name__
        clsName = f'{moduleName}_'
        if hasattr(module, clsName):
            cls_obj = getattr(module, clsName)
            # 安全地获取registerCommands方法
            # 不使用inspect.getmembers避免触发属性延迟加载
            methodName = 'registerCommands'
            if hasattr(cls_obj, methodName):
                regist = getattr(cls_obj, methodName)
                if callable(regist):
                    # log.d(f"加载类指令: {cls_name}")
                    try:
                        regist()
                        # log.d(f"注册指令模块: {clsName}")
                    except Exception as e:
                        log.ex(e, f"注册指令模块失败: {clsName}")

    
    @classmethod
    def setModulePriority(cls, module_name, priority):
        """设置模块优先级
        
        Args:
            module_name: 模块名
            priority: 优先级，数字越小优先级越高
        """
        cls.modulePriority[module_name] = priority
        # 重新排序模块
        cls._sort()
    
    @classmethod
    def registerCommands(cls):
        """注册命令"""
        regCmd = cls.reg
        
        @regCmd(r"#重启")
        def reset():
            """功能：重新加载所有脚本并重启脚本引擎
            指令名：reloadAll
            中文名：重启
            参数：无
            示例：重启
            """
            return cls._reset()
        
        @regCmd(r"#加载|jz (?P<moduleName>.+)")
        def reLoad(moduleName):
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
        
 
        cls.HelpStr = """
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
        
        @regCmd(r"#帮助|bz(?P<command>.+)?") 
        def help(command=None):
            """功能：列出所有可用命令
            参数：
              moduleName -要查询的模块名, 为空时查询所有模块
              command - 要查询的命令名称, 为空时查询所有命令
            示例：帮助
            示例：帮助 _CmdMgr
            示例：帮助 重启
            示例：帮助 CCmds 加载
            """
            result = "可用命令:\n"
            command = command.strip() if command else ''
            if command == '':
                # 查询所有命令
                result = cls.HelpStr
            elif command.startswith('@'):
                # 查询指定模块的命令
                moduleName = command[1:].strip()
                for moduleName, module_cmds in cls.cmdModules:
                    if moduleName and moduleName.lower() != moduleName.lower():
                        continue
                    result += f"\n[模块: {moduleName} (优先级: {cls.modulePriority.get(moduleName, 999)})]\n"
                    for cmd_name, cmd in sorted(module_cmds.items()):
                        result += f"  {cmd.name}\t\t: {cmd.match}\n"
            else:
                #具体某个指令的帮助
                cmd = cls._findCommand(command)
                if not cmd:
                    return f"e~无效指令{command}"
                result = f'{cmd.name}\n{cmd.match}\n{cmd.doc}'
            return result
        

        @regCmd(r"#时间|sj")
        def time():
            """
            功能：获取当前时间
            """ 
            return str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        @regCmd(r"#信息|xx")
        def info():
            """
            功能：查看设备连接状态
            """  
            g = _G._G_
            if g.isServer():
                return{
                    'Timestamp': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                }
            else:
                device = g.CDevice()
                return {
                    "deviceID": device.deviceID if device else "未知",
                    "state": device.state(),
                    "timestamp": str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                }
    

    @classmethod
    def onLoad(cls, old):
        log = _G._G_.Log()
        log.i("注册指令 _CmdMgr_")
        if old is not None:
            cls.regAllCmds()
        return True
    
# 创建全局单例实例
regCmd = _CmdMgr_.reg