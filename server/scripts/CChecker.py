import time
import threading
from typing import Dict, Any, List, Callable, Optional
import _G
import _Log


class CChecker_:
    """页面检查器类，用于验证页面状态并执行相应操作"""
    
    _checkers = []  # 存储所有活跃的检查器
    _checkThread = None  # 检查线程
    _running = False  # 线程运行状态
    _checkInterval = 3  # 默认检查间隔(秒)
    _lock = threading.Lock()  # 线程安全锁
    _pageChecker = None  # 页面检测器实例
    _appChecker = None  # 应用检测器实例

    
    def __init__(self, name: str, config: Dict[str, Any], page=None):
        """初始化检查器
        
        Args:
            name: 检查器名称
            config: 检查器配置字典
            page: 所属页面
        """
        self.name = name
        self.page = page
        self._action = config.get('do', '')
        self._check = config.get('check', name)
        self.interval = config.get('interval', 0)
        self.timeout = config.get('timeout', 0)
        self.startTime = time.time()  # 初始化时设置开始时间
        self.lastCheckTime = 0  # 上次检查时间
        self.onResult = None  # 默认回调函数
        self.enabled = True  # 是否启用

    @property
    def pastTime(self) -> int:
        return int(time.time() - self.startTime)

    def check(self):
        """执行检查逻辑
        Returns:
            bool: 检查是否通过
        """
        try:
            if self._check == '': 
                return True
            if self.timeout > 0 and self.pastTime > self.timeout:
                _Log.c.d(f"检查器 {self.name} 超时")
                self.callResult(False)
                self.enabled = False
                return True
            g = _G._G_
            tools = g.Tools()
            # 当代码执行，返回结果为PASS时，表示执行成功·
            ret = tools.eval(self, self._check)
            if ret != 'PASS':
                return ret
            # 否则检查文本规则
            # log.d(f"执行检查器文本规则: {rule}")
            ret = tools.matchText(self._check)
            if not ret:
                _Log.c.d(f"检查器文本规则不匹配: {self._check}")
                return False
            self.callResult(True)
            return True
        except Exception as e:
            _Log.c.ex(e, f"执行检查器失败: {self._check}")
            return False
        
    def callResult(self, result: bool):
        if self.onResult:
            self.onResult(result)
            self.onResult = None
        
    def do(self):
        _G._G_.Tools().eval(self, self._action)
    
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
    def stop(cls):
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
    def _loop(cls):
        """检查线程主循环"""
        log = _G._G_.Log()
        log.i("检查线程开始运行")
        
        while cls._running:
            try:
                # 复制检查器列表以避免迭代时修改
                active_checkers = cls.gets()
                current_time = time.time()
                
                i = 0  # 初始化i变量
                while i < len(active_checkers):
                    checker = active_checkers[i]
                    if not cls._running or not checker.enabled:
                        break
                    # 检查是否到达检查间隔时间
                    deltaTime = current_time - checker.lastCheckTime
                    if checker.interval > 0 and deltaTime < checker.interval:
                        i += 1  # 增加索引
                        continue  # 未到达检查间隔，跳过此检查器
                    try:
                        # 更新上次检查时间
                        checker.lastCheckTime = current_time
                        ret = checker.check()
                        if ret:
                            log.i(f"检查器 {checker.name} 匹配成功，执行操作")
                            checker.do()
                        i += 1  # 增加索引
                    except Exception as e:
                        log.ex(e, f"执行检查器 {checker.name} 出错")
                        i += 1  # 即使出错也要增加索引
                
                time.sleep(0.5)                    
            except Exception as e:
                log.ex(e, "检查线程异常")
                time.sleep(1)  # 发生异常时短暂暂停
        
        log.i("检查线程已停止")
    
    @classmethod
    def add(cls, checker):
        """注册检查器到全局列表
        Args:
            checker: 要注册的检查器实例
        """
        with cls._lock:
            if checker not in cls._checkers:
                cls._checkers.append(checker)
                return True
            return False

    
    @classmethod
    def remove(cls, checker):
        """从全局列表中移除检查器
        
        Args:
            checker: 要移除的检查器实例
        """
        with cls._lock:
            if checker in cls._checkers:
                cls._checkers.remove(checker)
                return True
            return False
    
    @classmethod
    def gets(cls) -> List["CChecker_"]:
        """获取所有活跃的检查器
        
        Returns:
            检查器实例列表
        """
        with cls._lock:
            return cls._checkers.copy()
    
    @classmethod
    def _pageCheck(cls) -> bool:
        App = _G._G_.App()
        curApp = App.getCurApp()
        if curApp is None:
            return False
        page = curApp.rootPage.detectPage()
        return page is not None
    

    @classmethod
    def _addPageChecker(cls):
        """确保页面检测器已创建"""
        if cls._pageChecker is None:
            config = {
                'check': "{this._pageCheck()}",
                'interval': 3
            }
            checker = cls("页面检测器", config)
            cls._pageChecker = checker
            cls.add(checker)
            checker.enabled = False
            _Log.c.i("创建页面检测器")
    
    
    @classmethod
    def checkCurPage(cls, callback: Callable[[bool], None], timeout: int = None) -> bool:
        """设置要检测的目标页面
        
        Args:
            callback: 检测结果回调函数
            timeout: 超时时间(秒)
            
        Returns:
            bool: 是否成功设置检测
        """
        with cls._lock:
            # 设置目标页面和回调
            checker = cls._pageChecker
            checker.timeout = timeout or 3
            checker.onResult = callback
            return True
        
    @classmethod
    def _appCheck(cls) -> bool:
        checker = cls._appChecker
        App = _G._G_.App()
        if not App.detectCurApp():
            return False
        if checker.name == App.getCurAppName():
            return False
        return True

    @classmethod
    def _addAppChecker(cls):
        """确保应用检测器已创建"""
        if cls._appChecker is None:
            config = {
                'check': "{this._appCheck()}",
                'interval': 3
            }
            checker = cls("应用检测器", config)
            cls._appChecker = checker
            cls.add(checker)
            checker.enabled = False
            _Log.c.i("创建应用检测器")
   
    @classmethod
    def checkCurApp(cls, callback: Callable[[bool], None], timeout: int = None) -> bool:
        """设置要检测的当前应用
        Args:
            callback: 检测结果回调函数
            timeout: 超时时间(秒)
            
        Returns:
            bool: 是否成功设置检测
        """
        with cls._lock:
            # 设置回调
            checker = cls._appChecker
            checker.timeout = timeout or 3
            checker.onResult = callback
            return True
   
