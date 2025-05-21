from datetime import datetime
from SDatabase import db
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError

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
        _G._G_.Log().ex(e, "数据库事务执行失败")
        raise
    finally:
        db.session.remove()
