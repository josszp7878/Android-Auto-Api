from datetime import datetime
from pathlib import Path

class Log:
    """统一的日志管理类"""
    _instance = None
    _initialized = False
    MAX_CACHE_SIZE = 3000  # 最大缓存条数
    
    def __init__(self):
        if not hasattr(self, '_cache'):
            self._cache = []
            self._visualLogs = []
    
    def clear(self):
        """清空日志缓存"""
        print('清空日志缓存')
        self._cache.clear()
        self._visualLogs.clear()  # 注释掉这行
        
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def init(self, is_server=True):
        """初始化日志系统"""
        if self._initialized:
            return self
            
        # 确保日志根目录存在
        Path("logs").mkdir(parents=True, exist_ok=True)
        self.is_server = is_server
        self._initialized = True
        
        if is_server:
            # 加载当天的日志
            self._load()
        return self
        
    def uninit(self):
        """反初始化日志系统"""
        # 保存日志
        self.save()  # 这里调用了一次
        self.clear()
    
    def _get_log_path(self, date=None):
        """获取日志文件路径"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        return Path(f"logs/{date}.log")
    
    def _load(self, date=None):
        """从文件加载日志到缓存"""
        try:
            self._cache = []
            log_path = self._get_log_path(date)
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8') as f:
                    self._cache = f.readlines()
                # print(f'从文件加载日志: {log_path}, 缓存大小: {len(self._cache)}')
                # 加载后立即过滤
                count = self.Filter(None)
        except Exception as e:
            self.ex(e, '加载日志文件失败')
    
    def save(self):
        """将日志缓存保存到文件"""
        try:
            log_path = self._get_log_path()
            if not self._cache:
                return
                
            # 打印调用栈
            import traceback
            print('\n保存日志调用栈:')
            for line in traceback.format_stack()[:-1]:  # 去掉最后一行(当前函数)
                print(line.strip())
                
            print(f'@@@保存日志到文件: {log_path}')
            with open(log_path, 'w', encoding='utf-8') as f:
                for line in self._cache:
                    f.write(line if line.endswith('\n') else line + '\n')
        except Exception as e:
            self.ex(e, '保存日志缓存失败')
    
    def add(self, log):
        # 添加到缓存
        self._cache.append(log)
        # # 限制缓存大小
        # if len(self._cache) > self.MAX_CACHE_SIZE:
        #     self._cache.pop(0)
        try:
            from app import socketio
            socketio.emit('S2B_AddLog', {
                'message': log
            })
        except Exception as e:
            print(f'发送日志到控制台失败: {e}')


    def _log(self, content, level='i', tag=None):
        timestamp = datetime.now()
        # 如果是服务器端，发送到控制台
        if self.is_server:
            log_line = self.format(timestamp, tag, level, content)
            self.add(log_line)
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
                    log_line = self.format(timestamp, tag, level, content)
                    if device and device.connected:
                        device.sio.emit('C2S_Log', {
                            'message': log_line
                        })
                    else:
                        # 未连接时直接打印
                         print(log_line)
            except Exception as e:
                print(f'发送日志到服务器失败: {e}')
    
    
    def Filter(self, filter_str=None):
        """过滤日志并更新显示缓存"""
        if not filter_str:
            self._visualLogs = self._cache
        else:
            date = None
            try:
                date = datetime.strptime(filter_str, '%Y-%m-%d')
            except Exception:
                pass
            if date:
                self._visualLogs = [
                    line for line in self._cache 
                    if f"##{date.strftime('%Y-%m-%d')}##" in line
                ]
            else:
                self._visualLogs = [
                    line for line in self._cache 
                    if f"##{filter_str}##" in line
                ]
        
        # 发送缓存统计信息
        try:
            from app import socketio
            socketio.emit('S2B_LogCount', {
                'total': len(self._cache),
                'filtered': len(self._visualLogs)
            })
        except Exception as e:
            print(f'发送日志统计失败: {e}')
            
        return len(self._visualLogs)
    
    def refreshLogs(self, page=1):
        try:
            per_page = 100  # 每页日志条数
            # 使用显示缓存
            logs = self._visualLogs        
            # 计算分页
            total = len(logs)
            start = (page - 1) * per_page + 1  # 起始索引从1开始
            end = min(start + per_page - 1, total)  # 结束索引
            
            # 发送日志统计信息
            try:
                from app import socketio
                socketio.emit('S2B_LogCount', {
                    'start': start if total > 0 else 0,
                    'end': end,
                    'total': total
                })
            except Exception as e:
                print(f'发送日志统计失败: {e}')
            
            page_logs = logs[start:end]
            has_more = end < total
            from app import socketio
            socketio.emit('S2B_RefreshLogs', {
                'logs': page_logs,
                'is_realtime': False,
                'has_more': has_more,
                'page': page,
                'total': total,
                'message': f'找到了 {len(page_logs)} 条日志记录'
            })
        except Exception as e:
            Log.ex(e, '获取日志失败')
    
    @classmethod
    def show(cls, filter_str=None, page=1):
        """显示日志"""
        # 调用过滤函数
        cls().Filter(filter_str)
        cls().refreshLogs(page)
    
    @classmethod
    def d(cls, message, tag=None):
        """输出调试级别日志"""
        Log()._log(message, 'd', tag)
    
    @classmethod
    def i(cls, message, tag=None):
        """输出信息级别日志"""
        Log()._log(message, 'i', tag)
    
    @classmethod
    def w(cls, message, tag=None):
        """输出警告级别日志"""
        Log()._log(message, 'w', tag)
    
    @classmethod
    def e(cls, message, tag=None):
        """输出错误级别日志"""
        Log()._log(message, 'e', tag)

    @classmethod
    def printEx(cls, message, e=None, tag=None):
        import traceback
        message = f'{message} Exception: {e}, {traceback.format_exc()}'
        print(message)     
        
    @classmethod
    def ex(cls, e, message, tag=None):
        import traceback
        message = f'{message} Exception: {e}, {traceback.format_exc()}'
        Log()._log(message, 'e', tag)     
    
    def format(self, timestamp, tag, level, message):
        """格式化日志消息
        格式: "HH:MM:SS##tag##level##message"
        """
        # 格式化时间,只保留时分秒
        time_str = timestamp.strftime('%H:%M:%S')
        
        # 确保级别是小写的单个字符
        level = str(level).lower()[0]
        if level not in 'ewi':
            level = 'i'
        # 确保消息不为空
        message = str(message or '')
        tag = str(tag or '@')
        
        return f"{time_str}##{tag}##{level}##{message}"
