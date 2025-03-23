from app import create_app, socketio
import signal
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
from config import config
from SDatabase import Database
import _G

def signal_handler(sig, frame):
    """处理 Ctrl+C 信号"""
    log = _G._G_.Log()
    log.i('正在关闭服务器...')
    log.uninit()
    exit(0)


if __name__ == '__main__':
    try:

        # 创建应用实例
        app = create_app('development')
        cfg = config['development']
 
        print(f'app: {app}')
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        
        # 初始化日志系统并打开服务器日志
        g = _G._G_
        log = g.Log()
        g.load(True)      
         # 启动服务器
        log.i(f'服务器启动在: http://{cfg.SERVER_HOST}:{cfg.SERVER_PORT}')
        # print(f'ddd111')
        
        # 初始化数据库
        Database.init(app)
        # 注册所有命令
        import _CmdMgr
        _CmdMgr._CmdMgr_.regAllCmds()
        socketio.run(
            app, 
            host=cfg.SERVER_HOST,
            port=cfg.SERVER_PORT,
            debug=False,
            use_reloader=False,  # 禁用重载器
            log_output=False      # 启用日志输出
        )
    except Exception as e:
        log.ex(e, f'服务器启动失败')
        log.uninit()
    finally:
        log.i('服务器关闭')
