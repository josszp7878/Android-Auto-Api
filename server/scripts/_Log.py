from datetime import datetime
from enum import Enum
import os
import re
import _G
from typing import List
# 导入数据库模块
from SDatabase import Database, db
from sqlalchemy import func
import time
import random

class TAG(Enum):
    """标签"""
    CMD = "CMD"
    SCMD = "SCMD"
    Server = "@"

class LogModel_(db.Model):
    """日志数据模型"""
    __tablename__ = 'logs'
    
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.String(20))
    tag = db.Column(db.String(50))
    level = db.Column(db.String(10))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def toDict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'time': self.time,
            'tag': self.tag,
            'level': self.level,
            'message': self.message,
        }

class _Log_:
    """统一的日志管理类"""
    _cache: List[LogModel_] = []
    _cache = []  # 任务列表
    _lastDate = None  # 最近一次缓存的日期

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
    def clear(cls):
        """清空日志缓存"""
        cls.i('清空日志缓存')
        cls._cache.clear()


    @classmethod
    def clientScriptDir(cls):
        dir = None
        import _G
        # 直接使用_G_.android而不是通过Tools获取
        android = _G._G_.android
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
        """反初始化日志系统，保存到数据库"""
        cls.save()
        cls.clear()

    @classmethod
    def gets(cls, date=None) -> List['LogModel_']:
        """
        获取特定日期的所有日志
        :param date: 日期，默认为今天
        :return: 日志列表
        """
        if date is None:
            date = datetime.now().date()
        if cls._lastDate == date:
            return cls._cache
        # 清除当前缓存
        try:
            # 使用Database.sql确保在事务内完成查询和序列化
            def _getLogs(db):
                # 正确使用Model.query而不是db.query
                return LogModel_.query.filter(
                    func.date(LogModel_.time) == date
                ).all()
                
            cls._cache = Database.sql(_getLogs)
            cls._lastDate = date
            return cls._cache
        except Exception as e:
            cls.ex(e, f'获取日期日志列表失败: {date}')
            return []

    @classmethod
    def save(cls):
        """将日志缓存保存到数据库"""
        try:
            # cls.log_('保存日志到数据库')
            newLogs = [log for log in cls._cache if hasattr(log, '_isNew')]
            if len(newLogs) < 50:
                return
            # 使用Eventlet的spawn而不是线程
            def _save():
                try:
                    # 保存到数据库
                    def _saveLogs(db):
                        for log in newLogs:
                            db.session.add(log)
                            del log._isNew
                        db.session.commit()
                    Database.sql(_saveLogs)
                    # cls.log_("日志数据库保存完成", None, 'd')
                except Exception as thread_err:
                    cls.log_(f"日志保存异步操作异常: {thread_err}", None, 'e')
            
            # 使用Eventlet的spawn替代线程
            import eventlet
            eventlet.spawn(_save)            
        except Exception as e:
            cls.ex(e, '保存日志缓存失败')

    @classmethod
    def createID(cls)->int:
        # 精确到毫秒的时间戳
        timestamp = int(time.time() * 1000)
        # 6位随机数
        random_num = random.randint(100000, 999999)
        # 组合并取哈希的最后10位（纯数字版本）
        combined = f"{timestamp}{random_num}"
        return int(combined) % 10000000000  # 保证不超过10位数
    
    @classmethod
    def Blog(cls, message, tag=None, level='i'):
        try:
            id = cls.createID()
            time_str = datetime.now().strftime('%H:%M:%S')
            log = LogModel_(
                id=id,
                tag=tag,
                level=level,
                message=message,
                time=time_str
            )
            log._isNew = True
            cls._cache.append(log)
            cls.save()
            g = _G._G_
            from SDeviceMgr import deviceMgr
            g.emit('S2B_sheetUpdate', {'type': 'logs', 'data': [log.toDict()]}, deviceMgr.curConsoleSID)
        except Exception as e:
            cls.ex_(e, '发送日志到控制台失败')

    @classmethod
    def _parseLevel(cls, content, level='i'):
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
        # 提取level标记
        m = re.search(r'([dDiIwWEecC])[~]', content)
        if m:
            level = m.group(1).lower()  # 提取level字符
            # 提取剩余内容(去掉level标记,可能LEVEL标记在中间)
            content = re.sub(m.group(0), '', content).strip()
            if content == '':
                content = None
            return (level, content)
        # 默认使用传入的级别
        return (level, content)

    @classmethod
    def createLogData(cls, tag, content, level='i'):
        """创建日志数据"""
        time = datetime.now().strftime('%H:%M:%S')
        level, content = cls._parseLevel(content, level)
        if content is None:
            return None
            
        log_model = LogModel_(
            tag=tag,
            level=level,
            message=content,
            time=time
        )
        return log_model


    @classmethod
    def _serverLog(cls, tag, level, content):
        try:
            log_model = cls.createLogData(tag, content, level)
            if log_model:
                cls.Blog(log_model.message, log_model.tag, log_model.level)
            return log_model
        except Exception as e:
            cls.ex_(e, '发送日志到服务器失败')
            return None

    @classmethod
    def _clientLog(cls, logData):
        """发送日志到前端"""
        try:
            # 确保logData是有效的
            if logData and isinstance(logData, LogModel_):
                return logData
            return None
        except Exception as e:
            cls.ex_(e, '发送日志到服务器失败')
            return None


    @classmethod
    def ex_(cls, e, message=None, tag=None):
        """打印异常信息"""
        content = cls.formatEx('异常', e, message)
        cls.log_(content, tag, 'e')

    @classmethod
    def i_(cls, content, tag=None):
        """打印日志到终端"""
        cls.log_(content, tag, 'i')

    @classmethod
    def d_(cls, content, tag=None):
        """打印日志到终端"""
        cls.log_(content, tag, 'd')

    @classmethod
    def c_(cls, content, tag=None):
        """打印日志到终端"""
        cls.log_(content, tag, 'c')

    @classmethod
    def w_(cls, content, tag=None):
        """打印日志到终端"""
        cls.log_(content, tag, 'w')

    @classmethod
    def e_(cls, content, tag=None):
        """打印日志到终端"""
        cls.log_(content, tag, 'e')


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
            color = cls.COLORS['white']
        elif level == 'd':
            color = cls.COLORS['cyan']
        elif level == 'c':
            color = cls.COLORS['green']
        # 打印带颜色的日志到终端，去掉日志级别标识
        if tag:
            print(f"{color}{tag}: {content}{cls.COLORS['reset']}")
        else:
            print(f"{color}{content}{cls.COLORS['reset']}")


    # 正常打印日志，会向本地和远程前台发送日志
    @classmethod
    def log(cls, content, tag=None, level='i'):
        """记录日志"""
        try:
            # 强制转换非字符串内容
            content = str(content)
            g = _G._G_
            isServer = g.isServer()
            logData = None
            if isServer:
                log_model = cls.createLogData(tag, content, level)
                if log_model:
                    cls.Blog(log_model.message, log_model.tag, log_model.level)
                    cls.log_(content, tag, level)
                    logData = log_model
            else:
                # 客户端环境，获取设备对象并发送日志到服务端
                device = g.CDevice()
                if device:
                    deviceId = device.deviceID()
                    tag = f'{deviceId}{tag}' if tag else deviceId
                    # 创建字典格式的日志数据
                    logDict = {
                        'message': content,
                        'level': level,
                        'tag': tag,
                        'time': datetime.now().strftime('%H:%M:%S')
                    }
                    # 通过设备对象发送日志到服务端
                    if device.connected():
                        device.emit('C2S_Log', logDict)
                # 同时打印到终端
                cls.log_(content, tag, level)
                logData = logDict
            return logData
        except Exception as e:
            cls.ex_(e, '记录日志失败')
            return None


    @classmethod
    def log_(cls, content, tag=None, level='i'):
        """打印日志到终端"""
        g = _G._G_
        server = g.isServer()
        # 直接从_G_获取android对象
        android = g.android if not server else None
        tag = tag if tag else ''
        level, content = cls._parseLevel(content, level)
        if android:
            android.log(content, tag, level)
        else:
            cls._PCLog_(content, tag, level)

    @classmethod
    def c(cls, message, tag=None):
        """输出调试级别日志"""
        cls.log(message, tag, 'c')

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
        stack = traceback.format_exc()
        # 将stack中的文件名手机本地路径形式。路径改成相对路径，方便编辑器里面点击跳转
        # 比如：data/user/0/cn.vove7.andro_accessibility_api.demo/files/scripts/_CmdMgr.py
        # 改成：scripts/_CmdMgr.py
        stack = stack.replace('data/user/0/cn.vove7.andro_accessibility_api.demo/files/', '')
        return f'{message} Exception: {e}, {stack}'

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
        return isinstance(message, str) and message.startswith('e~')
        
    @classmethod
    def isWarning(cls, message):
        return isinstance(message, str) and message.startswith('w~')

    @classmethod
    def onLoad(cls, oldCls):
        """初始化日志系统，从数据库加载日志"""
        if oldCls:
            cls._cache = oldCls._cache


# 初始化日志系统
_Log_.onLoad(None)


