from enum import Enum
from typing import Dict, Any, List,  Optional, TYPE_CHECKING
import _G
import datetime
import os
if TYPE_CHECKING:
    from _Page import _Page_
import json
import re
import threading
import time
from CSchedule import CSchedule_
g = _G.g
log = g.Log()


class CChecker_:
    """页面检查器类，用于验证页面状态并执行相应操作"""

    # 存储模板和运行时检查器
    _templates: List["CChecker_"] = None  # 存储所有checker模板
    _checkers: List["CChecker_"] = []     # 存储所有活跃的检查器
    _checkThread: Optional[threading.Thread] = None  # 检查线程
    _running: bool = False  # 线程运行状态
    _lock = threading.Lock()  # 线程安全锁
    _checkInterval: int = 3  # 默认检查间隔(秒)
    
    # 默认值实例，在类初始化时创建
    DEFAULT = None

    @classmethod
    def templates(cls):
        """获取模板列表，如果未加载则先加载"""
        if not cls._templates:
            cls.loadConfig()
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
        self.interval = 0         # 默认检查间隔为0
        self.timeout = 5          # 默认超时为5秒
        self.type = 'once'        # 默认类型为一次性
        self.entry = {}          # 新增：入口代码，页面名为键，执行代码为值
        self.exit = ""           # 新增：出口逻辑，页面名或代码

        # 运行时属性（不会被序列化）
        self.data = data          # 附加数据
        self.pastTime = 0         # 已运行时间
        self.startTime = 0        # 开始时间
        self.lastTime = 0         # 上次检查时间
        self._enabled = False     # 是否启用
        self.children = []        # 存储由当前检查器启动的子检查器
        self.childThreads = []    # 存储子检查器的线程

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
        if 'interval' in config:
            self.interval = config['interval']
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
        default = self.get_default()
        
        # 检查和保存非默认值字段
        if self._match:
            result['match'] = self._match
        if self._childs:
            result['childs'] = self._childs        
        if self.event:  # 只有当有操作时才保存
            result['event'] = self.event.copy()
            
        # 其他属性只有当不是默认值时才保存
        if self.interval != default.interval:
            result['interval'] = self.interval
            
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

    @classmethod
    def get_default(cls) -> "CChecker_":
        """获取默认配置实例"""
        if cls.DEFAULT is None:
            # 创建默认实例
            cls.DEFAULT = cls("__default__")
        return cls.DEFAULT

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
        tools = g.CTools()
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
            tools = g.CTools()
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
        # 无操作
        none = ''
        # 结束schedule
        endSchedule = 'endSchedule'
        # 结束本次check，继续schedule
        end = 'end'
        # 出错
        error = 'error'
    
    # 执行操作
    def Do(self) -> eDoRet:
        try:
            events = self.event.items() if self.event else []
            ret = self.eDoRet.none
            tools = g.CTools()
            log.d(f"{self.name}.Do")
            if len(events) == 0: 
                # 没有操作，直接点击match
                if tools.click(self.match):
                    ret = self.eDoRet.end
                return ret                    
            else:
                for actionName, action in events:
                    # 以$结尾的操作，表示执行后退出
                    actionName = actionName.strip()
                    strs = actionName.split('》')
                    next = self.eDoRet.none
                    if len(strs) > 1:
                        actionName = strs[0]
                        next = self.eDoRet(strs[1])                    
                    if actionName != '':
                        item = tools.matchText(actionName)
                        if item is None and tools.isAndroid():
                            continue
                        if '(?P<' in actionName:
                            m = re.search(actionName, item['t'])
                            # 将m里面的参数设置只能怪self.data里面去
                            for k, v in m.groupdict().items():
                                self.data[k] = v
                    action = action.strip() if action else ''
                    ret = False
                    if action == '':
                        ret = tools.click(actionName)
                    else:
                        codes = action.split(';')
                        for code in codes:
                            code = code.strip()
                            if code.lower() == 'exit':
                                ret = 3
                            elif code.lower() == 'click':
                                ret = tools.click(actionName)
                            elif code.lower() == 'back':
                                ret = tools.goBack()
                            elif code.lower() == 'home':
                                ret = tools.goHome()
                            elif code.lower() == 'detect':
                                ret = g.App().detect()
                            else:
                                if not code.startswith('@'):
                                    code = f'@ {code}'
                                ret = tools.do(self, code)
                if isinstance(ret, str):
                    # 将ret转换为eDoRet
                    ret = self.eDoRet(ret)
                elif not isinstance(ret, self.eDoRet):
                    ret = next if ret else self.eDoRet.none
                return ret
        except Exception as e:
            log.ex(e, f"执行操作失败: {self.event}")
            return self.eDoRet.error

    @classmethod
    def _findTemplate(cls, name: str) -> Optional["CChecker_"]:
        """在模板列表中查找指定名称的模板"""
        name = name.lower()
        for template in cls.templates():
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
        for template in cls.templates():
            if template.name.lower() == checkName:
                return template
        if create:
            # 创建新模板（默认值直接在构造函数中设置）
            template = cls(checkName)
            cls.templates().append(template)
            return template
        return None

    @classmethod
    def getTemplates(cls, pattern: str) -> List["CChecker_"]:
        """获取匹配指定模式的模板列表"""
        pattern = pattern.lower()
        return [t for t in cls.templates() if pattern in t.name.lower()]

    @classmethod
    def save(cls):
        """保存checker配置到文件"""
        import os
        try:
            configPath = os.path.join(_G.g.rootDir(), 'config', 'Checks.json')
            
            # 将模板列表转换为可序列化的字典列表
            saveConfig = [template.toConfig() for template in cls.templates()]
            # 删除重复的模板
            saveConfig = [t for n, t in enumerate(saveConfig) if t not in saveConfig[n + 1:]]
            saveConfig.sort(key=lambda x: x['name'])        
            with open(configPath, 'w', encoding='utf-8') as f:
                json.dump(saveConfig, f, indent=2, ensure_ascii=False)
            log.i(f"保存{len(saveConfig)}个checker配置")
        except Exception as e:
            log.ex(e, "保存Checks.json失败")

    @classmethod
    def check(cls, checkName: str, data: Any):
        """启动指定检查器并覆盖参数"""
        try:
            config = cls._getTemplate(checkName, False)
            if not config:
                return
            childsList = config.childs
            if childsList is None or childsList.strip() == '':
                return
            for childName in childsList.split(','):
                cls._addCheck(childName, data)
        except Exception as e:
            log.ex(e, f"启动检查器 {checkName} 失败")


    @classmethod
    def _addCheck(cls, checkName: str, data: Any):
        """启动指定检查器并覆盖参数"""
        g = _G._G_
        checkName = g.App().getCheckName(checkName)
        checker = cls.get(checkName, create=True)
        if checker is None:
            log.w(f"创建checker失败: {checkName}")
            return
        checker.data = data
        checker.enabled = True
        log.w(f"+ checker: {checkName}")


    @classmethod
    def delete(cls, checkName: str = None) -> bool:
        """删除检查器"""
        if not checkName:
            return False
        templates = CChecker_.templates()
        toDel = next((t for t in templates if t.name.lower() == checkName.lower()), None)
        if not toDel:
            return False
        templates.remove(toDel)     
        CChecker_._save()
        return True

    @classmethod
    def onLoad(cls, oldCls):
        """热加载时的处理"""
        log.i("加载CChecker")
        if oldCls:
            # 保留原有克隆逻辑
            cls.end()
            cls._checkInterval = oldCls._checkInterval
            # 转移DEFAULT实例
            cls.DEFAULT = oldCls.DEFAULT
        cls._templates = None  # 清空模板缓存强制重新加载
        # cls.start()

    @classmethod
    def remove(cls, checker: "CChecker_"):
        """删除检查器"""
        with cls._lock:
            if checker in cls._checkers:
                cls._checkers.remove(checker)

    @classmethod
    def uncheckPage(cls, page: "_Page_"):
        """移除检查器"""
        if page is None:
            return
        for checker in cls._checkers:
            if checker.data == page:
                cls.remove(checker)

    @classmethod
    def get(cls, checkerName: str, config: Dict[str, Any] = None, create: bool = True) -> Optional["CChecker_"]:
        """获取指定名称的检查器"""
        checkerName = checkerName.lower()
        template = cls.getTemplate(checkerName,False)
        if not template:
            log.e(f"{checkerName} 未定义")
            return None
        # 先查找已存在的运行时检查器
        checker = next(
            (checker for checker in cls._checkers if checker.name == checkerName), None)
        if checker is None and create:
            # 创建新的运行时检查器
            checker = cls(checkerName)
            # 只复制非默认值属性
            config_dict = template.toConfig()
            checker.fromConfig(config_dict)
            # 添加到运行时检查器列表
            cls._checkers.append(checker)
            # 覆盖额外参数
            if config:
                for k, v in config.items():
                    if hasattr(checker, k):
                        setattr(checker, k, v)
        return checker
    
    def begin(self, params: Dict[str, Any] = None) -> eDoRet:
        """执行检查器
        """
        if params:
            for k, v in params.items():
                setattr(self, k, v)
        self._stopAllChildren()
        if self._onEnter():
            ret = self._update()
            self._onExit()
            # 停止所有子检查器
            self._stopAllChildren()
            return ret
        return self.eDoRet.error

    def _onExit(self):
        """执行出口逻辑"""
        exitCode = self.exit
        if exitCode:
            try:
                log.d(f"执行出口逻辑: {exitCode}")
                if exitCode.startswith('@'):
                    # 作为代码执行
                    tools.do(self, exitCode)
                else:
                    # 作为页面名称，进行跳转
                    g.App().gotoPage(self.exit)
            except Exception as e:
                log.ex(e, f"执行出口逻辑失败: {exitCode}") 

    def _onEnter(self) -> bool:
        """执行入口代码
        根据当前页面名称执行对应的entry代码，然后进行match匹配
        Returns:
            bool: 入口执行是否成功
        """
        try:
            entryList = self.entry
            if entryList:
                # 匹配并执行entry代码
                curPageName = g.App().currentApp().currentPage.name
                entryCode = next((code for pageName, code in entryList.items() 
                            if re.search(pageName, curPageName)), None) or entryList.get('', None)
                if entryCode:
                    tools = g.CTools()
                    # 执行入口代码
                    ret = tools.do(self, entryCode)
                    log.d(f"执行入口代码: {entryCode}=>{ret}")
                    if not ret:
                        log.w(f"执行入口代码失败: {entryCode}")
                        return False
            # 如果entry执行成功，延时3秒后进行匹配
            time.sleep(3)
            return self.Match()
        except Exception as e:
            log.ex(e, f"执行入口代码异常: {self.name}")
            return False
    
    def _update(self) -> eDoRet:
        """执行检查器更新逻辑
        0. 循环判定基于checker的enable属性
        1. 匹配event是否存在，成功则执行对应逻辑
        2. 匹配childs里的子检查器，匹配成功则异步执行对应update()
        3. 如果timeout为正数，判定超时，超时直接跳出更新循环
        4. 通过设置enable为False可以结束checker生命周期
        5. 循环跳出后，停止所有子检查器并执行出口逻辑
        Returns:
            eDoRet: 执行结果
        """
        startTime = time.time()
        self.enabled = True
        self.children = []
        self.childThreads = []
        try:
            log.i(f"开始执行checker {self.name} 更新循环")
            ret = self.eDoRet.none
            # 主循环，条件是检查器启用状态
            while self.enabled:
                # 处理超时逻辑
                if self.timeout > 0:
                    currentTime = time.time()
                    elapsedTime = currentTime - startTime
                    if elapsedTime > self.timeout:
                        log.d(f"checker {self.name} 超时")
                        break
                # 执行检查器操作
                ret = self.Do()
                if ret == self.eDoRet.end or ret == self.eDoRet.endSchedule:
                    log.d(f"checker {self.name} 结束")
                    break
                elif ret == self.eDoRet.error:
                    raise Exception(f"checker {self.name} 执行出错")
                # 启动子检查器
                self._startChildren()
                # 等待间隔
                time.sleep(1) 
            self._exit()
            return ret
        except Exception as e:
            log.ex(e, f"执行检查器更新循环异常: {self.name}")
            return self.eDoRet.error
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
                    # 获取检查器
                    checker = CChecker_.get(childName, create=True)
                    if checker and checker.Match():
                        log.d(f"匹配到子检查器: {childName}")
                        
                        # 添加到当前检查器的子检查器列表
                        if checker not in self.children:
                            self.children.append(checker)
                        
                        # 异步启动子检查器的update方法
                        thread = threading.Thread(
                            target=checker._update,
                            daemon=True
                        )
                        self.childThreads.append(thread)
                        thread.start()
                except Exception as e:
                    log.ex(e, f"执行子检查器失败: {childName}")

    def _stopAllChildren(self):
        """停止所有子检查器"""
        # 停止所有子检查器
        for child in self.children:
            child.enabled = False        
        # 等待所有子线程结束
        for thread in self.childThreads:
            if thread.is_alive():
                thread.join(1)  # 等待最多1秒
        # 清空子检查器和线程列表
        self.children = []
        self.childThreads = []

    



