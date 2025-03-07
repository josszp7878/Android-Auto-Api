from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
import _Log

class Database:
    """数据库管理类"""
    @classmethod
    def getDB(cls) -> SQLAlchemy:
        if hasattr(cls, '_db'):
            return cls._db
        # print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
        cls._db = SQLAlchemy()
        return cls._db
    
    @classmethod
    def commit(cls, obj=None):
        """安全的提交更改
        Args:
            obj: 可选，需要确保被跟踪的对象
        Returns:
            bool: 提交是否成功
        """
        try:
            db = cls.getDB()
            if obj is not None and obj not in db.session:
                # 只有当对象未被跟踪时才merge
                obj = db.session.merge(obj)
            db.session.commit()
            return True
        except Exception as e:
            _Log.Log_.ex(e, "数据库提交失败")
            db.session.rollback()
            return False
        
    @classmethod
    def init(cls, app):
        db = cls.getDB()
        """初始化数据库"""
        db.init_app(app)        
        # 导入所有模型以确保它们被注册
        import models
        with app.app_context():
            try:
                # 添加连接事件监听器来清除表缓存
                def on_connect(dbapi_con, connection_record):
                    with dbapi_con.cursor() as cursor:
                        cursor.execute('FLUSH TABLES')
                
                event.listen(db.engine, 'connect', on_connect)
                
                # 只创建不存在的表
                db.create_all()
                _Log.Log_.i("数据库初始化成功")
            except Exception as e:
                _Log.Log_.ex(e, "数据库初始化错误")
                raise


# 导出全局db实例
db = Database.getDB()
