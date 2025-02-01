from client import client
from CFileServer import fileServer
from logger import log
import time
import os

# 定义为模块级别的全局变量
waitting = False

def Begin(deviceID=None, server=None):
    log.init(is_server=False)
    fileServer.init(server)
    
    global waitting  # 在函数开始时声明使用全局变量
    waitting = True    
    def onUpdated(ok):
        global waitting  # 在回调函数中也声明使用全局变量
        waitting = False
        
    fileServer.updateScripts(onUpdated)
    print("更新脚本")
    count = 0
    while waitting:
        try:
            time.sleep(1)
            print(".", end="", flush=True)
            count += 1
        except KeyboardInterrupt:
            print('\n正在退出...') 
            return           
        except Exception as e:
            break
    client.Begin(deviceID)

def End():
    """清理函数"""
    client.End()

def main():
    # 命令行启动支持
    import sys
    device_id = sys.argv[1] if len(sys.argv) > 1 else None
    server_url = sys.argv[2] if len(sys.argv) > 2 else None
    Begin(device_id, server_url)

if __name__ == '__main__':
    main() 