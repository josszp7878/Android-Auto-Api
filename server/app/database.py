from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc, event, text
from scripts.logger import Log
from flask import current_app

# 创建全局 db 实例
db = SQLAlchemy()

def init_db(app):
    """初始化数据库"""
    db.init_app(app)
    
    # 导入所有模型以确保它们被注册
    from . import models, STask
    
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

def commit(model):
    """安全提交数据库更改
    Args:
        model: 数据库模型实例
    """
    try:
        session = db.session
        # 检查对象是否已经在其他session中
        if model in session:
            # 如果已经在当前session中，直接提交
            session.commit()
        else:
            # 如果不在当前session中，先合并再提交
            session.merge(model)
            session.commit()
        return True
    except Exception as e:
        Log.ex(e, '数据库提交失败')
        session.rollback()
        return False
