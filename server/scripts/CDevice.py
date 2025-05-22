import socketio
import threading
from datetime import datetime
import time
import _G

class CDevice_:
    _instance = None  # 单例实例
    _server = None
    _deviceID = None
    _connected = False

    @classmethod
    def connected(cls):
        return cls._connected


    @classmethod
    def deviceID(cls):
        return cls._deviceID

    @classmethod
    def server(cls):
        return cls._server

    @classmethod
    def init(cls, deviceID=None, server=None):
        if not hasattr(cls, 'initialized'):
            cls._deviceID = deviceID
            cls._server = server
            cls._connected = False
            # 配置 socketio 客户端
            sio = socketio.Client(
                reconnection=True,
                reconnection_attempts=5,
                reconnection_delay=1,
                reconnection_delay_max=5,
                logger=False,  # 关闭详细日志
                engineio_logger=False  # 关闭 Engine.IO 日志
            )

            # 注册事件处理器
            sio.on('connect')(cls.on_connect)
            sio.on('S2C_DoCmd')(cls.onS2C_DoCmd)
            sio.on('S2C_CmdResult')(cls.onS2C_CmdResult)
            sio.on('disconnect')(cls.on_disconnect)
            sio.on('connect_error')(cls.on_connect_error)
            _G._G_.sio = sio

            # 添加通用事件监听器，捕获所有事件
            # self.sio.on('*')(self.on_any_event)
            cls.initialized = True

    @classmethod
    def uninit(cls):
        """释放资源"""
        print('客户端 设备 uninit')
        cls.logout()
        cls.disconnect()
        cls.initialized = False
    # def on_any_event(self, event, data):
    #     """捕获所有事件"""
    #     try:
    #         if event not in ['connect', 'S2C_DoCmd', 'S2C_CmdResult', 'disconnect', 'connect_error']:
    #             _Log._Log_.i(f'收到未处理的事件: {event}, 数据: {data}')
    #     except Exception as e:
    #         _Log._Log_.ex(e, f'处理事件 {event} 出错')


    @classmethod
    def disconnect(cls):
        """断开连接"""
        g = _G._G_
        log = g.Log()
        try:
            if cls._connected:
                log.i(f'正在断开设备 {cls._deviceID} 的连接...')
                _G._G_.sio.disconnect()
                log.i(f'设备 {cls._deviceID} 已断开连接')
                cls._connected = False
            else:
                log.i(f'设备 {cls._deviceID} 未连接，无需断开')
        except Exception as e:
            log.ex(e, '断开连接时发生错误')

    @classmethod
    def connect(cls):
        """连接服务器核心逻辑"""
        waitting = True
        tools = _G._G_.Tools()
        def onConnected(ok):
            nonlocal waitting
            waitting = False
            if not ok:
                tools.toast("服务器连接失败")
        cls._connect(onConnected)
        timeout = 30
        start_time = time.time()
        while waitting:
            if time.time() - start_time > timeout:
                print("连接超时")
                break
            time.sleep(1)
            print(".", end="", flush=True)

        if not cls._connected:
            tools.toast("无法连接到服务器")

    @classmethod
    def _connect(cls, callback=None):
        """连接到服务器（异步方式）"""
        g = _G._G_
        log = g.Log()
        try:
            # 如果已连接，先断开
            if cls._connected:
                log.i('客户端已经连接')
                return
            connect_url = f"{g.Tools().getServerURL(cls._server)}?device_id={cls._deviceID}"
            # log.i(f"开始连接: {connect_url}")

            def connect_async():
                try:
                    # log.i("正在创建连接...")
                    # # 测试网络连接
                    # import socket
                    # try:
                    #     # 解析主机名
                    #     host = server_url.split('://')[1].split(':')[0]
                    #     port = int(server_url.split(':')[-1].split('?')[0])
                    #     log.i(f"正在测试连接到主机: {host}:{port}")

                    #     # 创建socket连接测试
                    #     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    #         sock.settimeout(5)
                    #         sock.connect((host, port))
                    #         log.i(f"网络连接测试成功: {host}:{port}")
                    # except Exception as e:
                    #     log.e(f"网络连接测试失败: {str(e)}")
                    #     if callback:
                    #         callback(False)
                    #     return
                    try:
                        # 使用已有的socketio客户端进行连接
                        # log.i("开始 socketio 连接...")
                        _G._G_.sio.connect(
                            connect_url,
                            transports=['websocket', 'polling'],
                            auth={'device_id': cls._deviceID}
                        )
                        # log.d("socketio 连接成功")
                        if callback:
                            callback(True)
                    except Exception as e:
                        log.e(f"socketio 连接失败: {str(e)}")
                        if callback:
                            callback(False)
                except Exception as e:
                    log.e(f"连接过程发生异常: {str(e)}")
                    if callback:
                        callback(False)

            threading.Thread(target=connect_async, daemon=True).start()
            return True

        except Exception as e:
            log.ex(e, '启动连接失败')
            if callback:
                callback(False)
            return False

    @classmethod
    def login(cls):
        """登录设备（带重试）"""
        g = _G._G_
        log = g.Log()
        if not cls._connected:
            log.w(f"设备 {cls._deviceID} 未连接，无法登录")
            return False

        retry_count = 3
        while retry_count > 0:
            try:
                # log.i(f"尝试登录设备 {cls._deviceID}，剩余尝试次数: {retry_count}")
                cls.emit('C2S_Login', {
                    'device_id': cls._deviceID,
                    'timestamp': str(datetime.now()),
                    'status': 'login'
                })
                return True
            except Exception as e:
                retry_count -= 1
                if retry_count == 0:
                    log.ex(e, '登录重试失败')
                    return False
                log.w(f'登录失败，剩余重试次数: {retry_count}')
                time.sleep(1)  # 重试前等待

    @classmethod
    def logout(cls):
        """注销设备"""
        g = _G._G_
        log = g.Log()
        cls.emit('C2S_Logout', {
            'device_id': cls._deviceID
        })
        log.i("设备已注销")


    @classmethod
    def onS2C_DoCmd(cls, data):
        """处理客户端收到的命令"""
        g = _G._G_
        log = g.Log()
        try:
            command = data.get('command')
            cmdData = data.get('data', None)
            cmd_id = data.get('cmd_id')  # 获取命令ID

            # 使用 CmdMgr 执行命令
            cmd = {'id': cmd_id, 'data': cmdData, 'cmd': command}
            g.CmdMgr().do(cmd)
            cmdName = cmd.get('name')
            if cmdName == 'reset':
                log.i(f'收到重置命令: {command}，不发送结果')
                # 不发送结果，但也不抛出异常
                return
            # 发送命令结果，无需在这里单独记录日志，因为CmdResult会在服务端被处理并记录
            cls._sendCmdResult(cmd)
        except Exception as e:
            log.ex(e, f'执行命令出错: {command}')

    @classmethod
    def _sendCmdResult(cls, cmd):
        """发送命令结果"""
        cls.emit('C2S_CmdResult', {
            'result': cmd.get('result'),
            'device_id': cls._deviceID,
            'cmdName': cmd.get('name'),
            'cmd_id': cmd.get('id')  # 返回命令ID
        })

    @classmethod
    def sendCmdResult(cls, cmd, result):
        """发送命令结果"""
        if cmd is None:
            return
        cmd['result'] = result
        cls._sendCmdResult(cmd)

    @classmethod
    def on_connect(cls):
        """连接成功回调"""
        g = _G._G_
        log = g.Log()
        log.i(f'已连接到服务器, server: {cls._server}')
        cls._connected = True

        # 连接成功后在新线程中执行登录
        def do_login():
            try:
                if cls.login():
                    log.i("登录成功")
                else:
                    log.e("登录失败")
            except Exception as e:
                log.ex(e, "登录过程出错")

        threading.Thread(target=do_login, daemon=True).start()

    @classmethod
    def on_connect_error(cls, data):
        """连接错误回调"""
        g = _G._G_
        log = g.Log()
        log.e(f'连接错误: {data}')
        # 尝试记录更详细的错误信息
        if hasattr(data, 'args') and len(data.args) > 0:
            log.e(f'连接错误详情: {data.args[0]}')

        # 如果是认证错误，可能是设备ID冲突
        error_msg = str(data)
        if 'authentication' in error_msg.lower() or 'auth' in error_msg.lower():
            log.e(f'可能是设备ID {cls._deviceID} 已被使用，请尝试使用其他设备ID')

    @classmethod
    def on_disconnect(cls):
        """断开连接回调"""
        g = _G._G_
        log = g.Log()
        log.w(f'设备 {cls._deviceID} 断开连接，SID: {_G._G_.sio.sid if hasattr(_G._G_.sio, "sid") else "未知"}')
        cls._connected = False

    @classmethod
    def send_command(cls, cmd):
        """发送命令到服务器"""
        g = _G._G_
        log = g.Log()
        log.i(f'TODO:发送命令到服务器: {cmd}')
        return True

    @classmethod
    def onS2C_CmdResult(cls, data):
        print(f'结果: {data["result"]}')

    @classmethod
    def emit(cls, event, data=None):
        """发送事件到服务器
        Args:
            event: 事件名称
            data: 事件数据
        Returns:
            bool: 是否发送成功
        """
        g = _G._G_
        log = g.Log()
        try:
            sio = g.sio
            if not sio:
                log.log_('e', "Socket未初始化")
                return False
            if not sio.connected:
                log.log_('e', "未连接到服务器")
                return False
            data['device_id'] = cls._deviceID
            sio.emit(event, data)
            return True
        except Exception as e:
            log.ex_(e, f'发送事件失败: {event}')
            return False

    @classmethod
    def TakeScreenshot(cls):
        """截取当前屏幕并发送到服务器"""
        g = _G._G_
        log = g.Log()
        try:
            android = g.android
            if not android:
                log.e("Android环境未初始化")
                return False
            image = android.takeScreenshot()
            log.i(f'截图成功: {image}')
            if image:
                cls.emit("C2S_Screenshot", {"device_id": cls._deviceID, "image": image})
        except Exception as e:
            log.ex(e, "截图失败")


    @classmethod
    def onUnload(cls):
        cls.uninit()

    @classmethod
    def onLoad(cls, oldCls):
        if oldCls:
            cls._server = oldCls._server
            cls._deviceID = oldCls._deviceID
            cls.init()
            cls.connect()

CDevice_.onLoad(None)