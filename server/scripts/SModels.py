from datetime import datetime
from SDatabase import db, Database
import _G
import sqlalchemy

class SModel_:
    """基础模型类，只支持('type', default) tuple字段声明"""
    def __init__(self, table: str, fields: dict = None, pk: str = 'id'):
        self.table = table
        self.fields = self._normalizeFields(fields or {})
        self.pk = pk

    def _normalizeFields(self, fields):
        new_fields = {}
        for k, v in fields.items():
            if isinstance(v, tuple) and len(v) == 2:
                new_fields[k] = {'type': v[0], 'default': v[1]}
            else:
                raise ValueError(f"字段{repr(k)}的定义必须为('type', default) tuple")
        return new_fields

    def _fillDefaults(self, data: dict, skip_pk=True):
        # 自动补齐未传字段，优先用fields的default
        result = {}
        for k, v in self.fields.items():
            if skip_pk and k == self.pk:
                continue
            if k in data:
                result[k] = data[k]
            elif 'default' in v:
                d = v['default']
                result[k] = d() if callable(d) else d
            else:
                result[k] = None
        return result

    def genInsertSql(self):
        keys = [k for k in self.fields if k != self.pk]
        columns = ', '.join(keys)
        values = ', '.join([f':{k}' for k in keys])
        return f"INSERT INTO {self.table} ({columns}) VALUES ({values})"

    def genUpdateSql(self):
        keys = [k for k in self.fields if k != self.pk]
        setStr = ', '.join([f"{k} = :{k}" for k in keys])
        return f"UPDATE {self.table} SET {setStr} WHERE {self.pk} = :{self.pk}"

    def genSelectSql(self):
        columns = ', '.join(self.fields.keys())
        return f"SELECT {columns} FROM {self.table}"

    def all(self, date: datetime = None, where: str = None):
        try:
            sql = self.genSelectSql()
            params = {}
            if date and 'time' in self.fields:
                sql += " WHERE date(time) = :date"
                if isinstance(date, datetime):
                    date = date.strftime('%Y-%m-%d')
                params['date'] = date
            if where:
                sql += f" AND {where}"
            log = _G._G_.Log()
            # log.i_(f'获取所有记录jjj: {sql}, {params}')
            result = db.session.execute(sql, params)
            return [self.toDict(row) for row in result.fetchall()]
        except Exception as e:
            _G._G_.Log().ex(e, f"获取所有记录失败: {self.table}")
            return []

    def insert(self, data: dict):
        try:
            data = self._fillDefaults(data)
            sql = self.genInsertSql()
            db.session.execute(sql, data)
            db.session.commit()
            return True
        except Exception as e:
            _G._G_.Log().ex(e, f"插入数据失败: {self.table}")
            db.session.rollback()
            return False

    def update(self, data: dict):
        try:
            data = self._fillDefaults(data, skip_pk=False)
            sql = self.genUpdateSql()
            db.session.execute(sql, data)
            db.session.commit()
            return True
        except Exception as e:
            _G._G_.Log().ex(e, f"更新数据失败: {self.table}")
            db.session.rollback()
            return False

    def toDict(self, row):
        if not row:
            return None
        data = dict(row)
        for k, v in data.items():
            if isinstance(v, datetime):
                data[k] = v.strftime('%Y-%m-%d %H:%M:%S')
        return data

class DeviceModel_:
    """设备数据模型（自动SQL实现）"""
    table = 'devices'
    fields = {
        'id': ('int', None),
        'name': ('str', ''),
        'score': ('int', 0),
        'lastTime': ('datetime', lambda: datetime.now()),
    }
    model = SModel_(table, fields)

    @classmethod
    def all(cls, date: datetime = None):
        return cls.model.all(date)

    @classmethod
    def get(cls, name: str, create: bool = False):
        try:
            sql = cls.model.genSelectSql() + " WHERE name = :name"
            result = db.session.execute(sql, {'name': name})
            row = result.fetchone()
            if not row and create:
                data = {'name': name}
                cls.model.insert(data)
                result = db.session.execute(sql, {'name': name})
                row = result.fetchone()
            return cls.model.toDict(row) if row else None
        except Exception as e:
            _G._G_.Log().ex(e, f"获取或创建设备记录失败: {cls.table}")
            return None

    @classmethod
    def commit(cls, data: dict):
        try:
            name = data.get('name')
            sql = f"SELECT id FROM {cls.table} WHERE name = :name"
            result = db.session.execute(sql, {'name': name})
            row = result.fetchone()
            if row:
                data['id'] = row['id']
                return cls.model.update(data)
            else:
                return cls.model.insert(data)
        except Exception as e:
            _G._G_.Log().ex(e, "提交设备数据失败")
            db.session.rollback()
            return False

# class EarningRecordModel_:
#     """收益记录表（自动SQL实现）"""
#     table = 'earnings'
#     fields = {
#         'id': ('int', None),
#         'deviceId': ('str', None),
#         'appName': ('str', None),
#         'earnType': ('str', None),
#         'amount': ('float', 0.0),
#         'time': ('datetime', lambda: datetime.now())
#     }
#     model = SModel_(table, fields)

