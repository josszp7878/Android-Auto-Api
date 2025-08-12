import re
from typing import Dict, Optional
from _App import _App_
from RPC import RPC
import _G


class _Device_():
    """设备App管理基类：提供查询、创建和跟踪当前app的功能"""

    def __init__(self):
        self._apps: Dict[str, _App_] = {}  # 设备的App列表
        self._currentApp: Optional[_App_] = None  # 当前跟踪的App
        self._lastApp: Optional[_App_] = None  # 上一次跟踪的App
        self._curAppInfo = {}

    @property
    def apps(self) -> Dict[str, _App_]:
        """获取设备的App列表（Lazy初始化）"""
        if not self._apps:
            self._loadApps()
        return self._apps

    @property
    def currentApp(self) -> Optional[_App_]:
        """获取当前App"""
        return self._currentApp

    @property
    def lastApp(self) -> Optional[_App_]:
        """获取上一次App"""
        return self._lastApp

    @property
    def curAppName(self) -> str:
        """获取当前应用名称"""
        return self._curAppInfo.get('appName')

    def isConnected(self) -> bool:
        return True
    
    @property
    def curAppInfo(self) -> dict:
        """获取当前应用信息"""
        return self._curAppInfo
    
    @RPC()
    def setCurApp(self, appInfo: dict):
        """设置当前检测应用名称"""
        if not appInfo:
            return
        g = _G._G_
        log = g.Log()
        curAppName = (self._curAppInfo.get('appName')
                      if self._curAppInfo else None)
        if curAppName == appInfo.get('appName'):
            # 如果应用名称相同，则不更新
            return
        log.i(f"@@设置当前应用为: {appInfo}")
        self._curAppInfo = appInfo
        # 如果是已知应用则更新实例
        app = self.getApp(appInfo.get('appName'))
        self._currentApp = app
        if app:
            self._lastApp = app
        if not g.isServer():
            # 检查设备是否连接后再进行RPC同步
            try:
                if self.isConnected():
                    # rpc 同步服务端
                    g.RPCClient(self.id, '_Device_.setCurApp',
                               {'appInfo': appInfo})
                else:
                    log.d(f"设备{self.name}未连接，跳过RPC同步")
            except Exception as e:
                log.ex_(e, f"RPC同步失败: {appInfo}")

    def getAppByID(self, id: int) -> "_App_":
        """根据ID获取应用实例"""
        for app in self.apps.values():
            if app.id == id:
                return app
        return None

    def matchApp(self, name: str) -> Optional[str]:
        """匹配应用"""
        App = _G._G_.App()
        name = name.strip().lower() if name else ''
        for appName in App.getAppNames():
            if re.match(name, appName):
                return appName
        return None

    def getApp(self, name: str, create: bool = False) -> Optional[_App_]:
        """获取指定的App
        Args:
            name: App名称
            create: 服务端支持从模板创建，客户端不支持创建
        Returns:
            Optional[_App_]: App实例或None
        """
        g = _G._G_
        log = g.Log()
        try:
            name = self.matchApp(name)
            if not name:
                return None
            # 首先检查缓存中是否存在
            if name in self.apps:
                return self.apps[name]
            if not create:
                return None
            app = self._createApp({'name': name})
            if app:
                self.apps[name] = app   # 添加到缓存
                return app
            return None
        except Exception as e:
            log.ex_(e, f"获取App失败: {name}")
            return None

    def _createApp(self, data: dict) -> '_App_':
        """创建App"""
        return None

    def currentInfo(self) -> str:
        """显示当前客户端的实时信息"""
        g = _G._G_
        log = g.Log()

        try:
            # 获取当前应用和页面信息
            currentApp = self.currentApp
            if currentApp:
                appName = currentApp.name
                currentPage = currentApp.curPage
                pageName = currentPage.name if currentPage else "未知页面"
            else:
                appName = "未知应用"
                pageName = "未知页面"

            # 获取当前任务信息
            taskInfo = "无任务"
            if currentApp and currentApp.curTask:
                task = currentApp.curTask
                taskName = task.name
                taskState = (task.state.name if hasattr(task.state, 'name')
                             else str(task.state))
                progress = getattr(task, 'progress', 0)
                taskInfo = f"{taskName}（{taskState}，{progress}%）"

            # 格式化输出
            result = f"""设备：{self.name}（{self.id}）
显示：{appName}-{pageName}
任务：{taskInfo}"""

            return result

        except Exception as e:
            log.ex(e, "获取当前信息失败")
            return f"e~获取当前信息失败: {str(e)}"

    @RPC()
    def getAppList(self) -> dict:
        """获取设备的App列表"""
        g = _G._G_
        log = g.Log()
        try:
            return [app.data for app in self.apps.values()]
        except Exception as e:
            log.ex_(e, "获取App列表失败")
            return []

    def _detectCurrentApp(self) -> Optional[str]:
        """检测当前App（子类需要实现）"""
        # 这个方法应该由子类实现，根据具体环境检测当前App
        return None

    def _loadApps(self):
        """加载App数据（子类可以重写）"""
        # 子类可以重写这个方法来加载持久化的App数据
        pass

    def _saveApps(self):
        """保存App数据（子类可以重写）"""
        # 子类可以重写这个方法来保存App数据到持久化存储
        pass

    def toDict(self) -> dict:
        """转换为字典格式"""
        return {
            'apps': {name: {'name': name,
                            'description': getattr(app, 'description', '')}
                     for name, app in self.apps.items()},
            'currentApp': self._currentApp.name if self._currentApp else None
        }

    @classmethod
    def get(cls, id) -> '_Device_':
        """获取Device实例"""
        g = _G._G_
        log = g.Log()
        try:
            if g.isServer():
                device = g.SDeviceMgr().get(id)
                return device
            else:
                # 客户端获取当前设备实例
                device = g.CDevice()
                if device is None:
                    log.e("客户端获取当前设备失败")
                return device
        except Exception as e:
            log.ex_(e, f"获取Device实例异常: id={id}")
            return None