from flask import Flask
from flask_socketio import SocketIO
from .models import db
import logging
import os
import eventlet
eventlet.monkey_patch()

# 获取server目录的绝对路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 配置日志级别 - 关闭 Socket.IO 的系统日志
logging.getLogger('engineio').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)  # 也关闭 Flask 的开发服务器日志

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "devices.db")}'
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
    logger=False,  # 关闭 Socket.IO 日志
    engineio_logger=False,  # 关闭 Engine.IO 日志
    ping_interval=25,
    ping_timeout=60
)

# 注册蓝图
from .routes import bp
app.register_blueprint(bp)

# 创建数据库
init_db()

from app import routes, websocket 

