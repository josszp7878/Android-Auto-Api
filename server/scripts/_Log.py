from datetime import datetime
from enum import Enum
import os
from pathlib import Path

TempKey = '_IsServer' 

class TAG(Enum):
    """标签"""
    CMD = "CMD"
    SCMD = "SCMD"
    Server = "@"

class _Log:
    """统一的日志管理类"""
    _cache = []
    _visualLogs = []
    _isServer = True    
    _scriptDir = None

    @classmethod
    def OnPreload(cls):
        """热更新前的预处理，保存当前状态"""
        globals()[TempKey] = cls._isServer
        print(f'日志系统热更新前保存状态: isServer={globals().get(TempKey)}')
        return True
    
    @classmethod
    def IsServer(cls):
        """是否是服务器端"""
        return cls._isServer


    @classmethod
    def OnReload(cls):
        """热更新后的回调函数，恢复之前的状态"""
        if TempKey in globals():
            print(f'日志系统热更新后恢复状态: isServer={globals()[TempKey]}')
            cls.init(globals()[TempKey])
            del globals()[TempKey]
        return True

    @classmethod
    def clear(cls):
        """清空日志缓存"""
        print('清空日志缓存')
        cls._cache.clear()
        cls._visualLogs.clear()

    @classmethod
    def init(cls, is_server=True):
        """初始化日志系统"""
        cls._isServer = is_server
        if is_server:
            cls._load()
        return cls
    
    @classmethod
    def scriptDir(cls):
        if cls._scriptDir:
            return cls._scriptDir
        if cls._isServer:
            cls._scriptDir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
        else:
            from CTools import CTools
            android = CTools.android()
            if android:
                # Android环境下使用应用私有目录
                cls._scriptDir = android.getFilesDir('scripts', True)
                _Log.i(f"Android脚本目录: {cls._scriptDir}")
            else:
                # 开发环境使用当前目录
                cls._scriptDir = os.path.dirname(os.path.abspath(__file__))
                _Log.i(f"开发环境脚本目录: {cls._scriptDir}")
        if not os.path.exists(cls._scriptDir):
            cls._scriptDir = None
            _Log.ex(Exception('脚本目录不存在'), '脚本目录不存在')
        return cls._scriptDir
        
    @classmethod
    def uninit(cls):
        """反初始化日志系统"""
        cls.save()
        cls.clear()
    
    @classmethod
    def _get_log_path(cls, date=None):
        """获取日志文件路径"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        from app import APP_LOGS
        return Path(APP_LOGS) / f"{date}.log"
    
    @classmethod
    def _load(cls, date=None):
        """从文件加载日志到缓存并发送到前端"""
        try:
            cls._cache = []
            log_path = cls._get_log_path(date)
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8') as f:
                    cls._cache = f.readlines()
                
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
        """将日志缓存保存到文件"""
        try:
            log_path = cls._get_log_path()
            if not cls._cache:
                return
                
            print(f'保存日志到文件: {log_path}')
            with open(log_path, 'w', encoding='utf-8') as f:
                for line in cls._cache:
                    f.write(line if line.endswith('\n') else line + '\n')
        except Exception as e:
            cls.ex(e, '保存日志缓存失败')
    
    @classmethod
    def add(cls, log):
        """添加日志到缓存并发送到前端"""
        # 添加到缓存
        cls._cache.append(log)
        # print(f'添加日志到缓存####%%%: {log}')
        # 发送到前端
        try:
            from app import socketio
            socketio.emit('S2B_AddLog', {
                'message': log
            })
        except Exception as e:
            print(f'发送日志到控制台失败: {e}')

    @classmethod
    def log(cls, content, tag=None, level=None):
        """记录日志"""
        timestamp = datetime.now()
        log_line = ''
        # 如果content是dict类型，将它转换成JSON格式的字符串
        if isinstance(content, dict):
            try:
                import json
                content = json.dumps(content, ensure_ascii=False)
                level = level or 'i'
            except Exception as e:
                content = str(content)
        
        # 如果是服务器端，直接添加到缓存
        if cls._isServer:
            log_line = cls.format(timestamp, tag, level, content)
            cls.add(log_line)
        else:
            # 客户端模式，发送到服务器处理
            try:
                from CDevice import CDevice
                device = CDevice.instance()
                if device:
                    if tag:
                        tag = f'{device.deviceID}{tag}'
                    else:
                        tag = device.deviceID
                    log_line = cls.format(timestamp, tag, level, content)
                    if device and device.connected:
                        device.sio.emit('C2S_Log', {
                            'message': log_line
                        })
            except Exception as e:
                log_line = f'发送日志到服务器失败: {e}'
        print(log_line)
    
    @classmethod
    def format(cls, timestamp, tag, level, message):
        """格式化日志消息
        新格式: "HH:MM:SS@@tag##level->message"
        """
        if not message:
            return ''
        # 格式化时间,只保留时分秒
        time_str = timestamp.strftime('%H:%M:%S')
        if level:
            level = f'{level}->'
        else:
            # 如果级别为空，用message自带的级别
            level = ''
        # 确保消息不为空
        tag = str(tag or TAG.Server.value)
        return f"{time_str}@@{tag}##{level}{message}"
    
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
    
 
    



