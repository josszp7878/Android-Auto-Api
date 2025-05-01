import os


class Config:
    """基础配置类"""
    # MySQL配置 - 远程数据库
    MYSQL_HOST = os.getenv('MYSQL_HOST', '47.120.32.243')  # 远程数据库地址
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'love78')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'SGG')
    
    # SQLAlchemy配置
    SQLALCHEMY_DATABASE_URI = (
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}'
        f'@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,               # MySQL默认最大连接数
        'max_overflow': 5,             # 超过pool_size后最多创建的连接数
        'pool_timeout': 30,            # 连接池获取连接的超时时间
        'pool_recycle': 3600,          # 一小时自动回收连接，避免MySQL默认8小时超时断开
        'pool_pre_ping': True,         # 每次请求前ping一下数据库，确保连接有效
        'echo': False,                 # 关闭SQL语句输出
        'echo_pool': False,            # 关闭连接池日志
        'connect_args': {              # MySQL特定的连接参数
            'connect_timeout': 10,      # 连接超时时间
            'read_timeout': 30,         # 读取超时时间
            'write_timeout': 30         # 写入超时时间
        }
    }
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    SERVER_ID = 'Server'

    # 服务器配置
    SERVER_HOST = '0.0.0.0'  # 监听所有网络接口
    SERVER_PORT = 5000

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    # 可以在这里覆盖特定的数据库配置
    # SQLALCHEMY_DATABASE_URI = 'mysql://dev_user:dev_password@localhost/dev_db'


class ProductionConfig(Config):
    """生产环境配置"""
    # 生产环境可能需要不同的数据库配置
    # SQLALCHEMY_DATABASE_URI = 'mysql://prod_user:prod_password@localhost/prod_db'


# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 