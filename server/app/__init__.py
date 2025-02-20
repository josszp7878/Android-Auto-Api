from flask import Flask
from flask_socketio import SocketIO
from .database import init_db
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

# 配置更详细的日志
logging.basicConfig(level=logging.DEBUG)  # 设置根日志级别为 DEBUG
engineio_logger = logging.getLogger('engineio')
engineio_logger.setLevel(logging.DEBUG)
socketio_logger = logging.getLogger('socketio')
socketio_logger.setLevel(logging.DEBUG)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.DEBUG)

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
    
    # 初始化数据库
    init_db(app)
    
    # 初始化 SocketIO
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode='eventlet',
        logger=False,
        engineio_logger=False
    )
    
    # 导入并注册事件处理器
    from . import Server  # 移到这里，确保在 socketio 初始化后导入
    
    # 注册蓝图
    from .routes import bp
    app.register_blueprint(bp)

    return app

