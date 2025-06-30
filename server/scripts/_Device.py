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
        self._curAppName = None

    @property
    def info(self) -> dict:
        """获取设备信息"""
        return {
            'id': self.id,
        }
    
    @info.setter
    def info(self, value: dict):
        """设置设备信息"""
        self.id = int(value.get('id'))
    
    @property
    def deviceName(self) -> str:
        """获取设备名称"""
        return self.name
        
    @property
    def apps(self) -> Dict[str, _App_]:
        """获取设备的App列表（Lazy初始化）"""
        if not self._apps:
            self._loadApps()
        return self._apps
    
    @RPC()
    def setCurApp(self, name: str):
        """设置当前检测应用名称"""
        if name == self._curAppName:
            return
        g = _G._G_
        self._curAppName = name
        # 如果是已知应用则更新实例
        if name in self._apps:
            self._currentApp = self._apps[name]
        if not g.isServer():
            # rpc 同步服务端
            g.RPCClient(self.id, '_Device_.setCurApp', {'name': name})
    
    @property
    def currentApp(self) -> Optional[_App_]:
        """获取当前App"""
        return self._currentApp

    @property
    def curAppName(self) -> str:
        """获取当前应用名称"""
        return self._curAppName

    def getAppByID(self, id: int) -> "_App_":
        """根据ID获取应用实例"""
        for app in self.apps.values():
            if app.id == id:
                return app
        return None
    
    def matchApp(self, name: str) -> Optional[str]:
        """匹配应用"""
        App = _G._G_.App()
        for appName in App.getAppNames():
            if re.match(name, appName):
                return appName
        return None

    def getApp(self, name: str, create: bool = False) -> Optional[_App_]:
        """获取指定的App
        Args:
            name: App名称
            lazyCreate: 服务端支持从模板创建，客户端不支持创建
        Returns:
            Optional[_App_]: App实例或None
        """
        g = _G._G_
        log = g.Log()
        try:
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
    
    def currentInfo(self)->str:
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
                    taskState = task.state.name if hasattr(task.state, 'name') else str(task.state)
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
            'apps': {name: {'name': name, 'description': getattr(app, 'description', '')} 
                    for name, app in self.apps.items()},
            'currentApp': self._currentApp.name if self._currentApp else None
        }
    
   
    @classmethod
    def get(cls, id=None)->'_Device_':
        """获取Device实例"""
        g = _G._G_
        log = g.Log()
        try:
            if g.isServer():
                # 服务端获取设备实例
                if id:
                    # 根据设备ID获取指定设备
                    deviceMgr = g.SDeviceMgr()
                    device = deviceMgr.get(id)
                    # if device is None:
                    #     log.e(f"服务端根据设备ID获取设备失败: id={id}, 设备不存在或未连接")
                    return device
                else:
                    # 获取默认设备（可能是第一个在线设备）
                    deviceMgr = g.SDeviceMgr()
                    devices = deviceMgr.getOnlineDevices()
                    if not devices:
                        log.e("服务端获取默认设备失败: 没有在线设备")
                        return None
                    device = devices[0]
                    log.d(f"服务端获取默认设备: device={device}")
                    return device
            else:
                # 客户端获取当前设备实例
                device = g.CDevice()
                if device is None:
                    log.e("客户端获取当前设备失败")
                # else:
                    # log.d(f"客户端成功获取设备实例: device={device}")
                return device
        except Exception as e:
            log.ex_(e, f"获取Device实例异常: id={id}")
            return None