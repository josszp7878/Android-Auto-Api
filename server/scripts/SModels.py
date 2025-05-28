from datetime import datetime
from SDatabase import db
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
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
    def get(cls, params: dict, create=False):
        """获取或创建设备记录"""
        name = params.get('name')
        instance = cls.query.filter_by(name=name).first()
        if not instance and create:
            instance = cls(name=name)
            db.session.add(instance)
            db.session.commit()
        return instance

    def toDict(self):
        return {
            'id': self.id,
            'name': self.name,
            'score': self.score,
            'lastTime': self.lastTime.strftime('%Y-%m-%d %H:%M:%S') if self.lastTime else None
        }    
    
    def commit(self, data: dict):
        """提交数据更新"""
        from SDatabase import Database
        
        def _commit(db):
            try:
                session = db.session
                # 通过ID获取最新数据
                model = DeviceModel.query.get(self.id)
                
                if not model:
                    return False
                # 更新字段
                model.name = data.get('name', model.name)
                if 'score' in data:
                    model.score = data['score']
                
                # 处理时间字段
                last_time = data.get('lastTime')
                if last_time:
                    if isinstance(last_time, str):
                        model.lastTime = datetime.strptime(last_time, '%Y-%m-%d %H:%M:%S')
                    else:
                        model.lastTime = last_time

                session.commit()
                return True
            except Exception as e:
                print(f"数据库提交失败: {str(e)}")
                session.rollback()
                return False

        try:
            return Database.sql(_commit)
        except Exception as e:
            _G._G_.Log().ex(e, "提交数据更新失败")
            return False

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
    deviceId = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    time = db.Column(db.DateTime, default=datetime.now)
    endTime = db.Column(db.DateTime)
    score = db.Column(db.Integer, default=0)
    progress = db.Column(db.Float, default=0.0)
    state = db.Column(db.String(20))
    life = db.Column(db.Integer, default=0)

    @classmethod
    def get(cls, params: dict, create=False):
        """获取或创建任务记录"""
        deviceId = params.get('deviceId')   
        name = params.get('name')
        instance = cls.query.filter_by(deviceId=deviceId, name=name).first()
        if not instance and create:
            instance = cls(deviceId=deviceId, name=name)
            db.session.add(instance)
            db.session.commit()
        return instance

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

    def commit(self, data: dict) -> bool:
        """提交数据更新"""
        try:
            for key, value in data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            db.session.commit()
            return True
        except Exception as e:
            _G._G_.Log().ex(e, '提交数据失败')
            return False

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
