from SDatabase import db
from datetime import datetime

class LogModel_(db.Model):
    """日志数据模型"""
    __tablename__ = 'logs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    time = db.Column(db.DateTime, default=datetime.now)
    tag = db.Column(db.String(50))
    level = db.Column(db.String(10))
    message = db.Column(db.Text)
    
    def toDict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'date': self.time.strftime('%Y-%m-%d') if self.time else '',
            'time': self.time.strftime('%H:%M:%S') if self.time else '',
            'tag': self.tag,
            'level': self.level,
            'message': self.message,
        }
    
    @classmethod
    def add(cls, message, tag=None, level='i')->dict:
        """添加日志记录"""
        from SDatabase import Database
        def do_add(db):
            session = db.session
            time = datetime.now()
            instance = session.query(cls).filter_by(message=message, tag=tag, level=level, time=time).first()
            if not instance:
                instance = cls(message=message, tag=tag, level=level, time=time)
                session.add(instance)
                session.commit()
            return instance.toDict()
        return Database.sql(do_add)