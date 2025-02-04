from flask import Flask
from flask_socketio import SocketIO
from .models import db
import logging
import os
import eventlet
from pathlib import Path
eventlet.monkey_patch()

# 定义应用根目录
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # server目录
APP_DATA = os.path.join(APP_ROOT, 'data')  # 数据目录
APP_LOGS = os.path.join(APP_DATA, 'logs')  # 日志目录

# 确保必要的目录存在
for dir_path in [APP_DATA, APP_LOGS]:
    os.makedirs(dir_path, exist_ok=True)

# 确保screenshots目录存在
SCREENSHOTS_DIR = os.path.join(APP_ROOT, 'app', 'static', 'screenshots')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# 配置日志级别 - 关闭 Socket.IO 的系统日志
logging.getLogger('engineio').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)  # 也关闭 Flask 的开发服务器日志

app = Flask(__name__, 
    static_folder='static',  # 确保这个路径正确
    static_url_path='/static'  # 确保这个URL前缀正确
)
app.config['SECRET_KEY'] = 'dev'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(APP_DATA, "devices.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SERVER_ID'] = '@'

# 初始化数据库
db.init_app(app)

def init_db():
    with app.app_context():
        db.create_all()
        print(f'数据库表已创建: {app.config["SQLALCHEMY_DATABASE_URI"]}')

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=False,
    engineio_logger=False,
    ping_interval=25,
    ping_timeout=60,
    engineio_opts={'async_handlers': True}
)

# 注册蓝图
from .routes import bp
app.register_blueprint(bp)

# 创建数据库
init_db()

from app import routes, websocket 

