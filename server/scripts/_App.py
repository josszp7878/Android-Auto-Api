from datetime import datetime
import threading
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
    _lastApp = None  # 当前应用实例（延迟初始化）

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
    def setCurName(cls, name: str):
        """设置当前检测应用名称"""
        if name != cls._curAppName:
            cls._curAppName = name
            # 如果是已知应用则更新实例
            if name in cls.apps():
                cls._lastApp = cls.apps()[name]
    
    _apps: Dict[str, "_App_"] = {}

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
    def last(cls) -> "_App_":
        """获取当前应用实例"""
        if cls._lastApp is None:
            cls._lastApp = cls.getTemplate(_G.TOP, True)
        return cls._lastApp
    
    @classmethod
    def cur(cls) -> "_App_":
        """获取当前应用实例"""
        return cls.getTemplate(cls._curAppName, False)
    
    @classmethod
    def detectApp(cls) -> Tuple['_App_', str]:
        """获取当前应用"""
        g = _G._G_
        log = g.Log()
        tools = g.Tools()
        try:
            detectedApp = (tools.curApp() if tools.isAndroid()
                          else cls._curAppName)
            cls._curAppName = detectedApp
            
            # 当检测到已知应用时更新实例
            if detectedApp in cls.apps():
                cls._lastApp = cls.apps()[detectedApp]
                
            return cls._lastApp, detectedApp
        except Exception as e:
            log.ex(e, "获取当前应用失败")
            return None, None
    
    @property
    def toPage(self) -> "_Page_":
        """获取当前页面"""
        return self._toPage

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
        if match:
            name = match.group('name')
            if name is None:
                name = cls.last().name
            return name, match.group('pageName')
        # 如果没找到应用名，使用当前应用    
        name = cls.last().name
        return name, str  # 返回当前应用和页面名称    

    @property
    def curPage(self) -> "_Page_":
        """获取当前页面"""
        return self._curPage

    def _setCurrentPage(self, page: "_Page_") -> bool:
        """设置当前页面"""
        g = _G._G_
        log = g.Log()
        try:
            if page is None or page == self._curPage:
                return False
            ret = page.begin()
            if ret is None:
                return False
            self._lastPage = self._curPage
            self._curPage = page
            log.i(f"> {page.name}")
            return True
        except Exception as e:
            log.ex(e, f"设置当前页面失败: {page.name}")
            return False

    # 检测toast
    # 先检查toast的key是否匹配，如果匹配，则执行action
    # 如果action以@开头，则认为是一个表达式，需要执行表达式,将执行结果赋值给action，在执行后续action逻辑
    # action中包含逗号，则认为是一个按钮和操作的组合，如果没有，则认为是一个按钮
    def detectToast(self):
        """检测toast"""
        g = _G._G_
        tools = g.Tools()
        log = g.Log()
        for key, action in self._toasts.items():
            if tools.check(key, self):
                if action.startswith('@'):
                    # 如果action以@开头，则认为是一个表达式，需要执行表达式
                    try:
                        action = tools.eval(self, action[1:], log)
                    except Exception as e:
                        log.ex(e, f"执行表达式失败: {action}")
                        continue
                # 如果action中包含逗号，则认为是一个按钮和操作的组合，如果没有，则认为是一个按钮
                click = action
                do = ''
                if ',' in action:
                    click, do = action.split(',')
                log.d(f"Toast匹配: {key}，点击: {click}，操作: {do}")
                self.curPage.click(click, do)
                break


    def detectPage(self, page: "_Page_", timeout=3):
        """匹配页面"""
        if not page:
            return False
        g = _G._G_
        tools = g.Tools()
        log = g.Log()
        if tools.isAndroid():
            time.sleep(timeout)
        tools.refreshScreenInfos()
        try:
            #先检测当前页面 self._toPage
            page = None
            if self._toPage:
                if self._toPage.match():
                    page = self._toPage
                    self._toPage = None
            if not page:
                # 检测当前应用中的alert类型页面
                pages = self.getPages()
                for p in pages:
                    if p.isAlert and p.match():
                        page = p
                        break
            if not page:
                if g.isAndroid() and not self.curPage.match():
                    log.e("检测到未配置的弹出界面")
            if page:
                self._setCurrentPage(page)
        except Exception as e:
            log.ex(e, f"检测页面 {page.name} 失败")

    def back(self)->bool:
        """返回上一页"""
        return self.goPage(self._lastPage)
       
    def home(self):
        """返回主页"""
        g = _G._G_
        tools = g.Tools()
        log = g.Log()
        try:
            if tools.isAndroid():
                tools.goHome()
            else:
                self.setCurName(_G.TOP)
            return True
        except Exception as e:
            log.ex(e, "返回主页失败")
            return False
        
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


    def getPage(self, name, create=False, includeCommon=False)->Optional["_Page_"]:
        """获取页面"""
        try:
            g = _G._G_
            log = g.Log()
            page = None
            if name in self._pages:
                page = self._pages[name]
            if includeCommon and self.name != _G.TOP:
                # 获取公共页面
                commonPage = _App_.Top().getPage(name, False, False)
                if not commonPage:
                    log.e(f"加载公共页面 {name} 失败")
                    return None
                # 直接返回公共页面，getInst会在需要时创建实例
                return commonPage
            if page or not create:
                return page                            
            if name.startswith('#'):
                # 解析引用页面格式: #引用页面名{参数}
                import re
                import json
                match = re.match(r'#([^{]+)(?:{(.+)})?', name)
                if match:
                    pageName = match.group(1)
                    params = match.group(2)
                    # 获取引用的页面
                    refPage = self.getPage(pageName, False, True)
                    if refPage:
                        # 如果有参数，解析参数
                        paramsDict = None
                        if params:
                            content = f'{{{params.strip()}}}'
                            content = content.replace("'", '"')
                            try:
                                paramsDict = json.loads(content)                                    
                            except Exception as e:
                                log.ex(e, f"解析引用页面参数失败: {content}")
                        # 创建页面实例并设置参数
                        page = refPage.getInst(paramsDict)
            else:
                # 创建新页面
                from _Page import _Page_
                page = _Page_(self.name, name)
            if page:
                self._pages[name] = page
            return page
        except Exception as e:
            log.ex(e, f"获取页面 {name} 失败")
            return None

    def getPages(self, pattern: str = None):
        """获取匹配指定模式的页面列表"""
        return self._pages.values()

    def delPage(self, pageName: str) -> bool:
        """删除页面"""
        if not pageName:
            return False
            
        # 解析页面名称，获取应用名和页面名
        pageName = pageName.strip().lower()
        if self.PathSplit in pageName:
            name, page_name = pageName.split(self.PathSplit, 1)
        else:
            # 使用当前应用
            name = self.curName()
            page_name = pageName
            
        # 在页面字典中查找匹配的页面
        if page_name in self._pages:
            # 找到匹配的页面，删除它
            page = self._pages.pop(page_name)
            
            # 如果不是临时页面，保存配置
            if not page.hasAttr(_G.TEMP):
                self.saveConfig()
            return True
        return False

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
    def isHome(cls) -> bool:
        """检查是否在主屏幕"""
        g = _G._G_
        tools = g.Tools()
        if g.android is None:
            return cls.curName() == _G.TOP
        return tools.isHome()
    
    @classmethod
    def goHome(cls)->bool:
        """返回主屏幕"""
        return cls.open(_G.TOP)    
    
    @classmethod
    def open(cls, name) -> "_App_":
        """跳转到指定应用"""
        try:
            g = _G._G_
            log = g.Log()
            app = cls.getTemplate(name)
            if not app:
                log.w(f"未知应用:{name}")
            else:
                name = app.name
            tools = g.Tools()
            if name == cls._curAppName:
                return app
            ok = tools.openApp(name)
            if not ok:
                return None
            cls.setCurName(name)
            if g.isAndroid():
                time.sleep(5)
            app, name = cls.detectApp()
            if app:
                cls.setCurName(name)
                log.i(f"=>{name}")
            return app
        except Exception as e:
            log.ex(e, f"跳转到应用 {name} 失败")
            return None

    def findPath(self, fromPage: "_Page_", toPage: "_Page_", visited=None, path: List["_Page_"]=None) -> List["_Page_"]:
        """在整个页面树中查找从fromPage到toPage的路径
        Args:
            fromPage: 起始页面
            toPage: 目标页面
            visited: 已访问页面集合(内部使用)
            path: 当前路径(内部使用)
        Returns:
            list: 从fromPage到toPage的路径，如果没找到则返回[]
        """
        # 初始化visited和path
        if visited is None:
            visited = set()
        if path is None:
            path = [fromPage]  # 第一次调用时，path只包含起始页面
            
        # 如果已经访问过当前页面，返回空路径避免循环
        if fromPage in visited:
            return []
            
        # 标记当前页面为已访问
        visited.add(fromPage)
        
        # 如果找到目标页面，直接返回当前路径，不管目标页面是否有exit配置
        if fromPage.name == toPage.name:
            return path
            
        # 如果当前页面没有exit配置，返回空路径
        if not fromPage.exit:
            return []
            
        # 遍历所有exit页面
        for pageName in fromPage.exit.keys():
            page = self.getPage(pageName)
            if page and page not in visited:
                # 递归搜索下一个页面
                resultPath = self.findPath(page, toPage, visited, path + [page])
                if resultPath:
                    return resultPath
                    
        return []

    def _findPath(self, pageNames, name, visited=None) -> Optional["_Page_"]:
        """在指定页面列表中查找指定名称的页面"""
        g = _G._G_
        log = g.Log()
        if len(pageNames) == 0:
            return None
        for pageName in pageNames:  
            page = self.getPage(pageName)
            if page is None:
                log.d(f"{name}的子页面: {pageName}不存在")
                continue
            result = self.findPath(page, self.getPage(name))
            if result:
                return result[-1]  # 返回路径的最后一个节点名称
        return None
    
    def goPage(self, page: '_Page_', direct=False) -> bool:
        """设置要跳转到的目标页面
        设置_targetPage属性，由应用更新循环中的_update方法处理实际跳转
        
        Args:
            page: 目标页面
        Returns:
            bool: 是否成功设置
        """
        try:
            if not page:
                return False
            g = _G._G_
            log = g.Log()
            # 如果已经在目标页面，直接返回成功
            if self._curPage and self._curPage.name == page.name:
                return True
            # 如果直接跳转，直接设置目标页面
            if self._curPage and direct:
                self._toPage = page
                return True
            # 计算路径并缓存
            if self._curPage:
                path = self.findPath(self._curPage, page)
                if path:
                    self._path = path
                    # log.i(f"设置页面跳转目标: {page.name}, 路径: {path}")
                else:
                    log.e(f"找不到从 {self._curPage.name} 到 {page.name} 的路径")
                    return False
            return True
        except Exception as e:
            log.ex(e, "设置页面跳转目标失败")
            return False
        

    @classmethod
    def go(cls, target: str) -> '_Page_':
        """跳转到指定应用的指定页面
        Args:
            target: 目标页面路径
        Returns:
            _Page_: 目标页面
        """
        g = _G._G_
        log = g.Log()
        try:
            if not target:
                log.e("目标页面路径不能为空")
                return None
            name, pageName = cls.parseName(target)
            ret = cls.open(name)
            if ret:
                app = cls.last()
                if app:
                    page = app.getPage(pageName)
                    if app.goPage(page, False):
                        return page
            return None
        except Exception as e:
            log.ex(e, f"跳转到应用 {name} 的页面 {pageName} 失败")
            return None
        
    @classmethod
    def closeApp(cls, name=None) -> bool:
        """关闭应用"""
        g = _G._G_
        log = g.Log()
        try:
            if name is None:
                name = cls.last().name  # 通过cur方法获取实例名称
            
            app = cls.getTemplate(name)
            if not app:
                return False
            # 保存计数器数据
            # app._saveData()
            app._stop()
            
            # 重置到主屏幕
            if name == cls.last().name:
                cls._lastApp = cls.Top()  # 修改属性名称
                cls._curAppName = _G.TOP
            return True
        except Exception as e:
            log.ex(e, f"关闭应用 {name} 失败")
            return False
    
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
        if oldCls:
            cls._curAppName = oldCls._curAppName
            cls._lastApp = oldCls._curApp  # 修改属性名称
        else:
            cls._lastApp = cls.getTemplate(_G.TOP, True)        
        cls.loadConfig()

    # 处理页面跳转逻辑
    def _updateGoPath(self, log: "_Log_"):
        """处理页面跳转逻辑"""
        try:
            if not self._path:
                return True
            curPage = self.curPage
            # 检查当前页面是否在路径中
            if curPage not in self._path:
                log.w(f"当前页面 {curPage.name} 不在预定路径中")
                self._clearPath()
                return
            # 找到当前页面在路径中的位置
            index = self._path.index(curPage) + 1
            # 已经是路径中的最后一个页面，说明已到达目标
            if index >= len(self._path):
                self._clearPath()
                return
            self._ToPage(self._path[index])
        except Exception as e:
            log.ex(e, "处理页面跳转逻辑失败")
    
    def _ToPage(self, page: "_Page_")->bool:
        """跳转到路径中的下一个页面"""
        if not page:
            return False
        g = _G._G_
        tools = g.Tools()
        self.curPage.doExit(page.name)
        if not tools.isAndroid():
            self._toPage = page
        return True
    
    def _clearPath(self):
        """清空路径目标"""
        self._path = None

    def _doUpdate(self):
        """应用级别的更新循环"""
        try:
            g = _G._G_
            log = g.Log()  # 需要再这里获取，这样就能支持LOG的动态更新
            # 检测toast
            self.detectToast()
            # 检测当前页面
            self.detectPage(self.curPage)
            # 处理页面跳转逻辑
            self._updateGoPath(log)
            # 更新当前页面
            if self.curPage:
                self.curPage.update()
            self.userEvents = []
            # 更新当前任务
            curTask = g.CDevice().curTask()
            if curTask:
                curTask.update(g)
            
        except Exception as e:
            log.ex(e, f"应用更新失败：{self.name}")
        

    @classmethod
    def _update(cls):
        """全局应用更新循环
        """
        interval = 0.3
        tools = _G._G_.Tools()
        if tools.isAndroid():
            interval = 1
        while True:
            time.sleep(interval)
            cls.detectApp()
            app = cls.cur()
            if app:
                # 只更新当前已知应用
                app._doUpdate()

    @classmethod
    def update(cls):
        """全局应用更新循环线程"""
        thread = threading.Thread(target=cls._update)
        thread.start()

    def sendUserEvent(self, eventName: str) -> bool:
        """添加用户事件到事件列表
        Args:
            eventName: 用户事件名称
        Returns:
            bool: 是否添加成功
        """
        log = _G._G_.Log()
        try:
            if eventName not in self.userEvents:
                self.userEvents.append(eventName)
                log.d(f"添加用户事件: {eventName}")
            return True
        except Exception as e:
            log.ex(e, f"添加用户事件失败: {eventName}")
            return False  

    def LoadScore(self, date: datetime = None) -> List[dict]:
        # 导航到收益页面
        g = _G._G_
        App = g.App()
        App.go('收益')
        # 等待页面加载
        time.sleep(1)
        # 获取页面内容
        test_file = os.path.join(g.rootDir(), "data", "result.json")
        content = None
        if os.path.exists(test_file):
            with open(test_file, "r", encoding="utf-8") as f:
                content = f.read()
        from CScore import CScore_
        return CScore_.loadScore(content, date)
    
    # RPC方法示例
    @RPC()
    def getScores(self, date: datetime = None) -> dict:
        """获取收益分数 - RPC远程调用方法"""
        g = _G._G_
        log = g.Log()
        try:
            if g.isServer():
                from SDeviceMgr import deviceMgr
                deviceID = self.deviceId
                if deviceID is None:
                    deviceID = deviceMgr.curDevice.id
                result = g.RPC(deviceID, '_App_', 'getScores', {'id':self.id, 'args': [date]})
                self._onGetScores(result, date)
                return {
                    'result': result
                }
            else:
                scores = self.LoadScore(date)
                return {
                    'result': scores
                }
        except Exception as e:
            log.ex_(e, "获取收益分数失败")
            return {
                'error': f"获取收益分数失败: {str(e)}"
            }
        
    def _onGetScores(self, result: dict, date: datetime = None):
        """处理获取收益结果"""
        if not result:
            return
        log = _G._G_.Log()
        # 处理收益数据
        changedTasks = []
        for item in result:
            taskName = item.get("name", "未知任务")
            taskScore = item.get("amount", 0)  # 客户端返回的是amount字段
            if not taskName or taskScore <= 0:
                continue
            from STask import STask_
            # 获取或创建任务
            task = STask_.get(deviceId=self.id, name=taskName, date=date, create=True)
            if not task:
                log.e(f"创建任务失败: {taskName}")
                continue
            task.score = taskScore
            if task.commit():
                changedTasks.append(task)
    
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