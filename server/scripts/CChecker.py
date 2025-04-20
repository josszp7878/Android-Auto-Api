import re
import time
import threading
import json
from typing import Dict, Any, List, Callable, Optional, TYPE_CHECKING
import _G
if TYPE_CHECKING:
    from _Page import _Page_
    from CTools import CTools_
g = _G.g
log = g.Log()
tools: "CTools_" = g.Tools()


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
        self._checks = None      # 检查器列表
        self.do = {}        # 默认操作为空
        self.interval = 0         # 默认检查间隔为0
        self.timeout = 5          # 默认超时为5秒
        self.type = 'once'        # 默认类型为一次性

        # 运行时属性（不会被序列化）
        self.data = data          # 附加数据
        self.pastTime = 0         # 已运行时间
        self.startTime = 0        # 开始时间
        self.lastTime = 0         # 上次检查时间
        self._enabled = False     # 是否启用

        # 如果有配置，则更新属性
        if config:
            self.update_from_dict(config)

    def update_from_dict(self, config: Dict[str, Any]):
        """从字典更新属性，只更新存在的字段"""
        if 'do' in config and config['do']:
            self.do = config['do'].copy() if isinstance(config['do'], dict) else {}
        if 'match' in config and config['match']:
            self._match = config['match']
        if 'checks' in config and config['checks']:
            self._checks = config['checks']
        if 'interval' in config:
            self.interval = config['interval']
        if 'timeout' in config:
            self.timeout = config['timeout']
        if 'type' in config:
            self.type = config['type']
        return self

    def to_dict(self) -> Dict[str, Any]:
        """将对象转换为可序列化的字典，只保存非默认值"""
        result = {'name': self.name}  # 名称是必须的
        
        # 确保DEFAULT实例已初始化
        default = self.get_default()
        
        # 检查和保存非默认值字段
        if self._match:
            result['match'] = self._match
        if self._checks:
            result['checks'] = self._checks        
        if self.do:  # 只有当有操作时才保存
            result['do'] = self.do.copy()
            
        # 其他属性只有当不是默认值时才保存
        if self.interval != default.interval:
            result['interval'] = self.interval
            
        if self.timeout != default.timeout:
            result['timeout'] = self.timeout
            
        if self.type != default.type:
            result['type'] = self.type
            
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
        
    def addProp(self, prop: str, value: str, value1: str = None)->bool:
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
                value = CChecker_._addStrListProp(self._match, split, value, range)
                if value:
                    self._match = value
                    log.d(f"_match: {oldVal} => {self._match}")
            elif 'che' in prop:
                oldVal = self._checks
                value = CChecker_._addStrListProp(self._checks, ',', value, value1)
                if value:
                    self._checks = value
                    log.d(f"_checks: {oldVal} => {self._checks}")
            elif 'do' in prop:
                oldVal = self.do
                self.do[value] = value1
                log.d(f"do: {oldVal} => {self.do}")
            else:
                log.e(f"不支持add的属性: {prop}")
                return False
            return True
        except Exception as e:
            log.ex(e, f"add{prop}失败: {value}")
            return False
        
    def removeProp(self, prop: str, value: str)->bool:
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
            elif 'che' in prop:
                oldVal = self._checks
                split = ','
                value = value.strip(split)
                value = CChecker_._delStrListProp(self._checks, split, value)
                if value:
                    self._checks = value
                    log.d(f"_checks: {oldVal} => {self._checks}")
            elif 'do' in prop:
                oldVal = self.do
                self.do.pop(value)
                log.d(f"do: {oldVal} => {self.do}")
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
        #从当前屏幕获取match文字对应的坐标
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
    def _addStrListProp(cls, curVal:str, split:str, value: str, range: str = None):
        #为了支持已有ITEM的替换，先将match转换为列表
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
    def _delStrListProp(cls, curVal:str, split:str, value: str):
        #为了支持已有ITEM的替换，先将match转换为列表
        if curVal:
            return re.sub(rf'[{split}\s]*{value}', '', curVal)
        return curVal


    @property
    def checks(self) -> List[str]:
        return self._checks

    @checks.setter
    def checks(self, value: List[str]):
        self._checks = value

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        log.d(f"设置检查器 {self.name} 状态为 {value}")
        if value:
            self.startTime = time.time()
            self.lastTime = 0
    
    def Match(self)->bool:
        """执行检查逻辑
        Returns:
            bool: 检查是否通过
        """
        result = False
        try:
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
    
    Exit = 'exit'
    # 执行操作
    # 返回True表示执行完成，可以退出，False表示执行失败，继续check.直到TIMEOUT
    def Do(self) -> bool:
        try:
            endDo = len(self.do) <= 1
            actions = self.do
            if not actions: 
                #没有操作，直接点击match
                return tools.click(self.match)
            for actionName, action in self.do.items():
                # 以$结尾的DO操作，表示执行后退出
                actionName = actionName.strip()
                if actionName.endswith('$'):
                    endDo = True
                    actionName = actionName[:-1]
                if actionName != '':
                    item = tools.matchText(actionName)
                    if item is None and tools.isAndroid():
                        continue
                    if '(?P<' in actionName:
                        m = re.search(actionName, item['t'])
                        #将m里面的参数设置只能怪self.data里面去
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
                        if code.lower() == self.Exit:
                            ret = self.Exit
                        elif code.lower() == 'click':
                            ret = tools.click(actionName)
                        elif code.lower() == 'back':
                            ret = tools.goBack()
                        elif code.lower() == 'home':
                            ret = tools.goHome()
                        elif code.lower() == 'detect':
                            ret = g.App().detect()
                        else:
                            if not code.startswith('{'):
                                code = f'{{ {code} }}'
                            ret = tools.do(self, code)
                if ret == self.Exit:
                    return True
                if ret:
                    return endDo
        except Exception as e:
            log.ex(e, f"执行操作失败: {self.do}")
        return False

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
            saveConfig = [template.to_dict() for template in cls.templates()]
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
            config = cls.getTemplate(checkName, False)
            if not config:
                return
            checks = config.checks
            if checks is None or checks.strip() == '':
                return
            for check in checks.split(','):
                cls._addCheck(check, data)
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
        cls.start()

    @classmethod
    def remove(cls, checker: "CChecker_"):
        """删除检查器"""
        with cls._lock:
            if checker in cls._checkers:
                cls._checkers.remove(checker)

    @classmethod
    def start(cls, interval: int = None):
        """启动定期检查线程
        Args:
            interval: 检查间隔(秒)，如果为None则使用默认值
        """
        try:
            if cls._checkThread and cls._checkThread.is_alive():
                return False

            if interval is not None:
                cls._checkInterval = max(1, interval)  # 确保间隔至少为1秒
            cls._checkers = []
            cls._running = True
            cls._checkThread = threading.Thread(target=cls._loop, daemon=True)
            cls._checkThread.start()
            log.i(f"启动检查线程，间隔{cls._checkInterval}秒")
            return True
        except Exception as e:
            log.ex(e, "启动检查线程失败")
            return False

    @classmethod
    def end(cls):
        """停止定期检查线程"""
        try:
            with cls._lock:
                cls._running = False
                if cls._checkThread and cls._checkThread.is_alive():
                    cls._checkThread.join(1.0)  # 等待线程结束，最多1秒
                # log.i("停止检查线程")
                return True
        except Exception as e:
            log.ex(e, "停止检查线程失败")
            return False

    @classmethod
    def _loop(cls):
        """检查线程主循环"""
        log.i("检查线程开始运行")
        while cls._running:
            try:
                # 复制检查器列表以避免迭代时修改
                checkers = cls._checkers
                currentTime = time.time()

                i = 0  # 初始化i变量
                while i < len(checkers):
                    checker = checkers[i]
                    if not cls._running:
                        break
                    if not checker.enabled:
                        i += 1
                        continue
                    # 检查是否到达检查间隔时间
                    deltaTime = currentTime - checker.lastTime
                    if checker.interval > 0 and deltaTime < checker.interval:
                        i += 1  # 增加索引
                        continue  # 未到达检查间隔，跳过此检查器
                    # 检查是否超时
                    checker.pastTime = currentTime - checker.startTime
                    if checker.type != 'deamon':
                        if checker.timeout > 0 and checker.pastTime > checker.timeout:
                            log.d(f"检查器 {checker.name} 超时")
                            checker.enabled = False
                            i += 1
                            continue    # 跳过此检查器
                    try:
                        # 更新上次检查时间
                        checker.lastTime = currentTime
                        ret = checker.Match()
                        if ret:
                            if checker.Do():
                                if checker.type == 'temp':
                                    checkers.remove(checker)
                                elif checker.type == 'once':
                                    checker.enabled = False
                        i += 1  # 增加索引
                    except Exception as e:
                        log.ex(e, f"执行检查器 {checker.name} 出错")
                        i += 1  # 即使出错也要增加索引

                time.sleep(1)
            except Exception as e:
                log.ex(e, "检查线程异常")
                time.sleep(1)  # 发生异常时短暂暂停
        log.i("检查线程已停止")

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
            config_dict = template.to_dict()
            checker.update_from_dict(config_dict)
            # 添加到运行时检查器列表
            cls._checkers.append(checker)
            # 覆盖额外参数
            if config:
                for k, v in config.items():
                    if hasattr(checker, k):
                        setattr(checker, k, v)
        return checker
