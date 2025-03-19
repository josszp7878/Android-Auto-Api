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

socketio = SocketIO(logger=False, engineio_logger=False, async_mode='eventlet')


def create_app(config_name='development', debug=False):
    """创建 Flask 应用"""
    app = Flask(
        __name__,
        static_folder='static',
        static_url_path='/static',
        template_folder='templates')
    
    # 加载配置
    app.config.from_object(config[config_name])

    from SDatabase import db
    # 初始化数据库
    db.init_app(app)
    
    # 初始化 SocketIO（必须在蓝图注册前）
    socketio.init_app(app, cors_allowed_origins="*")
    
    # 创建所有数据库表
    with app.app_context():
        db.create_all()
    
    # 导入并注册事件处理器
    import Server
    
    # 注册蓝图
    from SRoutes import bp
    app.register_blueprint(bp)

    app.debug = debug

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        try:
            db.session.remove()
        except:
            pass

    return app

