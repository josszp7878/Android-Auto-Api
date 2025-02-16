from flask_sqlalchemy import SQLAlchemy

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
            db.create_all()
            print("数据库表创建成功")
        except Exception as e:
            print(f"数据库初始化错误: {e}")
            raise 