import time
import sys
from CDevice import CDevice
from logger import Log

# 固定配置
DEFAULT_DEVICE_ID = 'TEST1'
client = None

def Begin(deviceID=None, server=None):
    deviceID = deviceID or DEFAULT_DEVICE_ID
    server = server or "localhost"
    Log.i(f"@@@@%%%%设备 {deviceID} 正在连接到服务器{server}")
    device = CDevice(deviceID)
    if not device.connect(f"http://{server}:5000"):
        Log.e("连接服务器失败")
        return
    import CmdMgr
    import Cmds
    print("客户端运行中... 按Ctrl+C退出")    
    try:
        while True:
            if device.RunFromApp:
                time.sleep(1)
            else:
                cmd_input = input(f"{deviceID}> ").strip()
                if not cmd_input:
                    continue
                # 解析命令和参数
                parts = cmd_input.split()
                cmd = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []
                # 尝试调用对应的方法
                try:
                    cmd = next((x for x in dir(device) if x.lower().startswith(cmd.lower())), None)
                    if cmd:
                        Log.i(f'do cmd: {cmd}')
                        method = getattr(device, cmd)
                        if args:
                            method(*args)
                        else:
                            method()
                    else:
                        # 如果不是内置命令，就作为普通命令发送
                        device.send_command(cmd_input)
                        
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