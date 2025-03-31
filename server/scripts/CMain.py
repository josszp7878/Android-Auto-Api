import sys
import _G

def Begin(deviceID=None, server=None, fromAndroid=None):
    """初始化客户端"""
    _G._G_.load(False)
    import CClient
    client = CClient.CClient_()
    client.updateFiles()
    client.Begin(deviceID, server, fromAndroid)
    

def End():
    try:
        import CClient
        CClient.CClient_.End()
    except Exception as e:
        _G._G_.Log().ex(e, f'End失败')


def main():
    # 命令行启动支持
    deviceID = sys.argv[1] if len(sys.argv) > 1 else None
    server = sys.argv[2] if len(sys.argv) > 2 else None
    Begin(deviceID, server, False)


if __name__ == '__main__':
    main()
