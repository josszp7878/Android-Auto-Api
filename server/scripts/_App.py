import time
import _G
import os
import json
from typing import Optional, List, Tuple, TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from _Page import _Page_
    from _Log import _Log_
    from CTask import CTask_

class _App_:
    """应用管理类：整合配置与实例"""
    _curAppName = _G.TOP  # 当前检测到的应用名称
    _lastApp = None  # 当前应用实例（延迟初始化）
    @classmethod
    def curName(cls):
        """获取当前应用名称"""
        return cls._curAppName
    
    @classmethod
    def setCurName(cls, appName: str):
        """设置当前检测应用名称"""
        if appName != cls._curAppName:
            cls._curAppName = appName
            # 如果是已知应用则更新实例
            if appName in cls.apps():
                cls._lastApp = cls.apps()[appName]
    
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
    
    @classmethod
    def last(cls) -> "_App_":
        """获取当前应用实例"""
        if cls._lastApp is None:
            cls._lastApp = cls.getApp(_G.TOP, True)
        return cls._lastApp
    
    @classmethod
    def cur(cls) -> "_App_":
        """获取当前应用实例"""
        return cls.getApp(cls._curAppName, False)
    
    @classmethod
    def detectApp(cls)->Tuple['_App_', str]:
        """获取当前应用"""
        g = _G._G_
        log = g.Log()
        tools = g.Tools()
        try:
            detectedApp = tools.curApp() if tools.isAndroid() else cls._curAppName
            cls._curAppName = detectedApp
            
            # 当检测到已知应用时更新实例
            if detectedApp in cls.apps():
                cls._lastApp = cls.apps()[detectedApp]
                
            return cls._lastApp, detectedApp
        except Exception as e:
            log.ex(e, "获取当前应用失败")
            return None, None
    
    def __init__(self, name: str, info: dict):
        self.name = name
        self._curPage: Optional["_Page_"] = None
        self._lastPage: Optional["_Page_"] = None
        self.rootPage: Optional["_Page_"] = None
        self.ratio = info.get("ratio", 10000)
        self.description = info.get("description", '')
        self.timeout = info.get("timeout", 5)
        self._pages: Dict[str, "_Page_"] = {}  # 应用级的页面列表
        self._path: Optional[List["_Page_"]] = None  # 当前缓存的路径 [path]
        self.userEvents: List[str] = []  # 用户事件列表
        # self._runner = CRun_(self)  # 新增批处理运行器
        self._tasks: Dict[str, "CTask_"] = {}  # 任务字典，KEY为任务名
        self._curTask: Optional["CTask_"] = None  # 当前任务

    # @property
    # def runner(self) -> CRun_:
    #     """获取批处理运行器"""
    #     return self._runner

    PathSplit = '-'
    @classmethod
    def parseName(cls, str: str) -> Tuple[str, str]:
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
                appName = cls.last().name
            return appName, match.group('name')
        # 如果没找到应用名，使用当前应用    
        appName = cls.last().name
        return appName, str  # 返回当前应用和页面名称    

    @property
    def curPage(self) -> "_Page_":
        """获取当前页面"""
        return self._curPage

    def _setCurrentPage(self, page: "_Page_")->bool:
        """设置当前页面"""
        if page is None or page == self._curPage:
            return False
        g = _G._G_
        log = g.Log()
        log.d(f"当前页面为: {page.name}")
        ret = self._startPage(page)
        if ret is None:
            return False
        self._lastPage = self._curPage
        self._curPage = page
        return True

    def detectPage(self, page: "_Page_", timeout=3):
        """匹配页面"""
        if not page:
            return False
        g = _G._G_
        tools = g.Tools()
        log = g.Log()
        time.sleep(timeout)
        tools.refreshScreenInfos()
        try:
            curPage = self.curPage
            # 检测当前应用中的alert类型页面
            from _Page import ePageType
            pages = [p for p in self.getPages() if p and p != curPage and p.type == ePageType.alert.value]
            if len(pages) > 0:
                for p in pages:
                    if p.match():
                        log.i(f"弹窗: {p.name}")
                        self._setCurrentPage(p)
                        return
            #检测exitPages
            for p in curPage.exitPages:
                if p.match():
                    log.i(f"跳转: {p.name}")
                    self._setCurrentPage(p)
                    return
            if g.isAndroid() and not curPage.match():
                log.e("检测到未配置的弹出界面")
        except Exception as e:
            log.ex(e, f"检测页面 {page.name} 失败")

    def back(self)->bool:
        """返回上一页"""
        if self._lastPage:
            return self._toPage(self._lastPage)
        return False
       
    def home(self):
        """返回主页"""
        g = _G._G_
        tools = g.Tools()
        log = g.Log()
        try:
            if tools.isAndroid():
                tools.goHome()
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
            appName = rootConfig.get('name', appName)  
            app = cls.getApp(appName, True)
            rootPage = app.getPage(appName, True)   
            rootPage.config = rootConfig
            app._curPage = rootPage
            app.rootPage = rootPage
            pages = app._loadConfig(config)
            for page in pages.values():
                page.setParent(rootPage)
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
                
            # 不再处理commonPages配置
            
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
        try:
            g = _G._G_
            log = g.Log()
            page = None
            if name in self._pages:
                page = self._pages[name]
            if includeCommon and self.name != _G.TOP:
                # 获取公共页面
                commonPage = _App_.Top().getPage(name, False, False)
                if not commonPage:
                    log.e(f"加载公共页面 {name} 失败")
                    return None
                # 直接返回公共页面，getInst会在需要时创建实例
                return commonPage
            if page or not create:
                return page
            # 创建新页面
            from _Page import _Page_
            page = _Page_(self.name, name)
            if page:
                self._pages[name] = page
            return page
        except Exception as e:
            log.ex(e, f"获取页面 {name} 失败")
            return None

    def getPages(self, pattern: str = None):
        """获取匹配指定模式的页面列表"""
        return self._pages.values()

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
    def open(cls, appName) -> "_App_":
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
            if appName == cls._curAppName:
                return app
            ok = tools.openApp(appName)
            if not ok:
                log.e(f"=>{appName}")
                return None
            cls.setCurName(appName)
            if g.isAndroid():
                time.sleep(5)
            app, appName = cls.detectApp()
            if app:
                cls.setCurName(appName)
                log.i(f"=>{appName}")
            return app
        except Exception as e:
            log.ex(e, f"跳转到应用 {appName} 失败")
            return None

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
        
        # # 如果这是根页面且没找到，尝试搜索其他应用
        # if toPage.name != _G.TOP:
        #     for app in _App_.apps().values():
        #         if app.rootPage != fromPage and app.rootPage not in visited:
        #             resultPath = self.findPath(app.rootPage, toPage, visited, path + [app.rootPage])
        #             if resultPath:
        #                 return resultPath
        
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
                return result[-1]  # 返回路径的最后一个节点名称
        return None
    
    def goPage(self, page: '_Page_') -> bool:
        """设置要跳转到的目标页面
        设置_targetPage属性，由应用更新循环中的_update方法处理实际跳转
        
        Args:
            page: 目标页面
        Returns:
            bool: 是否成功设置
        """
        try:
            if not page:
                return False
            g = _G._G_
            log = g.Log()
            # 如果已经在目标页面，直接返回成功
            if self._curPage and self._curPage.name == page.name:
                return self._startPage(self._curPage)                
            # 计算路径并缓存
            if self._curPage:
                path = self.findPath(self._curPage, page)
                if path:
                    self._path = path
                    # log.i(f"设置页面跳转目标: {page.name}, 路径: {path}")
                else:
                    log.e(f"找不到从 {self._curPage.name} 到 {page.name} 的路径")
                    return False
            # else:
                # 如果当前没有页面，直接设置目标页面
                # log.i(f"设置页面跳转目标: {page.name}, 无需路径")
                
            # log.i(f"设置页面跳转目标: {page.name}")
            return True
        except Exception as e:
            log.ex(e, "设置页面跳转目标失败")
            return False
        

    @classmethod
    def go(cls, target: str) -> '_Page_':
        """跳转到指定应用的指定页面
        Args:
            target: 目标页面路径
        Returns:
            _Page_: 目标页面
        """
        g = _G._G_
        log = g.Log()
        try:
            if not target:
                log.e("目标页面路径不能为空")
                return None
            appName, pageName = cls.parseName(target)
            ret = cls.open(appName)
            if ret:
                app = cls.last()
                if app:
                    page = app.getPage(pageName)
                    if app.goPage(page):
                        return page
            return None
        except Exception as e:
            log.ex(e, f"跳转到应用 {appName} 的页面 {pageName} 失败")
            return None
        
    @classmethod
    def closeApp(cls, appName=None) -> bool:
        """关闭应用"""
        g = _G._G_
        log = g.Log()
        try:
            if appName is None:
                appName = cls.last().name  # 通过cur方法获取实例名称
            
            app = cls.getApp(appName)
            if not app:
                return False
            app._stop()
            
            # 重置到主屏幕
            if appName == cls.last().name:
                cls._lastApp = cls.Top()  # 修改属性名称
                cls._curAppName = _G.TOP
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
        if appName is None:
            return None
        apps = cls.apps()
        app = apps.get(appName)
        if not app and create:
            app = cls(appName, {})
            apps[appName] = app
        return app

    @classmethod
    def getAllApps(cls) -> List[str]:
        """获取所有应用名称"""
        return cls.getAppNames()

    @classmethod
    def onLoad(cls, oldCls=None):
        """克隆"""
        if oldCls:
            cls._curAppName = oldCls._curAppName
            cls._lastApp = oldCls._curApp  # 修改属性名称
        else:
            cls._lastApp = cls.getApp(_G.TOP, True)
        cls.loadConfig()

    def _startPage(self, page: '_Page_') -> '_Page_':
        """启动页面检查器
        Returns:
            _Page_: 页面实例
        """
        g = _G._G_
        log = g.Log()
        try:
            if page is None:
                return None
            if page.begin():
                return page
            else:
                return None
        except Exception as e:
            log.ex(e, f"启动页面{page.name} 失败")
            return None
   
    def _update(self, log: "_Log_"):
        """应用级别的更新循环"""
        try:
            # 检测当前页面
            self.detectPage(self.curPage)
            # 处理页面跳转逻辑
            self._updateGoPath(log)
            # 更新当前页面
            if self.curPage:
                self.curPage.update()
            self.userEvents = []
            # 更新当前任务
            if self._curTask:
                self._curTask.update()
            
        except Exception as e:
            log.ex(e, f"应用更新失败：{self.name}")

    # 处理页面跳转逻辑
    def _updateGoPath(self, log: "_Log_"):
        """处理页面跳转逻辑"""
        try:
            if not self._path:
                return True
            curPage = self.curPage
            # 检查当前页面是否在路径中
            if curPage not in self._path:
                log.w(f"当前页面 {curPage.name} 不在预定路径中")
                self._clearPath()
                return
            # 找到当前页面在路径中的位置
            index = self._path.index(curPage)
            # 已经是路径中的最后一个页面，说明已到达目标
            if index == len(self._path) - 1:
                self._clearPath()
                return
            # 如果不是最后一个页面，则进行跳转
            if index >= 0 and index < len(self._path) - 1:
                self._toPage(self._path[index + 1])
        except Exception as e:
            log.ex(e, "处理页面跳转逻辑失败")
    
    def _toPage(self, page: "_Page_")->bool:
        """跳转到路径中的下一个页面"""
        g = _G._G_
        tools = g.Tools()
        self.curPage.doExit(page.name)
        if not tools.isAndroid():
            # 非安卓平台需要直接设置当前页面，不能用检测页面
            page.alwaysMatch(True)
        return True
    
    def _clearPath(self):
        """清空路径目标"""
        self._path = None

        

    @classmethod
    def update(cls):
        """全局应用更新循环
        """
        while True:
            time.sleep(1)
            cls.detectApp()
            app = cls.cur()
            log = _G._G_.Log()  # 需要再这里获取，这样就能支持LOG的动态更新
            if app:
                # 只更新当前已知应用
                app._update(log)
            # else:
            #     log.w(f"未知应用 {cls.curName()}")

    def sendUserEvent(self, eventName: str) -> bool:
        """添加用户事件到事件列表
        Args:
            eventName: 用户事件名称
        Returns:
            bool: 是否添加成功
        """
        log = _G._G_.Log()
        try:
            if eventName not in self.userEvents:
                self.userEvents.append(eventName)
                log.d(f"添加用户事件: {eventName}")
            return True
        except Exception as e:
            log.ex(e, f"添加用户事件失败: {eventName}")
            return False
  
    @classmethod
    def getTasks(cls, name)-> Tuple['_App_', List['CTask_']]:
        """获取任务实例"""
        g = _G._G_
        log = g.Log()
        if not name:
            return None, None
        appName, taskName = cls.parseName(name)
        app = cls.getApp(appName)
        if app is None:
            log.e(f"应用 {appName} 不存在")
            return app, None
        tasks = []
        if taskName is None:
            tasks = list(app._tasks.values())
        else:
            task = app._tasks.get(name)
            if task is None:
                log.e(f"任务 {name} 不存在")
            else:
                tasks.append(task)
        return app, tasks

    @classmethod
    def getTask(cls, name)-> Tuple['_App_', 'CTask_']:
        """获取任务实例"""
        g = _G._G_
        log = g.Log()
        if not name:
            return None, None
        appName, taskName = cls.parseName(name)
        app = cls.getApp(appName)
        if app is None:
            log.e(f"应用 {appName} 不存在")
            return app, None
        task = app._tasks.get(name) if taskName else app._curTask
        if task is None:
            log.e(f"任务 {name} 不存在")
        return app, task

    @classmethod
    def startTask(cls, name: str)->'CTask_':
        """启动任务"""
        g = _G._G_
        log = g.Log()
        try:
            app, task = cls.getTask(name)
            # 如果当前有任务在运行，先停止
            if app._curTask:
                app._curTask.stop(cancel=True)
                app._curTask = None
            # 检查任务是否已存在，不存在则创建
            if task is None:
                from CTask import CTask_
                task = CTask_.create(name, app)
                if task and task.begin():
                    app._tasks[name] = task
                    app._curTask = task
                    return task
                else:
                    return None
        except Exception as e:
            log.ex(e, f"启动任务失败: {name}")
            return None
            
    @property
    def curTask(self):
        """获取当前任务"""
        return self._curTask
    


_App_.onLoad()
