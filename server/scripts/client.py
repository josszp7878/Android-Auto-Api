import sys
# print("Python Path:", sys.executable)
# print("PYTHONPATH:", sys.path)
try:
    import socketio
    print("SocketIO Path:", socketio.__file__)
except ImportError as e:
    print("Import Error:", e)

import time
from CDevice import CDevice
from CmdMgr import cmdMgr
from logger import Log
from tools import Tools

# 固定配置
DEFAULT_DEVICE_ID = 'TEST1'
client = None

def Begin(deviceID=None, server=None):
    """客户端启动入口"""
    # 初始化平台判定
    Tools().initPlatform()
    # 初始化日志系统
    Log().init(is_server=False)
    deviceID = deviceID or DEFAULT_DEVICE_ID
    device = CDevice(deviceID)
    import Cmds
    server = server or "localhost"
    Log.i(f"@@@@%%%%设备 {deviceID} 正在连接到服务器{server} {device.deviceID}")
    if not device.connect(f"http://{server}:5000"):
        Log.e("连接服务器失败")
        return
    import CmdMgr
    print("客户端运行中... 按Ctrl+C退出")    
    try:
        runFromApp = Tools().isAndroid()
        while True:
            if not runFromApp:
                cmd_input = input(f"{deviceID}> ").strip()
                if cmd_input:
                    # 直接使用 CmdMgr 处理命令
                    try:
                        result = CmdMgr.CmdMgr().do(cmd_input)
                        if result:
                            print(result)
                    except Exception as e:
                        Log.ex(e, '执行命令出错')
            time.sleep(0.1)
    except KeyboardInterrupt:
        Log.i('\n正在退出...')
    except Exception as e:
        Log.ex(e, '发生错误')
    finally:
        End()


def End():
    Log.i("End")
    if client:
        client.logout()
        client.disconnect()
        Log.i("已断开服务器连接")
    # 在这里添加任何需要的清理逻辑



if __name__ == '__main__':
    # 如果有命令行参数，则使用第一个参数作为设备ID，第二个参数作为服务器URL
    device_id = sys.argv[1] if len(sys.argv) > 1 else None
    server_url = sys.argv[2] if len(sys.argv) > 2 else None
    Begin(device_id, server_url)