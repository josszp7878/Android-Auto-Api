from flask import Flask
from flask_sqlalchemy import SQLAlchemy
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
        """在Flask应用上下文中执行数据库操作"""
        try:
            if cls.app is None:
                raise RuntimeError("未初始化Flask应用")
                
            with cls.app.app_context():
                db = cls.getDB()
                return dbFun(db)
        except Exception as e:
            print(f"数据库上下文异常: {str(e)}")
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
            print(f"数据库删除失败: {str(e)}")
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
            print(f"数据库提交失败: {str(e)}")
            db.session.rollback()
            return False
        
    @classmethod
    def init(cls, app: Flask)->bool:
        """初始化数据库"""
        log = _G._G_.Log()
        try:
            cls.app = app
            db = cls.getDB()
            db.init_app(app)
            with app.app_context():
                db.create_all()
            return True
        except Exception as e:
            log.e(f"error: 数据库连接失败 {e}")
            return False


# 导出全局db实例
db = Database.getDB()

