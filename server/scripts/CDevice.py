import socketio
import threading
import _G
from concurrent.futures import ThreadPoolExecutor
import traceback
from typing import cast

class CDevice_:
    _instance = None  # 单例实例
    _server = None
    _deviceID = None
    _connected = False
    _executor = ThreadPoolExecutor(max_workers=4)
    _state = 'offline'  # 新增，维护设备状态
    _connectLock = threading.Lock()

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
            # 配置 socketio 客户端（关闭自动重连）
            sio = socketio.Client(
                reconnection=False,  # 关闭自动重连
                logger=False,  # 关闭详细日志
                engineio_logger=False  # 关闭 Engine.IO 日志
            )
            sio.on('connect')(cls.on_connect)
            sio.on('S2C_DoCmd')(cls.onS2C_DoCmd)
            sio.on('S2C_CmdResult')(cls.onS2C_CmdResult)
            sio.on('S2C_updateDevice')(cls.handleUpdateDevice)
            sio.on('S2C_updateTask')(cls.handleUpdateTask)
            sio.on('disconnect')(cls.on_disconnect)
            sio.on('connect_error')(cls.on_connect_error)
            _G._G_.setIO(sio)
            cls.initialized = True

    @classmethod
    def uninit(cls):
        """释放资源"""
        print('客户端 设备 uninit')
        cls.logout()
        cls.disconnect()
        cls.initialized = False


    @classmethod
    def disconnect(cls)->bool:
        """断开连接"""
        g = _G._G_
        log = g.Log()
        if cls._state == 'offline':
            log.i(f'设备 {cls._deviceID} 已处于离线状态，无需断开')
            return False
        try:
            if cls._connected:
                log.i(f'正在断开设备 {cls._deviceID} 的连接...')
                g.sio().disconnect()
                log.i(f'设备 {cls._deviceID} 已断开连接')
                cls._connected = False
                cls._state = 'offline'  # 断开后状态设为offline
                return True
            else:
                log.i(f'设备 {cls._deviceID} 未连接，无需断开')
                return False
        except Exception as e:
            log.ex(e, '断开连接时发生错误')
            return False

    @classmethod
    def connect(cls) -> bool:
        g = _G._G_
        log = g.Log()
        try:
            if cls._connected:
                log.i('客户端已经连接')
                return True
            connect_url = f"{g.Tools().getServerURL(cls._server)}?device_id={cls._deviceID}"
            sio = cast(socketio.Client, g.sio())
            sio.connect(
                connect_url,
                transports=['websocket', 'polling'],
                auth={'device_id': cls._deviceID},
                wait=True,
                wait_timeout=5
            )
            if sio.connected:
                cls._state = 'online'
                return cls.login()
            else:
                g.Tools().toast("无法连接到服务器")
                cls._state = 'offline'
                return False
        except Exception as e:
            log.ex(e, '连接失败')
            return False

    @classmethod
    def login(cls):
        """异步登录示例"""
        g = _G._G_
        log = g.Log()
        try:
            ok = g.emitRet('C2S_Login')
            if ok:
                log.i_("登录成功")
                cls._state = 'login'  # 登录成功，状态设为login
                return True
            log.e_("登录失败")
            return False
        except Exception as e:
            log.ex_(e, "登录异常")
            return False
    
    @classmethod
    def logout(cls):
        """注销设备"""
        g = _G._G_
        log = g.Log()
        g.emit('C2S_Logout', {})
        log.i(f'设备 {cls._deviceID} 登出')
        cls._state = 'logout'  # 登出后状态设为logout


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
            result = cmd.get('result')
            return result
        except Exception as e:
            log.ex(e, f'执行命令出错: {command}')
            return None

    @classmethod
    def on_connect(cls):
        """连接成功回调"""
        g = _G._G_
        log = g.Log()
        log.i(f'已连接到服务器, server: {cls._server}')
        cls._connected = True
        cls._state = 'online'  # 连接成功，状态设为online
        threading.Thread(target=cls.login, daemon=True).start()

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
        log.w(f'设备 {cls._deviceID} 断开连接')
        cls._connected = False
        cls._state = 'offline'  # 断开连接，状态设为offline

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
                g.emit("C2S_Screenshot", {"device_id": cls._deviceID, "image": image})
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

   
    @property
    def deviceId(self):
        """获取设备ID"""
        return self._deviceId
    
    @classmethod
    def handleUpdateDevice(cls, data):
        g = _G._G_
        log = g.Log()
        try:
            name = data.get('name')
            newDeviceId = name
            if newDeviceId != self._deviceId:
                return
            self._deviceId = newDeviceId
            log.i(f'客户端设备ID已更新: {self._deviceId}')
            return True
        except Exception as e:
            log.ex(e, '处理设备更新请求失败')
            return False

    @classmethod
    def handleUpdateTask(cls, data):
        g = _G._G_
        log = g.Log()
        try:
            if not data:
                return
            taksName = data.get('name')
            task = g.App().getTask(taksName)
            if task is None:
                return
            for k, v in data.items():
                # 优先找 setXxx 方法
                method_name = f'set{k[0].upper()}{k[1:]}'
                setter = getattr(task, method_name, None)
                if callable(setter):
                    setter(v)
                    log.i_(f'调用方法: {method_name}({v})')
                else:
                    try:
                        setattr(task, k, v)
                        log.i_(f'设置属性: {k} = {v}')
                    except AttributeError as e:
                        # log.w_(f'属性 {k} 不能赋值: {e}')
                        pass
            return True
        except Exception as e:
            log.ex(e, '处理任务更新请求失败')
            return False

    @classmethod
    def state(cls):
        return cls._state

CDevice_.onLoad(None)