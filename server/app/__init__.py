from flask import Flask
from flask_socketio import SocketIO
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

# 配置日志级别为INFO（关闭详细日志）
logging.basicConfig(level=logging.INFO)  # 将根日志级别改为 INFO
engineio_logger = logging.getLogger('engineio')
engineio_logger.setLevel(logging.WARNING)  # 将 Engine.IO 日志级别改为 WARNING
socketio_logger = logging.getLogger('socketio')
socketio_logger.setLevel(logging.WARNING)  # 将 Socket.IO 日志级别改为 WARNING
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)  # 将 Werkzeug 日志级别改为 INFO

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
    
    # 初始化 SocketIO
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode='eventlet',
        logger=False,  # 关闭详细日志
        engineio_logger=False,  # 关闭 Engine.IO 日志
        ping_timeout=60,  # 增加 ping 超时时间
        ping_interval=25  # 保持默认 ping 间隔
    )
    
    # 导入并注册事件处理器
    from . import Server  # 移到这里，确保在 socketio 初始化后导入
    
    # 注册蓝图
    from .routes import bp
    app.register_blueprint(bp)

    return app

