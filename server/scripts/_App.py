import time
import _G
import os
import json
from typing import Optional, List, Tuple, TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from _Page import _Page_
    from CSchedule import CSchedule_

class _App_:
    """应用管理类：整合配置与实例"""
    _curAppName = _G.TOP  # 当前应用名称
    @classmethod
    def curName(cls):
        """获取当前应用名称"""
        return cls._curAppName
    
    @classmethod
    def setCurName(cls, appName: str):
        """设置当前应用名称"""
        if appName != cls._curAppName:
            cls._curAppName = appName
            # 更新已打开应用集合
            if appName != _G.TOP:
                cls.openedApps.add(appName)
    
    _apps: Dict[str, "_App_"] = {} 
    @classmethod
    def apps(cls) -> Dict[str, "_App_"]:
        """获取所有应用"""
        if not cls._apps:
            cls._apps = {}
        return cls._apps

    @classmethod
    def Top(cls):
        """获取主屏幕/桌面应用"""
        return cls.getApp(_G.TOP, True)
    
    openedApps = set()  # 存储已打开的应用名称，用于跟踪和管理
    
    @classmethod
    def cur(cls) -> "_App_":
        """获取当前应用"""
        return cls.apps().get(cls._curAppName)
    
    @classmethod
    def detectApp(cls, targetApp: str, setCur=True)->bool:
        """获取当前应用
        Returns:
            bool: 是否检测到应用
        """
        g = _G._G_
        log = g.Log()
        tools = g.Tools()
        try:
            if tools.isAndroid():
                appName = tools.curApp()
            else:
                appName = targetApp
            if setCur:
                app = cls.getApp(appName, True)
                if app is None:
                    log.w(f"未知应用:{appName}")
                else:
                    cls.setCurName(appName)
                    appName = app.name
            if appName != targetApp:
                log.e(f"当前应用是 {appName} 而不是：{targetApp}")
                return False
            return True
        except Exception as e:
            log.ex(e, "获取当前应用失败")
            return False
    
    def __init__(self, name: str,  info: dict):
        self.name = name
        self._curPage: Optional["_Page_"] = None
        self.rootPage: Optional["_Page_"] = None
        self.ratio = info.get("ratio", 10000)
        self.description = info.get("description", '')
        self.timeout = info.get("timeout", 5)
        self._pages: Dict[str, "_Page_"] = {}  # 应用级的页面列表
        self._runPages: Dict[str, "_Page_"] = {}  # 运行中的页面 {pageName: page}
        # 为应用创建调度器
        from CSchedule import CSchedule_
        self.scheduler: "CSchedule_" = CSchedule_(self)

    PathSplit = '-'
    @classmethod
    def parsePageName(cls, str: str) -> Tuple[str, str]:
        """解析应用和页面名称
        Args:
                str: 应用和名称，格式为 "应用名-名称"
        Returns:
            Tuple[str, str]: (应用名, 名称)
        """
        if not str or not str.strip():
            return None, None
        import re
        match = re.match(fr'(?P<appName>\S+)?\s*{cls.PathSplit}\s*(?P<name>\S+)?', str)
        if match:
            appName = match.group('appName')
            if appName is None:
                appName = cls.cur().name
            return appName, match.group('name')
        # 如果没找到应用名，使用当前应用    
        appName = cls.cur().name
        return appName, str  # 返回当前应用和页面名称    

    @property
    def curPage(self) -> "_Page_":
        """获取当前页面"""
        return self._curPage

    def _setCurrentPage(self, page: "_Page_"):
        """设置当前页面"""
        if page is None:
            return
        log = _G._G_.Log()
        log.d(f"当前页面为: {page.name}")
        self._curPage = page

    def detectPage(self, page: "_Page_", setCur=True, timeout=3) -> bool:
        """匹配页面"""
        g = _G._G_
        tools = g.Tools()
        log = g.Log()
        timeout = timeout or 3
        time.sleep(timeout)
        tools.refreshScreenInfos()
        try:
            target = page
            if not page.Match():
                page = self._detectPage(self.rootPage)
                if not page:
                    log.e(f"检测页面 {page.name} 失败")
                    return False
            if setCur:
                self._setCurrentPage(page)                
            if page.name != target.name:
                log.e(f"当前页面是 {page.name} 而不是：{target.name}")
                return False
            return True
        except Exception as e:
            log.ex(e, f"检测页面 {page.name} 失败")
            return False

    @classmethod
    def _detectPage(cls, page: "_Page_", depth=0) -> Optional["_Page_"]:
        """匹配页面"""
        if depth > 10 or not page:
            return None
        if page.Match():
            return page
        for child in page.children:
            ret = _App_._detectPage(child, depth + 1)
            if ret:
                return ret
        return None
    
    def back(self):
        """返回上一页"""
        g = _G._G_
        tools = g.Tools()
        log = g.Log()
        try:
            par = self.curPage.parent
            if par is None:
                log.e(f"{self.curPage.name} 没有父页面")
                return False
            if tools.isAndroid():
                tools.goBack()
                if not self.detectPage(par):
                    return False
            else:
                self._setCurrentPage(par)
            return True
        except Exception as e:
            log.ex(e, "返回上一页失败")
            return False

    def home(self):
        """返回主页"""
        g = _G._G_
        tools = g.Tools()
        log = g.Log()
        try:
            if tools.isAndroid():
                tools.goHome()
                if not self.detectApp(_G.TOP):
                    log.e(f"返回主页失败，检测应用 {_G.TOP} 失败")
                    return False
            else:
                self.setCurName(_G.TOP)
            return True
        except Exception as e:
            log.ex(e, "返回主页失败")
            return False
        
    @classmethod
    def configDir(cls)->str:
        """获取配置文件目录"""
        return os.path.join(_G.g.rootDir(), 'config', 'pages')
    
    @classmethod
    def loadConfig(cls, fileName=None)->bool:
        """加载配置文件
        Args:
            fileName: 配置文件名或路径，如果为None则加载所有配置文件            
        Returns:
            Dict[str, List]: 返回处理的应用及其页面列表，格式 {appName: [page1, page2, ...]}
        """
        g = _G._G_
        log = g.Log()
        try:
            import glob
            if fileName:
                configFiles = [fileName]
            else:
                configFiles = glob.glob(os.path.join(cls.configDir(), '*.json'))
            for app in cls.apps().values():
                app._stop()
            cls._apps = None
            for configFile in configFiles:
                if not os.path.exists(configFile):
                    continue
                cls.loadConfigFile(configFile)
            return True
        except Exception as e:
            log.ex(e, "加载配置文件失败")
            return False
    
    @classmethod
    def loadConfigFile(cls, configPath)->bool:
        """加载单个配置文件
        Args:
            configPath: 配置文件路径
        """
        g = _G._G_
        log = g.Log()
        try:
            with open(configPath, 'r', encoding='utf-8') as f:
                config = json.load(f)
            appName = os.path.basename(configPath)[:-5]
            #根据root的name，获取应用
            rootConfig = config.get('root', {})
            if not rootConfig:
                log.e(f"配置文件 {configPath} 没配置")
                return False
            appName = rootConfig.get('name', '')  
            app = cls.getApp(appName, True)
            rootPage = app.getPage(appName, True)   
            rootPage.config = rootConfig
            rootPage.parent = app.rootPage
            app._curPage = rootPage
            app.rootPage = rootPage
            pages = app._loadConfig(config)
            for page in pages.values():
                page.parent = rootPage
            return True
        except Exception as e:
            log.ex(e, f"加载配置文件失败: {configPath}")
            return False

    def _loadConfig(self, config: dict) -> Dict[str, "_Page_"]:
        """加载应用配置
        Args:
            config: 应用配置字典
        Returns:
            Dict[str, "_Page_"]: 返回加载的页面列表
        """
        g = _G._G_
        log = g.Log()
        try:
            # 加载根页面配置
            root = config.get('root')
            if not root:
                log.e(f"应用 {self.name} 配置缺少root节点")
                return {}
            # 更新应用信息
            self.ratio = root.get('ratio', 10000)
            self.description = root.get('description', '')
            
            # 加载页面配置
            pages = root.get('pages', {})
            for pageName, pageConfig in pages.items():
                # 创建或获取页面
                page = self.getPage(pageName, True)
                page.config = pageConfig
                if not page:
                    log.e(f"创建页面 {pageName} 失败")
                    continue
                # 添加到页面列表
                self._pages[pageName] = page
            log.i(f"应用 {self.name} 配置加载完成，共 {len(self._pages)} 个页面")
            return self._pages
        except Exception as e:
            log.ex(e, f"加载应用 {self.name} 配置失败")
            return {}

    def saveConfig(self) -> str:
        """保存配置
        Returns:
            str: 配置文件路径
        """
        g = _G._G_
        log = g.Log()
        try:
            # 获取当前应用的所有页面
            pages = self.getPages()
            # 过滤出非临时页面
            pages = [p for p in pages if p.type != 'temp']
            #remove root page
            pages.remove(self.rootPage)
            # 将页面转换为字典格式
            pageConfigs = {}
            for page in pages:
                pageConfigs[page.name] = page.config
            rootConfig = self.rootPage.config
            rootConfig['pages'] = pageConfigs
            output = {
                'root': rootConfig
            }
            # 写入配置文件
            path = self.configDir()
            if not os.path.exists(path):
                os.makedirs(path)
            path = os.path.join(path, f'{self.name}.json')
            with open(path, 'w', encoding='utf-8') as f:
                    json.dump(output, f, ensure_ascii=False, indent=2)
            return path
        except Exception as e:
            log.ex(e, f"保存配置文件失败")
            return None


    def getPage(self, name, create=False, includeCommon=False)->Optional["_Page_"]:
        """获取页面"""
        page = None
        if name in self._pages:
            page = self._pages[name]
        elif includeCommon:
            page = _App_.Top().getPage(name, create, False)
            return page
        if page is None and create:
            from _Page import _Page_
            page = _Page_(self.name, name)
            if page:
                self._pages[name] = page
        return page

    def getPages(self, pattern: str = None) -> List["_Page_"]:
        """获取匹配指定模式的页面列表"""
        if pattern:
            pattern = pattern.lower()
            return [p for p in self._pages.values() if pattern in p.name.lower()]
        return list(self._pages.values())

    def delPage(self, pageName: str) -> bool:
        """删除页面"""
        if not pageName:
            return False
            
        # 解析页面名称，获取应用名和页面名
        pageName = pageName.strip().lower()
        if self.PathSplit in pageName:
            appName, page_name = pageName.split(self.PathSplit, 1)
        else:
            # 使用当前应用
            appName = self.curName()
            page_name = pageName
            
        # 在页面字典中查找匹配的页面
        if page_name in self._pages:
            # 找到匹配的页面，删除它
            page = self._pages.pop(page_name)
            
            # 如果不是临时页面，保存配置
            if page.type != 'temp':
                self.saveConfig()
            return True
        return False

    @classmethod
    def getAppNames(cls) -> list:
        """获取所有应用名称列表
        Returns:
            list: 应用名称列表
        """
        return list(cls.apps().keys())

    @classmethod
    def exist(cls, appName: str) -> bool:
        """检查应用是否存在
        Args:
            appName: 应用名称
        Returns:
            bool: 是否存在
        """
        return appName in cls.apps().keys()

    @classmethod
    def detect(cls, setCur=True):
        """检测当前页面"""
        try:
            g = _G._G_
            log = g.Log()
            cls.detectApp(cls.curName(), setCur)
            cls.cur().detectPage(cls.curPage, setCur)
        except Exception as e:
            log.ex(e, "检测当前页面失败")

    @classmethod
    def isHome(cls) -> bool:
        """检查是否在主屏幕"""
        g = _G._G_
        tools = g.Tools()
        if g.android is None:
            return cls.curName() == _G.TOP
        return tools.isHome()
    
    @classmethod
    def goHome(cls)->bool:
        """返回主屏幕"""
        return cls.open(_G.TOP)    
    
    @classmethod
    def open(cls, appName) -> bool:
        """跳转到指定应用"""
        try:
            g = _G._G_
            log = g.Log()
            app = cls.getApp(appName)
            if not app:
                log.w(f"未知应用:{appName}")
            else:
                appName = app.name
            tools = g.Tools()
            if appName == cls.curName():
                return True
            ok = tools.openApp(appName)
            if not ok:
                log.e(f"=>{appName}")
                return False
            if g.isAndroid():
                time.sleep(5)
            ok = cls.detectApp(appName)
            log.log(f"=>{appName}", None, 'i' if ok else 'e')
            return ok
        except Exception as e:
            log.ex(e, f"跳转到应用 {appName} 失败")
            return False

    def findPath(self, fromPage: "_Page_", toPage: "_Page_", visited=None, path=None) -> List["_Page_"]:
        """在整个页面树中查找从fromPage到toPage的路径
        Args:
            fromPage: 起始页面
            toPage: 目标页面
            visited: 已访问页面集合(内部使用)
            path: 当前路径(内部使用)
        Returns:
            list: 从fromPage到toPage的路径，如果没找到则返回[]
        """
        if visited is None:
            visited = set()
        if path is None:
            path = [fromPage]            
        if fromPage in visited:
            return []
        visited.add(fromPage)        
        # 检查当前页面
        if fromPage.name == toPage.name:
            return path        
        # 搜索子页面
        toPages = fromPage.exit.keys()
        for pageName in toPages:
            page = self.getPage(pageName)
            if page and page not in visited:
                resultPath = self.findPath(page, toPage, visited, path + [page])
                if resultPath:
                    return resultPath
        
        # 搜索父页面
        fromPages = fromPage.entry.keys()
        for pageName in fromPages:
            page = self.getPage(pageName)
            if page and page not in visited:
                resultPath = self.findPath(page, toPage, visited, path + [page])
                if resultPath:
                    return resultPath
        
        # 如果这是根页面且没找到，尝试搜索其他应用
        if toPage.name != _G.TOP:
            for app in _App_.apps.values():
                if app.rootPage != fromPage and app.rootPage not in visited:
                    resultPath = self.findPath(app.rootPage, toPage, visited, path + [app.rootPage])
                    if resultPath:
                        return resultPath
        
        return []

    def _findPath(self, pageNames, name, visited=None) -> Optional["_Page_"]:
        """在指定页面列表中查找指定名称的页面"""
        g = _G._G_
        log = g.Log()
        if len(pageNames) == 0:
            return None
        for pageName in pageNames:  
            page = self.getPage(pageName)
            if page is None:
                log.d(f"{name}的子页面: {pageName}不存在")
                continue
            result = self.findPath(page, self.getPage(name))
            if result:
                return result[-1]  # 返回路径的最后一个节点
        return None

    def goPage(self, pageName) -> bool:
        """跳转到目标页面
        Args:
            pageName: 目标页面名称
        Returns:
            bool: 是否成功
        """
        try:
            g = _G._G_
            log = g.Log()
            if self._curPage.name == pageName:
                return self._startPage(self._curPage)
            #跳转页面
            page = self.getPage(pageName)
            if not page:
                log.e(f"未知页面: {pageName}")
                return False
            pages = self.findPath(self._curPage, page)
            if not pages:
                log.e(f"找不到从 {self._curPage.name} 到 {page.name} 的路径")
                return False
            # log.i(f"跳转路径: {'->'.join([p.name for p in pages])}")
            
            # 执行路径中的每一步跳转
            for i in range(1, len(pages)):  # 从1开始，因为0是当前页面
                nextPage = pages[i]
                # 执行跳转动作
                result = self.enter(nextPage)
                nextPage.resetLife()
                if not result:
                    return False
            return True
        except Exception as e:
            log.ex(e, "跳转失败")
            return False
        
    def enter(self, page: "_Page_") -> bool:
        """进入指定页面
        Args:
            toPage: 目标页面
        Returns:
            bool: 是否成功进入
        """
        g = _G._G_
        log = g.Log()
        if page is None:
            return False
        if self.curPage is None:
            log.e(f"{self.name} 当前页面为空")
            return False
        toPageName = page.name
        self.curPage._doExit(toPageName)
        return self._startPage(page)

    @classmethod
    def go(cls, target: str) -> bool:
        """跳转到指定应用的指定页面
        Args:
            target: 目标页面路径
        Returns:
            bool: 是否成功
        """
        g = _G._G_
        log = g.Log()
        try:
            if not target:
                log.e("目标页面路径不能为空")
                return False
            appName, pageName = cls.parsePageName(target)
            ret = cls.open(appName)
            if ret:
                return cls.cur().goPage(pageName) 
            return False
        except Exception as e:
            log.ex(e, f"跳转到应用 {appName} 的页面 {pageName} 失败")
            return False
        
    @classmethod
    def closeApp(cls, appName=None) -> bool:
        """关闭应用
        Args:
            appName: 应用名称，如果为None则关闭当前应用
        
        Returns:
            bool: 是否成功关闭
        """
        g = _G._G_
        log = g.Log()
        try:
            # 获取应用名称
            if appName is None:
                appName = cls._curAppName
            
            # 获取应用实例
            app = cls.getApp(appName)
            if not app:
                log.e(f"应用 {appName} 不存在")
                return False
            app._stop()     
             # 从打开的应用列表中移除
            if appName in cls.openedApps:
                cls.openedApps.remove(appName)           
            # 如果是当前应用，返回到主屏幕
            if appName == cls._curAppName:
                cls.setCurName(_G.TOP)
                
            log.i(f"应用 {appName} 已关闭")
            return True
        except Exception as e:
            log.ex(e, f"关闭应用 {appName} 失败")
            return False
        
    @classmethod
    def getApp(cls, appName, create=False) -> "_App_":
        """获取应用
        Args:
            appName: 应用名称
            create: 如果不存在是否创建
        Returns:
            _App_: 应用实例
        """
        try:
            g = _G._G_
            log = g.Log()
            apps = cls.apps()
            app = apps.get(appName)
            if not app and create:
                app = cls(appName, {})
                apps[appName] = app
            return app
        except Exception as e:
            log.ex(e, f"获取应用 {appName} 失败")
            return None        

    @classmethod
    def getAllApps(cls) -> List[str]:
        """获取所有应用名称"""
        return cls.getAppNames()

    @classmethod
    def onLoad(cls, oldCls=None):
        """克隆"""
        if oldCls:
            cls._curAppName = oldCls._curAppName
            cls.openedApps = oldCls.openedApps
        else:
            cls.openedApps = set()  # 初始化已打开应用集合
        cls.loadConfig()

    def _getRunPage(self, name: str, data: dict = None, create: bool = True) -> Optional["_Page_"]:
        """获取运行页面
        Args:
            name: 页面名称
            data: 页面数据
            create: 如果不存在是否创建
        Returns:
            _Page_: 页面实例
        """
        try:
            g = _G._G_
            log = g.Log()
            # 先在本应用查找
            page = self._runPages.get(name)
            if page:
                return page
            if create:
                page = self.getPage(name, False, True)
                if page is None:
                    log.e(f"页面: {name}没配置")
                    return None
                from _Page import _Page_
                page = _Page_(self.name, name)
                page.config = page.config
                if data:
                    for key, value in data.items():
                        setattr(page, key, value)
            return page
        except Exception as e:
            log.ex(e, f"获取运行页面 {name} 失败")
            return None
        
    def runScheduler(self, pageName: str, data: dict = None):
        """运行调度器"""
        page = self._getRunPage(pageName, data, False)
        if page:
            self.scheduler.run(page)

    def startPage(self, pageName: str, data: dict = None) -> bool:
        """启动页面检查器
        Args:
            pageName: 页面名称
            data: 可选的数据
        Returns:
            bool: 是否成功启动
        """
        # 获取或创建页面对象
        page = self._getRunPage(pageName, data, False)
        if not page:
            # 如果页面不存在，创建页面
            page = self.getPage(pageName, True, True)
        return self._startPage(page)
 
    def _startPage(self, page: '_Page_') -> bool:
        """启动页面检查器
        Returns:
            bool: 是否成功启动
        """
        g = _G._G_
        log = g.Log()
        try:
            if page is None:
                return False
            page.end()            
            # 验证页面是否存在
            if not self.detectPage(page, True):
                return False
            self._runPages[page.name] = page
            page.begin()
            return True
        except Exception as e:
            log.ex(e, f"启动页面{page.name} 失败")
            return False
   
    def stopPage(self, pageName: str, cancel=False) -> bool:
        """停止页面执行
        Args:
            page: 要停止的页面
            cancel: 是否强制取消
        Returns:
            bool: 是否成功停止
        """
        try:
            g = _G._G_
            log = g.Log()
            pages = []
            for name, page in self._runPages.items():
                if pageName and name != pageName:
                    continue
                pages.append(page)
            for page in pages:
                self._stop(page, cancel)
            return True
        except Exception as e:
            log.ex(e, "停止页面失败")
            return False

    def _stop(self, page: "_Page_" = None, cancel=False) -> bool:
        """停止页面执行
        Args:
            page: 要停止的页面
            cancel: 是否强制取消
        Returns:
            bool: 是否成功停止
        """
        try: 
            runPages = self._runPages
            if page is None:
                # 停止应用内所有运行中的页面
                runningPages = list(runPages.values())
                for page in runningPages:
                    page.end(cancel)
                runPages.clear()
                # 停止应用的调度器
                if hasattr(self, 'scheduler'):
                    self.scheduler.stop()    
            else:
                page.end(cancel)
                if page.name in runPages:
                    runPages.pop(page.name)
            return True
        except Exception as e:
            _G._G_.Log().ex(e, f"停止页面 {page.name} 失败")
            return False
        

_App_.onLoad()
