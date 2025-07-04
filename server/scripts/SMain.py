import signal
import ssl
import subprocess
import time
import logging
import os

# 检查是否在调试模式
DEBUG_MODE = os.getenv('DEBUG_MODE') == '1'

# 修复SSL递归错误 - 在导入任何网络相关模块前执行
def fix_ssl_recursion():
    """修复Python 3.8中的SSL递归错误"""
    try:
        # 方法1: 禁用SSL验证
        ssl._create_default_https_context = ssl._create_unverified_context
        
        # 方法2: 修复TLS版本设置
        if hasattr(ssl, 'TLSVersion'):
            original_minimum_version = ssl.SSLContext.minimum_version
            def patched_minimum_version_setter(self, value):
                if hasattr(self, '_minimum_version'):
                    object.__setattr__(self, '_minimum_version', value)
                else:
                    self._minimum_version = value
            def patched_minimum_version_getter(self):
                return getattr(self, '_minimum_version', ssl.TLSVersion.TLSv1_2)
            
            ssl.SSLContext.minimum_version = property(patched_minimum_version_getter, patched_minimum_version_setter)
        
        # 方法3: 设置环境变量
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        os.environ['CURL_CA_BUNDLE'] = ''
        
        return True
    except Exception as e:
        print(f"SSL修复警告: {e}")
        return False

# 执行SSL修复
fix_ssl_recursion()

if not DEBUG_MODE:
    import eventlet
    import urllib3.util.ssl_
    # 确保在导入其他模块前先执行monkey_patch
    eventlet.monkey_patch()

from flask import Flask
from flask_socketio import SocketIO
from SConfig import config
from SDatabase import Database
from SDatabase import db
import _G

# 额外的urllib3修复
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    if hasattr(urllib3.util.ssl_, 'create_urllib3_context'):
        urllib3.util.ssl_.create_urllib3_context = lambda *args, **kwargs: ssl.create_default_context()
except ImportError:
    pass

# 配置日志
logging.basicConfig(level=logging.INFO)
engineio_logger = logging.getLogger('engineio')
engineio_logger.setLevel(logging.WARNING)
socketio_logger = logging.getLogger('socketio')
socketio_logger.setLevel(logging.WARNING)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)

# 根据调试模式选择异步模式
async_mode = 'threading' if DEBUG_MODE else 'eventlet'

# 创建socketio实例
socketio = SocketIO(
    logger=False, 
    engineio_logger=False, 
    async_mode=async_mode,
    ping_timeout=120,  # 心跳超时时间（秒），要比客户端的大
    ping_interval=30,  # 心跳间隔时间（秒）
    cors_allowed_origins="*"
)

def createApp(configName='development', debug=False):
    """创建Flask应用"""
    app = Flask(__name__, 
               static_folder='../static',
               static_url_path='/static',
               template_folder='../templates')
    
    app.config.from_object(config[configName])
    
    # 初始化数据库
    Database.init(app)
    
    # 初始化SocketIO
    socketio.init_app(app, cors_allowed_origins="*")
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
    
    # 导入并注册路由
    from SRoutes import bp
    app.register_blueprint(bp)
    
    # 导入并注册任务API蓝图
    # from STaskAPI import task_bp
    # app.register_blueprint(task_bp)
    
    app.debug = debug
    return app

def signalHandler(sig, frame):
    """处理Ctrl+C信号"""
    print('正在关闭服务器...')
    exit(0)

def protInUse(port, log):
    """检查Windows系统上端口是否被占用"""
    cmdTest = False
    try:
        result = subprocess.run(f'netstat -ano | findstr :{port}', 
                            shell=True, 
                            text=True, 
                            capture_output=True)
        cmdTest = 'LISTENING' in result.stdout
        if cmdTest:
            log.i(f'通过netstat检测到端口{port}被占用')
    except Exception as e:
        log.ex(e, '系统命令检测端口占用失败')
    return cmdTest

def killProcessesOnPort(port, log):
    """查找并终止Windows系统上占用端口的所有进程"""
    success = False
    try:
        result = subprocess.run(f'netstat -ano | findstr :{port}', 
                            shell=True, 
                            text=True, 
                            capture_output=True)
        if result.stdout:
            pids = set()
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 5 and ('LISTENING' in line or 'ESTABLISHED' in line):
                    pid = parts[-1]
                    pids.add(pid)
            
            for pid in pids:
                log.i(f'发现端口{port}被PID为{pid}的进程占用，正在尝试终止...')
                killResult = subprocess.run(f'taskkill /F /PID {pid}', 
                                        shell=True,
                                        text=True,
                                        capture_output=True)
                if 'SUCCESS' in killResult.stdout:
                    log.i(f'已成功终止PID为{pid}的进程')
                    success = True
                else:
                    log.w(f'终止PID为{pid}的进程失败: {killResult.stderr}')
        return success
    except Exception as e:
        log.ex(e, f'尝试终止占用端口{port}的进程时出错')
        return False

def checkPort(port, log):
    """检查端口是否被占用，如果被占用则尝试终止占用进程"""
    maxAttempts = 3
    for attempt in range(maxAttempts):
        if protInUse(port, log):
            log.w(f'端口{port}已被占用，尝试终止占用进程... (尝试 {attempt+1}/{maxAttempts})')
            if killProcessesOnPort(port, log):
                log.i(f'成功释放端口{port}')
                time.sleep(1)
                if not protInUse(port, log):
                    break
            else:
                log.w(f'无法自动释放端口{port}')
        else:
            break
        
        if attempt == maxAttempts - 1:
            log.w(f'多次尝试后仍无法释放端口{port}，请手动关闭占用该端口的进程')

if __name__ == '__main__':
    # 创建应用实例
    app = createApp('development')
    cfg = config['development']
    
    # 初始化日志系统
    g = _G._G_
    log = g.Log()
    g.load(True)
    
    # 输出当前模式信息
    if DEBUG_MODE:
        log.i('运行在调试模式 - 使用threading异步模式')
    else:
        log.i('运行在生产模式 - 使用eventlet异步模式')
        
    import Server
    # 初始化Server模块的socketio事件
    Server.initSocketIO(socketio)
    
    try:
        port = cfg.SERVER_PORT
        checkPort(port, log)
        # 注册信号处理器
        signal.signal(signal.SIGINT, signalHandler)
        
        # 启动服务器
        log.i(f'服务器启动在: http://{cfg.SERVER_HOST}:{cfg.SERVER_PORT}')
        
        # 注册所有命令
        g.CmdMgr().regAllCmds()
        socketio.run(
            app, 
            host=cfg.SERVER_HOST,
            port=cfg.SERVER_PORT,
            debug=False,
            use_reloader=False,
            log_output=False
        )
    except Exception as e:
        log.ex(e, '服务器启动失败')
    finally:
        log.i_('服务器关闭') 
        log.uninit()