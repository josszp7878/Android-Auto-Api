from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
import _G

class Database:
    """数据库管理类"""
    _db = None
    app: Flask = None
    
    @classmethod
    def getDB(cls) -> SQLAlchemy:
        if cls._db is None:
            cls._db = SQLAlchemy()
        return cls._db
    
      
    @classmethod
    def sql(cls, dbFun):
        """在Flask应用上下文中执行数据库操作
        Args:
            dbFun: 数据库操作函数，接收db参数
        Returns:
            操作结果
        """
        try:
            # 检查app_context是否已设置
            if cls.app is None:
                _G._G_.Log().w("数据库操作需要Flask应用上下文，但未设置")
                return None
                
            # 在应用上下文中执行
            with cls.app.app_context():
                db = cls.getDB()
                result = dbFun(db)
                return result
        except Exception as e:
            _G._G_.Log().ex(e, "数据库操作失败")
            if hasattr(cls._db, "session"):
                cls._db.session.rollback()
            return None
        
    @classmethod
    def delete(cls, obj=None):
        """删除对象"""
        try:
            db = cls.getDB()
            db.session.delete(obj)
            db.session.commit()
            return True
        except Exception as e:
            _G._G_.Log().ex(e, "数据库删除失败")
            db.session.rollback()
            return False

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
            _G._G_.Log().ex(e, "数据库提交失败")
            db.session.rollback()
            return False
        
    @classmethod
    def init(cls, app: Flask):
        db = cls.getDB()
        cls.app = app
        """初始化数据库"""
        db.init_app(app)        
        # 导入所有模型以确保它们被注册
        import SModels
        # 在应用上下文中创建所有不存在的表
        with app.app_context():
            # 添加连接事件监听器来清除表缓存
            def on_connect(dbapi_con, connection_record):
                with dbapi_con.cursor() as cursor:
                    cursor.execute('FLUSH TABLES')
            
            event.listen(db.engine, 'connect', on_connect)
            
            # 只创建不存在的表
            db.create_all()


# 导出全局db实例
db = Database.getDB()
