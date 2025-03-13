"""
全局状态管理模块 (兼容服务端和客户端)
"""
import threading
import os
from typing import TYPE_CHECKING, List, Callable

if TYPE_CHECKING:
    from CFileServer import CFileServer_
    from CClient import CClient_
    from _Log import _Log_
    from _CmdMgr import _CmdMgr_
    from CTools import CTools_
    from CPageMgr import CPageMgr_

g = {}

class _G_:
    # 使用线程安全的存储
    _lock = threading.Lock()
    _dir = None
    _store = {}
    _isServer = None    
    @classmethod
    def IsServer(cls):
        """是否是服务器端"""    
        return cls._isServer
    
    @classmethod
    def setIsServer(cls, isServer):
        """设置是否是服务器端"""
        cls._isServer = isServer
    
    @classmethod
    def Clone(cls, oldCls):
        """克隆"""
        cls._isServer = oldCls._isServer
        cls._dir = oldCls._dir
        cls._store = oldCls._store

    @classmethod
    def rootDir(cls):
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
    def CTools(cls) -> 'CTools_':
        return cls.getClass('CTools')

    @classmethod
    def PageMgr(cls) -> 'CPageMgr_':
        return cls.getClass('CPageMgr')
    
    @classmethod
    def CFileServer(cls) -> 'CFileServer_':
        return cls.getClass('CFileServer')
    
    @classmethod
    def CmdMgr(cls) -> '_CmdMgr_':
        return cls.getClass('_CmdMgr')


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
            cls.Log().ex(e, f"获取类方法失败: {methodName}")

    @classmethod
    def getClass(cls, moduleName):
        """通用类获取方法
        Args:
            module_name: 模块名（如'_Log'）
            class_name: 类名（如'Log_'）
            store_key: 存储键（默认使用类名）
        """
        #一定不要使用cls.Log()，否则会陷入死循环
        className = cls.getClassName(moduleName)
        if className not in cls._store:
            import _Log
            log = _Log._Log_
            try:
                module = __import__(moduleName, fromlist=[className])
                klass = None
                try:
                    klass = getattr(module, className)
                except Exception as e:
                    log.w(e, f"获取类失败: {className}")
                    return None
                cls._store[className] = klass
            except Exception as e:
                log.ex(e, f"导入{moduleName}失败")
                return None
        return cls._store[className]


    @classmethod
    def getFileNames(cls, dir: str, ext: str = '.py', func: Callable[[str], bool] = None):
        """扫描指定目录下的Python模块
        
        根据当前环境(服务器/客户端)扫描对应前缀的Python文件，
        并将符合条件的模块名添加到modules列表中
        
        Args:
            dir: 要扫描的目录路径
            modules: 用于存储找到的模块名的列表
            func: 可选的过滤函数，接受文件名并返回布尔值
        """
        fileNames: List[str] = []
        log = cls.Log()
        dir = f'{cls.rootDir()}/{dir}'
        try:
            prefix = 'S' if cls.IsServer() else 'C'
            for file in os.listdir(dir):
                if ext and not file.endswith(ext):
                    continue
                firstChar = file[0]
                if firstChar != prefix and firstChar != '_':
                    continue
                if func is None or func(file):
                    module = file[:-3]  # 去掉.py后缀
                    fileNames.append(module)
        except Exception as e:
            log.ex(e, "扫描脚本目录失败")
        return fileNames

    @classmethod
    def findFileName(cls, fileName: str, dir: str = None):
        """查找文件名，保证忽略文件名的大小写，返回实际的文件名"""
        fileNames = cls.getFileNames(dir)
        for file in fileNames:
            if file.lower() == fileName.lower():
                return file
        return None
