from flask_migrate import Migrate

# 在 create_app 函数中添加
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    # ...其他配置...
    migrate.init_app(app, db)
    return app 