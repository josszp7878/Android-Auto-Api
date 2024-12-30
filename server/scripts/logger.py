from datetime import datetime
from pathlib import Path

class Log:
    """简单的日志处理类"""
    _instance = None
    LOG_DIR = "logs"
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
            cls._instance.log_file = None
        return cls._instance
    
    def __init__(self):
        if not self.initialized:
            self._open_log_file()
            self.initialized = True
    
    def __del__(self):
        self._close_log_file()
    
    def _open_log_file(self):
        """打开日志文件"""
        try:
            if self.log_file:
                self.log_file.close()
            
            timestamp = datetime.now()
            log_dir = Path(self.LOG_DIR)
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / f"{timestamp.strftime('%Y-%m-%d')}.log"
            
            self.log_file = open(log_path, 'a', encoding='utf-8', buffering=1)
            print(f'打开日志文件: {log_path}')
        except Exception as e:
            print(f'打开日志文件失败: {e}')
            self.log_file = None
    
    def _close_log_file(self):
        """关闭日志文件"""
        try:
            if self.log_file:
                self.log_file.flush()
                self.log_file.close()
                self.log_file = None
                print('关闭日志文件')
        except Exception as e:
            print(f'关闭日志文件失败: {e}')
    
    def _log(self, message, level='i', source=None):
        """内部日志处理方法"""
        timestamp = datetime.now()
        log_line = f"[{timestamp}] [{level}] {source}: {message}\n"
        
        # 写入日志文件
        try:
            if self.log_file:
                self.log_file.write(log_line)
                self.log_file.flush()
        except Exception as e:
            print(f'写入日志失败: {e}')
            
        # 打印到控制台
        # print(log_line.strip())
        
        # 发送到服务器
        try:
            from CDevice import CDevice
            device = CDevice()
            if device and device.connected:
                device.send_log(message, level)
        except Exception as e:
            print(f'发送日志到服务器失败: {e}')
    
    @classmethod
    def i(cls, message, tag=None):
        """输出信息级别日志"""
        Log()._log(message, 'i', tag)
    
    @classmethod
    def w(cls, message,tag=None):
        """输出警告级别日志"""
        Log()._log(message, 'w', tag)
    
    @classmethod
    def e(cls, message,tag=None):
        """输出错误级别日志"""
        Log()._log(message, 'e', tag) 
        
    # @classmethod
    # def d(cls, message,tag=None):
    #     """输出调试级别日志"""
    #     Log()._log(message, 'd', tag) 
