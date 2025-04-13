import time
import threading
from typing import Dict, Any, List, Callable, Optional, TYPE_CHECKING
import _G
import _Log
if TYPE_CHECKING:
    from _Page import _Page_
    from CTools import CTools_
g = _G.g
log = g.Log()
tools: "CTools_" = g.Tools()


class CChecker_:
    """页面检查器类，用于验证页面状态并执行相应操作"""

    _templates: Dict[str, Dict[str, Any]] = {}  # 存储所有checker模板配置
    _checkInterval: int = 3  # 默认检查间隔(秒)

    _checkers: List["CChecker_"] = []  # 存储所有活跃的检查器
    _checkThread: Optional[threading.Thread] = None  # 检查线程
    _running: bool = False  # 线程运行状态
    _lock = threading.Lock()  # 线程安全锁

    # 默认配置（新增）
    DEFAULT_CONFIG = {
        'check': '',
        'do': {},
        'interval': 0,
        'timeout': 5,
        'type': 'temp'
    }

    


    def __init__(self, name: str, config: Dict[str, Any], data=None):
        """初始化检查器

        Args:
            name: 检查器名称
            config: 检查器配置字典
            data: 检查器数据(可选)
        """
        self.name = name.lower()
        self.data = data
        self._actions: dict[str, str] = config.get('do', {})
        self._check = config.get('check', name)
        self.interval = config.get('interval', 0)
        self.timeout = config.get('timeout', 5)
        self.pastTime = 0
        self.startTime = 0  # 初始化时设置开始时间
        self.lastTime = 0  # 上次检查时间
        self.onResult: Optional[Callable[[bool], None]] = None  # 默认回调函数
        self._enabled = False
        self.type = config.get('type', 'temp')

        # 应用默认配置（新增）
        for k, v in self.DEFAULT_CONFIG.items():
            if k not in config:
                setattr(self, k, v)
        # 覆盖自定义配置
        for k, v in config.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def __str__(self):
        return f"{self.name} {self._check}"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        log.d(f"设置检查器 {self.name} 状态为 {value}")
        if value:
            self.startTime = time.time()
            self.lastTime = 0

    def _setMatch(self, check: str) -> bool:
        """设置检查"""
        if not self._editChecker:
            return False
        self._check = check
        return True

    def _addDo(self, check: str, action: str) -> bool:
        """添加操作"""
        # 更新新配置
        self._actions.update({check: action})
        return True

    def _check(self):
        """执行检查逻辑
        Returns:
            bool: 检查是否通过
        """
        result = False
        try:
            if self._check == '':
                return True
            log.d(f"执行检查器: {self.name}")
            result = tools.check(self, self._check)
            if not result:
                # 否则检查文本规则
                result = tools.matchText(self._check)
        except Exception as e:
            log.ex(e, f"执行检查器失败: {self._check}")
            result = False
        if result and self.onResult:
            # 如果检查器结果为True，则执行回调函数,否则继续check.直到TIMEOUT
            self.onResult(result)
            self.onResult = None
        return result

    Exit = 'exit'
    # 执行操作
    # 返回True表示执行完成，可以退出，False表示执行失败，继续check.直到TIMEOUT
    def do(self) -> bool:
        try:
            endDo = len(self._actions) <= 1
            for actionName, action in self._actions.items():
                # 以$结尾的DO操作，表示执行后退出
                actionName = actionName.strip()
                if actionName.startswith('@'):
                    endDo = True
                    actionName = actionName[1:]
                if actionName != '' and tools.matchText(actionName) == None:
                    continue
                action = action.strip()
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
            log.ex(e, f"执行操作失败: {self._actions}")
        return False

    @classmethod
    def loadTemplates(cls, templates: Dict[str, Dict[str, Any]]):
        """加载checker模板配置

        Args:
            templates: 包含所有模板配置的字典 {模板名: 配置}
        """
        for name, config in templates.items():
            cls._templates[name] = config
        log.i(f"已加载{len(templates)}个checker模板")

    @classmethod
    def _add(cls, checkerName: str, config: Dict[str, Any]) -> Optional["CChecker_"]:
        """创建并注册checker到全局列表        
        Args:
            checkerName: checker模板名称
            config: 覆盖模板的配置参数(可选)
            page: 关联的页面(可选)

        Returns:
            CChecker_: 创建的checker实例，如果创建失败则返回None
        """
        checker = cls(checkerName, config)
        log.d(f"添加checker: {checkerName}")
        with cls._lock:
            cls._checkers.append(checker)
        return checker

    @classmethod
    def add(cls, checkerName: str, config: Dict[str, Any] = None) -> Optional["CChecker_"]:
        """创建并注册checker到全局列表        
        Args:
            checkerName: checker模板名称
            page: 关联的页面(可选)
            config: 覆盖模板的配置参数(可选)

        Returns:
            CChecker_: 创建的checker实例，如果创建失败则返回None
        """
        template = cls._templates.get(checkerName, None)
        actConfig = config
        if template:
            # 合并模板和自定义配置
            actConfig = template.copy()
            if config and config != {}:
                actConfig.update(config)
        if actConfig is None:
            log.w(f"缺少checker配置: {checkerName}")
            return None
        return cls._add(checkerName, actConfig)

    @classmethod
    def remove(cls, checker: "CChecker_"):
        """删除检查器"""
        with cls._lock:
            cls._checkers.remove(checker)

    @classmethod
    def start(cls, interval: int = None):
        """启动定期检查线程
        Args:
            interval: 检查间隔(秒)，如果为None则使用默认值
        """
        try:
            if cls._checkThread and cls._checkThread.is_alive():
                # _Log.c.i("检查线程已在运行中")
                return False

            if interval is not None:
                cls._checkInterval = max(1, interval)  # 确保间隔至少为1秒
            cls._checkers = []
            # cls._initDetecter()
            cls._running = True
            cls._checkThread = threading.Thread(target=cls._loop, daemon=True)
            cls._checkThread.start()
            _Log.c.i(f"启动检查线程，间隔{cls._checkInterval}秒")
            return True
        except Exception as e:
            _Log.c.ex(e, "启动检查线程失败")
            return False

    @classmethod
    def end(cls):
        """停止定期检查线程"""
        try:
            with cls._lock:
                cls._running = False
                if cls._checkThread and cls._checkThread.is_alive():
                    cls._checkThread.join(1.0)  # 等待线程结束，最多1秒
                _Log.c.i("停止检查线程")
                return True
        except Exception as e:
            _Log.c.ex(e, "停止检查线程失败")
            return False

    @classmethod
    def get(cls, checkerName: str, config: Dict[str, Any] = None, create: bool = True) -> Optional["CChecker_"]:
        """获取指定名称的检查器"""
        checkerName = checkerName.lower()
        checker = next(
            (checker for checker in cls._checkers if checker.name == checkerName), None)
        if checker is None and create:
            checker = cls.add(checkerName, config)
        return checker

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
                        # log.d(f"检查器 {checker.name} 超时: {pastTime} > {checker.timeout}")
                        if checker.timeout > 0 and checker.pastTime > checker.timeout:
                            log.d(f"检查器 {checker.name} 超时")
                            checker.enabled = False
                            i += 1
                            continue    # 跳过此检查器
                    try:
                        # 更新上次检查时间
                        checker.lastTime = currentTime
                        ret = checker._check()
                        if ret:
                            # log.i(f"检查器 {checker.name} 匹配成功，执行操作")
                            if checker.do():
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

    # ##############################################################
    # # 应用页面检测器
    # ##############################################################
    # detectTimeout = 10
    # detectName = '页面检测'
    # _detecter: Optional["CChecker_"] = None  # 页面检测器实例
    # def _detect(self) -> bool:
    #     page = self.data
    #     App = _G._G_.App()
    #     app = App.detectCurApp()
    #     pageName = ''
    #     if app:
    #         page = app.detectPage(page)
    #         if page:
    #             pageName = page.name
    #     log.i(f"当前页面: {App.getCurAppName()}.{pageName}")
    #     return False

    # @classmethod
    # def _initDetecter(cls) -> "CChecker_":
    #     """确保页面检测器已创建"""
    #     if cls._detecter is None:
    #         checker = cls.get(cls.detectName, {
    #             'check': '', #必须设置空，否则会把名字当初检查条件
    #             'do': {'': '{this._detect()}'},
    #             'type': 'once',
    #             'timeout': cls.detectTimeout,
    #             'interval': 3,
    #         }, True)
    #         cls._detecter = checker
    #     return cls._detecter
    
    # @classmethod
    # def detect(cls, timeout: int = 3):
    #     """等待页面检测器检测到页面"""
    #     if timeout is None:
    #         timeout = cls.detectTimeout
    #     cls._detecter.enabled = True
    #     cls._detecter.timeout = timeout
    #     time.sleep(timeout)
    # ##############################################################

    @classmethod
    def loadConfig(cls):
        """加载checker配置文件"""
        import os
        import json
        try:
            configPath = os.path.join(_G.g.rootDir(), 'config', 'Checks.json')
            with open(configPath, 'r', encoding='utf-8') as f:
                configs = json.load(f)
                for name, cfg in configs.items():
                    # 合并默认配置和文件配置
                    merged = cls.DEFAULT_CONFIG.copy()
                    merged.update(cfg)
                    cls._templates[name] = merged
                log.i(f"加载{len(configs)}个checker配置")
        except Exception as e:
            log.ex(e, "加载Checks.json失败")

    @classmethod
    def saveConfig(cls):
        """保存checker配置到文件"""
        import os
        import json
        try:
            configPath = os.path.join(_G.g.rootDir(), 'config', 'Checks.json')
            # 过滤默认值并生成精简配置
            saveConfig = {}
            for name, cfg in cls._templates.items():
                filtered = {k:v for k,v in cfg.items() 
                           if v != cls.CChecker_.get(k, None)}
                if filtered:
                    saveConfig[name] = filtered
            with open(configPath, 'w', encoding='utf-8') as f:
                json.dump(saveConfig, f, indent=2, ensure_ascii=False)
            log.i(f"保存{len(saveConfig)}个checker配置")
        except Exception as e:
            log.ex(e, "保存Checks.json失败")

    @classmethod
    def check(cls, checkName: str, param: dict = None):
        """启动指定检查器并覆盖参数"""
        checker = cls.get(checkName, param, True)
        if checker:
            # 覆盖参数
            if param:
                for k, v in param.items():
                    if hasattr(checker, k):
                        setattr(checker, k, v)
            checker.enabled = True
            return checker
        return None

    _editChecker: Optional["CChecker_"] = None  # 新增类变量存储编辑状态

    @classmethod
    def _startEdit(cls, checkName: str) -> bool:
        """启动编辑检查器"""
        checker = cls.get(checkName, create=True)
        if not checker:
            return False
        
        # 深拷贝配置（修复参数错误）
        cls._editChecker = CChecker_(
            name=checker.name,
            config={
                'check': checker._check,
                'do': dict(checker._actions),  # 使用dict确保深拷贝
                'interval': checker.interval,
                'timeout': checker.timeout,
                'type': checker.type
            }
        )
        return True

    @classmethod
    def _endEdit(cls, cancel: bool = False) -> bool:
        """结束编辑"""
        if not cls._editChecker:
            return False
        
        try:
            if not cancel:
                # 保存到模板配置
                newConfig = {
                    'check': cls._editChecker._check,
                    'do': cls._editChecker._actions,
                    'interval': cls._editChecker.interval,
                    'timeout': cls._editChecker.timeout,
                    'type': cls._editChecker.type
                }
                # 过滤默认值
                filtered = {
                    k: v for k, v in newConfig.items()
                    if v != cls.DEFAULT_CONFIG.get(k, None)
                }
                cls._templates[cls._editChecker.name] = filtered
                cls.saveConfig()
            return True
        finally:
            cls._editChecker = None

    @classmethod
    def _delete(cls, checkName: str) -> bool:
        """删除检查器"""
        checkName = checkName.lower()
        if checkName in cls._templates:
            try:
                del cls._templates[checkName]
                # 同时删除正在运行的检查器
                with cls._lock:
                    cls._checkers = [c for c in cls._checkers if c.name != checkName]
                cls.saveConfig()
                return True
            except Exception as e:
                log.ex(e, f"删除检查器 {checkName} 失败")
        return False

  # === 核心功能方法 ===
    # ... saveConfig、check、startEdit、edit、endEdit、delete 等方法 ...

    # === 指令注册和克隆方法（放在类定义末尾）===
    @classmethod
    def registerCommands(cls):
        """注册检查器相关指令（补充参数校验）"""
        from _CmdMgr import regCmd
        import json

        @regCmd(r"#开始编辑|ksbj(?P<checkName>\S+)")
        def startEditCheck(checkName):
            if not checkName.strip():
                return "e~检查器名称不能为空"
            return cls._startEdit(checkName);

        @regCmd(r"如果|rg|if\s*(?P<check>.+?)\s*就(?P<do>\{.*\})")
        def addDo(check, do):
            return cls._editChecker._addDo(check, do)
        
        @regCmd(r"#设置匹配|szpp(?P<match>.+)")
        def setMatch(match):
            return cls._editChecker._setMatch(match)

        @regCmd(r"#结束编辑|jsbj (?P<cancel>[01])")
        def endEditCheck(cancel='0'):
            return f"e~{cls._endEdit(cancel=bool(int(cancel)))}"

        @regCmd(r"#删除检查|scjc (?P<checkName>\S+)")
        def delCheck(checkName):
            return f"e~{cls._delete(checkName)}"

        @regCmd(r"#检查列表|jclb")
        def listCheck():
            return "当前检查器列表：\n" + "\n".join(
                f"{name}（{len(cfg['do'])}个操作）" 
                for name, cfg in cls._templates.items()
            )
        
        @regCmd(r"#显示检查|xscj (?P<checkName>\S+)")
        def showCheck(checkName):
            checker = cls.get(checkName, create=False)
            if checker: 
                return f"检查器 {checkName} 配置：\n" + json.dumps(checker._actions, indent=2, ensure_ascii=False)
            return f"检查器 {checkName} 不存在"

        @regCmd(r"#检查|jc (?P<checkerName>\S+)(?:\s+(?P<enabled>\S+))?")
        def check(checkerName, enabled=None):
            """
            功能：停止指定名称的检查器
            指令名: check-c
            中文名: 检查-jc
            参数: checkerName - 检查器名称
            示例: 检查 每日签到
            """ 
            g = _G._G_
            enabled = g.Tools().toBool(enabled, True)
            checkerName = checkerName.lower()
            if checkerName.startswith('@'):
                checkerName = checkerName[1:].strip()
                # 检查应用和页面，格式为app.page
                page = g.App().getAppPage(checkerName)
                if page:
                    page.check()
                    return f"已经开始检查页面 {page.name}"
            elif checkerName.startswith('!'):
                pageName = checkerName[1:].strip()
                g.App().currentApp().detectPage(pageName)
                return "已关闭当前应用"

            # 检查器
            checker = cls.get(checkerName, create=True)
            # log.i(f"checker.config = {checker._actions}")
            if checker:
                checker.enabled = enabled
                return f"检查器 {checkerName} 已设置为 {enabled}"
            else:
                return f"e~无效检查器: {checkerName}"
    
    @classmethod
    def onLoad(cls, oldCls):
        log.i("加载CChecker")
        cls.registerCommands()
        if oldCls:
            # 保留原有克隆逻辑
            cls.end()
            cls._templates = oldCls._templates.copy()
            cls._checkInterval = oldCls._checkInterval
        else:
            cls.loadConfig()
        cls.start()
    
CChecker_.onLoad(None)