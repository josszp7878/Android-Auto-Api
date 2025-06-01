from datetime import datetime
from SDatabase import db
import _G

class SModel_:
    """基础模型类"""
    def __init__(self, table: str):
        self.table = table

    def all(self, date: datetime = None):
        """获取所有任务记录"""
        try:
            sql = f"SELECT * FROM {self.table}"
            if date:
                sql += " WHERE date(time) = :date"
            result = db.session.execute(sql, {'date': date})
            return [self.toDict(row) for row in result.fetchall()]
        except Exception as e:
            _G._G_.Log().ex(e, f"获取所有任务记录失败: {self.table}")
            return []
    
    def toDict(self, row):
        """转换为字典格式（增加空值保护）"""
        if not row:
            return None
        data = dict(row)
        # print(f'转换为字典格式: {data}')
        # 转换所有datetime字段
        for k, v in data.items():
            if isinstance(v, datetime):
                data[k] = v.strftime('%Y-%m-%d %H:%M:%S')
        return data

        

class DeviceModel():
    """设备数据模型（直接SQL实现）"""
    table = 'devices'
    model = SModel_(table)

    @classmethod
    def all(cls, date: datetime = None):
        """获取所有设备"""
        return cls.model.all(date)

    @classmethod
    def get(cls, name: str, create: bool = False):
        try:
            sql = f"SELECT * FROM {cls.table} WHERE name = :name"
            result = db.session.execute(sql, {'name': name})
            row = result.fetchone()
            if not row and create:
                # 创建新设备
                now = datetime.now()
                sql = f"INSERT INTO {cls.table} (name, lastTime, score) VALUES (:name, :lastTime, :score)"
                db.session.execute(sql, {'name': name, 'lastTime': now, 'score': 0})
                db.session.commit()
                # 再查一次
                result = db.session.execute(sql, {'name': name})
                row = result.fetchone()
            return cls.model.toDict(row) if row else None
        except Exception as e:
            _G._G_.Log().ex(e, f"获取或创建设备记录失败: {cls.table}")
            return None
        
    @classmethod
    def commit(cls, data: dict):
        """插入或更新设备数据"""
        try:
            name = data.get('name')
            score = data.get('score', 0)
            lastTime = data.get('lastTime', datetime.now())
            # 先查是否存在
            sql = f"SELECT id FROM {cls.table} WHERE name = :name"
            result = db.session.execute(sql, {'name': name})
            row = result.fetchone()
            if row:
                # 存在则更新
                sql = f"UPDATE {cls.table} SET score = :score, lastTime = :lastTime WHERE name = :name"
                db.session.execute(sql, {'score': score, 'lastTime': lastTime, 'name': name})
            else:
                # 不存在则插入
                sql = f"INSERT INTO {cls.table} (name, score, lastTime) VALUES (:name, :score, :lastTime)"
                db.session.execute(sql, {'name': name, 'score': score, 'lastTime': lastTime})
            db.session.commit()
            return True
        except Exception as e:
            _G._G_.Log().ex(e, "提交设备数据失败")
            db.session.rollback()
            return False

    # @classmethod
    # def toDict(cls, row):
    #     return {
    #         'id': row.id,
    #         'name': row.name,
    #         'score': row.score,
    #         'lastTime': row.lastTime.strftime('%Y-%m-%d %H:%M:%S') if row.lastTime else None
    #     }

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
    

class TaskModel:
    """任务数据模型（直接SQL实现）"""
    table = 'tasks'
    model = SModel_(table)

    @classmethod
    def all(cls, date: datetime = None):
        """获取所有任务记录"""
        return cls.model.all(date)


    @classmethod
    def get(cls, deviceId: str, name: str, date: datetime = None, create: bool = False):
        """获取或创建任务记录"""
        try:
            date = date or datetime.now()
            # 查询现有记录
            sql = f"""SELECT * FROM {cls.table} 
                   WHERE deviceId = :deviceId 
                     AND name = :name 
                     AND time = :date"""
            result = db.session.execute(sql, {
                'deviceId': deviceId,
                'name': name,
                'date': date
            })
            row = result.fetchone()
            
            if not row and create:
                # 创建新任务
                now = datetime.now()
                insert_sql = f"""INSERT INTO {cls.table} 
                              (deviceId, name, time, progress, state, score)
                              VALUES 
                              (:deviceId, :name, :time, 0.0, 'pending', 0)"""
                db.session.execute(insert_sql, {
                    'deviceId': deviceId,
                    'name': name,
                    'time': date or now
                })
                db.session.commit()
                # 重新查询新记录
                result = db.session.execute(sql, {
                    'deviceId': deviceId,
                    'name': name,
                    'date': date
                })
                row = result.fetchone()
            
            return cls.model.toDict(row) if row else None
        except Exception as e:
            _G._G_.Log().ex(e, "获取任务记录失败")
            return None

    @classmethod
    def commit(cls, data: dict):
        """提交任务数据"""
        try:
            update_sql = f"""UPDATE {cls.table} SET
                          progress = :progress,
                          state = :state,
                          score = :score,
                          endTime = :endTime
                        WHERE id = :id"""
            db.session.execute(update_sql, data)
            db.session.commit()
            return True
        except Exception as e:
            _G._G_.Log().ex(e, "提交任务数据失败")
            db.session.rollback()
            return False