from datetime import datetime
from SDatabase import db
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
import _Log

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

class AppModel(db.Model):
    __tablename__ = 'apps'
    id = db.Column(db.Integer, primary_key=True)
    deviceId = db.Column(db.String(50), nullable=False)
    appName = db.Column(db.String(100), nullable=False)
    totalScore = db.Column(db.Float, default=0.0)
    income = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='active')
    lastUpdate = db.Column(db.DateTime, default=datetime.now)

    @classmethod
    def from_device(cls, device):
        return cls(
            deviceId=device.device_id,
            appName=device.appName,
            totalScore=device.totalScore,
            income=device.income,
            status=device.status
        )

@contextmanager
def session_scope():
    """提供事务范围的会话，自动处理提交/回滚和异常"""
    try:
        yield db.session
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        _Log._Log_.ex(e, "数据库事务执行失败")
        raise
    finally:
        db.session.remove()

# 移除这里的示例代码
# with session_scope() as session:
#     # 使用 session 进行数据库操作
#     pass

