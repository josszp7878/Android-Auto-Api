from flask import Flask
from flask_socketio import SocketIO
from .database import init_db, db
import logging
import os
import eventlet
from config import config

eventlet.monkey_patch()

# 定义应用根目录
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA = os.path.join(APP_ROOT, 'data')
APP_LOGS = os.path.join(APP_DATA, 'logs')

# 确保必要的目录存在
for dir_path in [APP_DATA, APP_LOGS]:
    os.makedirs(dir_path, exist_ok=True)

# 确保screenshots目录存在
SCREENSHOTS_DIR = os.path.join(APP_ROOT, 'app', 'static', 'screenshots')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# 配置日志级别
logging.getLogger('engineio').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

socketio = SocketIO()
app = None


def create_app(config_name='development'):
    """创建 Flask 应用"""
    global app
    app = Flask(__name__,
                static_folder='static',
                static_url_path='/static')
    
    # 加载配置
    app.config.from_object(config[config_name])
    
    # 测试数据库连接
    try:
        # 初始化数据库
        init_db(app)
        with app.app_context():
            # 测试数据库连接
            db.engine.connect()
            print("数据库连接成功！")
    except Exception as e:
        print(f"数据库连接错误: {e}")
        raise

    # 初始化 SocketIO
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode='eventlet',  # 使用eventlet作为异步模式
        logger=False,
        engineio_logger=False
    )

    # 注册蓝图
    from .routes import bp
    app.register_blueprint(bp)

    return app

