from flask import Flask
from flask_socketio import SocketIO
from .models import db
import logging
import os
import eventlet
eventlet.monkey_patch()  # 在导入其他模块前执行monkey patch

# 获取server目录的绝对路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 配置日志级别，只显示WARNING及以上级别的日志
logging.getLogger('engineio').setLevel(logging.WARNING)
logging.getLogger('socketio').setLevel(logging.WARNING)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'
# 修改数据库路径到server目录
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "devices.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SERVER_ID'] = '@'  # 服务器ID

# 初始化数据库
db.init_app(app)

# 确保在应用上下文中创建数据库
def init_db():
    with app.app_context():
        db.create_all()
        print(f'数据库表已创建: {app.config["SQLALCHEMY_DATABASE_URI"]}')

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',  # 明确指定使用eventlet
    logger=True,
    engineio_logger=False,
    ping_interval=25,  # 设置心跳间隔
    ping_timeout=60    # 设置心跳超时时间
)

# 注册蓝图
from .routes import bp
app.register_blueprint(bp)

# 在socketio初始化后创建数据库
init_db()

from app import routes, websocket 