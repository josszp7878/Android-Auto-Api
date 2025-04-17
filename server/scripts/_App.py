from pathlib import Path
import time
import _Log
import _G
from typing import Optional, List, Tuple, TYPE_CHECKING
if TYPE_CHECKING:
    import _Page

class _App_:
    """应用管理类：整合配置与实例"""
    _curAppName = _G.TOP  # 当前应用名称
    apps = {}  # 存储应用实例 {appName: _App_实例}
    Top: "_App_" = None

    @classmethod
    def currentApp(cls):
        """获取当前应用"""
        return cls.getApp(cls._curAppName, True)
    
    def __init__(self, name:str, rootPage: "_Page._Page_", info:dict):
        self.name = name
        self.rootPage = rootPage
        self._currentPage = rootPage
        self.ratio = info.get("ratio", 10000)
        self.description = info.get("description", '')
        self.timeout = info.get("timeout",5)

    def getCheckName(self, checkName: str) -> str:
        """获取检查器名称"""
        if not checkName or checkName.strip() == '':
            return None
        
        if checkName.startswith('@'):
            #页面匹配
            checkName = checkName[1:]
            checkName = self.name + '-' + checkName
        return checkName

    @property
    def currentPage(self):
        return self._currentPage
    
    def _setCurrentPage(self, page: "_Page._Page_"):
        if page == self._currentPage:
            return
        self._currentPage = page
        log = _G._G_.Log()
        log.i(f"当前页面: {page.name if page else 'None'}")
        Checker = _G._G_.Checker()
        Checker.uncheckPage(self._currentPage)
        checkerName = self.getCheckName(page.name)
        self.checkPage(checkerName)
    
    def checkPage(self, checkerName: str):
        """检查页面"""
        try:
            if checkerName is None: 
                return
            g = _G._G_
            log = g.Log()
            Checker = g.Checker()
            checkerName = self.getCheckName(checkerName)
            Checker.check(checkerName, self)
        except Exception as e:
            log.ex(e, f"检查页面失败: {checkerName}")
    
    def detectPage(self, pageName, delay:int=3)->bool:
        """客户端实现：通过屏幕检测当前页面"""
        try:
            g = _G._G_
            log = g.Log()
            if delay > 0:
                time.sleep(delay)
            ret = True
            if pageName is not None:
                #检测特定页面
                if isinstance(pageName, str):
                    page = self.getPage(pageName)
                    if page is None:
                        log.e(f"找不到页面: {pageName}")
                        return False
                else:
                    page = pageName
                ret = _App_._doMatchPage(page)             
            else:
                #获取当前页面，可能不是目标页面
                tools = _G._G_.CTools()  
                if tools.android is not None:
                    tools.refreshScreenInfos()
                    page = _App_._matchPage(self.rootPage)
                    if page is None:
                        # log.e("检测当前页面失败")
                        return False
                else:
                    page = self._currentPage
            self._setCurrentPage(page)
            return ret
        except Exception as e:
            _G._G_.Log().ex(e, f"检测页面失败: {pageName}")
            return False
    
    def _doMatchPage(self, page: "_Page._Page_") -> bool:
        """检测页面是否匹配"""
        g = _G._G_
        log = g.Log()
        Checker = g.Checker()
        checkerName = self.getCheckName(page.name)
        checker = Checker.getTemplate(checkerName, create=False)
        ret = False
        if checker:
            ret = checker.match()
            if not ret:
                log.e(f"页面{page.name}不匹配")
                return False
        return ret
    
    @classmethod
    def _matchPage(cls, page: "_Page._Page_", depth=0) -> Optional["_Page._Page_"]:
        """递归检测页面
        Args:   
            page: 要检测的页面
            depth: 当前递归深度
        """
        try:
            if _App_._doMatchPage(page):
                return page
            for child in page.children.values():
                page = child._matchPage(depth + 1)
                if page:
                    return page
        except Exception as e:
            _G._G_.Log().ex(e, f"检测页面失败: {page.name}")
        return None 
    
    @classmethod
    def getAppPage(cls, pageName)->Optional["_Page._Page_"]:
        g = _G._G_
        log = g.Log()
        appName, pageName = g.Tools().toAppPageName(pageName)
        App = g.App()
        app = App.currentApp()
        if appName:
            app = App.getApp(appName, True)
            if not app:
                log.e(f"找不到应用: {appName}")
                return None
        page = app.currentPage
        if pageName:
            page = app.getPage(pageName)
            if not page:
                log.e(f"找不到页面: {pageName}")
                return None
        return page
    
    def getPage(self, pageName:str)->Optional["_Page._Page_"]:
        """获取指定页面"""
        if pageName.strip() == '':
            return self._currentPage
        if _G._G_.Tools().isRoot(pageName) or pageName == self.name:
            return self.rootPage
        return self.rootPage.findChild(pageName)
        
    def goPage(self, page: "_Page._Page_", checkWaitTime=None) -> bool:
        """跳转到目标页面
        Args:
            page: 目标页面
            checkWaitTime: 检查等待时间，如果为None则使用页面默认值
            
        Returns:
            成功返回目标页面对象，失败返回None
        """
        try:
            if self.currentPage == page:
                return True
            g = _G._G_
            log = g.Log()
            # 查找路径
            pages = self.currentPage.findPath(page.name)
            if pages is None:
                log.e(f"找不到从 {self.currentPage.name} 到 {page.name} 的路径")
                return False
            log.i(f"跳转路径: {'->'.join([p.name for p in pages])}")
            
            # 执行路径中的每一步跳转
            page = self.currentPage
            for i in range(1, len(pages)):  # 从1开始，因为0是当前页面
                nextPage = pages[i]
                
                # 执行跳转动作
                result = page.go(nextPage)
                if not result:
                    log.e(f"跳转失败: {page.name} -> {nextPage.name}")
                    return False
                if not self.detectPage(nextPage):
                    log.e(f"跳转失败: {page.name} -> {nextPage.name}")
                    return False
                page = nextPage
            return True
        except Exception as e:
            log.ex(e, "跳转失败")
            return False

    def go(self, tarName) -> bool:
        """跳转到指定页面"""
        try:
            if tarName is None or tarName.strip() == '':
                return False
            g = _G._G_
            log = g.Log()
            tarName = tarName.lower()
            tools = g.CTools()
            if tools.isTop(tarName):
                # 返回主屏幕，使用Top应用
                return self.goHome()
            # 使用getter方法获取当前应用名
            app = self
            page = None
            # 使用正则表达式匹配 appName.pageName 格式
            appName, pageName = tools.toAppPageName(tarName)
            # 获取目标应用
            if appName is not None and appName != self.name:
                app = self.getApp(appName, True)
                appName = app.name
                if app is None:
                    log.e(f"应用 {appName} 没配置")
                    return False
                ret = self.goApp(appName)
                if not ret:
                    log.e(f"打开应用失败: => {appName}")
                    return False
            if pageName is None:
                return True
            #处理页面跳转
            if tools.isRoot(pageName):
                page = app.rootPage                
            else:
                page = app.rootPage.findChild(pageName)
                if page is None:
                    if appName is not None:
                        log.e(f"应用{appName}中找不到页面{pageName}")
                        return False
                    #到所有其它应用中查找目标页面
                    for app1 in self.apps.values():
                        if app1 == self:
                            continue    
                        page = app1.rootPage.findChild(pageName)
                        if page:
                            app = app1
                            ret = self.goApp(app1)
                            if not ret:
                                log.e(f"跳转失败: {app1.name} -> {appName}")
                                return False
                            appName = app1.name
                            break
                if page is None:
                    log.e(f"所有应用都找不到页面{pageName}")
                    return False
                    # 如果目标应用不是当前应用，则跳转到目标应用
            return app.goPage(page) 
        except Exception as e:
            log.ex(e, "跳转失败")
        return False

    
    
    @classmethod
    def loadConfig(cls):
        """加载配置并创建应用实例与页面树"""
        g = _G._G_
        log = g.Log()      
        try:
            import json
            import os
            import _Page
            # 清空现有应用
            cls.apps: dict[str, "_App_"] = {}
            Page = _Page._Page_
            root = Page.Root()
            
            # 直接使用_App_类创建顶层App，无需区分服务端和客户端
            cls.Top = cls("Top", root, {})
            
            # 尝试加载配置文件
            try:
                configFile = os.path.join(_G.g.rootDir(), 'config', 'pages.json')
                with open(configFile, 'r', encoding='utf-8') as f:
                    configData = json.load(f)
            except Exception as e:
                log.e(f"加载配置文件失败: {e}")
                return False
            
            # 首先读取TOP节点的checkers配置
            topCheckers = configData.get("Top", {}).get("checkers", {})
            import CChecker
            Checker = CChecker.CChecker_
            if topCheckers:
                Checker.start()
                log.i(f"已加载{len(topCheckers)}个checker模板")
            
            # 创建根页面
            root = Page.createPage("Top", None, None, None)
            
            # 递归处理配置树
            def processNode(node, parentPage, parentName):
                for pageName, pageConfig in node.items():
                    if not isinstance(pageConfig, dict):
                        log.e(f"页面配置错误,该节点不是字典: {pageConfig}")
                        continue
                    # 创建页面对象
                    pageName = pageName.lower()
                    inAction = pageConfig.get("in", None)
                    outAction = pageConfig.get("out", None)
                    currentPage = Page.createPage(pageName, parentPage, inAction, outAction)
                    # 识别应用根节点（Top的直接子节点）
                    if parentName == "Top":
                        appInfo = pageConfig.get("app_info", {})
                        # 使用传入的AppClass创建实例
                        cls.apps[pageName] = _App_(
                            name=appInfo.get("name", pageName),
                            rootPage=currentPage,
                            info=appInfo
                        )
                    # log.d(f"创建应用 {pageName}，根页面 {currentPage.name}")

                    # 递归处理子节点
                    children = pageConfig.get("children", {})
                    if children:
                        processNode(children, currentPage, pageName)

            # 从Top节点开始处理
            processNode(configData.get("Top", {}).get("children", {}), root, "Top")
            
            log.i(f"加载完成：共{len(cls.apps)}个应用")
            # cls.printTopology()

        except Exception as e:
            log.ex(e, "配置加载失败")
            cls.apps.clear()

    @classmethod
    def printTopology(cls, appName:str=None):
        """打印页面拓扑结构"""
        log = _G._G_.Log()
        log.i("页面拓扑结构:")
        if appName and appName.strip() != '':
            app = cls.getApp(appName)
            if app:
                cls._printPageTree(app.rootPage)
            return
        for app in cls.apps.values():
            cls._printPageTree(app.rootPage)

    
    @classmethod
    def _printPageTree(cls, page, level=0):
        """递归打印页面树
        
        Args:
            page: 页面对象
            level: 当前层级
        """
        log = _G._G_.Log()
        indent = "  " * level
        log.d(f"{indent}└─ {page.name}")
        
        # 打印子页面
        for child in page.getAllChildren():
            cls._printPageTree(child, level + 1)
    
    @classmethod
    def getRatio(cls, appName: str) -> float:
        """获取应用的积分换算比例
        Args:
            appName: 应用名称
        Returns:
            float: 换算比例，如果应用不存在返回默认值0.01
        """
        app = cls.apps.get(appName)
        return app.ratio if app else 0.01
    
   
    @classmethod
    def getAppNames(cls) -> list:
        """获取所有应用名称列表
        Returns:
            list: 应用名称列表
        """
        return list(cls.apps.keys())
        
    @classmethod
    def exist(cls, appName: str) -> bool:
        """检查应用是否存在
        Args:
            appName: 应用名称
        Returns:
            bool: 应用是否存在
        """
        return appName in cls.apps

    @classmethod
    def fuzzyMatchApp(cls, appName: str) -> str:
        """根据输入的应用名模糊匹配最相近的应用
        Args:
            appName: 用户输入的应用名
        Returns:
            str: 匹配到的应用名，如果没有匹配到返回None
        """
        if appName is None or appName.strip() == '':
            return None
        log = _Log._Log_
        try:
            # 如果完全匹配，直接返回
            appName = appName.lower()
            if appName in cls.apps:
                return appName
            
            # 模糊匹配：检查输入是否是某个应用名的子串
            ret = _G._G_.Tools().regexMatch(appName, cls.apps.keys())
            log.i(f"模糊匹配: {appName} 结果为: {ret}")
            if ret:
                return ret
        except Exception as e:
            log.ex(e, "应用模糊匹配失败")
        return None
    
  

    @classmethod
    def getCurAppName(cls) -> str:
        """获取当前应用名称"""
        if _App_._curAppName is None:
            return _G.TOP
        return _App_._curAppName
        
    @classmethod
    def _setCurAppName(cls, appName: str):
        """设置当前应用名称"""
        if appName == _App_._curAppName:
            return
        _App_._curAppName = appName
        log = _G._G_.Log()
        log.i(f"当前应用: {appName}")

    @classmethod
    def detectAppName(cls) -> str:
        """检测当前运行的应用名
        Returns:
            str: 应用名称，如果未检测到则返回None
        """
        g = _G._G_
        log = g.Log()
        tools = g.Tools()
        try:
            # log.d("检测当前运行的应用")
            if tools.android is None:
                return cls.getCurAppName()
            # 获取当前运行的应用信息
            appInfo = g.Tools().getCurrentAppInfo()
            # log.i(f"当前应用信息: {appInfo}")
            if not appInfo:
                # log.w("无法获取当前运行的应用信息")
                return None
            # 检查是否在桌面
            if tools.isHome():
                return _G.TOP
            appName = appInfo.get("appName")
            return appName
        except Exception as e:
            log.ex(e, "检测当前运行的应用失败")
            return None

    @classmethod
    def detect(cls, appName:str=None, pageName:str=None, delay: int = 5) -> bool:
        try:
            """检测当前页面"""
            time.sleep(delay)
            g = _G._G_
            log = g.Log()
            curAppName = cls.detectAppName()
            if g.Tools().android is None:
                # 如果是PC端，则直接使用appName
                curAppName = appName
            cls._setCurAppName(curAppName)
            app = cls.apps.get(curAppName)
            if app:
                if not app.detectPage(pageName,0):
                    log.e(f"检测当前页面失败: {pageName}")
                    return False
            if appName is None or appName.strip() == '':
                return True
            return appName == curAppName
        except Exception as e:
            log.ex(e, "检测当前页面失败")
            return False
    
    @classmethod
    def isHome(cls) -> bool:
        """检查是否在主屏幕"""
        tools = _G._G_.Tools()
        if tools.android is None:
            return cls.getCurAppName() == _G.TOP
        return tools.isHome()
    
    @classmethod
    def goHome(cls)->bool:
        """返回主屏幕"""
        return cls.goApp(_G.TOP)    

    @classmethod
    def goApp(cls, appName, onOpened=None) -> bool:
        """跳转到指定应用"""
        try:
            g = _G._G_
            log = g.Log()
            app = None
            if not isinstance(appName,str):
                app = appName
                appName = appName.name
            else:
                app = g.App().getApp(appName, True)
            if app is None:
                log.e(f"打开未知应用{appName}")
            else:
                appName = app.name
            # 如果已经在目标应用，直接返回成功
            if cls.getCurAppName() == appName:
                return True
            tools = g.CTools()
            ret = tools.openApp(appName)
            if not ret:
                log.e(f"打开应用 {appName} 失败")
                return False
            # 等待应用打开检查
            ret = cls.detect(appName)
            return ret
        except Exception as e:
            log.ex(e, "切换应用失败")
            return False
    
   
    @classmethod
    def closeApp(cls, appName=None) -> bool:
        """关闭应用
        
        Args:
            appName: 应用名称，如果为None则关闭当前应用
            
        Returns:
            bool: 是否成功关闭应用
        """
        g = _G._G_
        log = g.Log()
        tools = g.Tools()
        
        # 如果未指定应用名，使用当前应用
        if not appName:
            appName = cls.getCurAppName()        
        if not appName:
            log.e("未指定要关闭的应用")
            return False
        
        # 如果是桌面应用，无需关闭
        if appName == _G.TOP:
            return True            
        # 关闭应用
        result = tools.closeApp(appName)
        if result:
            # 如果关闭的是当前应用，设置当前应用为主屏幕
            if appName == cls.getCurAppName():
                cls._setCurAppName(_G.TOP)
            return True
        return False
    
    @classmethod
    def getApp(cls, appName, fuzzyMatch=False) -> "_App_":
        """获取指定应用对象
        
        Args:
            appName: 应用名称
            fuzzyMatch: 是否进行模糊匹配，默认为False
            
        Returns:
            应用对象，如果未找到则返回None
        """
        if appName is None or appName.strip() == '':
            return None
        if _G._G_.Tools().isTop(appName):
            return cls.Top
        app = cls.apps.get(appName.lower())
        if app:
            return app
        # 精确匹配
        if not fuzzyMatch:
            return None
        # 使用相似度匹配
        matchedAppName = cls.fuzzyMatchApp(appName)
        if matchedAppName:
            return cls.apps.get(matchedAppName)
        return None
    
    @classmethod
    def getAllApps(cls) -> List[str]:
        """获取所有应用名称"""
        return list(cls.apps.keys())
    

    @classmethod
    def registerCommands(cls):
        """注册命令"""
        from _CmdMgr import regCmd
        @regCmd(r"#加载配置|jzpz")
        def loadConfig(cls):
            """加载配置"""
            g = _G._G_
            g.CFileServer().download('config/pages.json', lambda result: g.App().loadConfig())



    @classmethod
    def onLoad(cls, oldCls):
        """克隆"""
        if oldCls:
            cls.loadConfig()

_App_.onLoad(None)