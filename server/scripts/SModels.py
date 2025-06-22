from datetime import datetime, timedelta
from SDatabase import Database, db
import _G


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

    def _fillDefaults(self, data: dict):
        # 自动补齐未传字段，优先用fields的default
        result = {}
        for k, v in self.fields.items():
            if k in data:
                result[k] = data[k]
            elif 'default' in v and v['default'] is not None:
                # 只有当default不为None时才设置缺省值
                d = v['default']
                result[k] = d() if callable(d) else d
            # 如果default为None，则不设置该字段
        return result

    def genInsertSql(self, data: dict):
        keys = list(data.keys())
        columns = ', '.join(keys)
        values = ', '.join([f':{k}' for k in keys])
        return f"INSERT INTO {self.table} ({columns}) VALUES ({values})"

    def genUpdateSql(self, data: dict):
        keys = [k for k in data.keys() if k != self.pk]
        setStr = ', '.join([f"{k} = :{k}" for k in keys])
        return f"UPDATE {self.table} SET {setStr} WHERE {self.pk} = :{self.pk}"

    def genSelectSql(self):
        columns = ', '.join(self.fields.keys())
        return f"SELECT {columns} FROM {self.table}"

    def load(self, date: datetime = None, where: str = None):
        def db_operation(db):
            nonlocal date, where
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
                result = db.session.execute(sql, params)
                return [self.toDict(row) for row in result.fetchall()]
            except Exception as e:
                _G._G_.Log().ex_(e, f"获取所有记录失败: {self.table}")
                return []
        return Database.sql(db_operation)

    def _insert(self, data: dict):
        def db_operation(db):
            nonlocal data
            try:
                data = self._fillDefaults(data)
                sql = self.genInsertSql(data)
                # print(f'sql: {sql}')
                db.session.execute(sql, data)
                db.session.commit()
                # print(f'insertddddd: {data}')
                return True
            except Exception as e:
                _G._G_.Log().ex_(e, f"插入数据失败: {self.table}")
                db.session.rollback()
                return False
        return Database.sql(db_operation)

    def update(self, data: dict):
        def db_operation(db):
            nonlocal data
            try:
                data = self._fillDefaults(data)
                sql = self.genUpdateSql(data)
                db.session.execute(sql, data)
                db.session.commit()
                return True
            except Exception as e:
                _G._G_.Log().ex_(e, f"更新数据失败: {self.table}")
                db.session.rollback()
                return False
        return Database.sql(db_operation)
    
    def commit(self, data: dict):
        def db_operation(db):
            nonlocal data
            try:
                sql = f"SELECT id FROM {self.table} WHERE id = :id"
                id = data.get('id')
                if id:
                    result = db.session.execute(sql, {'id': id})
                    row = result.fetchone()
                    if row:
                        return self.update(data)
                print(f'insert: {data}')
                return self._insert(data)
            except Exception as e:
                _G._G_.Log().ex_(e, "提交设备数据失败")
                db.session.rollback()
                return False
        return Database.sql(db_operation)


    def save(self, data: dict):
        return self._insert(data)

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
        'lastTime': ('datetime', lambda: datetime.now())
    }
    model = SModel_(table, fields)

    @classmethod
    def all(cls, date: datetime = None):
        return cls.model.load(date)

    @classmethod
    def get(cls, name: str, create: bool = False):
        def db_operation(db):
            nonlocal name
            try:
                sql = cls.model.genSelectSql() + " WHERE name = :name"
                result = db.session.execute(sql, {'name': name})
                row = result.fetchone()
                if not row and create:
                    data = {'name': name}
                    cls.model._insert(data)
                    result = db.session.execute(sql, {'name': name})
                    row = result.fetchone()
                return cls.model.toDict(row) if row else None
            except Exception as e:
                _G._G_.Log().ex_(e, f"获取或创建设备记录失败: {cls.table}")
                return None
        return Database.sql(db_operation)

    @classmethod
    def commit(cls, data: dict):
        return cls.model.commit(data)


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
        return cls.model.load(date, where)

    @classmethod
    def get(cls, deviceId: str, name: str, date: datetime = None,
            create: bool = False):
        def db_operation(db):
            nonlocal deviceId, name, date, create
            log = _G._G_.Log()
            try:
                if not date:
                    date = datetime.now()
                date_str = date.strftime('%Y-%m-%d')
                sql = (cls.model.genSelectSql() +
                       " WHERE deviceId = :deviceId AND name = :name AND "
                       "DATE(time) = :date")
                params = {'deviceId': deviceId, 'name': name, 'date': date_str}
                result = db.session.execute(sql, params)
                row = result.fetchone()
                if not row and create:
                    data = {'deviceId': deviceId, 'name': name, 'time': date}
                    cls.model._insert(data)
                    result = db.session.execute(sql, params)
                    row = result.fetchone()
                return cls.model.toDict(row) if row else None
            except Exception as e:
                log.ex_(e, "获取任务记录失败")
                return None
        return Database.sql(db_operation)

    @classmethod
    def commit(cls, data: dict):
        return cls.model.commit(data)

