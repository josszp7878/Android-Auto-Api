import time
import sys
from device import Device
import Cmds  # 确保导入Cmds模块
from CmdMgr import cmdMgr
from tools import Tools, print

# 固定配置
DEFAULT_DEVICE_ID = 'TEST1'
client = None
def Begin(device=None, server=None):
    # 使用传入的设备ID或默认值
    device = device or DEFAULT_DEVICE_ID
    server = server or "localhost"
    tools = Tools()
    device = tools.setRunFromApp(device)
    # print(f"%%%%%_RunFromAPP in Begin: {tools.isRunFromApp()}")

    print(f"设备 {device} 已连接到服务器{server}")
    # 1. 连接服务器
    device = Device(device)
    if not device.connect(f"http://{server}:5000"):
        print("连接服务器失败")
        return
    
    print(f"设备 {device} 已连接到服务器{server}")
    print("支持的命令:")
    print("- status: 查看状态")
    print("- exit: 退出程序")
    print("客户端运行中... 按Ctrl+C退出")
    
    try:
        while True:
            if tools.isRunFromApp():
                time.sleep(1)
            else:
                cmd_input = input(f"{device}> ").strip()
                if not cmd_input:
                    continue
                # 解析命令和参数
                parts = cmd_input.split()
                cmd = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []
                
                if cmd == 'exit':
                    break                
                # 尝试调用对应的方法
                try:
                    cmd = next((x for x in dir(device) if x.lower().startswith(cmd.lower())), None)
                    if cmd:
                        print('do cmd:', cmd)
                        method = getattr(device, cmd)
                        if args:
                            method(*args)
                        else:
                            method()
                    else:
                        # 如果不是内置命令，就作为普通命令发送
                        device.send_command(cmd_input)
                        
                except Exception as e:
                    print(f"执行命令出错: {e}")
                
                time.sleep(0.1)
            
    except KeyboardInterrupt:
        print('\n正在退出...')
    except Exception as e:
        print(f'发生错误: {e}')
    finally:
        End()


def End():
    if client:
        client.logout()
        client.disconnect()
        print("已断开服务器连接")
    # 在这里添加任何需要的清理逻辑

if __name__ == '__main__':
    # 如果有命令行参数，则使用第一个参数作为设备ID，第二个参数作为服务器URL
    device_id = sys.argv[1] if len(sys.argv) > 1 else None
    server_url = sys.argv[2] if len(sys.argv) > 2 else None
    Begin(device_id, server_url)