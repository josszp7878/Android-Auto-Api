import time
import _G
from typing import Optional, Dict, List

class CApp_:
    """应用管理类：管理应用及其页面状态"""
    
    # 类变量
    _curAppName = _G.TOP  # 当前应用名称
    apps = {}  # 存储应用对象 {appName: CApp_对象}
    
    
    @classmethod
    def getCurAppName(cls, refresh=False) -> Optional[str]:
        """获取当前应用名称"""
        if refresh:
            cls._refreshCurApp()
        return cls._curAppName
    @classmethod
    def _refreshCurApp(cls) -> Optional[str]:
        """检测当前运行的应用并设置为当前应用
        
        Returns:
            str: 应用名称，如果未检测到则返回None
        """
        g = _G._G_
        log = g.Log()
        try:
            if g.CTools().android is None:
                if cls._curAppName is None:
                    cls._curAppName = _G.TOP
                return cls._curAppName
            # 获取当前运行的应用信息
            appInfo = g.CTools().getCurrentAppInfo()
            log.i(f"当前应用信息: {appInfo}")
            if not appInfo:
                log.w("无法获取当前运行的应用信息")
                return None
            appName = appInfo.get("appName")
            # 设置为当前应用
            cls._curAppName = appName
            # 检查应用是否在配置中
            log.i(f"检查应用 {appName} 是否在配置中")
            app = cls.getApp(appName)
            if app:
             # 检测应用当前页面
                currentPage = app.getCurPage()
                if currentPage:
                    app.setCurrentPage(currentPage)
                    log.i(f"检测到应用 {appName} 当前页面: {currentPage.name}")
            return appName
        except Exception as e:
            log.ex(e, "检测当前运行的应用失败")
            return None
        
    

    @classmethod
    def getApp(cls, appName) -> Optional["CApp_"]:
        """获取指定应用对象"""
        log = _G._G_.Log()
        # log.i(f"当前应用有： {cls.apps} ")
        return cls.apps.get(appName)
    
    @classmethod
    def getAllApps(cls) -> List[str]:
        """获取所有应用名称"""
        return list(cls.apps.keys())
    
    @classmethod
    def registerApp(cls, appName, rootPage) -> "CApp_":
        """注册应用"""
        log = _G._G_.Log()
        from _AppMgr import appMgr
        if not appMgr.exist(appName):
            log.w(f"未知应用 {appName}，请在应用配置里想配置")
        app = CApp_(appName, rootPage)
        cls.apps[appName] = app
        return app

    @classmethod
    def isHome(cls) -> bool:
        """检查是否在主屏幕"""
        tools = _G._G_.CTools()
        if tools.android is None:
            return cls._curAppName == _G.TOP
        return tools.isHome()
    
    @classmethod
    def goHome(cls):
        """返回主屏幕"""
        tools = _G._G_.CTools()
        if tools.android is None:
            cls._curAppName = _G.TOP    
            return True
        return tools.goHome()
    
    @classmethod
    def gotoApp(cls, appName) -> bool:
        """跳转到指定应用
        Args:
            appName: 应用名称
            
        Returns:
            bool: 是否成功跳转到应用
        """
        g = _G._G_
        log = g.Log()
       
        # 如果已经在目标应用，直接返回成功
        if cls._curAppName == appName:
            # log.i(f"已经在应用 {appName}，无需跳转")
            return True
        log.i(f"=> {appName}")
        # 点击应用图标
        # log.i(f"打开应用: {appName}")
        tools = g.CTools()
        if tools.android is None:
            result = True
        else:
            result = tools.openApp(appName)
        if not result:
            log.e(f"点击应用 {appName} 失败")
            return False
        # 设置当前应用名称
        cls._curAppName = appName    
        return True
        
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
        tools = g.CTools()
        
        # 如果未指定应用名，使用当前应用
        if not appName:
            appName = cls._curAppName        
        if not appName:
            log.e("未指定要关闭的应用")
            return False
        
        # 执行关闭应用操作
        log.i(f"关闭应用: {appName}")
        result = tools.closeApp(appName)        
        # 无论应用是否在配置中注册，都清除当前应用状态
        if result:
            cls._refreshCurApp()
            log.i(f"已关闭应用 {appName}")
            return True
        else:
            log.e(f"关闭应用 {appName} 失败")
            return False
    
    @classmethod
    def go(cls, tarPageName) -> bool:
        """跳转到指定页面，支持跨应用跳转"""
        g = _G._G_
        log = g.Log()
        
        # 获取当前应用
        curAppName = cls.getCurAppName()
        if not curAppName:
            log.e("无法确定当前应用")
            return False
        
        # 获取当前应用对象
        curApp = cls.getApp(curAppName)
        if not curApp:
            log.e(f"找不到当前应用 {curAppName} 的配置")
            return False
        
        # 查找完整路径
        fullPath = curApp.currentPage.findPath(tarPageName)
        if not fullPath:
            log.e(f"找不到从 {curApp.currentPage.name} 到 {tarPageName} 的路径")
            return False
        log.i(f"完整路径: {'->'.join([p.name for p in fullPath])}")
        # 分析跨应用跳转点
        crossAppIndex = -1
        targetApp = None
        for i, page in enumerate(fullPath):
            # 检查页面是否是其他应用的根页面
            for appName, app in cls.apps.items():
                if appName != curAppName and page == app.rootPage:
                    crossAppIndex = i
                    targetApp = appName
                    break
            if crossAppIndex != -1:
                break
        
        # 处理跨应用跳转
        if crossAppIndex != -1:
            # log.i(f"检测到跨应用跳转点: {fullPath[crossAppIndex].name} → {targetApp}")
            # 分割路径
            crossAppPath = fullPath[crossAppIndex:]
            remainPath = crossAppPath[1:] if len(crossAppPath) > 1 else []
            
            # 执行应用跳转
            if not cls.gotoApp(targetApp):
                log.e(f"跳转到应用 {targetApp} 失败")
                return False
            
            # 获取目标应用对象
            targetApp = cls.getApp(targetApp)
            if not targetApp:
                log.e(f"目标应用 {targetApp} 未注册")
                return False
            log.i(f"remainPath: {'->'.join([p.name for p in remainPath])}")
            # 执行目标应用内的路径
            if remainPath:
                targetPageName = remainPath[-1].name
                log.i(f"在应用 {targetApp} 内继续跳转到 {targetPageName}")
                return targetApp.gotoPage(targetPageName)
            return True
        
        # 无跨应用跳转，正常执行
        return curApp.gotoPage(tarPageName)

    def __init__(self, name, rootPage):
        """初始化应用对象
        
        Args:
            name: 应用名称
            rootPage: 应用根页面对象
        """
        self.name = name  # 应用名称
        self.rootPage = rootPage  # 应用根页面
        self.currentPage = rootPage  # 当前页面，初始为根页面
    
    def setCurrentPage(self, page):
        """设置应用当前页面"""
        self.currentPage = page
        return page
    
    def getCurPage(self, refresh=False):
        """获取应用当前页面"""
        if refresh:
            self.currentPage = self._getCurPage()
        return self.currentPage
    
    def _getCurPage(self):
        """检测应用当前处于哪个页面
        
        Returns:
            检测到的页面对象，如果未检测到则返回None
        """
        log = _G._G_.Log()
        log.i(f"检测应用dddd {self.name} 当前页面") 
        g = _G._G_
        # 刷新屏幕信息
        g.CTools().refreshScreenInfos()
        # 递归检查应用的所有页面
        return self._detectPageRecursive(self.rootPage)
    
    def _detectPageRecursive(self, page, depth=0):
        """递归检测页面
        
        Args:
            page: 要检测的页面
            depth: 当前递归深度
            
        Returns:
            检测到的页面对象，如果未检测到则返回None
        """
        g = _G._G_
        log = g.Log()
        
        # 检查当前页面规则
        if page.checkRules():
            # 先检查子页面，因为子页面规则更具体
            for child in page.getAllChildren():
                result = self._detectPageRecursive(child, depth + 1)
                if result:
                    return result
            
            # 如果没有匹配的子页面，返回当前页面
            return page
        
        return None
    
    def gotoPage(self, pageName, checkWaitTime=None):
        """跳转到目标页面
        Args:
            targetPageName: 目标页面名称
            checkWaitTime: 检查等待时间，如果为None则使用页面默认值
            
        Returns:
            成功返回目标页面对象，失败返回None
        """
        g = _G._G_
        log = g.Log()
        if pageName == _G.TOP:
            return CApp_.gotoApp(pageName)
        # 查找路径
        pages = self.currentPage.findPath(pageName)
        if pages is None:
            log.e(f"找不到从 {self.currentPage.name} 到 {pageName} 的路径")
            return None
        # 获取目标页面对象
        targetPage = pages[-1]
        # 如果已经在目标页面，直接返回成功
        if self.currentPage.name == targetPage.name:
            log.i(f"已经在目标页面 {targetPage.name}，无需跳转")
            return targetPage
        
        # 检查是否存在跨应用路径
        # for i in range(1, len(pages)):
        #     page = pages[i]
        #     # 检查页面是否是应用根页面
        #     for app_name, app in CApp_.apps.items():
        #         if app.name != self.name and page == app.rootPage:
        #             log.w(f"警告: 路径包含跨应用跳转到 {app_name}，暂不支持跨应用路径")
        #             return None
        
        # 执行路径中的每一步跳转
        current = self.currentPage
        for i in range(1, len(pages)):  # 从1开始，因为0是当前页面
            next_page = pages[i]
            # 执行跳转动作
            result = current.go(next_page, checkWaitTime)
            if not result:
                log.e(f"跳转失败: {current.name} -> {next_page.name}")
                return None
            current = next_page
        # 更新当前页面
        self.setCurrentPage(targetPage)
        return targetPage
    
    def isOnPage(self, pageName):
        """检查是否在指定页面
        Args:
            pageName: 页面名称
            
        Returns:
            bool: 是否在指定页面
        """
        # 先检查当前页面
        if self.currentPage and self.currentPage.name == pageName:
            return True
        
        # 重新检测当前页面
        detected = self.getCurPage()
        if detected:
            self.setCurrentPage(detected)
            return detected.name == pageName
        
        return False
    
    def goBack(self, checkWaitTime=None):
        """返回上一页
        
        Args:
            checkWaitTime: 检查等待时间，如果为None则使用页面默认值
            
        Returns:
            成功返回上一页面对象，失败返回None
        """
        g = _G._G_
        log = g.Log()
        android = g.CTools().android
        
        # 如果当前页面是应用根页面，返回主屏幕
        if self.currentPage == self.rootPage:
            log.i(f"当前已是应用 {self.name} 的根页面，返回主屏幕")
            return CApp_.goHome()
        # 获取父页面
        parentPage = self.currentPage.parent
        if not parentPage:
            log.e("当前页面没有父页面")
            return None
        
        # 执行返回操作
        log.i(f"返回上一页: {self.currentPage.name} -> {parentPage.name}")
        result = android.pressBack()
        if not result:
            log.e("执行返回操作失败")
            return None
        
        # 等待指定时间
        wait_time = checkWaitTime if checkWaitTime is not None else parentPage.checkWaitTime
        if wait_time > 0:
            # log.i(f"等待 {wait_time} 秒后检查页面...")
            time.sleep(wait_time)
        
        # 验证父页面
        if parentPage.checkRules():
            log.i(f"成功返回到 {parentPage.name}")
            # 更新当前页面
            self.setCurrentPage(parentPage)
            return parentPage
        else:
            log.e(f"返回失败: 未能验证目标页面 {parentPage.name}")
            
            # 尝试重新检测当前页面
            detected = self.getCurPage()
            if detected:
                self.setCurrentPage(detected)
                log.i(f"检测到当前页面: {detected.name}")
                return detected
            
            return None 

    def findPath(self, toPage):
        """查找从当前页面到目标页面的路径"""
        path = []
        
        def find_parent(page, target):
            if page.name == target:
                return [page]
            for child in page.getAllChildren():
                result = find_parent(child, target)
                if result:
                    return [page] + result
            return None
        
        # 从根页面开始搜索
        path = find_parent(self.rootPage, toPage)
        return " → ".join([p.name for p in path]) if path else None 

    @classmethod
    def getAllRootPages(cls):
        """获取所有应用的根页面"""
        return [app.rootPage for app in cls.apps.values()] 