"""
全局状态管理模块 (兼容服务端和客户端)
"""
import threading
import os
from typing import TYPE_CHECKING, List, Callable, Optional, Union

if TYPE_CHECKING:
    from CFileServer import CFileServer_
    from CClient import CClient_
    from _Log import _Log_
    from _CmdMgr import _CmdMgr_
    from CTools import CTools_
    from _Tools import _Tools_
    from _App import _App_  
    from _Page import _Page_
    from CDevice import CDevice_ 
    from CChecker import CChecker_
    from CApp import CApp_  
    from SDeviceMgr import SDeviceMgr_
    from SCommandHistory import SCommandHistory_
TOP = "top"
UNKNOWN = 'unknown'


class _G_:
    # 使用线程安全的存储
    _lock = threading.Lock()
    _dir = None
    _store = {}
    _isServer = True    
    log = None
    _scriptNamesCache = None  # 添加脚本名称缓存

    @classmethod
    def init(cls):
        import _Log
        cls.log = _Log._Log_()     

    @classmethod
    def isServer(cls):
        """是否是服务器端"""    
        return cls._isServer
    
    @classmethod
    def load(cls, isServer:bool = None):
        """设置是否是服务器端"""
        # print(f"设置是否是服务器端YYYYYYYYf: {isServer}")
        if isServer is not None:
            cls._isServer = isServer
        from _App import _App_
        _App_.loadConfig()
    
    @classmethod
    def Clone(cls, oldCls):
        """克隆"""
        cls._isServer = oldCls._isServer
        cls._dir = oldCls._dir
        cls._store = oldCls._store

    @classmethod
    def rootDir(cls):
        """获取根目录"""
        if cls._dir:
            return cls._dir
        dir = None
        if not cls._isServer:
            import CTools
            android = CTools.CTools_.android
            if android:
                # Android环境下使用应用私有目录
                dir = android.getFilesDir(None, False)
        if not dir:
            # 开发环境使用当前目录
            dir = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))
        cls._dir = dir
        return cls._dir

        


    @classmethod
    def scriptDir(cls):
        dir = os.path.join(cls.rootDir(), 'scripts')
        if not os.path.exists(dir):
            os.makedirs(dir)
        return dir

    @classmethod
    def configDir(cls):
        dir = os.path.join(cls.rootDir(), 'config')
        if not os.path.exists(dir):
            os.makedirs(dir)
        return dir

    @classmethod
    def save(cls, key, value):
        """保存状态"""
        with cls._lock:
            cls._store[key] = value

    @classmethod
    def restore(cls, key, default=None):
        """恢复并删除状态"""
        with cls._lock:
            return cls._store.pop(key, default)

    @classmethod
    def get(cls, key, default=None):
        """获取状态"""
        return cls._store.get(key, default)

    @classmethod
    def clear(cls):
        """清空状态"""
        with cls._lock:
            cls._store.clear()

    @classmethod
    def getClassName(cls, module_name):
        """获取类名"""
        return f'{module_name}_'
    
    @classmethod
    def CClient(cls) -> 'CClient_':
        """获取客户端"""
        return cls.getClass('CClient')

    @classmethod
    def Log(cls) -> '_Log_':
        return cls.getClass('_Log')
    
    @classmethod
    def Checker(cls) -> 'CChecker_':
        return cls.getClass('CChecker')
        
    @classmethod
    def CTools(cls) -> 'CTools_':
        return cls.getClass('CTools')    
    @classmethod
    def STools(cls) -> '_Tools_':
        return cls.getClass('_Tools')   
    @classmethod
    def Tools(cls) -> '_Tools_':
        if cls.isServer():
            return cls.getClass('_Tools')    
        else:
            return cls.getClass('CTools')
    @classmethod
    def App(cls) -> '_App_':
        return cls.getClass('_App')
    
    @classmethod
    def CApp(cls) -> 'CApp_':
        return cls.getClass('CApp')
    
    @classmethod
    def Page(cls) -> '_Page_':
        return cls.getClass('_Page')
    
    @classmethod
    def CFileServer(cls) -> 'CFileServer_':
        return cls.getClass('CFileServer')
    
    @classmethod
    def CmdMgr(cls) -> '_CmdMgr_':
        return cls.getClass('_CmdMgr')
    
    @classmethod
    def CDevice(cls) -> 'CDevice_':
        return cls.getClass('CDevice')
    
    @classmethod
    def SDeviceMgr(cls) -> 'SDeviceMgr_':
        return cls.getClass('SDeviceMgr')

    @classmethod
    def SCommandHistory(cls) -> 'SCommandHistory_':
        return cls.getClass('SCommandHistory')

    @classmethod
    def CallMethod(cls, module, methodName, *args, **kwargs):
        try:
            if module is None:
                return
            klass = cls.getClass(module.__name__)
            if klass:
                method = getattr(klass, methodName, None)
                if method and callable(method):
                    return method(*args, **kwargs)
        except Exception as e:
            cls.log.ex(e, f"获取类方法失败: {methodName}")

    @classmethod
    def getClass(cls, moduleName):
        """通用类获取方法
        Args:
            module_name: 模块名（如'_Log'）
            class_name: 类名（如'Log_'）
            store_key: 存储键（默认使用类名）
        """
        moduleName = cls.getScriptName(moduleName)
        if not moduleName:
            return None
        # 从完整路径中提取文件名（不含扩展名）
        className = cls.getClassName(moduleName)
        if className not in cls._store:
            try:
                module = __import__(moduleName, fromlist=[className])
                klass = None
                try:
                    klass = getattr(module, className)
                except Exception as e:
                    cls.log.w(e, f"获取类失败: {className}")
                    return None
                cls._store[className] = klass
            except Exception as e:
                cls.log.ex(e, f"导入{moduleName}失败")
                return None
        return cls._store[className]

    @classmethod
    def getScriptName(cls, fileName: str):
        """获取脚本名"""
        scripts = cls.getScriptNames()
        if scripts:
            return cls._findFileInList(fileName, scripts)
        return None

    @classmethod
    def clearScriptNamesCache(cls):
        """清除脚本名称缓存"""
        cls._scriptNamesCache = None
        # cls.log.d("脚本名称缓存已清除")

    @classmethod
    def getScriptNames(cls):
        """扫描指定目录下的Python模块"""
        # 如果有缓存，直接返回缓存
        if cls._scriptNamesCache is not None:
            return cls._scriptNamesCache
        
        files = cls.getAllFiles('scripts')
        ext = '.py'
        fileNames: List[str] = []
        try:
            prefix = 'S' if cls.isServer() else 'C'
            for file in files:
                if ext and not file.endswith(ext):
                    continue
                firstChar = file[0]
                if firstChar != prefix and firstChar != '_':
                    continue
                module = file[:-3]  # 去掉.py后缀
                fileNames.append(module)
        except Exception as e:
            # 避免使用日志，直接打印错误
            print(f"扫描脚本目录失败: {e}")
        
        # 缓存结果
        cls._scriptNamesCache = fileNames
        
        return fileNames
    

    @classmethod
    def findFileName(cls, fileName: str, subDir: Optional[str] = None) -> Optional[str]:
        """在指定目录下查找文件
        
        Args:
            fileName: 要查找的文件名（不含扩展名）
            subDir: 子目录名，如果为None则在rootDir下查找
            
        Returns:
            找到的文件名（不含扩展名），未找到则返回None
        """
        files = cls.getAllFiles(subDir)
        return cls._findFileInList(fileName, files)
    
    @classmethod
    def _findFileInList(cls, fileName: str, files: List[str]) -> Optional[str]:
        """在文件列表中查找匹配的文件名，忽略大小写，支持带扩展名的文件名
        Args:
            fileName: 要查找的文件名
            files: 文件列表
            
        Returns:
            找到的文件名，未找到则返回None
        """
        fileNameLower = fileName.lower()
        for file in files:
            # 忽略大小写比较文件名
            fileLower = file.lower()
            if fileNameLower in fileLower:
                return file
        return None
    
    
    @classmethod
    def getAllFiles(cls, subDir: Optional[str] = None) -> List[str]:
        """获取指定目录下所有文件
        
        Args:
            subDir: 子目录名，如果为None则获取rootDir下所有文件
            
        Returns:
            文件名列表（不含扩展名）
        """
        # 确定搜索根目录
        if subDir:
            rootDir = os.path.join(cls.rootDir(), subDir)
        else:
            rootDir = cls.rootDir()
            
        # 不调用日志函数，避免循环依赖
        # cls.log.d(f"获取目录 {rootDir} 下的所有文件")
        
        # 存储所有文件
        all_files = []        
        # 递归搜索目录
        for root, _, files in os.walk(rootDir):
            for file in files:
                # 计算相对路径
                relPath = os.path.relpath(os.path.join(root, file), rootDir)
                all_files.append(relPath)
        
        return all_files


_G_.init()
g = _G_
