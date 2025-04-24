"""
全局状态管理模块 (兼容服务端和客户端)
"""
import threading
import os
import sys  # 添加sys模块导入
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from CFileServer import CFileServer_
    from CClient import CClient_
    from _Log import _Log_
    from _CmdMgr import _CmdMgr_
    from _Tools import _Tools_
    from _App import _App_  
    from _Page import _Page_
    from CDevice import CDevice_ 
    from CChecker import CChecker_
    from SDeviceMgr import SDeviceMgr_
    from SCommandHistory import SCommandHistory_
TOP = "top"
UNKNOWN = 'unknown'

# 添加一个标志，表示是否已经显示过权限提示
_permission_alert_shown = False

def checkPermission(permission):
    """检查权限是否已授予"""
    global _permission_alert_shown
    
    try:
        # 直接使用_G_类的android对象检查权限
        android = _G_.android
        if android:
            result = android.checkPermission(permission)
            
            # 如果权限被拒绝，但还没有显示过提示，则记录一条日志
            if not result and not _permission_alert_shown:
                from _Log import _Log_
                _Log_.w(
                    f"Permission denied: {permission.split('.')[-1]}", 
                    "Permission"
                )
                _permission_alert_shown = True  # 标记已经显示过提示
                
            return result
        return False
    except Exception as e:
        print(f"Check permission error: {e}")
        return False

class _G_:
    # 使用线程安全的存储
    _lock = threading.Lock()
    _dir = None
    _store = {}
    _isServer = True    
    log = None
    _scriptNamesCache = None  # 添加脚本名称缓存
    
    android = None   # Android服务对象，由客户端设置

    PASS = "pass"

    @classmethod
    def isAndroid(cls):
        """检查是否是Android环境"""
        return cls.android is not None
        
    @classmethod
    def isServer(cls):
        """是否是服务器端"""    
        return cls._isServer
    
    @classmethod
    def load(cls, isServer: bool = None):
        """设置是否是服务器端"""
        if isServer is not None:
            cls._isServer = isServer
        from _App import _App_
        _App_.loadConfig()

        # 不在这里初始化android对象，由客户端调用setAndroid方法设置
    
    @classmethod
    def rootDir(cls):
        """获取根目录"""
        if cls._dir:
            return cls._dir
        dir = None
        if not cls._isServer:
            # 直接使用android对象获取应用私有目录
            android = cls.android
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
        return cls.getClassLazy('CClient')

    @classmethod
    def Log(cls) -> '_Log_':
        return cls.getClassLazy('_Log')
    
    @classmethod
    def Checker(cls) -> 'CChecker_':
        return cls.getClassLazy('CChecker')
        
    @classmethod
    def Tools(cls) -> '_Tools_':
        """获取统一工具类实例"""
        return cls.getClassLazy('_Tools')
        
    @classmethod
    def App(cls) -> '_App_':
        return cls.getClassLazy('_App')
    
    @classmethod
    def Page(cls) -> '_Page_':
        return cls.getClassLazy('_Page')
    
    @classmethod
    def CFileServer(cls) -> 'CFileServer_':
        return cls.getClassLazy('CFileServer')
    
    @classmethod
    def CmdMgr(cls) -> '_CmdMgr_':
        """获取命令管理器"""
        return cls.getClassLazy('_CmdMgr')
    
    @classmethod
    def CDevice(cls) -> 'CDevice_':
        return cls.getClassLazy('CDevice')
    
    @classmethod
    def SDeviceMgr(cls) -> 'SDeviceMgr_':
        return cls.getClassLazy('SDeviceMgr')

    @classmethod
    def SCommandHistory(cls) -> 'SCommandHistory_':
        return cls.getClassLazy('SCommandHistory')

    @classmethod
    def CallMethod(cls, module, methodName, *args, **kwargs):
        try:
            if module is None:
                return
            klass = cls.getClassLazy(module.__name__)
            if klass:
                method = getattr(klass, methodName, None)
                if method and callable(method):
                    return method(*args, **kwargs)
        except Exception as e:
            cls.log.ex(e, f"获取类方法失败: {methodName}")

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
                # 处理模块前缀过滤，允许下划线开头的模块
                firstChar = file[0]
                if firstChar != prefix and firstChar != '_':
                    continue
                
                # 调试输出，找到匹配的文件
                print(f"找到脚本: {file}")
                
                module = file[:-3]  # 去掉.py后缀
                fileNames.append(module)
        except Exception as e:
            # 避免使用日志，直接打印错误
            print(f"扫描脚本目录失败: {e}")
        
        # 输出找到的所有脚本
        print(f"找到的所有脚本: {fileNames}")
        
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
            # if fileNameLower in fileLower:
            if fileNameLower == fileLower:
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

    @classmethod
    def setAndroid(cls, androidService):
        """设置Android服务对象
        
        该方法由客户端调用，传入已初始化的androidService对象
        """
        cls.android = androidService
        if cls.log:
            cls.log.i(f"设置Android服务对象: {androidService}")
        else:
            print(f"设置Android服务对象: {androidService}")

    @classmethod
    def onLoad(cls, oldCls):
        if oldCls:  
            cls._isServer = oldCls._isServer
            cls._dir = oldCls._dir
            cls._store = oldCls._store
            cls.android = oldCls.android  # 保留android对象
        import _Log
        cls.log = _Log._Log_()
        
        # 如果是客户端环境，尝试初始化android对象
        if not cls._isServer and cls.android is None:
            try:
                # 尝试初始化Android对象
                from java import jclass
                android = jclass(
                    "cn.vove7.andro_accessibility_api.demo.script.PythonServices")
                
                # 设置输入回调函数
                def onInput(text):
                    """Android输入回调函数"""
                    try:
                        log = cls.log
                        log.i(f"收到Android输入: {text}")
                        cls.CmdMgr().do({'cmd': text})
                    except Exception as e:
                        print(f"处理Android输入失败: {e}")
                    return True
                
                android.onInput(onInput)
                cls.android = android
                cls.log.i("成功初始化Android服务")
            except ImportError:
                # 如果不是Android环境，忽略错误
                pass
            except Exception as e:
                if cls.log:
                    cls.log.ex(e, "初始化Android服务失败")
                else:
                    print(f"初始化Android服务失败: {e}")

    @classmethod
    def getClassLazy(cls, moduleName):
        """延迟导入机制获取类，避免循环引用
        
        Args:
            moduleName: 模块名称
            
        Returns:
            对应的类对象
        """
        # 检查模块是否已缓存
        className = cls.getClassName(moduleName)
        if className in cls._store:
            return cls._store[className]
        
        try:
            # 先尝试直接导入
            try:
                __import__(moduleName)
                module = sys.modules[moduleName]
            except ImportError:
                # 如果直接导入失败，尝试通过getScriptName查找
                scriptName = cls.getScriptName(moduleName)
                if not scriptName:
                    if cls.log:
                        cls.log.w(f"找不到模块: {moduleName}")
                    return None
                
                __import__(scriptName)
                module = sys.modules[scriptName]
                moduleName = scriptName
            
            # 获取类
            className = cls.getClassName(moduleName)
            klass = getattr(module, className, None)
            if klass is None:
                if cls.log:
                    cls.log.w(f"获取类失败: {className}")
                return None
            
            # 缓存并返回
            cls._store[className] = klass
            return klass
        except Exception as e:
            if cls.log:
                cls.log.ex(e, f"延迟导入{moduleName}失败")
            return None

_G_.onLoad(None)
g = _G_
