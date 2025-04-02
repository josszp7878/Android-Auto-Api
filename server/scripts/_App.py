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

    @classmethod
    def Clone(cls, oldCls):
        """克隆"""
        cls.loadConfig()

    def __init__(self, name:str, rootPage: "_Page._Page_", info:dict):
        self.name = name
        self.rootPage = rootPage
        self.currentPage = rootPage
        self.ratio = info.get("ratio", 10000)
        self.description = info.get("description", '')
        self.timeout = info.get("timeout",5)

    @property   
    def curPage(self):
        """应用当前页面"""
        return self.currentPage
    
    @curPage.setter
    def curPage(self, page: "_Page._Page_"):
        """设置应用当前页面"""
        if page == self.currentPage:
            return
        self.currentPage = page
        
    def detectPage(self, page: "_Page._Page_"=None)->Optional["_Page._Page_"]:
        """客户端实现：通过屏幕检测当前页面"""
        if page is not None:
            #先自接检测目标页面
            if page.match():
                self.curPage = page
                return page
        #检测当前页面
        tools = _G._G_.CTools()  
        tools.refreshScreenInfos()
        page = self.rootPage.detectPage()
        if page is None:
            return None
        self.curPage = page
        return page
    
    
    @classmethod
    def loadConfig(cls):
        """加载配置并创建应用实例与页面树"""
        g = _G._G_
        log = g.Log()      
        try:
            import json
            import os
            import CChecker
            import _Page
            # 清空现有应用
            cls.apps = {}
            Page = _Page._Page_
            root = Page.Root()
            if g.isServer():
                from SApp import SApp_
                AppClass = SApp_
            else:
                from CApp import CApp_
                AppClass = CApp_
            cls.Top = AppClass("Top", root, {})
            # 尝试加载配置文件
            try:
                configFile = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "pages.json")
                with open(configFile, 'r', encoding='utf-8') as f:
                    configData = json.load(f)
            except Exception as e:
                log.e(f"加载配置文件失败: {e}")
                return False
            
            # 首先读取TOP节点的checkers配置
            topCheckers = configData.get("Top", {}).get("checkers", {})
            if topCheckers:
                CChecker.CChecker_.loadTemplates(topCheckers)
                log.i(f"已加载{len(topCheckers)}个checker模板")
            
            # 创建根页面
            root = Page.createPage("Top", None, [], None, None)
            
            # 递归处理配置树
            def processNode(node, parentPage, parentName):
                for pageName, pageConfig in node.items():
                    if not isinstance(pageConfig, dict):
                        log.e(f"页面配置错误,该节点不是字典: {pageConfig}")
                        continue
                    # 创建页面对象
                    pageName = pageName.lower()
                    match = pageConfig.get("match", [])
                    inAction = pageConfig.get("in", None)
                    outAction = pageConfig.get("out", None)
                    checkers = pageConfig.get("checkers", None)
                    dialogs = pageConfig.get("dialogs", None)
                    currentPage = Page.createPage(pageName, parentPage, match, inAction, outAction, checkers, dialogs)
                    # 识别应用根节点（Top的直接子节点）
                    if parentName == "Top":
                        appInfo = pageConfig.get("app_info", {})
                        # 使用传入的AppClass创建实例
                        cls.apps[pageName] = AppClass(
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
        log = _Log._Log_
        try:
            # 如果完全匹配，直接返回
            appName = appName.lower()
            if appName in cls.apps:
                return appName
            
            # 模糊匹配：检查输入是否是某个应用名的子串
            # ret, sim = _G._G_.CTools().similarMatch(appName, cls.apps.keys(),0)
            ret = _G._G_.Tools().regexMatch(appName, cls.apps.keys())
            log.i(f"模糊匹配: {appName} 结果为: {ret}")
            if ret:
                return ret
        except Exception as e:
            log.ex(e, "应用模糊匹配失败")
        return None
    
    @classmethod
    def detectCurApp(cls) -> "_App_":
        """检测当前运行的应用并设置为当前应用
        Returns:
            _App_: 应用实例，如果未检测到则返回None
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
                return cls.Top
            appName = appInfo.get("appName")
            cls._curAppName = appName
            app = cls.apps.get(appName)
            return app
        except Exception as e:
            log.ex(e, "检测当前运行的应用失败")
            return None

    @classmethod
    def getCurAppName(cls) -> str:
        """获取当前应用名称"""
        if _App_._curAppName is None:
            return _G.TOP
        return _App_._curAppName
        
    @classmethod
    def setCurAppName(cls, appName: str):
        """设置当前应用名称"""
        _App_._curAppName = appName
    
    @classmethod
    def getCurApp(cls, refresh=False) -> Optional["_App_"]:
        """获取当前应用对象"""
        appName = cls.getCurAppName()
        if appName.lower() == _G.TOP:
            return cls.Top
        return cls.apps.get(appName)
    
    @classmethod
    def isHome(cls) -> bool:
        """检查是否在主屏幕"""
        tools = _G._G_.Tools()
        if tools.android is None:
            return cls.getCurAppName() == _G.TOP
        return tools.isHome()
    
    @classmethod
    def goHome(cls):
        """返回主屏幕"""
        return cls.goApp(_G.TOP)    

    @classmethod
    def goApp(cls, appName, onOpened=None) -> bool:
        """跳转到指定应用"""
        try:
            g = _G._G_
            log = g.Log()
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
            result = False
            if not ret:
                log.e(f"打开应用 {appName} 失败")
                return False
            if tools.android is None:
                #对应PC端，这里一定要设置当前应用名称，否则无法检测到当前应用
                cls.setCurAppName(appName)
            # 等待应用打开检查
            time.sleep(g.Checker().pageChackerInterval)
            # 检查应用是否打开
            result = appName == cls.getCurAppName()
            log.i(f"=>{appName} : {result}")
            return result
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
                cls.setCurAppName(_G.TOP)
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
