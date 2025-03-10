from datetime import datetime
from enum import Enum
import os
from pathlib import Path
import json
import re

TempKey = '_IsServer' 

class TAG(Enum):
    """标签"""
    CMD = "CMD"
    SCMD = "SCMD"
    Server = "@"

class Log_:
    """统一的日志管理类"""
    _cache = []
    _visualLogs = []
    _scriptDir = None

    _isServer = None    
    @classmethod
    def IsServer(cls):
        """是否是服务器端"""    
        return cls._isServer
    
    @classmethod
    def init_(cls):
        if not hasattr(cls, '_init'):
            from _G import G
            cls._isServer = G.restore('_isServer')
            cls._scriptDir = G.restore('_scriptDir')
            print(f'日志系统初始化 log={G.get("Log_")}')
            cls._init = True

    @classmethod
    def OnPreload(cls):
        """热更新前的预处理，保存当前状态"""
        from _G import G
        G.save('_isServer', cls._isServer)
        G.save('_scriptDir', cls._scriptDir)
        cls.i(f'日志系统热更新前保存状态: isServer={cls._isServer}, scriptDir={cls._scriptDir}')
        return True
    

    @classmethod
    def clear(cls):
        """清空日志缓存"""
        cls.i('清空日志缓存')
        cls._cache.clear()
        cls._visualLogs.clear()

    @classmethod
    def setIsServer(cls, is_server=True):
        """设置是否是服务器端"""
        cls._isServer = is_server
        if is_server:
            cls._load()
        return cls
    
    @classmethod
    def clientScriptDir(cls):
        dir = None
        import CTools
        android = CTools.CTools_.android
        if android:
            # Android环境下使用应用私有目录
            dir = android.getFilesDir('scripts', True)
        else:
            # 开发环境使用当前目录
            dir = os.path.dirname(os.path.abspath(__file__))
            print(f"脚本目录: {dir}")
        return dir 
    
    @classmethod
    def rootDir(cls):
        dir = None
        import CTools
        android = CTools.CTools_.android
        if android:
            # Android环境下使用应用私有目录
            dir = android.getFilesDir()
        else:
            # 开发环境使用当前目录
            dir =  os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            print(f"根目录: {dir}")
        return dir 
    
    @classmethod
    def scriptDir(cls):
        dir = os.path.join(cls.rootDir(), 'scripts')
        if not os.path.exists(dir):
            os.makedirs(dir)
        return dir
        # if cls._scriptDir:
        #     return cls._scriptDir
        # if cls._isServer:
        #     cls._scriptDir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
        # else:
        #     cls._scriptDir = cls.clientScriptDir()
        # if not os.path.exists(cls._scriptDir):
        #     cls._scriptDir = None
        #     cls.ex(Exception('脚本目录不存在'), '脚本目录不存在')
        # return cls._scriptDir

    @classmethod
    def ConfigDir(cls):
        configDir = os.path.join(cls.rootDir(), 'config')
        if not os.path.exists(configDir):
            os.makedirs(configDir)
        return configDir
        # """获取配置文件目录"""
        # if cls._configDir:
        #     return cls._configDir
        # if cls._isServer:
        #     cls._configDir = "server/config"
        # else:
        #     import CTools
        #     android = CTools.CTools_.android
        #     if android is None:
        #         cls._configDir = "server/config"
        #     else:
        #         cls._configDir = android.getFilesDir('config', True)
        # return cls._configDir
    
    @classmethod
    def uninit(cls):
        """反初始化日志系统"""
        cls.save()
        cls.clear()
    
    @classmethod
    def _path(cls, date=None):
        """获取日志文件路径"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        from app import APP_LOGS
        return Path(APP_LOGS) / f"{date}.log"
    
    @classmethod
    def _load(cls, date=None):
        """从JSON文件加载日志"""
        try:
            cls._cache = []
            log_path = cls._path(date)
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            cls._cache.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            continue
                
                # 将加载的日志发送到前端
                try:
                    from app import socketio
                    socketio.emit('S2B_LoadLogs', {
                        'logs': cls._cache,
                        'date': date or datetime.now().strftime('%Y-%m-%d')
                    })
                except Exception as e:
                    print(f'发送日志到前端失败: {e}')
        except Exception as e:
            cls.ex(e, '加载日志文件失败')
    
    @classmethod
    def save(cls):
        """将日志缓存保存为JSON文件"""
        try:
            log_path = cls._path()
            if not cls._cache:
                return
                
            print(f'保存日志到文件: {log_path}')
            with open(log_path, 'w', encoding='utf-8') as f:
                for log in cls._cache:
                    json_line = json.dumps(log, ensure_ascii=False)
                    f.write(json_line + '\n')  # 每个JSON对象单独一行
        except Exception as e:
            cls.ex(e, '保存日志缓存失败')
    
    @classmethod
    def add(cls, logDict):
        """添加日志到缓存并发送到前端"""       
        cls._cache.append(logDict)
        try:
            from app import socketio
            socketio.emit('S2B_AddLog', logDict)
        except Exception as e:
            print(f'发送日志到控制台失败: {e}')

    @classmethod
    def log(cls, content, tag=None, level=None):
        """记录日志"""
        timestamp = datetime.now()
        if isinstance(content, dict):
            try:
                import json
                content = json.dumps(content, ensure_ascii=False)
                level = level or 'i'
            except Exception:
                content = str(content)
        if cls._isServer is not None:
            if cls._isServer:
                if level is None:
                    level = 'i'
                    match = re.match(r'(e|w|i|d)\s*->\*', content)
                    if match:
                        level = match.group(1)
                        content = content.replace(match.group(0), '').strip()
                logDict = {
                    'time': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'tag': tag or TAG.Server.value,
                    'level': level or 'i',
                    'message': content
                }
                cls.add(logDict)
            else:
                try:
                    from CDevice import CDevice
                    device = CDevice.instance()
                    if device:
                        tag = f'{device.deviceID}{tag}' if tag else device.deviceID
                        if device.connected:
                            device.sio.emit('C2S_Log', {
                                'time': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                'tag': tag,
                                'level': level or 'i',
                                'message': content
                            })
                except Exception as e:
                    print(f'发送日志到服务器失败: {e}')
        print(f"{timestamp.strftime('%H:%M:%S')} [{tag}] {level}: {content}")
    
       
    @classmethod
    def d(cls, message, tag=None):
        """输出调试级别日志"""
        cls.log(message, tag, 'd')
    
    @classmethod
    def Do(cls, message):
        """输出执行操作的日志"""
        cls.log(message, cls.TagDo)
    
    @classmethod
    def i(cls, message, tag=None):
        """输出信息级别日志"""
        cls.log(message, tag, 'i')
    
    @classmethod
    def w(cls, message, tag=None):
        """输出警告级别日志"""
        cls.log(message, tag, 'w')
    
    @classmethod
    def e(cls, message, tag=None):
        """输出错误级别日志"""
        cls.log(message, tag, 'e')
    

    @classmethod
    def formatEx(cls, message, e=None, tag=None):
        import traceback
        return f'{message} Exception: {e}, {traceback.format_exc()}'
        
    @classmethod
    def ex(cls, e, message, tag=None):
        message = cls.formatEx(message, e, tag)
        print(message)
        cls.log(message, tag, 'e')     
    
    # 定义一个常量，用于标记执行操作的日志
    TagDo = 'Do'
    
    @classmethod
    def isError(cls, message):
        return isinstance(message, str) and message.startswith('e->')
    @classmethod
    def isWarning(cls, message):
        return isinstance(message, str) and message.startswith('w->')

Log_.init_()


