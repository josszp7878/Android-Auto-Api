"""
全局状态管理模块 (兼容服务端和客户端)
"""
from datetime import datetime
import threading
import os
import sys  # 添加sys模块导入
import time
from typing import TYPE_CHECKING, List, Optional
from enum import Enum
import re

if TYPE_CHECKING:
    from CFileServer import CFileServer_
    from CClient import CClient_
    from _Log import _Log_
    from _CmdMgr import _CmdMgr_
    from _Tools import _Tools_
    from _App import _App_  
    from CDevice import CDevice_ 
    from SDeviceMgr import SDeviceMgr_
    from CTask import CTask_
    from CApp import CApp_

TOP = "top"
TEMP = "temp"
ROOT = "root"
ServerTag = "@"

class TaskState(str,Enum):
    """任务状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCESS = "success"
    FAILED = "failed"

class ConnectState(str,Enum):
    """连接状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    LOGIN = "login"
    LOGOUT = "logout"

    
class DateHelper:
    """统一的日期处理工具类"""
    
    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'  # 统一日期时间格式: 2025-06-19 10:30:45
    DATE_FORMAT = '%Y-%m-%d'  # 日期格式: 2025-06-19
    
    @classmethod
    def toDate(cls, date_str: str) -> datetime:
        """将字符串转换为日期对象，支持多种格式"""
        if not date_str:
            return datetime.now()
            
        date_str = date_str.strip()
        
        # 尝试解析完整日期时间格式 YYYY-MM-DD HH:MM:SS
        try:
            return datetime.strptime(date_str, cls.DATETIME_FORMAT)
        except ValueError:
            pass
            
        # 尝试解析日期格式 YYYY-MM-DD
        try:
            return datetime.strptime(date_str, cls.DATE_FORMAT)
        except ValueError:
            pass
            
        # 尝试解析旧格式 YYYYMMDD
        try:
            if re.match(r'^\d{8}$', date_str):
                return datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            pass
            
        # 尝试解析其他格式
        formats = ['%Y/%m/%d', '%Y.%m.%d', '%m/%d/%Y', '%d/%m/%Y']
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
                
        # 如果都失败了，返回今天
        return datetime.now()
    
    @classmethod
    def normalize(cls, date_input) -> str:
        """将各种日期格式统一转换为标准格式 YYYY-MM-DD
        
        Args:
            date_input: 支持的格式:
                - None: 返回今天
                - '2025-06-19': 保持不变
                - '20250619': 转换为 '2025-06-19'
                - datetime对象: 转换为 '2025-06-19'
                - '2025-06-19 10:30:45': 提取日期部分
                
        Returns:
            str: 标准格式的日期字符串 YYYY-MM-DD
        """
        if date_input is None:
            return datetime.now().strftime(cls.DATE_FORMAT)
            
        if isinstance(date_input, datetime):
            return date_input.strftime(cls.DATE_FORMAT)
            
        if isinstance(date_input, str):
            date_str = date_input.strip()
            
            # 已经是标准格式 YYYY-MM-DD
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                return date_str
                
            # 格式: YYYY-MM-DD HH:MM:SS (提取日期部分)
            if ' ' in date_str:
                date_part = date_str.split(' ')[0]
                return cls.normalize(date_part)
                
            # 旧格式 YYYYMMDD
            if re.match(r'^\d{8}$', date_str):
                try:
                    dt = datetime.strptime(date_str, '%Y%m%d')
                    return dt.strftime(cls.DATE_FORMAT)
                except ValueError:
                    pass
                    
            # 其他格式，尝试解析
            try:
                dt = cls.toDate(date_str)
                return dt.strftime(cls.DATE_FORMAT)
            except:
                pass
                
        # 如果无法解析，返回今天的日期
        return datetime.now().strftime(cls.DATE_FORMAT)
    
    

        
    


