from datetime import datetime
from enum import Enum
import os
from pathlib import Path
import json
import re
import _G
class TAG(Enum):
    """标签"""
    CMD = "CMD"
    SCMD = "SCMD"
    Server = "@"

class _Log_:
    """统一的日志管理类"""
    _cache = []
    _visualLogs = []

    

    @classmethod
    def clear(cls):
        """清空日志缓存"""
        cls.i('清空日志缓存')
        cls._cache.clear()
        cls._visualLogs.clear()

 
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
    def load(cls, date=None):
        """从JSON文件加载日志"""
        try:
            cls._cache = []
            log_path = cls._path(date)
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            # 逐行处理并忽略错误行
                            log = json.loads(line.strip())
                            if isinstance(log, dict):
                                cls._cache.append(log)
                        except Exception as e:
                            continue  # 忽略错误行
                
                # 保留原有发送逻辑
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
                    # print(log)
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
        
        # 强制转换非字符串内容
        if not isinstance(content, str):
            try:
                content = str(content)
            except Exception as e:
                content = f"无法转换日志内容: {type(content)}"

        # 处理特殊字符
        content = content.replace('"', "'") # 替换双引号
        
        # 构造日志字典
        logDict = {
            'time': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'tag': tag or TAG.Server.value,
            'level': level or 'i',
            'message': content[:500]  # 限制消息长度
        }
        
        # 保留原有发送逻辑
        if _G._G_.IsServer():
            cls.add(logDict)
        else:
            try:
                from CDevice import CDevice_
                device = CDevice_.instance()
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


