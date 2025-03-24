import json
from pathlib import Path
import _Log
import _G
from typing import Optional, List, Dict, Any, TYPE_CHECKING
if TYPE_CHECKING:
    import _Page

class _App_:
    """应用管理类：整合配置与实例"""
    _curAppName = _G.TOP  # 当前应用名称
    apps = {}  # 存储应用实例 {appName: _App_实例}

    def __init__(self, name:str, rootPage: "_Page._Page_", info:dict, alerts:list):
        self.name = name
        self.rootPage = rootPage
        self.currentPage = rootPage
        self.ratio = info.get("ratio", 10000)
        self.description = info.get("description", '')
        self.timeout = info.get("timeout", 30)
        self.alerts = alerts

    def setCurrentPage(self, page):
        """设置应用当前页面"""
        self.currentPage = page
        log = _G._G_.Log()
        log.i(f"当前应用.页面：[{self.name}].[{page.name}]")
        return page
    
    def getCurPage(self, refresh=False):
        """基类实现：基础页面获取逻辑"""
        return self.currentPage
    
    @classmethod
    def loadConfig(cls, AppClass=None):
        """加载配置并创建应用实例与页面树
        Args:
            AppClass: 要创建的应用类，如果为None则根据环境自动选择
        """
        g = _G._G_
        log = g.Log()
        try:
            configPath = Path(__file__).parent.parent / 'config' / 'pages.json'
            with open(configPath, 'r', encoding='utf-8') as f:
                configData = json.load(f)

            cls.apps.clear()
            import _Page
            Page = _Page._Page_
            root = Page.Root()

            def processNode(node, parentPage=None, parentName=None):
                """统一处理节点：创建应用实例和页面树"""
                for pageName, pageConfig in node.items():
                    if not isinstance(pageConfig, dict):
                        log.e(f"页面配置错误,该节点不是字典: {pageConfig}")
                        continue
                    # 创建页面对象
                    currentPage = Page.createPage(pageName, parentPage, pageConfig.get("check", []), pageConfig.get("in", None), pageConfig.get("out", None), pageConfig.get("alerts", None))
                    # 识别应用根节点（Top的直接子节点）
                    if parentName == "Top":
                        appInfo = pageConfig.get("app_info", {})
                        # 使用传入的AppClass创建实例
                        cls.apps[pageName] = AppClass(
                            name=appInfo.get("name", pageName),
                            rootPage=currentPage,
                            info=appInfo,
                            alerts=pageConfig.get("alerts", [])
                        )
                    # log.d(f"创建应用 {pageName}，根页面 {currentPage.name}")

                    # 递归处理子节点
                    children = pageConfig.get("children", {})
                    if children:
                        processNode(children, currentPage, pageName)

            # 从Top节点开始处理
            processNode(configData.get("Top", {}).get("children", {}), root, "Top")
            
            log.i(f"加载完成：共{len(cls.apps)}个应用")
            cls.printTopology()

        except Exception as e:
            log.ex(e, "配置加载失败")
            cls.apps.clear()

    @classmethod
    def printTopology(cls):
        """打印页面拓扑结构"""
        log = _G._G_.Log()
        log.i("页面拓扑结构:")
        
        # 获取所有应用的根页面
        rootPages = []
        for app in cls.apps.values():
            rootPages.append(app.rootPage)
        
        # 打印每个应用的页面树
        for rootPage in rootPages:
            cls._printPageTree(rootPage)
    
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
            matches = []
            for name in cls.apps.keys():
                # 计算相似度：如果输入是应用名的子串，或应用名是输入的子串
                if appName in name or name in appName:
                    # 计算匹配度：子串在全串中的比例
                    similarity = len(appName) / len(name) if len(name) > 0 else 0
                    matches.append((name, similarity))
            # 按相似度排序，取最匹配的
            if matches:
                matches.sort(key=lambda x: x[1], reverse=True)
                log.i(f"应用[{appName}]模糊匹配到[{matches[0][0]}]")
                return matches[0][0]
        except Exception as e:
            log.ex(e, "应用模糊匹配失败")
        return None
    
    @classmethod
    def getCurAppName(cls, refresh=False) -> Optional[str]:
        """获取当前应用名称"""
        if cls._curAppName is None:
            return _G.TOP
        return cls._curAppName
    
   
    
    @classmethod
    def getApp(cls, appName, fuzzyMatch=False) -> "_App_":
        """获取指定应用对象
        
        Args:
            appName: 应用名称
            fuzzyMatch: 是否进行模糊匹配，默认为False
            
        Returns:
            应用对象，如果未找到则返回None
        """
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

    def cast(self, cls):
        """将当前实例转换为指定类型，仅用于类型提示
        
        Args:
            cls: 目标类型
            
        Returns:
            self: 返回自身实例，但类型会被IDE识别为目标类型
        """
        return self