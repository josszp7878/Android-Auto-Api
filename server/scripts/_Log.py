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

    # ANSI颜色代码
    COLORS = {
        'reset': '\033[0m',
        'black': '\033[30m',
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        'bold': '\033[1m',
        'underline': '\033[4m'
    }

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
            cls.log_(f"脚本目录: {dir}")
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
                    cls.logEx_(e, '发送日志到前端失败')
        except Exception as e:
            cls.ex(e, '加载日志文件失败')
    
    @classmethod
    def save(cls):
        """将日志缓存保存为JSON文件"""
        try:
            log_path = cls._path()
            if not cls._cache:
                return
                
            cls.log_(f'保存日志到文件: {log_path}')
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
            cls.log_(logDict.get('message'), logDict.get('tag'), logDict.get('level'),  logDict.get('result'))          
            logs = cls._cache
            from app import socketio
            # 检查是否与最后一条日志内容相同
            lastLog = logs[-1] if len(logs) > 0 else None
            if lastLog:
                # 检查标签、级别和消息是否相同
                tagEqual = lastLog.get('tag') == logDict.get('tag')
                levelEqual = lastLog.get('level') == logDict.get('level')
                msgEqual = lastLog.get('message') == logDict.get('message')
                
                if (tagEqual and levelEqual and msgEqual):  # 去除可能的重复标记
                    # 更新重复计数
                    count = lastLog.get('count', 1) + 1
                    lastLog['count'] = count
                    # 打印调试信息
                    # print(f'更新重复计数: {count}, 消息: {lastLog.get("message")}')
                    # 通知前端更新
                    try:
                        # 确保发送完整的日志对象，包括时间戳
                        socketio.emit('S2B_EditLog', lastLog)
                    except Exception as e:
                        cls.logEx_(e, '发送EditLog事件失败')
                    return
                  # 打印带颜色的日志到终端
            # 确保新日志有count字段
            if 'count' not in logDict:
                logDict['count'] = 1
            
            logs.append(logDict)
            if socketio.server:
                try:
                    socketio.emit('S2B_AddLog', logDict)
                except Exception as e:
                    cls.logEx_(e,'发送AddLog事件失败')
        except Exception as e:
            cls.logEx_(e, '发送日志到控制台失败')


    @classmethod
    def _parseLevel(cls, content, level):
        """从字符串中提取级别信息
        
        Args:
            content: 可能包含级别前缀的字符串
            level: 默认级别
            
        Returns:
            tuple: (level, content) 级别和处理后的内容
        """
        if not content:
            return (level, None)
        
        # 如果已经是字典格式，直接返回
        if isinstance(content, dict):
            return content
        
        # 提取level标记（如"-d#", "e-", "#w"等格式）
        m = re.search(r'.*?([dDiIwWEecC])[#->]+(.*)', content)
        if m:
            level = m.group(1).lower()  # 提取level字符
            content = m.group(2).strip()  # 提取剩余内容
            return (level, content)
        
        # 默认使用传入的级别
        return (level, content)
    
    @classmethod
    def createLogData(cls, tag, content, level='i', result=None)->dict:
        """创建日志数据"""
        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        level, content = cls._parseLevel(content, level)
        if content is None:
            return None
        res = cls._parseLevel(result,level)
        # print(f'res@@@@: {res}')
        return {
            'time': time,
            'tag': tag,
            'level': level,
            'message': content,
            'result': res,
            'count': 1
        }   
    
    @classmethod
    def _serverLog(cls, tag, level, content, result=None)->dict:
        try:
            logData = cls.createLogData(tag, content, level, result)
            if logData:
                cls.add(logData)
            return logData
        except Exception as e:
            cls.logEx_(e, '发送日志到服务器失败')
            return None

    @classmethod
    def _clientLog(cls, tag, level, content, result=None)->dict:
        """发送日志到前端"""
        try:
            CDevice = _G._G_.CDevice()
            if CDevice:
                devID = CDevice.deviceID()
                tag = f'{devID}{tag}' if tag else devID
                logData = cls.createLogData(tag, content, level, result)
                if CDevice.connected():
                    CDevice.emit('C2S_Log', logData)
                cls.log_(logData.get('message'), logData.get('tag'),
                         logData.get('level'), logData.get('result'))
                return logData
        except Exception as e:
            cls.logEx_(e, '发送日志到服务器失败')
            return None
        
        
    @classmethod
    def log_(cls, content, tag=None, level=None, result=None):
        """打印日志到终端"""
        g = _G._G_
        server = g.isServer()
        android = None
        if not server:
            android = g.CTools().android
        tag = tag if tag else ''    
        level = level if level else 'i'
        res = None
        if result:
            res = result[1]
        if android:            
            android.log(content, tag, level, f'{result[0]}-{res}' if res else '')
        else:
            cls._PCLog_(content, tag, level)
            if res:
                cls._PCLog_(res, '', result[0])
            
    @classmethod
    def logEx_(cls, e, message=None, tag=None):
        """打印异常信息"""
        content = cls.formatEx('异常', e, message)
        cls.log_(content, tag, 'e')

    @classmethod
    def logI_(cls, content, tag=None):
        """打印日志到终端"""
        cls.log_(content, tag, 'i', '')

    @classmethod
    def logD_(cls, content, tag=None):
        """打印日志到终端"""
        cls.log_(content, tag, 'd', '')

    @classmethod
    def logW_(cls, content, tag=None):
        """打印日志到终端"""
        cls.log_(content, tag, 'w', '')

    @classmethod
    def logE_(cls, content, tag=None):
        """打印日志到终端"""
        cls.log_(content, tag, 'e', '')


    @classmethod
    def _PCLog_(cls, content, tag=None, level='i'):
        """打印带颜色的日志到终端"""
        if content is None:
            return
        # 根据日志级别选择颜色
        color = cls.COLORS['reset']
        if level == 'e':
            color = cls.COLORS['red']
        elif level == 'w':
            color = cls.COLORS['yellow']
        elif level == 'i':
            color = cls.COLORS['green']
        elif level == 'd':
            color = cls.COLORS['cyan']  
        # 打印带颜色的日志到终端，去掉日志级别标识
        if tag:
            print(f"{color}{tag}: {content}{cls.COLORS['reset']}")
        else:
            print(f"{color}{content}{cls.COLORS['reset']}")

            
    @classmethod
    def log(cls, content, tag=None, level='i', result:str=None)->dict:
        """记录日志"""
        try:
            # 强制转换非字符串内容
            content = str(content)
            isServer = _G._G_.isServer()
            logData = None
            tag = f'[{tag}]' if tag else ''
            if isServer:
                logData = cls._serverLog(tag, level, content, result)
            else:
                logData = cls._clientLog(tag, level, content, result)
            return logData
        except Exception as e:
            cls.logEx_(e, '记录日志失败')

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
    def printEx(cls, message, e, tag=None):
        print(cls.formatEx(message, e, tag))

    @classmethod
    def ex(cls, e, message, tag=None):
        message = cls.formatEx(message, e, tag)
        cls.log(message, tag, 'e')     
    
    # 定义一个常量，用于标记执行操作的日志
    TagDo = 'Do'
    
    @classmethod
    def isError(cls, message):
        return isinstance(message, str) and message.startswith('e->')
    @classmethod
    def isWarning(cls, message):
        return isinstance(message, str) and message.startswith('w->')

   
c = _Log_()
