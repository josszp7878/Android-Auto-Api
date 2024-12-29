import socketio
from datetime import datetime
import builtins
# try:
#     from java import jclass
#     # 获取必要的 Java 类
#     Log = jclass("android.util.Log")
# except ImportError:
#     pass

class Device:
    _instance = None  # 单例实例
    _cmdMgr = None   # 命令管理器实例
    _RunFromApp = False
    @property
    def RunFromApp(self):
        return self._RunFromApp
    _deviceID = None
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
            
            self.sio = socketio.Client(
                reconnection=True,
                reconnection_attempts=5,
                reconnection_delay=1,
                reconnection_delay_max=5,
                logger=False
            )
            
            # 设置socket事件处理器
            self.sio.on('connect', self.on_connect)
            self.sio.on('disconnect', self.on_disconnect)
            self.sio.on('connect_error', self.on_connect_error)
            self.sio.on('command', self.on_command)
            self.sio.on('command_result', self.on_command_result)
            
            self.initialized = True

    @classmethod
    def setCmdMgr(cls, mgr):
        """设置命令管理器"""
        cls._cmdMgr = mgr

    def isConnected(self):
        """检查是否已连接"""
        print('isConnected:', self.connected)
        return self.connected
    def disconnect(self):
        """断开连接"""
        if self.connected:
            self.sio.disconnect()
            Device.i(f'设备 {self.deviceID} 已断开连接')
            self.connected = False
    def connect(self, server_url):
        """连接到服务器"""
        Device.i(f'正在连接到服务器 {server_url}...')
        try:
            self.sio.connect(
                server_url,
                auth={'device_id': self.deviceID},
                wait_timeout=10,
                transports=['websocket', 'polling']
            )
            Device.i(f'连接成功，设备ID: {self.deviceID}')
            self.connected = True
            return True
        except Exception as e:
            Device.e(f'连接错误: {e}')
            return False

    def login(self):
        """设备登录"""
        self.sio.emit('device_login', {
            'device_id': self.deviceID,
            'timestamp': str(datetime.now())
        })
        return True
    
    def logout(self):
        self.sio.emit('device_logout', {
            'device_id': self.deviceID,
            'timestamp': str(datetime.now())
        })
        return True
    

    
    def on_command(self, data):
        Device.i(f'客户端收到命令: {data}')
        result = doCmd(data['command'])
        Device.i(f'客户端执行命令结果: {result}')
        if result is not None:
            response = {
                'device_id': self.deviceID,
                'result': result
            }
            Device.i(f'客户端发送响应: {response}')
            self.sio.emit('command_response', response)

    def on_command_result(self, data):
        """处理命令结果"""
        Device.i(f'命令结果: {data["result"]}')

    def on_connect(self):
        """连接成功回调"""
        Device.i('已连接到服务器')

    def on_connect_error(self, data):
        """连接错误回调"""
        Device.e(f'连接错误: {data}')

    def on_disconnect(self):
        """断开连接回调"""
        Device.w('断开连接')
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

    def send_log(self, message, level='info'):
        """发送日志到服务器"""
        if self.connected:
            self.sio.emit('client_log', {
                'device_id': self.deviceID,
                'message': message,
                'level': level
            })

    @staticmethod
    def _log(level, message):
        """内部日志处理方法"""
        timestamp = datetime.now()
        # print(f"[{timestamp}] [{level}] {message}")        
        # 如果实例存在且已连接，发送日志到服务器
        if Device._instance and Device._instance.connected:
            Device._instance.send_log(message, level)
            # 确保日志显示在最下面
            Device._instance.sio.emit('scroll_logs')
        else:
            builtins.print(f"[{timestamp}] [{level}] {message}")

    @staticmethod
    def i(message):
        """输出信息级别日志"""
        Device._log('INFO', message)

    @staticmethod
    def w(message):
        """输出警告级别日志"""
        Device._log('WARN', message)

    @staticmethod
    def e(message):
        """输出错误级别日志"""
        Device._log('ERROR', message)

    @staticmethod
    def print(message):
        Device.i(message)

