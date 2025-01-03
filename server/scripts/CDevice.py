import socketio
from datetime import datetime
from pathlib import Path
from logger import Log

class CDevice:
    _instance = None  # 单例实例
    _cmdMgr = None   # 命令管理器实例
    _RunFromApp = False
    @property
    def RunFromApp(self):
        return self._RunFromApp
    
    @property
    def deviceID(self):
        return self._deviceID
    
    @classmethod
    def instance(cls):
        """获取单例实例"""
        return cls._instance

    def __new__(cls, device_id=None):  # 显式声明参数
        if not cls._instance:            
            # 创建实例
            cls._instance = super().__new__(cls)
            # 可以在这里就保存参数
            cls._instance._device_id = device_id
        return cls._instance

    def __init__(self, deviceID=None):  # 同样的参数
        # 只在第一次初始化时设置属性
        if not hasattr(self, 'initialized'):
            # 使用已保存的参数或传入的参数
            if deviceID is None:
                deviceID = "1"            
            if deviceID and deviceID.startswith("_"):
                self._RunFromApp = True
                deviceID = deviceID[1:]

            self._deviceID = deviceID
            self.connected = False
            self._RunFromApp = False
            
            # 初始化 socketio 客户端
            self.sio = socketio.Client(
                reconnection=True,
                reconnection_attempts=5,
                reconnection_delay=1,
                reconnection_delay_max=5,
                logger=False
            )
            
            # 注册事件处理器
            self.sio.on('connect')(self.on_connect)
            self.sio.on('clientCommand')(self.on_command)
            self.sio.on('disconnect')(self.on_disconnect)
            self.sio.on('connect_error')(self.on_connect_error)
            
            self.initialized = True

    def isConnected(self):
        """检查是否已连接"""
        print('isConnected:', self.connected)
        return self.connected
    def disconnect(self):
        """断开连接"""
        if self.connected:
            self.sio.disconnect()
            Log.i(f'设备 {self.deviceID} 已断开连接')
            self.connected = False
            # 关闭日志文件
            self._close_log_file()
            
    _serverURL = None

    def connect(self, server_url=None):
        try:
                
            # Log.i(f'连接参数: device_id={self.deviceID}')
            if not server_url:
                server_url = self._serverURL
            else:
                self._serverURL = server_url
            
            # 连接到服务器，直接通过查询参数传递设备ID
            connect_url = f"{server_url}?device_id={self.deviceID}"
            print(f"连接 URL: {connect_url}")
            self.sio.connect(
                connect_url,
                transports=['websocket'],
                wait=True
            )
            
            # 打印连接后的 sid
            sid = self.sio.sid
            Log.i(f'连接成功，设备ID: {self.deviceID}, SID: {sid}')
            print(f'连接成功，SID: {sid}')
            
            self.connected = True
            return True
        except Exception as e:
            Log.ex(e, '连接错误')
            return False

    def login(self):
        # Log.i(f'设备 {self.deviceID} 登录: self.connected={self.connected}')
        if self.connected:
            self.sio.emit('device_login', {
                'device_id': self.deviceID,
                'timestamp': str(datetime.now()),
                'status': 'login'
            })
            return True
        return False
    
    def logout(self):
        self.sio.emit('device_logout', {
            'device_id': self.deviceID,
            'timestamp': str(datetime.now())
        })
        return True
    

    
    def on_command(self, data):
        """处理客户端收到的命令"""
        try:
            command = data.get('command')
            command_id = data.get('command_id')
            print(f'正在处理命令: {command}, ID: {command_id}')
            # Log.i(f'正在处理命令: {command}, ID: {command_id}')
            
            # 使用 CmdMgr 执行命令
            from CmdMgr import CmdMgr
            result = CmdMgr().do(command)
            
            # print(f'客户端执行命令结果: {result}')
            
            # 发送响应
            if result is not None:
                response = {
                    'command_id': command_id,
                    'device_id': self.deviceID,
                    'result': result
                }
                self.sio.emit('command_result', response)
                
        except Exception as e:
            error_msg = f'执行命令出错: {e}'
            Log.ex(e, '执行命令出错')
            if self.connected:
                self.sio.emit('command_result', {
                    'command_id': data.get('command_id'),
                    'result': error_msg,
                    'device_id': self.deviceID
                })

    def on_command_result(self, data):
        """处理命令结果"""
        Log.i(f'命令结果: {data["result"]}')

    def on_connect(self):
        """连接成功回调"""
        sid = self.sio.sid
        Log.i(f'已连接到服务器, SID: {sid}')
        print(f'客户端 SID: {sid}')
        
        # 连接后立即进行登录
        self.login()

    def on_connect_error(self, data):
        """连接错误回调"""
        Log.e(f'连接错误: {data}')

    def on_disconnect(self):
        """断开连接回调"""
        Log.w('断开连接')
        self.connected = False

    def send_command(self, cmd):
        """发送命令到服务器"""
        Log.i(f'TODO:发送命令到服务器: {cmd}')
        # if not self.connected:
        #     print('未连接到服务器')
        #     return False
        
        # response = {
        #     'status': 'success',
        #     'result': f'执行命令: {cmd}'
        # }
        # self.sio.emit('command_response', response)
        return True
