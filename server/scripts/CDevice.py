import socketio
import threading
from datetime import datetime
from pathlib import Path
from logger import Log
import time

class CDevice:
    currentAppName = ""
    _instance = None  # 单例实例
    _cmdMgr = None   # 命令管理器实例
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

    def __init__(self, deviceID=None):
        if not hasattr(self, 'initialized'):
            self._deviceID = deviceID
            self.connected = False            
            # 配置 socketio 客户端
            self.sio = socketio.Client(
                reconnection=True,
                reconnection_attempts=3,
                reconnection_delay=1,
                reconnection_delay_max=5,
                logger=False,
                engineio_logger=False
            )
            
            # 注册事件处理器
            self.sio.on('connect')(self.on_connect)
            self.sio.on('S2C_DoCmd')(self.onS2C_DoCmd)
            self.sio.on('S2C_CmdResult')(self.onS2C_CmdResult)
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
            
    def connect(self, server_url=None, callback=None):
        """连接到服务器（异步方式）"""
        try:
            connect_url = f"{server_url}?device_id={self.deviceID}"
            Log.i(f"开始连接: {connect_url}")
            
            def connect_async():
                try:
                    Log.i("正在创建连接...")
                    
                    # 测试网络连接
                    import socket
                    try:
                        # 解析主机名
                        host = server_url.split('://')[1].split(':')[0]
                        port = int(server_url.split(':')[-1].split('?')[0])
                        Log.i(f"正在测试连接到主机: {host}:{port}")
                        
                        # 创建socket连接测试
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                            sock.settimeout(5)
                            sock.connect((host, port))
                            Log.i(f"网络连接测试成功: {host}:{port}")
                    except Exception as e:
                        Log.e(f"网络连接测试失败: {str(e)}")
                        if callback:
                            callback(False)
                        return
                    
                    try:
                        # 最简单的连接配置
                        Log.i("开始 socketio 连接...")
                        self.sio.connect(
                            connect_url,
                            transports=['websocket', 'polling'],
                            auth={'device_id': self.deviceID}  # 新版本使用 auth 参数
                        )
                        Log.i("socketio 连接成功")
                        if callback:
                            callback(True)
                    except Exception as e:
                        Log.e(f"socketio 连接失败: {str(e)}")
                        if callback:
                            callback(False)
                except Exception as e:
                    Log.e(f"连接过程发生异常: {str(e)}")
                    if callback:
                        callback(False)
            
            threading.Thread(target=connect_async, daemon=True).start()
            return True
            
        except Exception as e:
            Log.ex(e, '启动连接失败')
            if callback:
                callback(False)
            return False

    def login(self):
        """登录设备（带重试）"""
        if not self.connected:
            return False
            
        retry_count = 3
        while retry_count > 0:
            try:
                self.sio.emit('device_login', {
                    'device_id': self.deviceID,
                    'timestamp': str(datetime.now()),
                    'status': 'login'
                })
                return True
            except Exception as e:
                retry_count -= 1
                if retry_count == 0:
                    Log.ex(e, '登录重试失败')
                    return False
                Log.w(f'登录失败，剩余重试次数: {retry_count}')
                time.sleep(1)  # 重试前等待

    def logout(self):
        self.sio.emit('device_logout', {
            'device_id': self.deviceID,
            'timestamp': str(datetime.now())
        })
        return True
    

    
    def onS2C_DoCmd(self, data):
        """处理客户端收到的命令"""
        try:
            command = data.get('command')
            print(f'正在处理命令: {command}')
            # 使用 CmdMgr 执行命令
            from CmdMgr import CmdMgr
            result, cmdName = CmdMgr().do(command)
            
            self.sio.emit('C2S_CmdResult', {
                'result': result,
                'device_id': self.deviceID,
                'command': command,
                'cmdName': cmdName
            })
        except Exception as e:
            result = Log.formatEx(f'执行命令出错: {e}')
            self.sio.emit('C2S_CmdResult', {
                'result': result,
                'device_id': self.deviceID,
                'command': command,
                'cmdName': None
            })
    
    def on_connect(self):
        """连接成功回调"""
        sid = self.sio.sid
        Log.i(f'已连接到服务器, SID: {sid}')
        self.connected = True
        
        # 连接成功后在新线程中执行登录
        def do_login():
            try:
                if self.login():
                    Log.i("登录成功")
                else:
                    Log.e("登录失败")
            except Exception as e:
                Log.ex(e, "登录过程出错")
        
        threading.Thread(target=do_login, daemon=True).start()

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
        return True
    
    def onS2C_CmdResult(self, data):
        print(f'结果: {data["result"]}')

    def emit(self, event, data=None):
        """发送事件到服务器
        Args:
            event: 事件名称
            data: 事件数据
        Returns:
            bool: 是否发送成功
        """
        try:
            if not self.connected:
                Log.e("未连接到服务器")
                return False
            
            if not self.sio:
                Log.e("Socket未初始化")
                return False
                
            self.sio.emit(event, data)
            return True
        except Exception as e:
            Log.ex(e, "发送事件失败")
            return False
 