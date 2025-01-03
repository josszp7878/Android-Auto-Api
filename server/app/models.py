from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class DeviceModel(db.Model):
    """设备数据模型"""
    __tablename__ = 'devices'
    
    device_id = db.Column(db.String(50), primary_key=True)
    status = db.Column(db.String(20), default='offline')
    last_seen = db.Column(db.DateTime, default=datetime.now)
    info = db.Column(db.JSON)

    def __repr__(self):
        return f'<Device {self.device_id}>'

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

