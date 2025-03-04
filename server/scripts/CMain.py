from CClient import client
from _Log import _Log
from CTools import CTools


def Begin(deviceID=None, server=None, runFromAndroid=False):
    """初始化客户端"""
    try:
        _Log().init(is_server=False)
        CTools.runFromAndroid = runFromAndroid
        client.Begin(deviceID, server)  
    except Exception as e:
        _Log.ex(e, "初始化客户端失败")

def End():
    """清理函数"""
    client.End()

def main():
    # 命令行启动支持
    import sys
    device_id = sys.argv[1] if len(sys.argv) > 1 else None
    server_url = sys.argv[2] if len(sys.argv) > 2 else None
    Begin(device_id, server_url, False)

if __name__ == '__main__':
    main() 