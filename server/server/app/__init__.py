from flask import Flask
from flask_socketio import SocketIO
from .models import db
import logging
import os
import eventlet
eventlet.monkey_patch()  # 在导入其他模块前执行monkey patch

# 配置日志级别，只显示WARNING及以上级别的日志
logging.getLogger('engineio').setLevel(logging.WARNING)
logging.getLogger('socketio').setLevel(logging.WARNING)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'
# 配置SQLite数据库
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///devices.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)

# 确保在应用上下文中创建数据库
with app.app_context():
    db.create_all()

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',  # 明确指定使用eventlet
    logger=True,
    engineio_logger=True
)

from app import routes, websocket 