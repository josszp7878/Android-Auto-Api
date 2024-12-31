from datetime import datetime
from pathlib import Path

class Log:
    """统一的日志管理类"""
    _instance = None
    MAX_CACHE_SIZE = 1000  # 最大缓存条数
    cache = {}  # 设备日志缓存 {device_id: [log_lines]}
    files = {}  # 设备日志文件 {device_id: file_handle}
    is_server = True
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
    
    def _defDeviceID(self):
        """获取当前设备ID"""
        if self.is_server:
            return 'server'
        else:
            from CDevice import CDevice
            device = CDevice()
            return device.deviceID
        
    @classmethod    
    def addCLog(self, device_id, message, level='i', tag=None):
        Log()._log(message, level, tag, device_id)
    
    def _log(self, message, level='i', tag=None, device_id=None):
        """内部日志处理方法"""
        if device_id is None:
            device_id = self._defDeviceID()
        timestamp = datetime.now()
        log_line = f"[{timestamp.strftime('%H:%M:%S')}] [{level}] {tag or device_id}: {message}\n"

        # print(f'@@@@@_log: {device_id}, {message}, {level}, {tag}')
        if self.is_server:
            # 服务器端写入缓存
            self._add(device_id, log_line)
        else:
            # 客户端发送到服务器
            try:
                from CDevice import CDevice
                device = CDevice()
                if device and device.connected:
                    device.send_log(message, level, tag)
            except Exception as e:
                print(f'发送日志到服务器失败: {e}')
        
        print(log_line.strip())
    
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
    
    def _add(self, device_id, log_line):
        """添加日志到缓存"""
        cache = self.cache.get(device_id, None)
        if cache is None:
            cache = []
            self.cache[device_id] = cache
        cache.append(log_line)
        # 限制缓存大小
        if len(cache) > self.MAX_CACHE_SIZE:
            cache.pop(0)
    
    def get(self, device_id=None):
        """获取缓存的日志"""
        if device_id:
            return self.cache.get(device_id, [])
        # 返回所有设备的缓存日志
        all_logs = []
        for logs in self.cache.values():
            all_logs.extend(logs)
        # 按时间戳排序
        all_logs.sort()
        return all_logs
    
    def _save(self, device_id):
        """将设备日志缓存保存到文件"""
        try:
            log_file = self.files.get(device_id)
            if log_file and device_id in self.cache:
                for line in self.cache[device_id]:
                    log_file.write(line)
                log_file.flush()
                # 清空缓存
                self.cache[device_id] = []
        except Exception as e:
            Log.ex(e, '保存日志缓存失败')
    
    def open(self, device_id):
        """打开设备日志文件"""
        try:
            # 关闭已存在的文件
            self.close(device_id)
            
            # 打开新文件
            timestamp = datetime.now()
            log_dir = Path(self._get_log_path(device_id))
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / f"{timestamp.strftime('%Y-%m-%d')}.log"
            
            log_file = open(log_path, 'a', encoding='utf-8', buffering=1)
            self.files[device_id] = log_file
            print(f'打开日志文件: {log_path}')
            
            # 初始化缓存
            self.cache[device_id] = []
            
        except Exception as e:
            Log.ex(e, '打开日志文件失败')
    
    def close(self, device_id):
        """关闭设备日志文件"""
        try:
            # 保存缓存
            self._save(device_id)
            
            # 关闭文件
            if device_id in self.files:
                self.files[device_id].close()
                del self.files[device_id]
                print(f'关闭日志文件: {device_id}')
                
        except Exception as e:
            Log.ex(e, '关闭日志文件失败')
