from SDatabase import Database
from datetime import datetime
from SModels import SModel_

class LogModel_():
    """日志数据模型（SQL实现）"""
    table = 'logs'
    model = SModel_(table)
    
    @classmethod
    def all(cls, date: datetime = None):
        """获取所有日志记录""" 
        return cls.model.all(date)

    @classmethod
    def get(
        cls, 
        message: str, 
        tag: str = None, 
        level: str = 'i', 
        create: bool = False
    ):
        """获取或创建日志记录（增加插入后验证）"""
        # print(f'获取或创建日志记录: {message}, {tag}, {level}, {create}')
        def db_operation(db):
            try:
                sql = f"""SELECT * FROM {cls.table} 
                      WHERE message=:message 
                      AND level=:level
                      AND (tag=:tag OR (:tag IS NULL AND tag IS NULL))"""
                params = {'message': message, 'tag': tag, 'level': level}
                result = db.session.execute(sql, params)
                row = result.fetchone()
                # print(f'获取或创建日志记录: {row}')
                if not row and create:
                    insert_sql = f"""INSERT INTO {cls.table} 
                                  (level, message, time, tag)
                                  VALUES 
                                  (:level, :message, :time, :tag)"""
                    time = datetime.now()
                    db.session.execute(insert_sql, {
                        'level': level,
                        'message': message,
                        'time': time,
                        'tag': tag
                    })
                    # print(f"插入影响行数: {insert_result.rowcount}")  # 调试插入结果
                    db.session.commit()
                    db.session.expire_all()  # 强制刷新会话缓存
                    result = db.session.execute(sql, params)
                    if result is None:
                        #print(f"新建记录失败@@@: result={result}, sql={sql}, params={params}")
                        return None
                    row = result.fetchone()
                    if not row:
                        # print("新建记录后查询失败22222")
                        return None
                data = cls.model.toDict(row) if row else None
                # print(f'获取或创建日志记录: {data}')
                return data
            except Exception as e:
                print(f"数据库操作异常: {str(e)}")
                return None
        
        return Database.sql(db_operation)

    @classmethod
    def commit(cls, data: dict):
        """提交日志数据"""
        try:
            update_sql = f"""UPDATE {cls.table} SET
                          level=:level,
                          message=:message,
                          time=:time,
                          tag=:tag
                        WHERE id=:id"""
            Database.sql(lambda db: db.session.execute(update_sql, data))
            return True
        except Exception as e:
            print("更新日志失败")
            return False
