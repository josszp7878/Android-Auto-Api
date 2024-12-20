import socketio
import time
from datetime import datetime

# 创建SocketIO客户端，添加一些配置
sio = socketio.Client(
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=1,
    reconnection_delay_max=5,
    logger=True  # 添加日志
)

@sio.event
def connect():
    print('已连接到服务器')
    # 模拟设备登录
    sio.emit('device_login', {
        'device_id': 'test_device_001',
        'timestamp': str(datetime.now())
    })

@sio.event
def connect_error(data):
    print(f'连接错误: {data}')

@sio.event
def disconnect():
    print('断开连接')

@sio.on('command')
def on_command(data):
    print(f'收到命令: {data}')
    response = {
        'status': 'success',
        'result': f'执行命令: {data["command"]}'
    }
    sio.emit('command_response', response)

def main():
    try:
        print('正在连接到服务器...')
        # 修改连接参数
        sio.connect(
            'http://localhost:5000',
            wait_timeout=10,
            transports=['websocket', 'polling'],  # 允许降级到polling
            wait=True
        )
        
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                print('\n正在断开连接...')
                break
            
    except Exception as e:
        print(f'发生错误: {e}')
    finally:
        if sio.connected:
            sio.disconnect()

if __name__ == '__main__':
    main() 