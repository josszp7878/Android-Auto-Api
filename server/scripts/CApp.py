import time
from typing import Optional, cast, TYPE_CHECKING
import _G
import _App
if TYPE_CHECKING:
    from _Page import _Page_

class CApp_(_App._App_):
    """客户端应用管理类"""

 
    
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
                currentApp = cls.getApp(cls.getCurAppName(), True)
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
       
    def _gotoPage(self, page: "_Page_", checkWaitTime=None) -> bool:
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
            
            Checker = g.Checker()
            # 执行路径中的每一步跳转
            page = self.currentPage
            for i in range(1, len(pages)):  # 从1开始，因为0是当前页面
                nextPage = pages[i]
                
                # 执行跳转动作
                result = page.go(nextPage)
                if not result:
                    log.e(f"跳转失败: {page.name} -> {nextPage.name}")
                    return False
                
                #移除当前页面检测器
                page.removeCheckers(Checker)
                # 将页面检测器添加到全局列表
                nextPage.addCheckers(Checker)
                # 等待检查页面跳转检查
                time.sleep(Checker.pageChackerInterval)
                # 检查页面跳转是否是目标页面
                result = self._curAppName == self.name and nextPage.name == self.currentPage.name
                log.i(f"->{nextPage.name} : {result}")
                if not result:
                    return False
                self.currentPage = nextPage
                page = nextPage
            return True
        except Exception as e:
            log.ex(e, "跳转失败")
            return False


    @classmethod
    def go(cls, pageName) -> bool:
        """跳转到指定页面"""
        try:
            g = _G._G_
            log = g.Log()
            pageName = pageName.lower()
            tools = g.CTools()
            if tools.isTop(pageName):
                # 返回主屏幕，使用Top应用
                return cls.goHome()
            # 使用getter方法获取当前应用名
            app = cls.getApp(cls.getCurAppName())
            page = None
            if tools.isRoot(pageName):
                # 返回当前应用的根页面
                page = app.rootPage
            else:
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
                if page is None:
                    # 目标应用不存在，到当前应用中查找目标页面
                    app = cls.getCurApp()
                    page = app.rootPage.findChild(pageName)
                if page is None:
                    #到所有其它应用中查找目标页面
                    for app in cls.apps.values():
                        if app == cls.getCurApp():
                            continue    
                        page = app.rootPage.findChild(pageName)
                        if page:
                            app = app
                            break
                if page is None:
                    log.e(f"所有应用都找不到页面{pageName}")
                    return False
                # 如果目标应用不是当前应用，则跳转到目标应用
                appName = app.name
                curAppName = cls.getCurAppName()
                # log.i(f"当前应用: {curAppName}, 目标应用: {appName}")
                if appName.lower() != curAppName.lower():
                    ret = cls.goApp(appName)
                    if not ret:
                        return False
                    if app is None:
                        log.e(f"目标应用未配置: {appName}")
                        return False
            cApp = cast(CApp_, app)
            return cApp._gotoPage(page)
        except Exception as e:
            log.ex(e, "跳转失败")
        return False


# 导出类
__all__ = ['CApp_']