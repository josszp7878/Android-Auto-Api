from app import app, socketio
from scripts.logger import Log
import signal
import sys

def signal_handler(sig, frame):
    """处理退出信号"""
    print('正在关闭服务器...')
    # 关闭服务器日志
    Log().close('server')
    sys.exit(0)

if __name__ == '__main__':
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 初始化日志系统并打开服务器日志
    Log().init(is_server=True)
    try:
        # 启动服务器
        Log.i('服务器启动')
        socketio.run(app, host='0.0.0.0', port=5000)
    except Exception as e:
        Log.e(f'服务器启动失败: {e}')
    finally:
        # 确保关闭日志
        Log().uninit()
