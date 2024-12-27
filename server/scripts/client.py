import socketio
from datetime import datetime
from CmdMgr import doCmd


class Client:
    """设备客户端类"""
    
    def __init__(self, device_id=None):
        self.device_id = device_id or 'test_device_001'
        self.connected = False
        
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=5,
            reconnection_delay=1,
            reconnection_delay_max=5,
            logger=True
        )
        
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('connect_error', self.on_connect_error)
        self.sio.on('command', self.on_command)
        self.sio.on('command_result', self.on_command_result)

    def isConnected(self):
        """检查是否已连接"""
        print('isConnected:', self.connected)
        return self.connected
    def disconnect(self):
        """断开连接"""
        if self.connected:
            self.sio.disconnect()
            print(f'设备 {self.device_id} 已断开连接')
            self.connected = False
    def connect(self, server_url):
        """连接到服务器"""
        print(f'@@@正在连接到服务器 {server_url}...')
        try:
            self.sio.connect(
                server_url,
                auth={'device_id': self.device_id},
                wait_timeout=10,
                transports=['websocket', 'polling']
            )
            print(f'连接成功，设备ID: {self.device_id}')
            self.connected = True
            return True
        except Exception as e:
            print(f'连接错误: {e}')
            return False

    def login(self):
        """设备登录"""
        self.sio.emit('device_login', {
            'device_id': self.device_id,
            'timestamp': str(datetime.now())
        })
        return True
    
    def logout(self):
        self.sio.emit('device_logout', {
            'device_id': self.device_id,
            'timestamp': str(datetime.now())
        })
        return True
    

    
    apkCall = False
    def on_command(self, data):
        print(f'客户端收到命令: {data}')
        result = doCmd(data['command'])
        print(f'客户端执行命令结果: {result}')
        if result is not None:
            response = {
                'device_id': self.device_id,
                'result': result
            }
            print(f'客户端发送响应: {response}')
            self.sio.emit('command_response', response)

    def on_command_result(self, data):
        """处理命令结果"""
        print(f'命令结果: {data["result"]}')

    def on_connect(self):
        """连接成功回调"""
        print('已连接到服务器')

    def on_connect_error(self, data):
        """连接错误回调"""
        print(f'连接错误: {data}')

    def on_disconnect(self):
        """断开连接回调"""
        print('断开连接')
        self.connected = False

    def send_command(self, cmd):
        """发送命令到服务器"""
        print(f'TODO:发送命令到服务器: {cmd}')
        # if not self.connected:
        #     print('未连接到服务器')
        #     return False
        
        # response = {
        #     'status': 'success',
        #     'result': f'执行命令: {cmd}'
        # }
        # self.sio.emit('command_response', response)
        return True

    def status(self):
        """查看设备状态"""
        status = "已连接" if self.connected else "未连接"
        print(f'设备状态: {status}')
        return True

