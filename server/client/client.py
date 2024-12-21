import socketio
import time
from datetime import datetime

"""
设备端程序原型
- 这个脚本将被改写为Android应用
- 保持相同的WebSocket通信逻辑
- 运行在实际的手机设备上

通信流程：
1. 设备连接服务器并自动注册
2. 接收服务器转发的命令
3. 执行命令并返回结果
4. 保持心跳连接
"""

# 创建SocketIO客户端，配置自动重连参数
sio = socketio.Client(
    reconnection=True,        # 启用自动重连
    reconnection_attempts=5,  # 最大重连次数
    reconnection_delay=1,     # 重连延迟(秒)
    reconnection_delay_max=5, # 最大重连延迟(秒)
    logger=True              # 启用日志
)

@sio.event
def connect():
    """连接成功回调：
    - 发送设备登录信息
    - 包含设备ID和时间戳
    """
    print('已连接到服务器')
    sio.emit('device_login', {
        'device_id': 'test_device_001',
        'timestamp': str(datetime.now())
    })

@sio.event
def connect_error(data):
    """连接错误回调：
    - 记录错误信息
    - 等待自动重连
    """
    print(f'连接错误: {data}')

@sio.event
def disconnect():
    """断开连接回调：
    - 记录断开信息
    - 清理资源
    """
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
        sio.connect(
            'http://localhost:5000',
            wait_timeout=10,
            transports=['websocket', 'polling'],  # 允许降级到polling
            wait=True
        )
        
        # 保持连接运行
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