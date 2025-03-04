import socketio
import threading
from datetime import datetime
from _Log import _Log
from CTools import CTools
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
            self.server_url = None
            # 配置 socketio 客户端
            self.sio = socketio.Client(
                reconnection=True,
                reconnection_attempts=5,
                reconnection_delay=1,
                reconnection_delay_max=5,
                logger=False,  # 关闭详细日志
                engineio_logger=False  # 关闭 Engine.IO 日志
            )
            
            # 注册事件处理器
            self.sio.on('connect')(self.on_connect)
            self.sio.on('S2C_DoCmd')(self.onS2C_DoCmd)
            self.sio.on('S2C_CmdResult')(self.onS2C_CmdResult)
            self.sio.on('disconnect')(self.on_disconnect)
            self.sio.on('connect_error')(self.on_connect_error)
            
            # 添加通用事件监听器，捕获所有事件
            # self.sio.on('*')(self.on_any_event)
            
            self.initialized = True

    def uninit(self):
        """释放资源"""
        print('客户端 设备 uninit')
        self.logout()
        self.disconnect()
        self.initialized = False
    # def on_any_event(self, event, data):
    #     """捕获所有事件"""
    #     try:
    #         if event not in ['connect', 'S2C_DoCmd', 'S2C_CmdResult', 'disconnect', 'connect_error']:
    #             Log.i(f'收到未处理的事件: {event}, 数据: {data}')
    #     except Exception as e:
    #         Log.ex(e, f'处理事件 {event} 出错')    
        
    def isConnected(self):
        """检查是否已连接"""
        print('isConnected:', self.connected)
        return self.connected
    def disconnect(self):
        """断开连接"""
        try:
            if self.connected:
                _Log.i(f'正在断开设备 {self.deviceID} 的连接...')
                self.sio.disconnect()
                _Log.i(f'设备 {self.deviceID} 已断开连接')
                self.connected = False
            else:
                _Log.i(f'设备 {self.deviceID} 未连接，无需断开')
        except Exception as e:
            _Log.ex(e, '断开连接时发生错误')

    def connect(self, server_url=None, callback=None):
        """连接到服务器（异步方式）"""
        try:
            # 如果已连接，先断开
            if self.connected:
                print('客户端已经连接')
                return
            
            if not server_url:
                server_url = self.server_url
            else:
                self.server_url = server_url
            connect_url = f"{server_url}?device_id={self.deviceID}"
            # Log.i(f"开始连接: {connect_url}")
            
            def connect_async():
                try:
                    # Log.i("正在创建连接...")
                    # # 测试网络连接
                    # import socket
                    # try:
                    #     # 解析主机名
                    #     host = server_url.split('://')[1].split(':')[0]
                    #     port = int(server_url.split(':')[-1].split('?')[0])
                    #     Log.i(f"正在测试连接到主机: {host}:{port}")
                        
                    #     # 创建socket连接测试
                    #     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    #         sock.settimeout(5)
                    #         sock.connect((host, port))
                    #         Log.i(f"网络连接测试成功: {host}:{port}")
                    # except Exception as e:
                    #     Log.e(f"网络连接测试失败: {str(e)}")
                    #     if callback:
                    #         callback(False)
                    #     return
                    try:
                        # 使用已有的socketio客户端进行连接
                        # Log.i("开始 socketio 连接...")
                        self.sio.connect(
                            connect_url,
                            transports=['websocket', 'polling'],
                            auth={'device_id': self.deviceID}
                        )
                        # Log.d("socketio 连接成功")
                        if callback:
                            callback(True)
                    except Exception as e:
                        _Log.e(f"socketio 连接失败: {str(e)}")
                        if callback:
                            callback(False)
                except Exception as e:
                    _Log.e(f"连接过程发生异常: {str(e)}")
                    if callback:
                        callback(False)
            
            threading.Thread(target=connect_async, daemon=True).start()
            return True
            
        except Exception as e:
            _Log.ex(e, '启动连接失败')
            if callback:
                callback(False)
            return False

    def login(self):
        """登录设备（带重试）"""
        if not self.connected:
            _Log.w(f"设备 {self.deviceID} 未连接，无法登录")
            return False
        
        retry_count = 3
        while retry_count > 0:
            try:
                _Log.i(f"尝试登录设备 {self.deviceID}，剩余尝试次数: {retry_count}")
                self.sio.emit('device_login', {
                    'device_id': self.deviceID,
                    'timestamp': str(datetime.now()),
                    'status': 'login'
                })
                return True
            except Exception as e:
                retry_count -= 1
                if retry_count == 0:
                    _Log.ex(e, '登录重试失败')
                    return False
                _Log.w(f'登录失败，剩余重试次数: {retry_count}')
                time.sleep(1)  # 重试前等待

    def logout(self):
        """注销设备"""
        try:
            if self.sio and self.sio.connected:
                self.sio.emit('device_logout', {
                    'device_id': self.deviceID
                })
                _Log.i("设备已注销")
            else:
                _Log.w("设备未连接，无法注销")
        except Exception as e:
            _Log.ex(e, "注销设备失败")
    

    
    def onS2C_DoCmd(self, data):
        """处理客户端收到的命令"""
        try:
            command = data.get('command')
            sender = data.get('sender')
            cmdData = data.get('data', {})
            cmd_id = data.get('cmd_id')  # 获取命令ID
            
            _Log.i(f'收到命令: {command} from {sender} data: {cmdData}')
            # 使用 CmdMgr 执行命令
            from _CmdMgr import _CmdMgr
            result, cmdName = _CmdMgr.do(command, sender, cmdData)
            
            self.sio.emit('C2S_CmdResult', {
                'result': result,
                'device_id': self.deviceID,
                'command': command,
                'cmdName': cmdName,
                'cmd_id': cmd_id  # 返回命令ID
            })
        except Exception as e:
            _Log.ex(e, f'执行命令出错: {command}')
            # 发送错误结果
            self.sio.emit('C2S_CmdResult', {
                'result': f'e->{str(e)}',
                'device_id': self.deviceID,
                'command': command,
                'cmdName': 'error',
                'cmd_id': data.get('cmd_id')  # 返回命令ID
            })
    
    def on_connect(self):
        """连接成功回调"""
        sid = self.sio.sid
        _Log.i(f'已连接到服务器, SID: {sid}')
        self.connected = True
        
        # 连接成功后在新线程中执行登录
        def do_login():
            try:
                if self.login():
                    _Log.i("登录成功")
                else:
                    _Log.e("登录失败")
            except Exception as e:
                _Log.ex(e, "登录过程出错")
        
        threading.Thread(target=do_login, daemon=True).start()

    def on_connect_error(self, data):
        """连接错误回调"""
        _Log.e(f'连接错误: {data}')
        # 尝试记录更详细的错误信息
        if hasattr(data, 'args') and len(data.args) > 0:
            _Log.e(f'连接错误详情: {data.args[0]}')
        
        # 如果是认证错误，可能是设备ID冲突
        error_msg = str(data)
        if 'authentication' in error_msg.lower() or 'auth' in error_msg.lower():
            _Log.e(f'可能是设备ID {self.deviceID} 已被使用，请尝试使用其他设备ID')

    def on_disconnect(self):
        """断开连接回调"""
        _Log.w(f'设备 {self.deviceID} 断开连接，SID: {self.sio.sid if hasattr(self.sio, "sid") else "未知"}')
        self.connected = False

    def send_command(self, cmd):
        """发送命令到服务器"""
        _Log.i(f'TODO:发送命令到服务器: {cmd}')
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
                _Log.e("未连接到服务器")
                return False
            
            if not self.sio:
                _Log.e("Socket未初始化")
                return False
                
            data['device_id'] = self.deviceID
            self.sio.emit(event, data)
            return True
        except Exception as e:
            _Log.ex(e, "发送事件失败")
            return False

    def TakeScreenshot(self):
        """截取当前屏幕并发送到服务器"""
        android = CTools.android()
        if not android:
            _Log.e("Android环境未初始化")
            return False
        image = android.takeScreenshot()
        if image:
            self.emit("C2S_Screenshot", {"device_id": self.deviceID, "image": image})
        return True