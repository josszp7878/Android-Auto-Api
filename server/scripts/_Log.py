from datetime import datetime
from enum import Enum
import os
import re
import _G
from typing import List
# 导入数据库模块
from SModels import LogModel_   
from SModelBase import SModelBase_

class TAG(Enum):
    """标签"""
    CMD = "CMD"
    SCMD = "SCMD"
    Server = "@"

class _Log_(SModelBase_):
    """统一的日志管理类"""
    _cache: List['_Log_'] = []
    _lastDate = None  # 最近一次缓存的日期

    def __init__(self, name: str):
        """初始化任务"""
        super().__init__(name, LogModel_)

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
        cls.clear()

    
    @classmethod
    def gets(cls, date=None) -> List['_Log_']:
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
            logs = LogModel_.all(date)
            cls._cache = [cls(t) for t in logs]
            cls._lastDate = date
            return cls._cache
        except Exception as e:
            cls.ex(e, f'获取日期日志列表失败: {date}')
            return []    
    
    @classmethod
    def add(cls, message, tag=None, level='i'):
        try:
            data = LogModel_.get(message, tag, level, True)
            if data:
                log = cls(data)
                cls._cache.append(log)
                log.refresh()
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
                cls.add(content, tag, level)
                cls.log_(content, tag, level)
                logData = content
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
                        g.emit('C2S_Log', logDict)
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

    @classmethod
    def t(cls, message):
        import traceback
        traceback.print_stack()
        cls.log_(message, None, 'w')

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


