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
        'pool_recycle': 280,  # 连接在280秒后回收
        'pool_timeout': 20,   # 等待连接的超时时间
        'pool_pre_ping': True # 每次连接前ping一下
    }
    SECRET_KEY = 'dev'
    SERVER_ID = '@'

    # 服务器配置
    SERVER_HOST = '0.0.0.0'  # 监听所有网络接口
    SERVER_PORT = 5000


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False


# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 