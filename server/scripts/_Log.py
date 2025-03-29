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
    def Clone(cls, oldCls):
        """克隆"""
        cls._cache = oldCls._cache
        cls._visualLogs = oldCls._visualLogs


    @classmethod
    def clear(cls):
        """清空日志缓存"""
        cls.i('清空日志缓存')
        cls._cache.clear()
        cls._visualLogs.clear()

 
    @classmethod
    def clientScriptDir(cls):
        dir = None
        import _G
        tools = _G._G_.Tools()
        android = tools.android
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
        try:
            logs = cls._cache
            from app import socketio
            # 检查是否与最后一条日志内容相同
            lastLog = logs[-1] if len(logs) > 0 else None
            if lastLog:
                # 检查标签、级别和消息是否相同
                tagEqual = lastLog.get('tag') == logDict.get('tag')
                levelEqual = lastLog.get('level') == logDict.get('level')
                msgEqual = lastLog.get('message') == logDict.get('message')
                # print(f'msg: {lastLog.get("message")}, logmsg: {logDict.get("message")} msgEqual: {msgEqual}')
                if (tagEqual and levelEqual and msgEqual):  # 去除可能的重复标记
                    # 更新重复计数
                    count = lastLog.get('count', 1) + 1
                    print(f'更新重复计数: {count}')
                    lastLog['count'] = count
                    # 通知前端更新
                    socketio.emit('S2B_EditLog', lastLog)
                    return
            logs.append(logDict)
            if socketio.server:
                socketio.emit('S2B_AddLog', logDict)
        except Exception as e:
            message = cls.formatEx('发送日志到控制台失败', e, '')
            print(message)


    @classmethod
    def _serverLog(cls, tag, level, content)->dict:
        try:
            # 检查content是否以特定格式开头，提取level
            m = re.match(r'^\s*([diwec])[\#\-]\s*(.+)$', content)
            if m:
                level = m.group(1)  # 提取level字符
                content = m.group(2)  # 提取剩余内容            
            time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')            
            # 创建新日志
            logData = {
                'time': time,
                'tag': tag,
                'level': level,
                'message': content,
                'count': 1
            }    
            cls.add(logData)
            return logData
        except Exception as e:
            print(f'发送日志到服务器失败: {e}')
            return None

    @classmethod
    def _clientLog(cls, tag, level, content)->dict:
        """发送日志到前端"""
        try:
            from CDevice import CDevice_
            device = CDevice_.instance()
            if device:
                tag = f'{device.deviceID}{tag}' if tag else device.deviceID
                time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logData = {
                    'time': time,
                    'tag': tag,
                    'level': level,
                    'message': content
                }
                if device.connected:
                    # print(f'发送日志到服务器: {logData}')
                    device.sio.emit('C2S_Log', logData)
                return logData  
        except Exception as e:
            print(f'发送日志到服务器失败: {e}')
            return None

    @classmethod
    def log(cls, content, tag=None, level='i')->dict:
        """记录日志"""
        try:
            # 强制转换非字符串内容
            content = str(content)
            isServer = _G._G_.isServer()
            logData = None
            tag = f'[{tag}]' if tag else ''
            if isServer:
                logData = cls._serverLog(tag, level, content)
            else:
                logData = cls._clientLog(tag, level, content)
            print(f"{tag} {level}: {content}")
            return logData
        except Exception as e:
            print(f'记录日志失败: {e}')

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

    @classmethod
    def cmdLog(cls, command, sender, executor, result=None):
        """记录指令日志（自动包含结果）"""
        # 生成标准格式
        message = f"{command}:{sender}→{executor}"
        if result is not None:
            message += f" => {result}"  # 结果截断
        cls.log(message, TAG.CMD.value, 'c')
    
    @classmethod
    def setCmdResult(cls, log, result=None):
        """记录指令结果"""
        if log is None:
            return
        res = str(result).replace('\n', ' ')
        log['result'] = res

c = _Log_()
