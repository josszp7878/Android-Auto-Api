from datetime import datetime
from flask_socketio import emit
from flask import current_app, has_request_context
from app import socketio
from .models import db, LogHistory

class Logger:
    # 日志级别常量
    LEVEL_INFO = 'I'
    LEVEL_WARNING = 'W'
    LEVEL_ERROR = 'E'

    @staticmethod
    def _log(source, message, level):
        """内部日志处理方法"""
        timestamp = datetime.now()
        
        # 保存到数据库
        log_entry = LogHistory(
            source=source,
            message=message,
            level=level,
            timestamp=timestamp
        )
        db.session.add(log_entry)
        db.session.commit()
        
        log_data = {
            'source': source,
            'message': message,
            'level': level,
            'timestamp': timestamp.isoformat()
        }
        
        # 在控制台打印
        level_text = {'I': 'INFO', 'W': 'WARN', 'E': 'ERROR'}[level]
        print(f"[{timestamp}] [{level_text}] {source}: {message}")
        
        # 发送到客户端
        try:
            socketio.emit('log_message', log_data, broadcast=True)
        except Exception as e:
            print(f"发送日志失败: {e}")

    @staticmethod
    def i(source, message):
        """输出信息级别日志"""
        Logger._log(source, message, Logger.LEVEL_INFO)

    @staticmethod
    def w(source, message):
        """输出警告级别日志"""
        Logger._log(source, message, Logger.LEVEL_WARNING)

    @staticmethod
    def e(source, message):
        """输出错误级别日志"""
        Logger._log(source, message, Logger.LEVEL_ERROR)

    @staticmethod
    def get_recent_logs(limit=100):
        """获取最近的日志"""
        return LogHistory.query.order_by(
            LogHistory.timestamp.desc()
        ).limit(limit).all()