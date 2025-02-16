from flask import Flask
from flask_socketio import SocketIO
from .database import init_db, db
import logging
import os
import eventlet
from pathlib import Path
eventlet.monkey_patch()

# 定义应用根目录
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA = os.path.join(APP_ROOT, 'data')
APP_LOGS = os.path.join(APP_DATA, 'logs')
DB_PATH = os.path.join(APP_DATA, 'devices.db')

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


def create_app(debug=False):
    """创建 Flask 应用"""
    global app
    app = Flask(__name__,
                static_folder='static',
                static_url_path='/static')
    
    # 使用绝对路径配置数据库
    app.config['SECRET_KEY'] = 'dev'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SERVER_ID'] = '@'

    # 初始化数据库
    init_db(app)

    # 初始化 SocketIO
    socketio.init_app(app, cors_allowed_origins="*")

    # 注册蓝图
    from .routes import bp
    app.register_blueprint(bp)

    return app

