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
    
    _checkers: List["CChecker_"] = []  # 存储所有活跃的检查器
    _templates: Dict[str, Dict[str, Any]] = {}  # 存储所有checker模板配置
    _checkThread: Optional[threading.Thread] = None  # 检查线程
    _running: bool = False  # 线程运行状态
    _checkInterval: int = 3  # 默认检查间隔(秒)
    _lock = threading.Lock()  # 线程安全锁
    _pageChecker: Optional["CChecker_"] = None  # 页面检测器实例
    _appChecker: Optional["CChecker_"] = None  # 应用检测器实例
    
    # 事件处理相关
    _pageDetectListeners: List[Callable[["_Page_"], None]] = []  # 页面检测事件监听器列表

    def __init__(self, name: str, config: Dict[str, Any], data=None):
        """初始化检查器
        
        Args:
            name: 检查器名称
            config: 检查器配置字典
            data: 检查器数据(可选)
        """
        self.name = name.lower()
        self.data = data
        self._actions:dict[str, str] = config.get('do', {})
        self._check = config.get('check', name)
        self.interval = config.get('interval', 0)
        self.timeout = config.get('timeout', 5)
        self.startTime = 0  # 初始化时设置开始时间
        self.lastTime = 0  # 上次检查时间
        self.onResult: Optional[Callable[[bool], None]] = None  # 默认回调函数
        self._enabled = False
        self.type = config.get('type', 'temp')
    
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
            self.lastTime = time.time()

    def check(self):
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
        
        
    # 执行操作 
    # 返回True表示执行完成，可以退出，False表示执行失败，继续check.直到TIMEOUT
    def do(self)->bool:
        try:
            for actionName, action in self._actions.items():
                #以$结尾的DO操作，表示执行后退出
                actionName = actionName.strip()
                endDo = actionName.startswith('@')
                if endDo:
                    actionName = actionName[1:]
                if actionName == '' or tools.matchText(actionName):
                    action = action.strip()
                    if action == '':
                        tools.click(actionName)
                    else:
                        codes = action.split(';')
                        for code in codes:
                            code = code.strip()
                            if code.lower() == 'exit':
                                return True
                            elif code.lower() == 'click':
                                tools.click(actionName)
                            else:
                                if not code.startswith('{'):
                                    code = f'{{ {code} }}'
                                result = tools.eval(self, code)
                                if str(result).lower() == 'exit':
                                    return True
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
    def _add(cls, checkerName: str, config: Dict[str, Any], page=None) -> Optional["CChecker_"]:
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
        checker.data = page
        with cls._lock:
            cls._checkers.append(checker)
        return checker
    
    @classmethod
    def add(cls, checkerName: str, page=None, config: Dict[str, Any] = None) -> Optional["CChecker_"]:
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
        return cls._add(checkerName, actConfig, page)
    
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
                _Log.c.i("检查线程已在运行中")
                return False
            
            if interval is not None:
                cls._checkInterval = max(1, interval)  # 确保间隔至少为1秒
            cls._addPageChecker()
            cls._addAppChecker()  # 添加应用检测器
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
    def stop(cls, checkerName: str) -> bool:
        """获取指定名称的检查器"""
        checkerName = checkerName.lower()
        checkers = [checker for checker in cls._checkers if checker.name == checkerName]
        if len(checkers) == 0:
            return False
        for checker in checkers:
            checker.enabled = False
        return True
    
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
                    pastTime = currentTime - checker.startTime 
                    # log.d(f"检查器 {checker.name} 超时: {pastTime} > {checker.timeout}")
                    if checker.timeout > 0 and pastTime > checker.timeout:
                        log.d(f"检查器 {checker.name} 超时")
                        checker.enabled = False
                        i += 1
                        continue
                    try:
                        # 更新上次检查时间
                        checker.lastTime = currentTime
                        ret = checker.check()
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


    def _detectPage(self) -> bool:
        page = self.data
        App = _G._G_.App()
        app = App.detectCurApp()
        if app:
            page = app.detectPage(page)
            # 触发页面检测事件
            self._onPageDetect(page)

        return False
    
    @classmethod
    def _onPageDetect(cls, page):
        """触发页面检测事件
        
        Args:
            page: 检测到的页面对象
        """
        if page:
            for listener in cls._pageDetectListeners:
                try:
                    listener(page)
                except Exception as e:
                    log.ex(e, "执行页面检测事件监听器出错")
    
    @classmethod
    def listenPageDetect(cls, listener: Callable[["_Page_"], None]):
        """添加页面检测事件监听器
        
        Args:
            listener: 页面检测事件监听器函数，接收检测到的页面对象作为参数
        """
        if listener not in cls._pageDetectListeners:
            cls._pageDetectListeners.append(listener)
            return True
        return False
    
    @classmethod
    def unListenPageDetect(cls, listener: Callable[["_Page_"], None]):
        """移除页面检测事件监听器
        
        Args:
            listener: 要移除的页面检测事件监听器函数
        """
        if listener in cls._pageDetectListeners:
            cls._pageDetectListeners.remove(listener)
            return True
        return False

    pageChackerInterval = 3
    @classmethod
    def _addPageChecker(cls)->"CChecker_":
        """确保页面检测器已创建"""
        checkName = "检测页面"
        if cls._pageChecker is None:
            config = {
                'do': {'' : '{this._detectPage()}'},
                'type': 'always',
                'interval': cls.pageChackerInterval,
            }
            cls._templates[checkName] = config
            checker = cls._add(checkName, config)
            checker.enabled = True
            cls._pageChecker = checker
        return checker
   
