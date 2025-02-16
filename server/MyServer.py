from app import create_app, socketio
import signal
from scripts.logger import Log
from scripts.tools import Tools
from app.Server import initServer


def signal_handler(sig, frame):
    """处理 Ctrl+C 信号"""
    Log.i('正在关闭服务器...')
    Log().uninit()
    exit(0)


if __name__ == '__main__':
    # 创建应用实例
    app = create_app()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    
    # 初始化日志系统并打开服务器日志
    Log().init(is_server=True)
    
    try:
        # 初始化服务器
        with app.app_context():
            initServer()
        
        # 启动服务器
        Log.i('服务器启动')
        socketio.run(app, host='0.0.0.0', port=Tools.port)
    except Exception as e:
        Log.e(f'服务器启动失败: {e}')
        Log().uninit()
