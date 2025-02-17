from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc, event, text
from scripts.logger import Log

# 创建全局 db 实例
db = SQLAlchemy()

def init_db(app):
    """初始化数据库"""
    db.init_app(app)
    
    # 导入所有模型以确保它们被注册
    from . import models, stask
    
    # 在应用上下文中创建所有表
    with app.app_context():
        try:
            # 添加连接事件监听器来清除表缓存
            def on_connect(dbapi_con, connection_record):
                with dbapi_con.cursor() as cursor:
                    cursor.execute('FLUSH TABLES')
            
            event.listen(db.engine, 'connect', on_connect)
            
            # 只创建不存在的表
            db.create_all()
            print("数据库初始化成功")
        except Exception as e:
            print(f"数据库初始化错误: {e}")
            raise

def commit(data, add=False):
    """安全的提交数据库更改"""
    session = db.session
    try:
        if add:
            session.add(data)
        else:
            session.merge(data)           
        session.commit()
    except exc.OperationalError as e:
        Log.e(f"数据库操作错误: {e}")
        session.rollback()
        # 尝试重新连接
        try:
            db.engine.connect()
            session.commit()
        except Exception as e2:
            Log.ex(e2, "数据库重连失败")
            raise
    except Exception as e1:
        Log.ex(e1, "数据库提交失败")
        session.rollback()
        raise
