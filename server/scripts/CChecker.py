from enum import Enum
from typing import Dict, Any, List,  Optional, TYPE_CHECKING
import _G
if TYPE_CHECKING:
    from _Page import _Page_
import json
import re
import threading
import time

g = _G.g
log = g.Log()

class CChecker_:
    """页面检查器类，用于验证页面状态并执行相应操作"""
    # 存储模板和运行时检查器
    _templates: List["CChecker_"] = None  # 存储所有checker模板
    _lock = threading.Lock()  # 线程安全锁
    
    # 默认值实例，在类初始化时创建
    _DEFAULT = None
    @classmethod
    def Default(cls) -> "CChecker_":
        """获取默认配置实例"""
        if cls._DEFAULT is None:
            # 创建默认实例
            cls._DEFAULT = cls("__default__")
        return cls._DEFAULT

    @classmethod
    def templates(cls):
        return cls._templates
    
    @classmethod
    def loadConfig(cls):
        """加载checker配置文件"""
        import os
        try:
            cls._templates = []
            configPath = os.path.join(_G.g.rootDir(), 'config', 'Checks.json')
            with open(configPath, 'r', encoding='utf-8') as f:
                # 加载JSON数组
                data = json.load(f)
                for item in data:
                    # 创建对象并加入模板列表
                    template = cls(item.get('name', ''), item)
                    cls._templates.append(template)
                log.i(f"加载{len(cls._templates)}个checker配置")
        except Exception as e:
            log.ex(e, "加载Checks.json失败")
            cls._templates = []

    def __init__(self, name: str, config: Dict[str, Any] = None, data=None):
        """初始化检查器，直接定义默认值

        Args:
            name: 检查器名称
            config: 检查器配置字典
            data: 检查器数据(可选)
        """
        # 核心属性（会被序列化）
        self.name = name.lower()  # 名称，必填
        self._match = None        # 默认匹配规则为名称
        self._childs = None      # 子检查器列表
        self.event = {}        # 默认事件处理为空
        self.timeout = 0         
        self.type = 'once'        # 默认类型为一次性
        self.entry = {}          # 新增：入口代码，页面名为键，执行代码为值
        self.exit = None           # 新增：出口逻辑，页面名或代码

        # 运行时属性（不会被序列化）
        self.data = data          # 附加数据
        self.pastTime = 0         # 已运行时间
        self.startTime = 0        # 开始时间
        self.lastTime = 0         # 上次检查时间
        self._enabled = False     # 是否启用
        self.children = []        # 存储由当前检查器启动的子检查器
        self.childThreads = []    # 存储子检查器的线程
        self.executedEvents = set()  # 记录已执行的事件
        self.ret = ''            # 返回值，用于外部获取执行结果
        self.forceCancelled = False  # 是否被外部强制取消标志

        # 如果有配置，则更新属性
        if config:
            self.fromConfig(config)

    def fromConfig(self, config: Dict[str, Any]):
        """从字典更新属性，只更新存在的字段"""
        if 'event' in config and config['event']:
            self.event = config['event'].copy() \
                if isinstance(config['event'], dict) else {}
        if 'match' in config and config['match']:
            self._match = config['match']
        if 'childs' in config and config['childs']:
            self._childs = config['childs']
        # 兼容旧配置
        elif 'checks' in config and config['checks']:
            self._childs = config['checks']
        if 'timeout' in config:
            self.timeout = config['timeout']
        if 'type' in config:
            self.type = config['type']
        if 'entry' in config and config['entry']:
            self.entry = config['entry'].copy() \
                if isinstance(config['entry'], dict) else {}
        if 'exit' in config and config['exit']:
            self.exit = config['exit']
        return self

    def toConfig(self) -> Dict[str, Any]:
        """将对象转换为可序列化的字典，只保存非默认值"""
        result = {'name': self.name}  # 名称是必须的
        
        # 确保DEFAULT实例已初始化
        default = self.Default()
        
        # 检查和保存非默认值字段
        if self._match:
            result['match'] = self._match
        if self._childs:
            result['childs'] = self._childs        
        if self.event:  # 只有当有操作时才保存
            result['event'] = self.event.copy()
            
        # 其他属性只有当不是默认值时才保存
        if self.timeout != default.timeout:
            result['timeout'] = self.timeout
            
        if self.type != default.type:
            result['type'] = self.type
            
        # 保存entry和exit属性
        if self.entry:
            result['entry'] = self.entry.copy()
            
        if self.exit:
            result['exit'] = self.exit
            
        return result

    def __str__(self):
        return f"{self.name} {self.match}"

    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @property
    def match(self) -> str:
        return self._match or self.name.split('-')[-1]
        
    def addProp(self, prop: str, value: str, value1: str = None) -> bool:
        log = _G.g.Log()
        try:    
            if 'mat' in prop:
                oldVal = self._match
                split = '&|'
                if value.startswith('|'):
                    split = '|&'
                    value = value[1:]
                elif value.startswith('&'):
                    value = value[1:]
                range = CChecker_.parseMatchRange(self._match, value1)
                value = CChecker_._addStrListProp(
                    self._match, split, value, range)
                if value:
                    self._match = value
                    log.d(f"_match: {oldVal} => {self._match}")
            elif 'chi' in prop or 'che' in prop:  # 兼容旧命令
                oldVal = self._childs
                value = CChecker_._addStrListProp(
                    self._childs, ',', value, value1)
                if value:
                    self._childs = value
                    log.d(f"_childs: {oldVal} => {self._childs}")
            elif 'event' in prop:
                oldVal = self.event
                self.event[value] = value1
                log.d(f"event: {oldVal} => {self.event}")
            elif 'entry' in prop:
                oldVal = self.entry
                self.entry[value] = value1
                log.d(f"entry: {oldVal} => {self.entry}")
            elif 'exit' in prop:
                oldVal = self.exit
                self.exit = value
                log.d(f"exit: {oldVal} => {self.exit}")
            else:
                log.e(f"不支持add的属性: {prop}")
                return False
            return True
        except Exception as e:
            log.ex(e, f"add{prop}失败: {value}")
            return False
        
    def removeProp(self, prop: str, value: str) -> bool:
        """删除指定属性
        Args:
            prop: 属性名
            value: 要删除的值
        Returns:
            bool: 删除是否成功
        """
        log = _G.g.Log()
        try:    
            if 'mat' in prop:
                oldVal = self._match
                value = value.strip('&').strip('|')
                value = CChecker_._delStrListProp(self._match, '&|', value)
                if value:
                    self._match = value
                    log.d(f"_match: {oldVal} => {self._match}")
            elif 'chi' in prop or 'che' in prop:  # 兼容旧命令
                oldVal = self._childs
                split = ','
                value = value.strip(split)
                value = CChecker_._delStrListProp(self._childs, split, value)
                if value:
                    self._childs = value
                    log.d(f"_childs: {oldVal} => {self._childs}")
            elif 'event' in prop:
                oldVal = self.event
                self.event.pop(value)
                log.d(f"event: {oldVal} => {self.event}")
            elif 'entry' in prop:
                oldVal = self.entry
                self.entry.pop(value)
                log.d(f"entry: {oldVal} => {self.entry}")
            elif 'exit' in prop:
                oldVal = self.exit
                self.exit = ""
                log.d(f"exit: {oldVal} => {self.exit}")
            else:
                log.e(f"不支持remove的属性: {prop}")
                return False
            return True
        except Exception as e:
            log.ex(e, f"remove{prop}失败: {value}")
            return False
  

        
    @classmethod
    def parseMatchRange(cls, match: str, range: str = None):
        """解析match的范围
        Args:
            match: 要解析的范围的文字
            range: 范围，可以是坐标，也可以是偏移量. 如果为'_'，则从当前屏幕获取match文字对应的坐标
        Returns:
            str: 范围
        """
        if not range:
            return range  
        tools = g.Tools()
        # 从当前屏幕获取match文字对应的坐标
        pos = tools.findTextPos(match)
        DEF = 75
        if range == '_':
            return f'{pos[0]-DEF},{pos[1]-DEF},{pos[0]+DEF},{pos[1]+DEF}'
        sX, sY = range.split(',') if range else (0, 0)
        x = int(sX) if sX else 0
        y = int(sY) if sY else 0
        if x > 0 or y > 0:

            if pos:
                if x > 0 and y > 0:
                    range = f'{pos[0] - x},{pos[1]-y},{pos[0]+x},{pos[1]+y}'
                elif x > 0:
                    range = f'{pos[0] - x},{pos[0]+x}'
                elif y > 0:
                    range = f'{pos[1] - y},{pos[1]+y}'
            else:
                return f"e~当前页面未找到{match}文字"
        return range
    
    @classmethod
    def _addStrListProp(cls, curVal: str, split: str, value: str, 
                        range: str = None):
        # 为了支持已有ITEM的替换，先将match转换为列表
        newValue = f'{value}{range}' if range else value
        if newValue == curVal:
            return None
        if curVal:
            m = re.search(rf'[{split}\s]*{value}[^{split}]*', curVal)
            newValue = f'{split[0]}{newValue}'
            if m:
                curVal = curVal.replace(m.group(0), newValue)
            else:                
                curVal = f'{curVal}{newValue}'
        else:
            curVal = newValue
        return curVal
    
    @classmethod
    def _delStrListProp(cls, curVal: str, split: str, value: str):
        # 为了支持已有ITEM的替换，先将match转换为列表
        if curVal:
            return re.sub(rf'[{split}\s]*{value}', '', curVal)
        return curVal


    @property
    def childs(self) -> List[str]:
        return self._childs

    @childs.setter
    def childs(self, value: List[str]):
        self._childs = value

    # 兼容旧代码
    @property
    def checks(self) -> List[str]:
        return self._childs

    @checks.setter
    def checks(self, value: List[str]):
        self._childs = value

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        log.d(f"设置检查器 {self.name} 状态为 {value}")
        if value:
            self.startTime = time.time()
            self.lastTime = 0
    
    def Match(self) -> bool:
        """执行检查逻辑
        Returns:
            bool: 检查是否通过
        """
        result = False
        try:
            tools = g.Tools()
            log.d(f"{self.name}.Match")
            match = self.match
            if match == '':
                return True
            log.d(f"匹配: {match}")
            result = tools.do(self, match, False)
            if not result:
                # 否则检查文本规则
                text = tools.matchText(match)
                result = text is not None
        except Exception as e:
            log.ex(e, f"匹配失败: {match}")
            result = False
        return result
    
    class eDoRet(Enum):
        none = ''
        # 结束schedule
        exit = 'exit'
        # 结束本次check，继续schedule
        end = 'end'
        # 取消本次check
        cancel = 'cancel'
        # 出错
        error = 'error'
    
    # 执行操作
    def Do(self) -> str:
        try:
            events = self.event.items() if self.event else []
            ret = ''
            tools = g.Tools()
            
            if len(events) == 0: 
                # 没有操作，直接点击match
                if tools.click(self.match):
                    ret = self.eDoRet.end.value
                log.d(f"{self.name}.Do: {ret}")
                self.ret = ret
                return ret
            else:
                for key, action in events:
                    # 如果该事件已执行过，则跳过
                    if key in self.executedEvents:
                        continue
                        
                    key = key.strip()
                    execute = False
                    text_match = None
                    
                    # 处理不同类型的key
                    if key.startswith('%'):
                        # 概率执行：%30 表示30%的概率执行
                        try:
                            probability = int(key[1:])
                            import random
                            execute = random.randint(1, 100) <= probability
                            log.d(f"概率执行({probability}%): {execute}")
                            # 概率事件无论是否执行，都标记为已处理，避免重复触发
                            self.executedEvents.add(key)
                        except Exception as e:
                            log.ex(e, f"解析概率失败: {key}")
                            continue
                    elif key.startswith('-'):
                        # 延时执行：-5 表示延时5秒后执行
                        try:
                            delay = int(key[1:])
                            log.d(f"延时执行({delay}秒)")
                            time.sleep(delay)
                            execute = True
                            # 延时事件执行后标记为已处理
                            self.executedEvents.add(key)
                        except Exception as e:
                            log.ex(e, f"解析延时失败: {key}")
                            continue
                    elif key == '':
                        # 无条件执行一次
                        execute = True
                        log.d("无条件执行")
                        # 无条件事件执行后标记为已处理
                        self.executedEvents.add(key)
                    else:
                        # 屏幕匹配文本，如果匹配到则执行
                        text_match = tools.matchText(key)
                        execute = text_match is not None
                        if not execute and g.isAndroid():
                            log.d(f"匹配文本失败: {key}")
                            continue
                        # 处理正则表达式捕获组
                        if execute and '(?P<' in key and text_match:
                            try:
                                m = re.search(key, text_match['t'])
                                if m:
                                    # 将匹配的命名捕获组添加到data中
                                    for k, v in m.groupdict().items():
                                        self.data[k] = v
                            except Exception as e:
                                log.ex(e, f"处理正则表达式捕获组失败: {key}")

                    # 如果条件满足，执行action
                    if execute:
                        result = False
                        action = action.strip() if action else ''
                        
                        if action == '':
                            # 空操作默认为点击
                            if text_match:
                                result = tools.click(key)
                            else:
                                result = True  # 无条件/概率/延时执行的空操作视为成功
                        else:
                            codes = action.split(';')
                            for code in codes:
                                code = code.strip()
                                if code == '':
                                    continue
                                # 处理特殊指令
                                result = self._onCmd(code)
                                # 如果特殊指令返回的不是none，则转换为字符串返回
                                if result != self.eDoRet.none:
                                    self.ret = result.value
                                    return self.ret
                                
                                # 非特殊指令的处理
                                if not code.startswith('@'):
                                    code = f'@ {code}'
                                result = tools.do(self, code)
                        
                        # 文本匹配类型的事件执行后标记为已处理
                        if text_match is not None:
                            self.executedEvents.add(key)
                                    
                        if isinstance(result, str) and result.startswith('#'):
                            ret = result
                            break
                
                log.d(f"{self.name}.Do: {ret}")
                self.ret = ret
                return ret
        except Exception as e:
            log.ex(e, f"执行操作失败: {self.event}")
            ret = self.eDoRet.error.value
            self.ret = ret
            return ret

    def _onCmd(self, code: str) -> eDoRet:
        """处理特殊指令
        Args:
            code: 要处理的指令代码
        Returns:
            eDoRet: 如果是特殊指令且执行成功，返回对应结果
                 否则返回eDoRet.none，表示不是特殊指令
        """
        try:
            code_lower = code.lower()
            tools = g.Tools()
            
            # 支持>>Ret格式指令，直接返回对应的eDoRet枚举
            if code.startswith('>>'):
                ret_str = code[2:].strip()
                try:
                    # 尝试将字符串转换为eDoRet枚举
                    return self.eDoRet(f'{ret_str}')
                except ValueError:
                    log.e(f"无效的eDoRet值: {ret_str}")
                    return self.eDoRet.none
            
            # 点击指令
            if code_lower == 'click':
                return self.eDoRet.none  # 由外部代码执行点击操作
                
            # 返回操作
            elif code_lower == 'back':
                tools.goBack()
                return self.eDoRet.none
                
            # 回到主页
            elif code_lower == 'home':
                tools.goHome()
                return self.eDoRet.none
                
            # 应用检测
            elif code_lower == 'detect':
                g.App().detect()
                return self.eDoRet.none
            # 页面跳转指令 ->pageName
            elif code.startswith('->'):
                # 提取目标页面名称
                page_name = code[2:].strip()
                if page_name:
                    log.d(f"跳转到页面: {page_name}")
                    # 先停止所有子检查器
                    self._stopAllChildren()
                    
                    # 尝试页面跳转
                    result = g.App().gotoPage(page_name)
                    if result:
                        # 跳转成功后取消当前检查器
                        return self.eDoRet.cancel
                    else:
                        log.e(f"跳转到页面 {page_name} 失败")
            
            return self.eDoRet.none  # 不是特殊指令
        except Exception as e:
            log.ex(e, f"处理特殊指令失败: {code}")
            return self.eDoRet.none  # 出错时视为非特殊指令

    @classmethod
    def _findTemplate(cls, name: str) -> Optional["CChecker_"]:
        """在模板列表中查找指定名称的模板"""
        name = name.lower()
        for template in cls._templates:
            if template.name.lower() == name:
                return template
        return None
    
    @classmethod
    def getTemplate(cls, checkName: str, create: bool = False) -> Optional["CChecker_"]:
        """获取指定名称的模板        
        Args:
            checkName: checker模板名称
            create: 如果不存在是否创建
        Returns:
            CChecker_: 模板对象，如果不存在且不创建则返回None
        """
        checkerName = checkName.strip() if checkName else ''
        if checkerName == '':
            return None
        checkerName = g.App().getCheckName(checkerName)
        return cls._getTemplate(checkerName, create=False)
    
    @classmethod
    def _getTemplate(cls, checkName: str, create: bool = False) -> Optional["CChecker_"]:
        """获取指定名称的模板        
        Args:
            checkName: checker模板名称
            create: 如果不存在是否创建
        Returns:
            CChecker_: 模板对象，如果不存在且不创建则返回None
        """
        checkName = checkName.strip() if checkName else ''
        if checkName == '' :
            return None
        for template in cls._templates:
            if template.name.lower() == checkName:
                return template
        if create:
            # 创建新模板（默认值直接在构造函数中设置）
            template = cls(checkName)
            cls._templates.append(template)
            return template
        return None

    @classmethod
    def getTemplates(cls, pattern: str) -> List["CChecker_"]:
        """获取匹配指定模式的模板列表"""
        pattern = pattern.lower()
        return [t for t in cls._templates if pattern in t.name.lower()]

    @classmethod
    def save(cls):
        """保存checker配置到文件"""
        import os
        try:
            configPath = os.path.join(_G.g.rootDir(), 'config', 'Checks.json')
            
            # 将模板列表转换为可序列化的字典列表
            saveConfig = [template.toConfig() for template in cls._templates]
            # 删除重复的模板
            saveConfig = [t for n, t in enumerate(saveConfig) if t not in saveConfig[n + 1:]]
            saveConfig.sort(key=lambda x: x['name'])        
            with open(configPath, 'w', encoding='utf-8') as f:
                json.dump(saveConfig, f, indent=2, ensure_ascii=False)
            log.i(f"保存{len(saveConfig)}个checker配置")
        except Exception as e:
            log.ex(e, "保存Checks.json失败")

    @classmethod
    def delTemplate(cls, checkName: str = None) -> bool:
        """删除检查器"""
        if not checkName:
            return False
        toDel = next((t for t in cls._templates if t.name.lower() == checkName.lower()), None)
        if not toDel:
            return False
        cls._templates.remove(toDel)
        if toDel.type != 'temp':
            cls._save()
        return True

    @classmethod
    def onLoad(cls, oldCls=None):
        """热加载时的处理"""
        log.i("加载CChecker")
        if oldCls:
            # 转移DEFAULT实例
            cls._DEFAULT = oldCls.DEFAULT
        cls.loadConfig()
        # cls.start()

    @classmethod
    def get(cls, checkerName: str, config: Dict[str, Any] = None, create: bool = True) -> Optional["CChecker_"]:
        """获取指定名称的检查器，此方法现在由App类调用
        
        Args:
            checkerName: 检查器名称
            config: 检查器配置
            create: 如果不存在是否创建
            
        Returns:
            CChecker_: 检查器实例，如果不存在且不创建则返回None
        """
        checkerName = checkerName.lower()
        template = cls.getTemplate(checkerName, False)
        if not template:
            log.e(f"{checkerName} 未定义")
            return None
            
        # 创建新的检查器实例
        if create:
            # 创建新的运行时检查器
            checker = cls(checkerName)
            # 只复制非默认值属性
            config_dict = template.toConfig()
            checker.fromConfig(config_dict)
            
            # 不再在此处添加到全局_checkers列表
            # 由App类的run方法管理检查器列表
            
            # 覆盖额外参数
            if config:
                for k, v in config.items():
                    if hasattr(checker, k):
                        setattr(checker, k, v)
            return checker
        return None
    
    def begin(self, params: Dict[str, Any] = None) -> threading.Thread:
        """异步执行checker.begin()
        """
        self.ret = ''
        thread = threading.Thread(target=self._begin, args=(params,))
        thread.start()
        return thread

    def _begin(self, params: Dict[str, Any] = None):
        """执行检查器
        """
        try:
            if params:
                for k, v in params.items():
                    setattr(self, k, v)
            self._stopAllChildren()
            
            # 确保ret一开始为空，重置强制取消状态
            self.ret = ''
            self.forceCancelled = False
            
            if self._onEnter():
                # 启动子检查器
                self._startChildren()
                # _update方法会设置self.ret
                ret = self._update()
                # 确保返回值与self.ret一致
                if ret != self.ret:
                    self.ret = ret
                
                # 首先检查是否被强制取消，如果是则跳过退出逻辑
                if self.forceCancelled or self.ret == self.eDoRet.cancel.value:
                    # 不执行退出逻辑
                    pass
                else:
                    try:
                        eRet = self.eDoRet(ret)
                        
                        # 只有当返回值不是error和cancel时才执行退出逻辑
                        ok = eRet != self.eDoRet.error and eRet != self.eDoRet.cancel
                        if ok:
                            self._onExit()
                    except Exception as e:
                        # 如果转换失败，默认不执行退出逻辑
                        log.ex(e, f"转换返回值失败: {ret}")
            else:
                log.d(f"检查器 {self.name} 入口检查未通过")
        except Exception as e:
            log.ex(e, f"执行检查器异常: {self.name}")
            self.ret = self.eDoRet.error.value
        finally:
            self._exit()
        return self.ret
    
    def _exit(self):
        """退出检查器"""
        log.d(f"退出 {self.name}")
        self._stopAllChildren()

    def _onExit(self):
        """执行出口逻辑"""
        log.d(f"执行出口逻辑: {self.name}")
        tools.do(self, self.exit)

    def _onEnter(self) -> bool:
        """执行入口代码
        根据当前页面名称执行对应的entry代码，然后进行match匹配
        Returns:
            bool: 入口执行是否成功
        """
        try:
            entryMap = self.entry
            #对entryMap里面的KEY进行tools.do(),根据返回决定是否执行对应的value.
            #如果key为空，则直接执行。
            tools = g.Tools()
            for key, code in entryMap.items():
                ret = key == '' or tools.check(self, key)
                if ret:
                    tools.do(self, code)
                    log.d(f"执行入口代码: {key}=>{code}=>{ret}")
            # 如果entry执行成功，延时3秒后进行匹配
            time.sleep(3)
            return self.Match()
        except Exception as e:
            log.ex(e, f"执行入口代码异常: {self.name}")
            return False
    
    def _update(self) -> str:
        """执行检查器更新逻辑
        0. 循环判定基于checker的enable属性
        1. 匹配event是否存在，成功则执行对应逻辑
        2. 匹配childs里的子检查器，匹配成功则异步执行对应update()
        3. 如果timeout为正数，判定超时，超时直接跳出更新循环
        4. 通过设置enable为False可以结束checker生命周期
        5. 循环跳出后，停止所有子检查器并执行出口逻辑
        Returns:
            str: 执行结果
        """
        startTime = time.time()
        self.enabled = True
        self.children = []
        self.childThreads = []
        self.executedEvents = set()  # 重置已执行事件记录
        try:
            # 主循环，条件是检查器启用状态
            while self.enabled:
                # 首先检查是否被外部强制取消
                if self.forceCancelled:
                    return self.eDoRet.cancel.value
                
                # 检查是否被外部停止，通过ret值判断
                if self.ret != '':
                    return self.ret
                    
                # 处理超时逻辑
                if self.timeout > 0:
                    currentTime = time.time()
                    elapsedTime = currentTime - startTime
                    if elapsedTime > self.timeout:
                        log.d(f"checker {self.name} 超时")
                        break
                # 执行检查器操作
                ret = self.Do()
                # 再次检查是否被外部强制取消（防止Do执行过程中被取消）
                if self.forceCancelled:
                    return self.eDoRet.cancel.value
                
                if ret != '':
                    # 确保强制取消的优先级高于Do的返回值
                    if not self.forceCancelled:
                        return ret
                    else:
                        return self.eDoRet.cancel.value
                time.sleep(1) 
            
            # 如果此时检查到强制取消标志，则返回cancel
            if self.forceCancelled:
                return self.eDoRet.cancel.value
                
            # 处理默认返回值
            ret = self.eDoRet.end.value
            # 确保外部设置的ret不被覆盖
            if self.ret != '' and self.ret != self.eDoRet.none.value:
                ret = self.ret
            else:
                self.ret = ret
            return ret
        except Exception as e:
            log.ex(e, f"执行检查器更新循环异常: {self.name}")
            ret = self.eDoRet.error.value
            self.ret = ret
            return ret
        finally:
            # 确保更新结束时禁用检查器
            self.enabled = False
            # 再次确保所有子检查器都被停止
            self._stopAllChildren()

    
    def _startChildren(self):
        """启动子检查器"""
        if self._childs:
            for childName in self._childs.split(','):
                childName = childName.strip()
                if not childName:
                    continue
                try:
                    # 获取当前应用
                    App = g.App()
                    curApp = App.currentApp()
                    if not curApp:
                        log.e("未找到当前应用，无法启动子检查器")
                        continue
                        
                    # 使用应用的run方法启动子检查器
                    if curApp.run(childName):
                        # 查找已创建的检查器实例
                        for child in curApp._checkers:
                            if child.name.lower() == childName.lower():
                                # 添加到子检查器列表
                                self.children.append(child)
                                break
                except Exception as e:
                    log.ex(e, f"{childName}启动失败: ")

    def _stopAllChildren(self):
        """停止所有子检查器"""
        try:
            # 获取当前应用
            App = g.App()
            curApp = App.currentApp()
            if not curApp:
                log.e("未找到当前应用，无法停止子检查器")
                return
                
            # 获取子检查器名称列表
            childNames = [child.name for child in self.children]
            
            # 使用应用的stop方法停止子检查器
            for childName in childNames:
                curApp.stop(childName)
                
            # 清空子检查器和线程列表
            self.children = []
            self.childThreads = []
        except Exception as e:
            log.ex(e, f"停止子检查器失败")

CChecker_.onLoad()



