from datetime import datetime
import time
import os
import json
import _G

from typing import Optional, List, Tuple, TYPE_CHECKING, Dict
from RPC import RPC
from SModelBase import SModelBase_
if TYPE_CHECKING:
    from _Page import _Page_
    from _Log import _Log_

class _App_(SModelBase_):
    """应用管理类：整合配置与实例"""
    _curAppName = _G.TOP  # 当前检测到的应用名称
    _apps: Dict[str, "_App_"] = {}
    _appNames: List[str] = None  # 缓存的应用名称列表
    
    def __init__(self, data: dict):
        g = _G._G_
        if g.isServer():
            from SModels import AppModel_
            super().__init__(data, AppModel_)
        else:
            super().__init__(data, None)

    def __getattr__(self, name):
        """重写 __getattr__ 方法，使 self.num 可以访问 self.data['num']"""
        # 防止无限递归：如果访问的是_data本身，则抛出AttributeError
        if name == 'data':
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        
        # 确保_data存在，如果不存在则返回None
        if not hasattr(self, 'data') or self.data is None:
            return None
            
        # 解析 name_type,先找最后一个'_'
        pos = name.rfind('_') + 1
        key = name
        valueType = 'str'
        if pos > 1:
            key = name[:pos-1]
            valueType = name[pos]
        else:
            valueType = 'str'
        data = self.data
        key = f'_{key}'
        if key in data:
            val = data[key]
            if valueType == 'n':
                return int(val)
            elif valueType == 'f':
                return float(val)
            elif valueType == 'b':
                return bool(val)
            else:
                return val
        return None

    @property
    def deviceId(self):
        """获取设备ID"""
        return int(self.getDBProp('deviceId', 0))

    @classmethod
    def curName(cls):
        """获取当前应用名称"""
        return cls._curAppName

    @classmethod
    def apps(cls) -> Dict[str, "_App_"]:
        """获取所有应用"""
        if not cls._apps:
            cls._apps = {}
        return cls._apps

    @classmethod
    def Top(cls):
        """获取主屏幕/桌面应用"""
        return cls.getTemplate(_G.TOP, True)
    
    @classmethod
    def cur(cls) -> "_App_":
        """获取当前应用实例"""
        return cls.getTemplate(cls._curAppName, False)

    @classmethod
    def getAppNames(cls) -> list:
        """获取所有应用名称列表，从Apps.json文件加载并缓存
        Returns:
            list: 应用名称列表
        """
        if cls._appNames is None:
            cls._loadAppNames()
        return cls._appNames or []
    
    @classmethod
    def _loadAppNames(cls):
        """从Apps.json文件加载应用名称"""
        g = _G._G_
        try:
            appsJsonPath = os.path.join(g.configDir(), 'Apps.json')
            if os.path.exists(appsJsonPath):
                with open(appsJsonPath, 'r', encoding='utf-8') as f:
                    cls._appNames = json.load(f)
                g.Log().i(f"从Apps.json加载了{len(cls._appNames)}个应用名称")
            else:
                cls._appNames = []
                g.Log().w("Apps.json文件不存在，使用空应用列表")
        except Exception as e:
            cls._appNames = []
            g.Log().ex(e, "加载Apps.json失败")

    @classmethod
    def exist(cls, name: str) -> bool:
        """检查应用是否存在
        Args:
            name: 应用名称
        Returns:
            bool: 是否存在
        """
        return name in cls.apps().keys()
    
    @classmethod
    def getByID(cls, id: int) -> "_App_":
        """根据ID获取应用实例"""
        g = _G._G_
        try:
            if g.isServer():
                # 服务端：在所有设备中查找
                deviceMgr = g.SDeviceMgr()
                devices = deviceMgr.devices
                for device in devices:
                    app = device.getAppByID(id)
                    if app:
                        return app
            else:
                # 客户端：在当前设备中查找
                device = g.CDevice()
                if device:
                    return device.getAppByID(id)
        except Exception as e:
            g.Log().ex(e, f"根据ID获取应用失败: {id}")
        return None
    
    @classmethod
    def get(cls, key, create=False) -> "_App_":
        """获取应用实例"""
        # 将 key 转换为设备名.应用名称
        if not key:
            return None
        # 如果key是数字，或者可以转换为数字，则认为是id
        if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
            app_id = int(key) if isinstance(key, str) else key
            return cls.getByID(app_id)
        if '.' in key:
            # 安全地分割：只在第一个.处分割，支持应用名中包含.的情况
            parts = key.split('.', 1)  # 限制最多分割成2部分
            if len(parts) == 2:
                deviceName, name = parts
            else:
                deviceName = None
                name = key
        else:
            deviceName = None
            name = key
        from _Device import _Device_
        device = _Device_.get(deviceName)
        if device:
            return device.getApp(name, create)
        return None
        
        
    @classmethod
    def getTemplate(cls, name, create=False) -> "_App_":
        """获取应用配置模板
        Args:
            name: 应用名称
            create: 如果不存在是否创建
        Returns:
            _App_: 应用实例
        """
        if name is None:
            return None
        apps = cls.apps()
        app = apps.get(name)
        if not app and create:
            app = cls({'name': name})
            apps[name] = app
        return app
   
    # RPC方法示例
    @RPC()
    def getScores(self, date: datetime = None) -> dict:
        """获取收益分数 - 服务端版本的RPC远程调用方法"""
        return None
        
    
    @RPC()
    def getCurrentPageInfo(self) -> dict:
        """获取当前页面信息 - RPC远程调用方法"""
        try:
            return {
                'result': {
                    'currentPage': self.curPage.name if self.curPage else None,
                    'appName': self.name,
                    'timestamp': datetime.now().isoformat()
                }
            }
        except Exception as e:
            return {
                'error': f"获取当前页面信息失败: {str(e)}"
            }
    
    @RPC()
    @classmethod
    def getAppList(cls) -> dict:
        """获取所有应用列表 - RPC远程调用方法"""
        try:
            return {
                'result': {
                    'apps': cls.getAppNames(),
                    'timestamp': datetime.now().isoformat()
                }
            }
        except Exception as e:
            return {
                'error': f"获取应用列表失败: {str(e)}"
            }