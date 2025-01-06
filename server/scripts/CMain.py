from client import client

def Begin(deviceID=None, server=None):
    """入口函数"""
    client.Begin(deviceID, server)

def End():
    """清理函数"""
    client.End()

if __name__ == '__main__':
    # 命令行启动支持
    import sys
    device_id = sys.argv[1] if len(sys.argv) > 1 else None
    server_url = sys.argv[2] if len(sys.argv) > 2 else None
    Begin(device_id, server_url) 