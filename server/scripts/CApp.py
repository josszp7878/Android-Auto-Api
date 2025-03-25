import _G
from typing import Optional, cast
import _App

class CApp_(_App._App_):
    """客户端应用管理类"""
    
    def getCurPage(self, refresh=False):
        """客户端实现：通过屏幕检测当前页面"""
        if refresh:
            _G._G_.Tools().refreshScreenInfos()
            import _Page
            self.currentPage = _Page._Page_.detectPage(self.rootPage)
        return self.currentPage
    
    def recordBehavior(self):
        """客户端特有方法：记录用户行为"""
        # ... [客户端行为记录逻辑]

    @classmethod
    def isHome(cls) -> bool:
        """检查是否在主屏幕"""
        tools = _G._G_.Tools()
        if tools.android is None:
            return cls._curAppName == _G.TOP
        return tools.isHome()
    
    @classmethod
    def goHome(cls):
        """返回主屏幕"""
        tools = _G._G_.Tools()
        if tools.goHome():
            cls._curAppName = _G.TOP
            return True
        return False

    @classmethod
    def gotoApp(cls, appName) -> Optional["CApp_"]:
        """跳转到指定应用
        Args:
            appName: 应用名称
            
        Returns:
            CApp_: 应用对象
        """
        g = _G._G_
        log = g.Log()
       
        # 如果已经在目标应用，直接返回成功
        if cls._curAppName == appName:
            return cls.getApp(appName)
        
        # 如果目标是桌面，使用goHome方法
        if appName == _G.TOP:
            if cls.goHome():
                return cls.getApp(_G.TOP)
            return None
            
        log.i(f"=> {appName}")
        tools = g.CTools()
        waitTime = None
        app = cls.getApp(appName)
        if app:
            waitTime = app.timeout
        result = tools.openApp(appName, waitTime)
        if not result:
            return None
        rootPage = app.rootPage
        rootPage.checkCheckers()
        # 设置当前应用名称
        cls._curAppName = appName
        app = cls.getApp(appName)
        # 检测该应用当前在哪个页面
        childPages = app.rootPage.children
        for _, page in childPages.items():
            if page.checkRules(page.rules):
                app.setCurrentPage(page)
                break
        return app
    
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
            appName = cls._curAppName        
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
            if appName == cls._curAppName:
                cls._curAppName = _G.TOP
            return True
        return False
    
    @classmethod
    def getAllRootPages(cls):
        """获取所有应用的根页面"""
        return [app.rootPage for app in cls.apps.values()] 
 
    @classmethod    
    def _findPage(cls, pageName, log):
        """查找目标页面
        
        Args:
            pageName: 目标页面名称
            log: 日志对象
            
        Returns:
            成功返回目标页面对象，失败返回None
        """
        try:
            import re
            # 使用正则表达式匹配 appName.pageName 格式
            match = re.match(r"(?P<appName>[^.。]+)[\.。](?P<pageName>.+)", pageName)
            if match:
                appName = match.group("appName")
                pageName = match.group("pageName")
                app = cls.getApp(appName, True)
                if app is None:
                    log.i(f"应用 {appName} 没配置")
                    return None, None
                page = app.rootPage.findChild(pageName)
                if page:
                    return app, page
            else:
                currentApp = cls.getApp(cls._curAppName, True)
                if currentApp:
                    rootPage = currentApp.rootPage
                    page = rootPage.findChild(pageName)
                    if page:
                        return currentApp, page                    
                for app in cls.apps.values():
                    if app == currentApp:
                        continue
                    rootPage = app.rootPage
                    page = rootPage.findChild(pageName)
                    if page:
                        return app, page

        except Exception as e:
            log.ex(e, "查找目标页面失败")
        return None, None
       
    def _gotoPage(self, pageName, checkWaitTime=None) -> Optional["_Page_"]:
        """跳转到目标页面
        Args:
            pageName: 目标页面名称
            checkWaitTime: 检查等待时间，如果为None则使用页面默认值
            
        Returns:
            成功返回目标页面对象，失败返回None
        """
        try:
            if self.currentPage.name == pageName:
                return self.currentPage
            g = _G._G_
            log = g.Log()
            if pageName in self.RootStr:
                pageName = self.name   
            # 查找路径
            pages = self.currentPage.findPath(pageName)
            if pages is None:
                log.e(f"找不到从 {self.currentPage.name} 到 {pageName} 的路径")
                return None
            log.i(f"找到路径: {'->'.join([p.name for p in pages])}")
            # 执行路径中的每一步跳转
            page = self.currentPage
            for i in range(1, len(pages)):  # 从1开始，因为0是当前页面
                nextPage = pages[i]
                # 执行跳转动作
                result = page.go(nextPage, checkWaitTime)
                if not result:
                    log.e(f"跳转失败: {page.name} -> {nextPage.name}")
                    return None
                page = nextPage
                self.setCurrentPage(nextPage)
            # 更新当前页面
            return page
        except Exception as e:
            log.ex(e, "跳转失败")
            return None

    TopStr = ["top", "主屏幕", "桌面"]
    RootStr = ["app", "应用", "root"]
    @classmethod
    def go(cls, pageName) -> bool:
        """跳转到指定页面
        
        Args:
            toPageName: 目标页面名称
            
        Returns:
            成功返回目标页面对象，失败返回None
        """
        try:
            g = _G._G_
            log = g.Log()
            # 1. 处理特殊情况
            ##############################################################    
            pageName = pageName.lower()
            if pageName in cls.TopStr:
                # 返回主屏幕，使用Top应用
                return cls.gotoApp(_G.TOP) is not None
            elif pageName in cls.apps:
                return cls.gotoApp(pageName) is not None    
            ##############################################################    
            app = cls.getApp(cls._curAppName)
            page = None
            import re
            # 使用正则表达式匹配 appName.pageName 格式
            match = re.match(r"(?P<appName>[^.。]+)[\.。](?P<pageName>.+)", pageName)
            if match:
                appName = match.group("appName")
                app = cls.getApp(appName, True)
                if app is None:
                    log.e(f"应用 {appName} 没配置")
                    return False
                # 目标应用存在，查找该应用的目标页面是否存在
                pageName = match.group("pageName")
                page = app.rootPage.findChild(pageName)
                if page is None:
                    log.e(f"{app.name} 找不到页面: {pageName}")
                    return False
            if app is None:
                #到所有应用中查找目标页面
                for app in cls.apps.values():
                    page = app.rootPage.findChild(pageName)
                    if page:
                        app = app
                        break
                if app is None:
                    log.e(f"所有应用都找不到页面{pageName}")
                    return False
            # 如果目标应用不是当前应用，则跳转到目标应用
            appName = app.name
            if appName != cls._curAppName:
                app = cls.gotoApp(appName)
                if not app:
                    log.e(f"跳转到应用 {appName} 失败")
                    return False
            app = cast(CApp_, app)
            # 在目标应用内跳转到目标页面
            return app._gotoPage(pageName) is not None
        except Exception as e:
            log.ex(e, "跳转失败")
        return False

    @classmethod
    def _refreshCurApp(cls) -> Optional[str]:
        """检测当前运行的应用并设置为当前应用
        
        Returns:
            str: 应用名称，如果未检测到则返回None
        """
        g = _G._G_
        log = g.Log()
        tools = g.Tools()
        try:
            if tools.android:
                # 获取当前运行的应用信息
                appInfo = g.Tools().getCurrentAppInfo()
                log.i(f"当前应用信息: {appInfo}")
                if not appInfo:
                    log.w("无法获取当前运行的应用信息")
                    return None
                # 检查是否在桌面
                if tools.isHome():
                    cls._curAppName = _G.TOP
                    return _G.TOP
                    
                appName = appInfo.get("appName")
                # 设置为当前应用
                cls._curAppName = appName
            return cls._curAppName
        except Exception as e:
            log.ex(e, "检测当前运行的应用失败")
            return None
   
    @classmethod
    def getCurAppName(cls, refresh=False) -> Optional[str]:
        """获取当前应用名称"""
        if refresh:
            cls._refreshCurApp()
        return super().getCurAppName(refresh)


# 导出类
__all__ = ['CApp_']