#     @classmethod
#     def all(cls, date: datetime = None, where: str = None):
#         return cls.model.all(date, where)

#     @classmethod
#     def get(cls, deviceId: str, appName: str, earnType: str, date: datetime = None, create: bool = False):
#         try:
#             date = date or datetime.now()
#             date_str = date.strftime('%Y-%m-%d')
#             sql = cls.model.genSelectSql() + " WHERE deviceId = :deviceId AND appName = :appName AND earnType = :earnType AND DATE(time) = :date"
#             params = {'deviceId': deviceId, 'appName': appName, 'earnType': earnType, 'date': date_str}
#             result = db.session.execute(sql, params)
#             row = result.fetchone()
#             if not row and create:
#                 data = {'deviceId': deviceId, 'appName': appName, 'earnType': earnType, 'time': datetime.now()}
#                 cls.model.insert(data)
#                 result = db.session.execute(sql, params)
#                 row = result.fetchone()
#             return cls.model.toDict(row) if row else None
#         except Exception as e:
#             _G._G_.Log().ex(e, "获取收益记录失败")
#             return None

#     @classmethod
#     def commit(cls, data: dict):
#         return cls.model.update(data)

# class AppModel(db.Model):
#     __tablename__ = 'apps'
#     id = db.Column(db.Integer, primary_key=True)
#     deviceId = db.Column(db.String(50), nullable=False)
#     appName = db.Column(db.String(100), nullable=False)
#     totalScore = db.Column(db.Float, default=0.0)
#     income = db.Column(db.Float, default=0.0)
#     state = db.Column(db.String(20), default='active')
#     lastUpdate = db.Column(db.DateTime, default=datetime.now)

#     @classmethod
#     def from_device(cls, device):
#         return cls(
#             deviceId=device.device_id,
#             appName=device.appName,
#             totalScore=device.totalScore,
#             income=device.income,
#             state=device.state
#         )
    

class TaskModel_:
    """任务数据模型（自动SQL实现）"""
    table = 'tasks'
    fields = {
        'id': ('int', None),
        'deviceId': ('str', None),
        'name': ('str', None),
        'time': ('datetime', lambda: datetime.now()),
        'progress': ('int', 0.0),
        'state': ('str', 'idle'),
        'score': ('int', 0),
        'life': ('int', 0)
    }
    model = SModel_(table, fields)

    @classmethod
    def all(cls, date: datetime = None, where: str = None):
        return cls.model.all(date, where)

    @classmethod
    def get(cls, deviceId: str, name: str, date: datetime = None, create: bool = False):
        log = _G._G_.Log()
        try:
            if not date:
                date = datetime.now()
            date_str = date.strftime('%Y-%m-%d')
            sql = cls.model.genSelectSql() + " WHERE deviceId = :deviceId AND name = :name AND DATE(time) = :date"
            params = {'deviceId': deviceId, 'name': name, 'date': date_str}
            result = db.session.execute(sql, params)
            row = result.fetchone()
            if not row and create:
                data = {'deviceId': deviceId, 'name': name, 'time': date}
                cls.model.insert(data)
                result = db.session.execute(sql, params)
                row = result.fetchone()
                # log.i_(f"创建任务: {data}, result: {row}")
            return cls.model.toDict(row) if row else None
        except Exception as e:
            log.ex(e, "获取任务记录失败")
            return None

    @classmethod
    def commit(cls, data: dict):
        return cls.model.update(data)

class LogModel_:
    """日志数据模型（自动SQL实现）"""
    table = 'logs'
    fields = {
        'id': ('int', None),
        'level': ('str', 'i'),
        'message': ('str', ''),
        'time': ('datetime', lambda: datetime.now()),
        'tag': ('str', None)
    }
    model = SModel_(table, fields)

    @classmethod
    def all(cls, date: datetime = None):
        return cls.model.all(date)

    @classmethod
    def get(cls, message: str, tag: str = None, level: str = 'i', create: bool = False):
        def db_operation(db):
            try:
                sql = cls.model.genSelectSql() + \
                      " WHERE message=:message AND level=:level AND (tag=:tag OR (:tag IS NULL AND tag IS NULL))"
                params = {'message': message, 'tag': tag, 'level': level}
                result = db.session.execute(sql, params)
                row = result.fetchone()
                if not row and create:
                    data = {'level': level, 'message': message, 'tag': tag}
                    cls.model.insert(data)
                    db.session.expire_all()
                    result = db.session.execute(sql, params)
                    row = result.fetchone()
                return cls.model.toDict(row) if row else None
            except Exception as e:
                print(f"数据库操作异常: {str(e)}")
                return None
        return Database.sql(db_operation)

    @classmethod
    def commit(cls, data: dict):
        return cls.model.update(data)
