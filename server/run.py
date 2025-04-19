# 确保在导入其他模块前先执行monkey_patch
import eventlet
eventlet.monkey_patch()

# 修复SSL递归错误
import ssl
try:
    # 尝试设置SSL上下文
    ssl._create_default_https_context = ssl._create_unverified_context
    
    # 添加以下代码来防止递归错误
    if hasattr(ssl, '_create_default_https_context') and hasattr(ssl, 'TLSVersion'):
        # 禁用TLSVersion的递归问题
        import urllib3.util.ssl_
        urllib3.util.ssl_.create_urllib3_context = lambda *args, **kwargs: ssl.create_default_context(*args, **kwargs)
except (AttributeError, ImportError):
    # 如果不支持，则跳过
    pass

# 其他导入
import signal
import socket
import subprocess
import time
from app import create_app, socketio
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

def protInUse(port, log):
    """检查Windows系统上端口是否被占用"""
    cmd_test = False
    try:
        result = subprocess.run(f'netstat -ano | findstr :{port}', 
                            shell=True, 
                            text=True, 
                            capture_output=True)
        cmd_test = 'LISTENING' in result.stdout
        if cmd_test:
            log.i(f'通过netstat检测到端口{port}被占用')
    except Exception as e:
        log.ex(e, '系统命令检测端口占用失败')
    
    # 任一方法检测到端口被占用，返回True
    return cmd_test

def killProcessesOnPort(port, log):
    """查找并终止Windows系统上占用端口的所有进程"""
    success = False
    try:
        # 获取所有占用该端口的进程
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
            
            # 终止所有找到的进程
            for pid in pids:
                log.i(f'发现端口{port}被PID为{pid}的进程占用，正在尝试终止...')
                kill_result = subprocess.run(f'taskkill /F /PID {pid}', 
                                        shell=True,
                                        text=True,
                                        capture_output=True)
                if 'SUCCESS' in kill_result.stdout:
                    log.i(f'已成功终止PID为{pid}的进程')
                    success = True
                else:
                    log.w(f'终止PID为{pid}的进程失败: {kill_result.stderr}')
            
        return success
    except Exception as e:
        log.ex(e, f'尝试终止占用端口{port}的进程时出错')
        return False

def checkPort(port, log):
     # 检查端口是否被占用，如果被占用则尝试终止占用进程
    max_attempts = 3
    for attempt in range(max_attempts):
        if protInUse(port, log):
            log.w(f'端口{port}已被占用，尝试终止占用进程... (尝试 {attempt+1}/{max_attempts})')
            if killProcessesOnPort(port, log):
                log.i(f'成功释放端口{port}')
                # 等待一小段时间确保端口完全释放
                time.sleep(1)
                if not protInUse(port, log):
                    break
            else:
                log.w(f'无法自动释放端口{port}')
        else:
            break
        
        if attempt == max_attempts - 1:
            log.w(f'多次尝试后仍无法释放端口{port}，请手动关闭占用该端口的进程')


if __name__ == '__main__':
    # 创建应用实例
    app = create_app('development')
    cfg = config['development']
    
    # 初始化日志系统
    g = _G._G_
    log = g.Log()
    g.load(True)
    
    try:
        port = cfg.SERVER_PORT
        checkPort(port, log)
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        
        # 启动服务器
        log.i(f'服务器启动在: http://{cfg.SERVER_HOST}:{cfg.SERVER_PORT}')
        
        # 初始化数据库
        Database.init(app)
        # 注册所有命令
        g.CmdMgr().regAllCmds()
        
               
        socketio.run(
            app, 
            host=cfg.SERVER_HOST,
            port=cfg.SERVER_PORT,
            debug=False,
            use_reloader=False,  # 禁用重载器
            log_output=False      # 启用日志输出
        )
    except Exception as e:
        log.ex(e, '服务器启动失败')
        log.uninit()
    finally:
        log.i('服务器关闭')