class _G_:
    # 使用线程安全的存储
    _lock = threading.Lock()
    _dir = None
    _store = {}
    _isServer = True    
    log = None
    _scriptNamesCache = None  # 添加脚本名称缓存
    
    android = None   # Android服务对象，由客户端设置
    _sio = None  # 实际的Socket.IO实例
    _consoles = set()  # 当前连接的控制台列表
    _pending_requests = {}  # {request_id: (event, callback/future)}
    _rpc_lock = threading.Lock()

    @classmethod
    def sio(cls):
        """获取Socket.IO实例"""
        return cls._sio

    @classmethod
    def setIO(cls, sio):
        """设置Socket.IO实例并初始化事件监听（线程安全）"""
        if sio is not None:
            cls._sio = sio
            # sio.on('_Result')(cls.on_Result)

    
    # @classmethod
    # def on_Result(cls, response):
    #     """统一处理所有RPC响应（类方法）"""
    #     request_id = response.get('requestId')
    #     log = cls.log
    #     log.i(f"收到_Result事件: {response}")
    #     with cls._rpc_lock:
    #         if request_id in cls._pending_requests:
    #             _, callback = cls._pending_requests.pop(request_id)
    #             if callback:
    #                 if isinstance(callback, asyncio.Future):
    #                     # 异步回调处理
    #                     callback.set_result(response)
    #                 else:
    #                     # 同步回调处理
    #                     callback(response)


    @classmethod
    def addConsole(cls, sid: str):
        """添加控制台"""
        if sid:
            cls._consoles.add(sid)
            print(f'addConsole: {cls._consoles}')
    
    @classmethod
    def removeConsole(cls, sid: str):
        """删除控制台"""
        if sid:
            if sid in cls._consoles:
                cls._consoles.remove(sid)
                print(f'removeConsole: {cls._consoles}')

    @classmethod
    def connect(cls):
        """连接"""
        if cls._sio is None:
            return False
        cls._sio.connect()
        return True

    @classmethod 
    def _serializeForJson(cls, obj):
        """递归转换对象，使其可以被JSON序列化"""
        from datetime import datetime, date
        
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, dict):
            # dict本身JSON支持，但需要处理值中可能的datetime对象
            return {k: cls._serializeForJson(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            # list/tuple本身JSON支持，但需要处理元素中可能的datetime对象
            return [cls._serializeForJson(item) for item in obj]
        elif isinstance(obj, set):
            # set不被JSON支持，需要转换为list并处理元素中可能的datetime对象
            return [cls._serializeForJson(item) for item in obj]
        else:
            # 其他类型直接返回（如str、int、float、bool、None等JSON原生支持的类型）
            return obj

    @classmethod
    def emit(cls, event, data=None, sid=None, timeout=8, callback=None)->bool:
        """发送事件并等待结果"""
        try:
            sio = cls._sio
            log = cls.log
            # log.i_(f'emit: {event}, {callback}')
            if sio is None:
                print('socketio无效')
                return False
            
            # 预处理数据，确保可以被JSON序列化
            if data is not None:
                data = cls._serializeForJson(data)
            
            # print(f'emit: {event}, {data}, {sid}')
            if cls.isServer():
                if sid:
                    sio.emit(event, data, room=sid, callback=callback)
                else:                    
                    # log.i_(f'emit: {event}, console count={len(cls._consoles)}, data={data}')
                    for sid in cls._consoles:
                        sio.emit(event, data, room=sid, callback=callback)
            else:
                device = cls.CDevice()
                if not device or not device.isConnected():
                    log.ex_(f"设备未连接: {event}, {data}")
                    return False
                if data is None:
                    data = {}
                data['device_id'] = device.name
                sio.emit(event, data, callback=callback)
        except Exception as e:
            log.ex_(e, f"发送事件失败: {event}, {data}")
            return False

    @classmethod
    def emitRet(cls, event, data=None, sid=None, timeout=10):
        """发送事件并等待结果"""
        try:
            log = cls.log
            # log.i_(f'发送ddd: event={event}, data={data}')
            result = None
            wait = True
            start_time = time.time()
            
            def onResult(*args):
                nonlocal result
                nonlocal wait
                response = args[0] if args else None
                result = response
                # log.i_(f'收到事件结果: event={event}, result={result}')
                wait = False
                return result
                
            if not cls.emit(event, data, sid, timeout, onResult):
                result = None
                
            # 添加超时控制的等待循环
            while wait:
                if time.time() - start_time > timeout:
                    log.w_(f'事件超时: event={event}, timeout={timeout}s')
                    wait = False
                    result = None
                    break
                time.sleep(0.1)
            return result
        except Exception as e:
            log.ex_(e, f"发送事件失败: {event}, {data}")
            return None
    
    # @classmethod
    # def rpc(cls, event, data=None, timeout=8):
    #     """事件式RPC（同步/异步通用）"""
    #     request_id = str(uuid.uuid4())
    #     future = asyncio.Future()

    #     with g._rpc_lock:
    #         g._pending_requests[request_id] = (event, future)

    #     # 发送请求
    #     g.emit(event, {
    #         ** (data or {}),
    #         'requestId': request_id
    #     })

    #     try:
    #         # 异步等待结果
    #         return asyncio.wait_for(future, timeout)
    #     except asyncio.TimeoutError:
    #         with g._rpc_lock:
    #             g._pending_requests.pop(request_id, None)
    #         raise TimeoutError(f"RPC call {event} timed out after {timeout}s")

    # @classmethod
    # def rpc_call(cls, call, timeout=8):
    #     """通用回调式RPC（适合连接等非事件场景）"""
    #     g = cls.instance()
    #     request_id = str(uuid.uuid4())
    #     result = None
    #     event = f'_SysCall_{request_id}'  # 生成唯一事件名

    #     # 创建临时回调
    #     def handler(response):
    #         nonlocal result
    #         if response.get('requestId') == request_id:
    #             result = response

    #     with g._rpc_lock:
    #         g._pending_requests[request_id] = (event, handler)

    #     # 执行调用（这里假设call函数会触发某个事件）
    #     call()

    #     # 等待结果
    #     start_time = time.time()
    #     while time.time() - start_time < timeout:
    #         if result is not None:
    #             return result
    #         time.sleep(0.1)
        
    #     # 超时处理
    #     with g._rpc_lock:
    #         g._pending_requests.pop(request_id, None)
    #     raise TimeoutError(f"RPC call timed out after {timeout}s")
    
    @classmethod
    def isAndroid(cls):
        """检查是否是Android环境"""
        return cls.android is not None
        
    @classmethod
    def isServer(cls):
        """是否是服务器端"""    
        return cls._isServer
    
    @classmethod
    def toTaskId(cls, appName: str, templateId: str) -> str:
        """生成任务唯一标识"""
        return f"{appName}_{templateId}"
    
    @classmethod
    def load(cls, isServer: bool = None):
        """设置是否是服务器端
        Args:
            isServer: 是否是服务端
            socketio_instance: SocketIO实例
        """
        if isServer is not None:
            cls._isServer = isServer
        cls.onLoad(None)

    
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
    def getDir(cls, subDir: str):
        dir = os.path.join(cls.rootDir(), subDir)
        if not os.path.exists(dir):
            os.makedirs(dir)
        return dir
    
    @classmethod
    def dataDir(cls, subDir: str = None):
        return cls.getDir(os.path.join('data', subDir))
    
    @classmethod
    def logDir(cls):
        return cls.getDir('logs')

    @classmethod
    def scriptDir(cls):
        return cls.getDir('scripts')

    @classmethod
    def configDir(cls):
        return cls.getDir('config')

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
    def Tools(cls) -> '_Tools_':
        """获取统一工具类实例"""
        return cls.getClassLazy('_Tools')
        
    @classmethod
    def App(cls) -> '_App_':
        if cls.isServer():
            return cls.getClassLazy('SApp')
        else:
            return cls.getClassLazy('CApp')
    
    @classmethod
    def CApp(cls) -> 'CApp_':
        return cls.getClassLazy('CApp')

    @classmethod
    def CTask(cls) -> 'CTask_':
        return cls.getClassLazy('CTask')
    
    @classmethod
    def Page(cls) -> 'CPage_.CPage_':
        """获取页面处理类，现在由CPage_实现"""
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
        """获取设备实例（单例模式）"""
        from CDevice import CDevice_
        return CDevice_.instance()
    
    @classmethod
    def toClassName(cls, className: str) -> str:
        """获取RPC类名"""
        if not className.endswith('_'):
            className = className + '_'
        return className
    
    @classmethod
    def RPCClient(cls, id, methodName: str, params: dict = None):
        """服务端调用"""
        if not methodName or '.' not in methodName:
            return None
        strs = methodName.split('.')
        className = strs[0]
        methodName = strs[1]
        if id:
            log = cls.log
            log.i(f"RPCClient@@@@@@@@@@@@: {id}, {methodName}, {params}")
            params['id'] = id
        return cls._RPC(None, className, methodName, params)

    @classmethod
    def RPCServer(cls, deviceID, methodName: str, params: dict = None):
        """服务端调用"""
        if not methodName or '.' not in methodName:
            return None
        strs = methodName.split('.')
        className = strs[0]
        methodName = strs[1]
        return cls._RPC(deviceID, className, methodName,  params)

    @classmethod
    def _RPC(cls, device_id: str, className: str, methodName: str, params: dict = None):
        """远程过程调用        
        Args:
            device_id: 设备ID（如果是服务端调用客户端，为None则是客户端调用服务端）
            className: 类名
            methodName: 方法名
            params: 参数字典
        """
        from RPC import callRPC
        return callRPC(device_id, className, methodName, params)
    
       
    @classmethod
    def handleRPC(cls, data: dict):
        """处理RPC调用"""
        from RPC import handleRpcCall
        return handleRpcCall(data)
    
    
    @classmethod
    def SDeviceMgr(cls) -> 'SDeviceMgr_':
        from SDeviceMgr import deviceMgr
        return deviceMgr

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
                # print(f"找到脚本: {file}")
                
                module = file[:-3]  # 去掉.py后缀
                fileNames.append(module)
        except Exception as e:
            # 避免使用日志，直接打印错误
            print(f"扫描脚本目录失败: {e}")
        
        # 输出找到的所有脚本
        # print(f"找到的所有脚本: {fileNames}")
        
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
    def onLoad(cls, oldCls):
        if oldCls:  
            cls._isServer = oldCls._isServer
            cls._dir = oldCls._dir
            cls._store = oldCls._store
            cls.android = oldCls.android  # 保留android对象
        import _Log
        log = _Log._Log_
        cls.log = log
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
            except ModuleNotFoundError:
                log.w("找不到Android服务")
            except Exception as e:
                log.ex(e, "初始化Android服务失败")

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
    
    @classmethod
    def toInt(cls, id, default=None) -> int:
        """将字符串转换为ID"""
        if isinstance(id, int):
            return id
        elif isinstance(id, str):
            if id.isdigit():
                return int(id)
        return default
        
    # 全角到半角的
    DefSymbolMap:dict = {
        '＜': '<',
        '＞': '>',
        '（': '(',
        '）': ')',
        '，': ',',
        '：': ':',
        '；': ';',
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
        '！': '!',
        '？': '?',
        '～': '~',
        '｜': '|',
        '＠': '@',
        '＃': '#',
        '＄': '$',
        '％': '%',
        '＆': '&',
        '＊': '*',
        '＋': '+',
        '－': '-',
        '／': '/',
        '＝': '=',
        '［': '[',
        '］': ']',
        '｛': '{',
        '｝': '}',
        '｀': '`',
        '　': ' ',  # 全角空格替换为半角空格
    }
    
    # OCR容易出错的字符对映射
    OcrErrorMap: dict = {
        '市': '币',
        '币': '市', 
        '全': '金',
        '金': '全',
        '奖': '将',
        '将': '奖',
        '现': '观',
        '看': '着',
        '着': '看',
        '告': '苦',
        '苦': '告',
        '视': '规',
        '规': '视',
        '属': '屬',
        '屬': '属',
        '打': '扎',
        '扎': '打',
        '支': '文',
        '文': '支',
        '付': '什',
        '什': '付',
    }
        
    @classmethod
    def replaceSymbols(cls, text: str, symbolMap: dict = None) -> str:
        """替换文本中的特殊符号
        
        Args:
            text: 要处理的文本
            symbol_map: 自定义符号映射表
            
        Returns:
            处理后的文本
        """
        if not text:
            return text
        # 使用自定义映射更新默认映射
        if symbolMap is None:
            symbolMap = cls.DefSymbolMap
        # 执行替换
        for full, half in symbolMap.items():
            text = text.replace(full, half)
        return text        

    @classmethod
    def ocrCompare(cls, str1: str, str2: str, maxDiff: int = 2) -> bool:
        """OCR字符串比较，判断两个字符串是否因OCR错误导致的差异
        
        Args:
            str1: 第一个字符串
            str2: 第二个字符串
            maxDiff: 最大允许的不同字符数
            
        Returns:
            如果两字符串只有少于等于maxDiff个容易出错的字符不同，返回True
        """
        if not str1 or not str2:
            return str1 == str2
            
        if str1 == str2:
            return True
            
        # 长度必须相等才进行OCR比较
        if len(str1) != len(str2):
            return False
            
        # 统计不同字符数
        diffCount = 0
        
        # 比较相同位置的字符
        for i in range(len(str1)):
            char1 = str1[i]
            char2 = str2[i]
            if char1 != char2:
                # 检查是否是OCR容易出错的字符对
                if cls.OcrErrorMap.get(char1) == char2 or cls.OcrErrorMap.get(char2) == char1:
                    diffCount += 1
                else:
                    # 不是OCR错误字符对，直接返回False
                    return False
                    
        return diffCount <= maxDiff

g = _G_

