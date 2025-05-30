from datetime import datetime
from SDatabase import db
import _G

class DeviceModel(db.Model):
    """设备数据模型"""
    __tablename__ = 'devices'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True)  # 只保留name
    lastTime = db.Column(db.DateTime, default=datetime.now)
    score = db.Column(db.Integer, default=0)

    @classmethod
    def all(cls, dataCls: type):
        """获取所有设备记录"""
        try:
            from SDatabase import Database
            
            def load(db):
                datas = DeviceModel.query.all()
                return [dataCls(d.name) for d in datas]
                
            return Database.sql(load)
        except Exception as e:
            _G._G_.Log().ex(e, "获取所有设备记录失败")
            return []

    @classmethod
    def get(cls, params: dict, create: bool = False):
        """获取或创建设备记录"""
        name = params.get('name')
        session = db.session
        instance = session.query(cls).filter_by(name=name).first()
        if not instance and create:
            instance = cls(name=name)
            session.add(instance)
            session.commit()
        return instance

    def toDict(self):
        return {
            'id': self.id,
            'name': self.name,
            'score': self.score,
            'lastTime': self.lastTime.strftime('%Y-%m-%d %H:%M:%S') if self.lastTime else None
        }    
    
    
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
    state = db.Column(db.String(20), default='active')
    lastUpdate = db.Column(db.DateTime, default=datetime.now)

    @classmethod
    def from_device(cls, device):
        return cls(
            deviceId=device.device_id,
            appName=device.appName,
            totalScore=device.totalScore,
            income=device.income,
            state=device.state
        )
    

class TaskModel(db.Model):
    """任务数据模型"""
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deviceId = db.Column(db.BigInteger, nullable=False)  # 设备ID，关联 DeviceModel.id
    name = db.Column(db.String(50), nullable=False)
    time = db.Column(db.DateTime, default=datetime.now)
    endTime = db.Column(db.DateTime)
    score = db.Column(db.Integer, default=0)
    progress = db.Column(db.Float, default=0.0)
    state = db.Column(db.String(20))
    life = db.Column(db.Integer, default=0)

    @classmethod
    def get(cls, params: dict, create: bool = False):
        """获取或创建任务记录"""
        from SDatabase import Database
        
        def do_get(db):
            deviceId = params.get('deviceId')   
            name = params.get('name')
            date = params.get('date')
            instance = cls.query.filter_by(deviceId=deviceId, name=name, time=date).first()
            if not instance and create:
                instance = cls(deviceId=deviceId, name=name, time=date)
                db.session.add(instance)
                db.session.commit()
            return instance
            
        return Database.sql(do_get)


    def toDict(self):
        return {
            'id': self.id,
            'name': self.name,
            'deviceId': self.deviceId,
            'progress': self.progress,
            'date': self.time.strftime('%Y-%m-%d') if self.time else '',
            'state': self.state,
            'score': self.score,
            'life': self.life
        }
