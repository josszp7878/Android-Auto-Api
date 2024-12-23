import time
import sys
from client import Client

# 固定配置
SERVER_URL = 'http://localhost:5000'
DEFAULT_DEVICE_ID = 'TEST1'


def main(device_id=None):
    # 使用传入的设备ID或默认值
    device_id = device_id or DEFAULT_DEVICE_ID
    
    # 1. 连接服务器
    client = Client(device_id)
    if not client.connect(SERVER_URL):
        print("连接服务器失败")
        return
    
    print(f"设备 {device_id} 已连接到服务器")
    print("支持的命令:")
    print("- login: 登录设备")
    print("- logout: 登出设备")
    print("- status: 查看状态")
    print("- exit: 退出程序")
    print("- 其他命令将被发送到服务器执行")
    print("客户端运行中... 按Ctrl+C退出")
    
    try:
        while True:
            cmd_input = input("输入命令> ").strip()
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
                cmd = next((x for x in dir(client) if x.lower().startswith(cmd.lower())), None)
                if cmd:
                    print('do cmd:', cmd)
                    method = getattr(client, cmd)
                    if args:
                        method(*args)
                    else:
                        method()
                else:
                    # 如果不是内置命令，就作为普通命令发送
                    client.send_command(cmd_input)
                    
            except Exception as e:
                print(f"执行命令出错: {e}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print('\n正在退出...')
    except Exception as e:
        print(f'发生错误: {e}')
    finally:
        client.logout()
        client.disconnect()
        print("已断开服务器连接")


if __name__ == '__main__':
    # 如果有命令行参数，则使用第一个参数作为设备ID
    device_id = sys.argv[1] if len(sys.argv) > 1 else None
    main(device_id)