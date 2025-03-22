import time
import _G
from typing import Optional, List

from typing import TYPE_CHECKING

import _App

class CApp_(_App._App_):
    """客户端应用管理类"""
    
    
    def getCurPage(self, refresh=False):
        """客户端实现：通过屏幕检测当前页面"""
        if refresh:
            _G._G_.CTools().refreshScreenInfos()
            import _Page
            self.currentPage = _Page._Page_.detectPage(self.rootPage)
        return self.currentPage
    
    def recordBehavior(self):
        """客户端特有方法：记录用户行为"""
        # ... [客户端行为记录逻辑]

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
            return True
        log.i(f"=> {appName}")
        # 点击应用图标
        tools = g.CTools()
        result = tools.openApp(appName)
        if not result:
            log.e(f"点击应用 {appName} 失败")
            return None
        # 设置当前应用名称
        cls._curAppName = appName
        app = cls.getApp(appName)
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
        tools = g.CTools()
        
        # 如果未指定应用名，使用当前应用
        if not appName:
            appName = cls._curAppName        
        if not appName:
            log.e("未指定要关闭的应用")
            return False
        
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
        for app in cls.apps.values():
            page = app.rootPage.findChild(pageName)
            if page:
                return app, page
        return None, None   
    
    def _gotoPage(self, pageName, checkWaitTime=None):
        """跳转到目标页面
        Args:
            pageName: 目标页面名称
            checkWaitTime: 检查等待时间，如果为None则使用页面默认值
            
        Returns:
            成功返回目标页面对象，失败返回None
        """
        try:
            g = _G._G_
            log = g.Log()
            # 如果已经在目标页面，直接返回成功
            if self.currentPage.name == pageName:
                return self.currentPage
            if pageName == _G.TOP:
                return CApp_.gotoApp(pageName)
            # 查找路径
            pages = self.currentPage.findPath(pageName)
            if pages is None:
                log.e(f"找不到从 {self.currentPage.name} 到 {pageName} 的路径")
                return None
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
            # 更新当前页面
            self.setCurrentPage(page)
            return page
        except Exception as e:
            log.ex(e,  f"跳转失败")
            return None

    @classmethod
    def go(cls, toPageName) -> Optional[str]:
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
            # 如果目标是Top(主屏幕)
            if toPageName == _G.TOP:
                log.i("返回主屏幕")
                if cls.goHome():
                    return _G.TOP
            
            # 如果目标是应用名
            if toPageName in cls.apps:
                app = cls.gotoApp(toPageName)
                if app:
                    return app.name
            
            # 2. 目标是应用内页面，查找包含目标页面的应用
            app, page = cls._findPage(toPageName, log)
            if not app or not page:
                log.e(f"找不到页面: {toPageName}")
                return False
            # 如果目标应用不是当前应用，则跳转到目标应用
            if app.name != cls._curAppName:
                cls.gotoApp(app.name)
            app = cls.getApp(cls._curAppName)
            # 在目标应用内跳转到目标页面
            page = app._gotoPage(page.name)
            if page:
                return page.name
        except Exception as e:
            log.ex(e,  f"跳转失败")
        return None

    @classmethod
    def _refreshCurApp(cls) -> Optional[str]:
        """检测当前运行的应用并设置为当前应用
        
        Returns:
            str: 应用名称，如果未检测到则返回None
        """
        g = _G._G_
        log = g.Log()
        tools = g.CTools()
        try:
            if tools.android:
                # 获取当前运行的应用信息
                appInfo = g.CTools().getCurrentAppInfo()
                log.i(f"当前应用信息: {appInfo}")
                if not appInfo:
                    log.w("无法获取当前运行的应用信息")
                    return None
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