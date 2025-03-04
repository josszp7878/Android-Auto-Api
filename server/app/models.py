from datetime import datetime
from Database import db

class DeviceModel(db.Model):
    """设备数据模型"""
    __tablename__ = 'devices'
    
    device_id = db.Column(db.String(50), primary_key=True)
    status = db.Column(db.String(20), default='offline')
    info = db.Column(db.JSON)
    last_seen = db.Column(db.DateTime, default=datetime.now)

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

class EarningRecord(db.Model):
    """收益记录表"""
    __tablename__ = 'earnings'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deviceId = db.Column(db.String(50), db.ForeignKey('devices.device_id'), nullable=False)
    appName = db.Column(db.String(50), nullable=False)
    earnType = db.Column(db.String(20), nullable=False)  # score或cash
    amount = db.Column(db.Float, nullable=False)  # 收益数量
    time = db.Column(db.DateTime, default=datetime.now)  # 收益时间
    
    def to_dict(self):
        return {
            'id': self.id,
            'deviceId': self.deviceId,
            'appName': self.appName,
            'earnType': self.earnType,
            'amount': self.amount,
            'time': self.time.strftime('%Y-%m-%d %H:%M:%S')
        }

