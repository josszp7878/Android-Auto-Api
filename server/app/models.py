from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class DeviceModel(db.Model):
    """设备数据模型"""
    __tablename__ = 'devices'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(64), unique=True, nullable=False)
    status = db.Column(db.String(20), default='offline')
    last_seen = db.Column(db.DateTime, default=datetime.now)
    info = db.Column(db.JSON)
    
    def to_dict(self):
        return {
            'status': self.status,
            'last_seen': self.last_seen,
            'info': self.info or {}
        }

    @staticmethod
    def from_device(device):
        """从Device对象创建数据库记录"""
        return DeviceModel(
            device_id=device.device_id,
            status=device.status,
            last_seen=device.last_seen,
            info=device.info
        ) 

class LogHistory(db.Model):
    """日志历史记录"""
    __tablename__ = 'log_history'
    
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(64), nullable=False)  # 日志来源
    message = db.Column(db.Text, nullable=False)  # 日志内容
    level = db.Column(db.String(20), default='info')  # 日志级别
    timestamp = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'source': self.source,
            'message': self.message,
            'level': self.level,
            'timestamp': self.timestamp.isoformat()  # 转换为 ISO 格式字符串
        } 