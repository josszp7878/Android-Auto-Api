from CClient import client
from CFileServer import fileServer
from logger import log
from CTools import CTools

def Begin(deviceID=None, server=None):
    log.init(is_server=False)
    client.Begin(deviceID, server)

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
    CTools.runFromAndroid = False
    main() 