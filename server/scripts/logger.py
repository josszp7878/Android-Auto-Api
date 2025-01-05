from datetime import datetime
from pathlib import Path

class Log:
    """统一的日志管理类"""
    _instance = None
    MAX_CACHE_SIZE = 3000  # 最大缓存条数
    cache = {}  # 设备日志缓存 {device_id: [log_lines]}
    def clear(self):
        self.cache.clear()
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def init(self, is_server=True):
        """初始化日志系统
        Args:
            is_server: 是否为服务器端
        """
        # 确保日志根目录存在
        Path("logs").mkdir(parents=True, exist_ok=True)
        self.is_server = is_server
        return self
    
    def uninit(self):
        """释放日志系统"""
        # 保存当前缓存的日志到文件
        for device_id, logs in self.cache.items():
            log_file = Path(f"logs/{device_id}.log")
            with log_file.open('a') as f:
                for log in logs:
                    f.write(log)
        self.clear()
        self._instance = None
        
    def _defDeviceID(self):
        """获取当前设备ID"""
        if self.is_server:
            # 服务器端使用当前选中的设备ID
            try:
                from app.device_manager import DeviceManager
                device_id = DeviceManager().curDeviceID
                return device_id if device_id else '@'
            except:
                return '@'
        else:
            from CDevice import CDevice
            device = CDevice()
            return device.deviceID
        
    
    def _log(self, content, level='i', tag=None, device_id=None):
        if device_id is None:
            device_id = self._defDeviceID()
        if tag is None:
            tag = device_id
        # print(f'日志: {content} deviceID={device_id}, tag={tag}')    
        timestamp = datetime.now()
        # 使用统一的格式化方法
        content = self.format(timestamp, tag, level, content)
        self.log(device_id, content)
       
    
    def log(self, device_id, content):
        """内部日志处理方法"""
        # 服务器端处理
        if self.is_server:
            # 写入缓存
            self._add(device_id, content + '\n')            
            try:
                # 向控制台发送日志
                from app.device_manager import DeviceManager
                DeviceManager().emit_to_console('add_log', {
                    'message': content,
                    'device_id': device_id
                })
            except Exception as e:
                import traceback
                print(f'发送日志到控制台失败: {e}')
                print(f'traceback: {traceback.format_exc()}')
        else:
            # 客户端发送到服务器
            try:
                from CDevice import CDevice
                device = CDevice()
                if device and device.connected:
                    device.sio.emit('client_log', {
                        'device_id': device.deviceID,
                        'message': content
                    })
            except Exception as e:
                print(f'发送日志到服务器失败: {e}')            
    
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
    def ex(cls, e, message, tag=None):
        import traceback
        message = f'{message} Exception: {e}, {traceback.format_exc()}'
        Log()._log(message, 'e', tag)     
    
    def _get_log_path(self, device_id):
        """获取设备日志路径"""
        return f"logs/{device_id}"
    
    def _key(self, device_id, date=None):
        """生成缓存键
        Args:
            device_id: 设备ID
            date: 日期字符串，None表示使用当前日期
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        return f"{device_id}_{date}"
    
    def _add(self, device_id, log_line):
        """添加日志到缓存"""
        logs = self.gets(device_id)
        logs.append(log_line)
        # 限制缓存大小
        if len(logs) > self.MAX_CACHE_SIZE:
            logs.pop(0)
    
    def gets(self, device_id, date=None):
        """获取设备日志，如果缓存不存在则从文件加载"""
        if device_id:
            # 如果缓存不存在，从文件加载
            cache_key = self._key(device_id, date)
            if cache_key not in self.cache:
                self._load(device_id, date)
            logs = self.cache.get(cache_key, [])
            return logs
    
    def _load(self, device_id, date=None):
        """从文件加载日志到缓存"""
        try:
            # 获取日志文件路径
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            log_dir = Path(self._get_log_path(device_id))
            log_path = log_dir / f"{date}.log"
            # 生成缓存键
            cache_key = self._key(device_id, date)
            
            # 如果文件存在，读取内容到缓存
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8') as f:
                    self.cache[cache_key] = f.readlines()
                print(f'从文件加载日志: {log_path}, 缓存大小: {len(self.cache[cache_key])}')
            else:
                # 如果文件不存在，初始化空缓存
                self.cache[cache_key] = []
            print(f'dddddd从文件加载日志: {log_path}, 缓存大小: {len(self.cache[cache_key])}')
        except Exception as e:
            Log.ex(e, '加载日志文件失败')
            self.cache[cache_key] = []
    
    def save(self, device_id, date=None):
        """将设备日志缓存保存到文件"""
        # 生成缓存键
        cache_key = self._key(device_id, date)
        if cache_key not in self.cache:
            return
        try:
            # 获取日志文件路径
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            log_dir = Path(self._get_log_path(device_id))
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / f"{date}.log"
            
            # 打开文件，追加写入缓存的日志
            with open(log_path, 'a', encoding='utf-8') as f:
                for line in self.cache[cache_key]:
                    f.write(line)
            print(f'日志已保存到文件: {log_path}, 缓存大小: {len(self.cache[cache_key])}')
            
        except Exception as e:
            Log.ex(e, '保存日志缓存失败')
    
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
