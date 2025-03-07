from app import create_app, socketio
import signal
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
from config import config
import _Log
from app.Database import Database

def signal_handler(sig, frame):
    """处理 Ctrl+C 信号"""
    _Log.Log_.i('正在关闭服务器...')
    _Log.Log_.uninit()
    exit(0)


if __name__ == '__main__':
    try:
        # 创建应用实例
        app = create_app('development')
        cfg = config['development']
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        
        # 初始化日志系统并打开服务器日志
        _Log.Log_.setIsServer(is_server=True)        
        # 启动服务器
        _Log.Log_.i(f'服务器启动在: http://{cfg.SERVER_HOST}:{cfg.SERVER_PORT}')
        
        # 初始化数据库
        Database.init(app)
        # 注册所有命令
        from _CmdMgr import _CmdMgr
        _CmdMgr.regAllCmds()
        socketio.run(
            app, 
            host=cfg.SERVER_HOST,
            port=cfg.SERVER_PORT,
            debug=False,
            use_reloader=False,  # 禁用重载器
            log_output=False      # 启用日志输出
        )
    except Exception as e:
        print(f'服务器启动失败: {_Log.Log_.formatEx(e)}')
        _Log.Log_.uninit()
    finally:
        _Log.Log_.i('服务器关闭')
