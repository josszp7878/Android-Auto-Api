from pathlib import Path
from datetime import datetime

class Log:
    """统一的日志处理类"""
    LOG_DIR = "logs"
    
    @staticmethod
    def get_log_path(device_id=None):
        """获取日志文件路径"""
        log_dir = Path(Log.LOG_DIR)
        if device_id:
            log_dir = log_dir / device_id
        log_dir.mkdir(parents=True, exist_ok=True)
        
        today = datetime.now().strftime('%Y-%m-%d')
        return log_dir / f"{today}.log"

    @staticmethod
    def _log(level, source, message):
        """内部日志处理方法"""
        timestamp = datetime.now()
        log_line = f"[{timestamp}] [{level}] {source}: {message}\n"
        
        # 写入日志文件
        log_path = Log.get_log_path('server' if source == 'Server' else source)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_line)
        
        # 打印到控制台
        print(log_line.strip())
        
        # 发送到客户端
        from app import socketio
        try:
            socketio.emit('log_message', {
                'source': source,
                'message': message,
                'level': level,
                'timestamp': timestamp.isoformat()
            })
        except Exception as e:
            print(f"发送日志失败: {e}")

    @staticmethod
    def i(source, message):
        """输出信息级别日志"""
        Log._log('INFO', source, message)

    @staticmethod
    def w(source, message):
        """输出警告级别日志"""
        Log._log('WARN', source, message)

    @staticmethod
    def e(source, message):
        """输出错误级别日志"""
        Log._log('ERROR', source, message)

    @staticmethod
    def read_logs(date=None, device_id=None):
        """读取指定日期的日志"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
            
        log_path = Log.get_log_path('server' if device_id == 'server' else device_id)
        if not log_path.exists():
            return []
            
        with open(log_path, 'r', encoding='utf-8') as f:
            logs = f.readlines()
            
        # 按时间戳排序
        def get_timestamp(log_line):
            try:
                # 提取时间戳部分 [2023-12-31 12:34:56.789]
                timestamp_str = log_line[1:log_line.index(']')]
                return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
            except:
                return datetime.min
            
        logs.sort(key=get_timestamp)
        return logs

def log_to_db(source, message, level='info'):
    # 移除数据库日志记录功能
    pass