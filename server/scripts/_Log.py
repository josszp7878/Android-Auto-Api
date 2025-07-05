"""
日志管理模块
"""
import threading
import os
import json
import glob
import time
import re
from datetime import datetime, timedelta
from typing import List
from enum import Enum
import _G


class TAG(Enum):
    """标签"""
    CMD = "CMD"
    SCMD = "SCMD"
    Server = "@"


class _Log_:
    """统一的日志管理类"""
    _cache: List['_Log_'] = []
    _lastDate = None  # 最近一次缓存的日期
    _logCacheLock = threading.Lock()
    _maxCacheSize = 100  # 最大缓存条数
    _threadLocal = threading.local()  # 线程本地存储，避免递归调用

    def __init__(self, data):
        """初始化日志对象"""
        if isinstance(data, dict):
            self.data = data
        else:
            self.data = {'message': str(data)}
        self._isDirty = False

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

    def toSheetData(self):
        """转换为表格数据格式"""
        return self.data

    @property
    def date(self):
        """获取日志日期"""
        time_str = self.data.get('time', '')
        if time_str:
            return time_str.split(' ')[0].replace('-', '') 
        return datetime.now().strftime(_G.DateHelper.DATE_FORMAT) 

    @classmethod
    def clear(cls):
        """清空日志缓存"""
        cls.i('清空日志缓存')
        cls._cache.clear()
        cls._lastDate = None

    @classmethod
    def _save(cls, force=False):
        """将日志缓存保存到文件"""
        try:
            if not cls._cache:
                return
            # print(f'save%%%: {len(cls._cache)}')
            if not force and len(cls._cache) < cls._maxCacheSize:
                return
            
            g = _G._G_
            # 统一使用文件保存方式
            dirtyLogs = [log for log in cls._cache 
                        if hasattr(log, 'dirty') and log.dirty]
            if not dirtyLogs:
                return
                
            today = datetime.now().strftime(_G.DateHelper.DATE_FORMAT)
            baseLogDir = g.logDir()
            
            # 根据环境确定子目录名
            if g.isServer():
                subDir = 'server'
            else:
                device = g.CDevice()
                subDir = device.name if device else 'unknown'
            
            # 创建带设备/服务器名的日志目录
            logDir = os.path.join(baseLogDir, subDir)
            os.makedirs(logDir, exist_ok=True)
            
            logFile = os.path.join(logDir, f'{today}.log')
            
            # 将dirty为True的日志追加到文件末尾，并设置dirty为False
            with open(logFile, 'a', encoding='utf-8') as f:
                for log in dirtyLogs:
                    f.write(json.dumps(log.toSheetData(), 
                                     ensure_ascii=False) + '\n')
            # 将dirty为True的日志设置为False
            for log in dirtyLogs:
                log.dirty = False
            cls._cache.clear()
            cls.log_(f'日志已保存到文件: {logFile}')
            
        except Exception as e:
            cls.ex_(e, '保存日志失败')

    @classmethod
    def _clean(cls):
        """清理指定天数前的日志文件"""
        try:
            g = _G._G_
            # 统一清理策略：服务器90天，客户端30天
            days = 90 if g.isServer() else 30
            cls.log_(f'清理日志文件: {days} 天前的日志')
            
            baseLogDir = g.logDir()
            
            # 根据环境确定子目录名
            if g.isServer():
                subDir = 'server'
            else:
                device = g.CDevice()
                subDir = device.name if device else 'unknown'
            
            logDir = os.path.join(baseLogDir, subDir)
            if not os.path.exists(logDir):
                return
                
            # 计算指定天数前的日期
            cutoffDate = datetime.now() - timedelta(days=days)
            
            # 获取所有日志文件
            logFiles = glob.glob(os.path.join(logDir, '*.log'))
            
            for logFile in logFiles:
                fileName = os.path.basename(logFile)
                fileDate = fileName.split('.')[0]
                fileDate = _G.DateHelper.toDate(fileDate)
                
                if fileDate < cutoffDate:
                    os.remove(logFile)
                    cls.log_(f'删除过期日志文件: {fileName}')
                    
        except Exception as e:
            cls.ex_(e, '清理过期日志文件失败')

    @classmethod
    def _add(cls, log):
        """添加日志到缓存"""
        try:
            with cls._logCacheLock:
                cls._cache.append(log)
                # print(f'add logdddddfff: {log.dirty}')
                cls._save()                    
        except Exception as e:
            cls.ex_(e, '添加日志到缓存失败')

    @classmethod
    def _loadLogs(cls, date):
        """内部日志加载方法，统一从文件加载"""
        logs = []
        try:
            g = _G._G_
            baseLogDir = g.logDir()
            
            # 根据环境确定子目录名
            if g.isServer():
                subDir = 'server'
            else:
                device = g.CDevice()
                subDir = device.name if device else 'unknown'
            
            logDir = os.path.join(baseLogDir, subDir)
            logFile = os.path.join(logDir, f'{date}.log')
            
            if os.path.exists(logFile):
                with open(logFile, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                logData = json.loads(line)
                                logs.append(cls(logData))
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            cls.ex_(e, f'从文件加载日志失败: {date}')
        return logs

    @classmethod
    def getLogs(cls, date=None):
        """获取指定日期的日志"""
        g = _G._G_
        try:

            # 统一日期格式处理
            dateHelper = _G.DateHelper()
            date = dateHelper.normalize(date)
            
            if date == datetime.now().strftime(dateHelper.DATE_FORMAT):
                # 如果是今天的日志，检查缓存
                if cls._cache and len(cls._cache) > 0:
                    first = cls._cache[0]
                    # 使用统一格式比较缓存中的日期
                    if dateHelper.normalize(first.date) == date:
                        return cls._cache
                # 缓存为空或缓存日期不匹配，加载今天的日志并缓存
                logs = cls._loadLogs(date)
                cls._cache = logs
                cls._lastDate = date
                cls.log_(f'加载了 {len(logs)} 条日志 (日期: {date})')
                
                # 如果是服务端，更新前台日志数据
                if g.isServer():
                    try:
                        logData = [log.toSheetData() for log in logs]
                        g.emit('S2B_sheetUpdate', 
                               {'type': 'logs', 'data': logData})
                        cls.log_(f'已更新前台日志数据，共 {len(logData)} 条')
                    except Exception as e:
                        cls.ex_(e, '更新前台日志数据失败')
                
                return cls._cache
            else:
                # 如果不是今天的日志，不缓存，直接返回
                return cls._loadLogs(date)
        except Exception as e:
            cls.ex_(e, '获取日志失败')
            return []

    @classmethod
    def uninit(cls):
        """反初始化日志系统，保存日志到文件"""
        cls._save(True)
        cls._clean()
        cls.clear()

    @classmethod
    def gets(cls, date=None) -> List['_Log_']:
        """
        获取特定日期的所有日志（兼容方法，调用getLogs）
        :param date: 日期，默认为今天
        :return: 日志列表
        """
        return cls.getLogs(date) 
       
    @classmethod
    def genID(cls):
        """生成日志ID"""
        return int(time.time() * 1000000)

    @property
    def dirty(self):
        """日志是否脏了"""
        return self._isDirty
    
    @dirty.setter
    def dirty(self, value: bool):
        self._isDirty = value
    
    @classmethod
    def add(cls, message, tag=None, level='i') -> dict:
        """添加日志到缓存"""
        # 防止递归调用
        if hasattr(cls._threadLocal, 'adding') and cls._threadLocal.adding:
            # 如果正在添加日志，直接返回避免无限递归
            print(f"[WARNING] 递归日志调用被阻止: {message}")
            return None
            
        try:
            cls._threadLocal.adding = True  # 设置递归标志
            
            logData = {
                'message': message, 
                'tag': tag, 
                'level': level, 
                'time': datetime.now().strftime(_G.DateHelper.DATETIME_FORMAT)
            }
            # set id to the max id + 1
            logData['id'] = cls.genID()
            # 创建_Log_对象并添加到缓存
            log = cls(logData)
            log.dirty = True
            cls._add(log)
            # 服务器环境下刷新前台数据
            if _G._G_.isServer():
                try:
                    _G._G_.emit('S2B_sheetUpdate', 
                               {'type': 'logs', 'data': [logData]})
                except Exception as e:
                    # 避免递归，直接打印错误而不是调用日志方法
                    print(f"[ERROR] 刷新前台日志数据失败: {e}")
                    
            return logData
        except Exception as e:
            # 避免递归，直接打印错误而不是调用日志方法
            print(f"[ERROR] 添加日志失败: {e}")
            return None
        finally:
            cls._threadLocal.adding = False  # 重置递归标志

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

    @classmethod
    def log(cls, content, tag=None, level='i', toServer=False) -> bool:
        """记录日志"""
        try:
            # 强制转换非字符串内容
            content = str(content)
            g = _G._G_
            isServer = g.isServer()
            
            if isServer:
                # 服务器环境：添加到本地缓存并打印
                cls.add(content, tag, level)
                cls.log_(content, tag, level)
            else:
                # 客户端环境：添加到本地缓存
                device = g.CDevice()
                if device:
                    deviceId = device.name
                    tag = f'{deviceId}{tag}' if tag else deviceId
                    # 添加到客户端本地缓存
                    log = cls.add(content, tag, level)
                    # 只在debug开启且连接时发送到服务端
                    if log and (toServer or device.getDBProp('debug')):
                        g.emit('C2S_Log', log)
                # 同时打印到终端
                cls.log_(content, tag, level)
            return True
        except Exception as e:
            cls.ex_(e, '记录日志失败')
            return False

    @classmethod
    def log2S(cls, content, tag=None, level='i'):
        return cls.log(content, tag, level, True)

    @classmethod
    def log_(cls, content, tag=None, level='i'):
        """打印日志到终端"""
        tag = tag if tag else ''
        level, content = cls._parseLevel(content, level)
        cls._PCLog_(content, tag, level)

    @classmethod
    def result(cls, result):
        """记录命令执行结果到日志"""
        # 调试输出
        # print(f"DEBUG: result方法收到参数: {result}, 类型: {type(result)}, 布尔值: {bool(result)}")
        
        if result is None:  # 只有None才返回，空字符串和False都要处理
            return
        content = ''
        level = 'i'
        if isinstance(result, str):
            # 只有当result是字符串时才解析日志级别
            level, content = cls._parseLevel(result, 'i')
        else:
            # 如果result不是字符串（比如列表、字典等），直接记录
            if isinstance(result, (list, dict)):
                content = f"  结果： 返回 {type(result).__name__} 数据，长度: {len(result)}"
            else:
                content = f"  结果： {str(result)}"
        
        if not content:  # 如果content为空才返回
            return
        
        length = len(content)
        if length > 100:
            content = content[:100] + '...'
        
        cls.add(content, '', level)

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
        stack = stack.replace(
            'data/user/0/cn.vove7.andro_accessibility_api.demo/files/', '')
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
        """初始化日志系统"""
        if oldCls:
            cls._cache = oldCls._cache        
        print('日志系统初始化完成')
        # 延迟预加载日志，避免在系统初始化时调用emit
        try:
            if _G._G_.isServer():
                # 延迟加载，让系统完全初始化后再加载
                import threading
                def delayed_load():
                    import time
                    time.sleep(3)  # 等待2秒让系统完全初始化
                    try:
                        today = datetime.now().strftime(_G.DateHelper.DATE_FORMAT)
                        cls.getLogs(today)  # 这会加载今天的日志并发送到前台
                    except Exception as e:
                        print(f'延迟预加载日志失败: {e}')
                
                thread = threading.Thread(target=delayed_load, daemon=True)
                thread.start()
        except Exception as e:
            print(f'启动日志预加载线程失败: {e}')


# 初始化日志系统
_Log_.onLoad(None)


