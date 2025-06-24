from datetime import datetime
from typing import Dict, List, Optional, Any
import json
from _App import _App_
from RPC import RPC
import _G
from SModels import AppModel_

class _Device_:
    """设备App管理基类：提供查询、创建和跟踪当前app的功能"""
    
    def __init__(self):
        self._apps: Dict[str, _App_] = {}  # 设备的App列表
        self._currentApp: Optional[_App_] = None  # 当前跟踪的App
        
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
    
       
    def getApp(self, appName: str, create: bool = True) -> Optional[_App_]:
        """获取指定的App
        Args:
            appName: App名称
            lazyCreate: 服务端支持从模板创建，客户端不支持创建
        Returns:
            Optional[_App_]: App实例或None
        """
        g = _G._G_
        log = g.Log()
        try:
            if not appName:
                return None
            # 首先检查缓存中是否存在
            if appName in self._apps:
                return self._apps[appName]            
            if not create:
                return None
            app = self.createApp({'appName': appName})
            if app:
                self._apps[appName] = app   # 添加到缓存
                return app
            return None
        except Exception as e:
            log.ex_(e, f"获取App失败: {appName}")
            return None

    def createApp(self, data: dict) -> '_App_':
        """创建App"""
        return None
    
    # @RPC()
    def getAvailableApps(self) -> dict:
        """获取可用的App列表（从数据库获取）"""
        try:
            g = _G._G_
            
            # 获取设备ID
            deviceId = getattr(self, 'id', 'default_device')
            
            # 从数据库获取所有App记录
            app_records = AppModel_.all(deviceId)
            availableApps = []
            
            for record in app_records:
                appName = record['appName']
                # 检查是否已加载到内存
                isLoaded = appName in self._apps
                
                availableApps.append({
                    'id': record['id'],
                    'appName': appName,
                    'totalScore': record['totalScore'],
                    'income': record['income'],
                    'status': record['status'],
                    'isLoaded': isLoaded,
                    'isCurrent': (self._currentApp and self._currentApp.name == appName),
                    'lastUpdate': record['lastUpdate']
                })
            
            return {
                'success': True,
                'apps': availableApps,
                'totalCount': len(availableApps),
                'loadedCount': len(self._apps),
                'currentApp': self._currentApp.name if self._currentApp else None
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
       
    @RPC()
    def getAppList(self) -> dict:
        """获取设备的App列表"""
        try:
            g = _G._G_
            log = g.Log()
            appList = []
            for appName, app in self._apps.items():
                appInfo = {
                    'name': appName,
                    'description': app.description if hasattr(app, 'description') else '',
                    'isCurrent': (app == self._currentApp),
                    'totalScore': getattr(app, 'totalScore', 0.0),
                    'income': getattr(app, 'income', 0.0),
                    'status': getattr(app, 'status', 'idle'),
                    'lastUpdate': getattr(app, 'lastUpdate', None)
                }
                appList.append(appInfo)
            
            return {
                'success': True,
                'apps': appList,
                'currentApp': self._currentApp.name if self._currentApp else None,
                'totalCount': len(appList)
            }
        except Exception as e:
            log.ex_(e, "获取App列表失败")
            return {
                'success': False,
                'error': str(e)
            }
   
    
    def setCurrentApp(self, appName: str) -> dict:
        """设置当前跟踪的App"""
        try:
            g = _G._G_
            log = g.Log()
            
            if not appName:
                self._currentApp = None
                return {
                    'success': True,
                    'currentApp': None,
                    'message': '已清除当前App'
                }
            # 获取App（支持Lazy创建）
            app = self.getApp(appName, create=True)
            if not app:
                return {
                    'success': False,
                    'error': f'App "{appName}" 不存在或创建失败'
                }
            
            # 设置当前App
            oldApp = self._currentApp
            self._currentApp = app
            
            log.i(f'设置当前App: {oldApp.name if oldApp else "None"} -> {appName}')
            
            return {
                'success': True,
                'oldApp': oldApp.name if oldApp else None,
                'currentApp': appName,
                'message': f'当前App已设置为: {appName}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    
    
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
                    for name, app in self._apps.items()},
            'currentApp': self._currentApp.name if self._currentApp else None
        }
    
    # def fromDict(self, data: dict):
    #     """从字典格式加载数据"""
    #     try:
    #         from _App import _App_
            
    #         # 清空现有数据
    #         self._apps.clear()
    #         self._currentApp = None
            
    #         # 加载App列表
    #         apps_data = data.get('apps', {})
    #         for appName, appInfo in apps_data.items():
    #             app = _App_(appName, appInfo)
    #             self._apps[appName] = app
            
    #         # 加载当前App
    #         currentAppName = data.get('currentApp')
    #         if currentAppName and currentAppName in self._apps:
    #             self._currentApp = self._apps[currentAppName]
            
    #     except Exception as e:
    #         _G._G_.Log().ex(e, "从字典加载App数据失败") 


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
                    if device is None:
                        log.e(f"服务端根据设备ID获取设备失败: id={id}, 设备不存在或未连接")
                    else:
                        log.d(f"服务端成功获取设备实例: id={id}, device={device}")
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
                else:
                    log.d(f"客户端成功获取设备实例: device={device}")
                return device
        except Exception as e:
            log.ex_(e, f"获取Device实例异常: id={id}")
            return None