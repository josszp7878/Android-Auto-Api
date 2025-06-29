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

    def __init__(self, data: dict):
        g = _G._G_
        if g.isServer():
            from SModels import AppModel_
            super().__init__(data, AppModel_)
        else:
            super().__init__(data, None)
        self._curPage: Optional["_Page_"] = None
        self._lastPage: Optional["_Page_"] = None
        self._toPage: Optional["_Page_"] = None
        self.rootPage: Optional["_Page_"] = None
        self._pages: Dict[str, "_Page_"] = {}  # 应用级的页面列表
        self._path: Optional[List["_Page_"]] = None  # 当前缓存的路径 [path]
        self.userEvents: List[str] = []  # 用户事件列表
        self._counters = {}  # 计数器字典，用于统计页面访问次数和事件触发次数
        self._countersModified = False  # 计数器是否被修改
        self._toasts = {}  # toasts配置字典，用于存储toast匹配规则和操作

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
    

    PathSplit = '-'
    @classmethod
    def parseName(cls, str: str) -> Tuple[str, str]:
        """解析应用和页面名称
        Args:
                str: 应用和名称，格式为 "应用名-名称"
        Returns:
            Tuple[str, str]: (应用名, 名称)
        """
        if not str or not str.strip():
            return None, None
        import re
        pattern = fr'(?P<name>\S+)?\s*{cls.PathSplit}\s*(?P<pageName>\S+)?'
        match = re.match(pattern, str)
        g = _G._G_
        device = g.CDevice()
        if match:
            name = match.group('name')
            if name is None:
                name = device.currentApp.name
            return name, match.group('pageName')
        # 如果没找到应用名，使用当前应用    
        name = device.currentApp.name
        return name, str  # 返回当前应用和页面名称    



 
        
    @classmethod
    def configDir(cls)->str:
        """获取配置文件目录"""
        return os.path.join(_G.g.rootDir(), 'config', 'pages')
    
    @classmethod
    def loadConfig(cls, fileName=None)->bool:
        """加载配置文件
        Args:
            fileName: 配置文件名或路径，如果为None则加载所有配置文件            
        Returns:
            Dict[str, List]: 返回处理的应用及其页面列表，格式 {appName: [page1, page2, ...]}
        """
        g = _G._G_
        log = g.Log()
        try:
            import glob
            if fileName:
                configFiles = [fileName]
            else:
                configFiles = glob.glob(os.path.join(cls.configDir(), '*.json'))
            cls._apps = None
            for configFile in configFiles:
                if not os.path.exists(configFile):
                    continue
                cls.loadConfigFile(configFile)
            return True
        except Exception as e:
            log.ex(e, "加载配置文件失败")
            return False
    
    @classmethod
    def loadConfigFile(cls, configPath)->bool:
        """加载单个配置文件
        Args:
            configPath: 配置文件路径
        """
        g = _G._G_
        log = g.Log()
        try:
            with open(configPath, 'r', encoding='utf-8') as f:
                config = json.load(f)
            name = os.path.basename(configPath)[:-5]
            #根据root的name，获取应用
            rootConfig = config.get(_G.ROOT)
            if not rootConfig:
                log.e(f"配置文件 {configPath} 没配置{_G.ROOT}节点")
                return False
            name = rootConfig.get('name', name)  
            app = cls.getTemplate(name, True)
            rootPage = app.getPage(_G.ROOT, True)   
            rootPage.config = rootConfig
            app._curPage = rootPage
            app.rootPage = rootPage
            app._loadConfig(config)
            # app._loadData()
            return True
        except Exception as e:
            log.ex(e, f"加载配置文件失败: {configPath}")
            return False

    def _loadConfig(self, config: dict) -> Dict[str, "_Page_"]:
        """加载应用配置
        Args:
            config: 应用配置字典
        Returns:
            Dict[str, "_Page_"]: 返回加载的页面列表
        """
        g = _G._G_
        log = g.Log()
        try:
            # 加载根页面配置
            root = config.get(_G.ROOT)
            if not root:
                log.e(f"应用 {self.name} 配置缺少{_G.ROOT}节点")
                return {}
            # 更新应用信息
            self.ratio = root.get('ratio', 10000)
            self.description = root.get('description', '')
            self._toasts = root.get('toasts', {})  # 加载toasts配置
            
            # 加载页面配置
            pages = root.get('pages', {})
            for pageName, pageConfig in pages.items():
                # 创建或获取页面
                page = self.getPage(pageName, True)
                page.config = pageConfig
                if not page:
                    log.e(f"创建页面 {pageName} 失败")
                    continue
                # 添加到页面列表
                self._pages[pageName] = page
                
            # log.i(f"应用 {self.name} 配置加载完成，共 {len(self._pages)} 个页面")
            return self._pages
        except Exception as e:
            log.ex(e, f"加载应用 {self.name} 配置失败")
            return {}

    def saveConfig(self) -> str:
        """保存配置
        Returns:
            str: 配置文件路径
        """
        g = _G._G_
        log = g.Log()
        try:
            # 获取当前应用的所有页面
            pages = self.getPages()
            # 过滤出非临时页面
            pages = [p for p in pages if not p.hasAttr(_G.TEMP)]
            #remove root page
            pages.remove(self.rootPage)
            # 将页面转换为字典格式
            pageConfigs = {}
            for page in pages:
                pageConfigs[page.name] = page.config
            rootConfig = self.rootPage.config
            rootConfig['pages'] = pageConfigs
            output = {
                _G.ROOT: rootConfig
            }
            # 写入配置文件
            path = self.configDir()
            if not os.path.exists(path):
                os.makedirs(path)
            path = os.path.join(path, f'{self.name}.json')
            with open(path, 'w', encoding='utf-8') as f:
                    json.dump(output, f, ensure_ascii=False, indent=2)
            return path
        except Exception as e:
            log.ex(e, f"保存配置文件失败")
            return None

    @classmethod
    def getAppNames(cls) -> list:
        """获取所有应用名称列表
        Returns:
            list: 应用名称列表
        """
        return list(cls.apps().keys())

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

    @classmethod
    def getAllApps(cls) -> List[str]:
        """获取所有应用名称"""
        return cls.getAppNames()

    @classmethod
    def onLoad(cls, oldCls=None):
        """克隆"""
        cls.loadConfig()

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