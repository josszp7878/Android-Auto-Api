import time
import socketio
import _G
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import cast, List, TYPE_CHECKING, Tuple
import socketio.exceptions  # 新增导入
from Base import Base_
from _Device import _Device_
from RPC import RPC
if TYPE_CHECKING:
    from CTask import CTask_
    from _App import _App_
    from CApp import CApp_


class CDevice_(Base_, _Device_):
    _instance = None  # 单例实例

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return
        super().__init__({})
        _Device_.__init__(self)  # 初始化App管理功能
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._state = _G.ConnectState.OFFLINE  # 新增，维护设备状态
        self._tasks = {}  # 任务字典，key为任务ID
        self._curTask = None
        # 统一使用data字典
        self.initialized = False
        self._running = False

    @classmethod
    def instance(cls, reset=False)->'CDevice_':
        """获取单例实例"""
        if cls._instance is None or reset:
            cls._instance = cls()
        return cls._instance

    @property
    def server(self):
        g = _G._G_
        return g.CFileServer().serverIP()

    def init(self, deviceID=None, server=None):
        if self.initialized:
            return
        g = _G._G_
        self.name = deviceID
        g.CFileServer().init(server)
        # 配置 socketio 客户端
        sio = socketio.Client(
            reconnection=True,  # 开启自动重连
            reconnection_attempts=10,  # 增加重连尝试次数
            reconnection_delay=2,  # 重连延迟时间（秒）
            reconnection_delay_max=30,  # 最大重连延迟时间
            logger=False,  # 关闭详细日志
            engineio_logger=False  # 关闭 Engine.IO 日志
        )
        sio.on('S2C_DoCmd')(self.onS2C_DoCmd)
        sio.on('S2C_CmdResult')(self.onS2C_CmdResult)
        sio.on('disconnect')(self.on_disconnect)
        _G._G_.setIO(sio)
        # 启动应用更新循环
        self._begin()
        self.initialized = True

    def uninit(self):
        """释放资源"""
        print('客户端 设备 uninit')
        # 结束应用更新循环
        self._end()
        self.logout()
        self.disconnect()
        self.initialized = False

    def disconnect(self) -> bool:
        """断开连接"""
        g = _G._G_
        log = g.Log()
        try:
            if not g.sio().connected:
                log.w(f"设备{self.name}已经断开，无需重复操作")
                return True

            g.sio().disconnect()
            log.i(f'设备 {self.name} 已断开连接')
            self._state = _G.ConnectState.OFFLINE  # 断开后状态设为offline
            return True
        except socketio.exceptions.ConnectionError as e:
            if "Already disconnected" in str(e):
                log.w(f"设备{self.name}已经断开连接")
                return True
            else:
                log.e(f"设备{self.name}断开失败: {str(e)}")
                return False
        except Exception as e:
            log.ex(e, f"设备{self.name}断开连接异常")
            return False

    def isConnected(self) -> bool:
        return self._state != _G.ConnectState.OFFLINE

    @RPC()
    def getDeviceInfo(self) -> dict:
        """获取设备信息 - RPC方法"""
        try:
            return {
                'result': {
                    'deviceId': self.id,
                    'deviceName': self.name,
                    'state': self._state.value if self._state else 'unknown',
                    'isConnected': self.isConnected(),
                    'taskCount': len(self._tasks),
                    'currentTask': (self._curTask.name 
                                   if self._curTask else None),
                    'server': self.server
                }
            }
        except Exception as e:
            return {
                'error': f"获取设备信息失败: {str(e)}"
            }

    def connect(self) -> bool:
        g = _G._G_
        log = g.Log()
        try:
            server_url = g.CFileServer().serverUrl()
            connect_url = f"{server_url}?device_id={self.name}"
            log.i(f"@@@@@连接地址: {connect_url}")
            sio = cast(socketio.Client, g.sio())

            log.i(f'正在连接设备 {self.name} ...')
            sio.connect(
                connect_url,
                transports=['websocket', 'polling'],
                auth={'device_id': self.name},
                wait=True,
                wait_timeout=30  # 增加连接超时时间
            )
            if sio.connected:
                self._state = _G.ConnectState.ONLINE
                return self.login()
            else:
                g.Tools().toast("无法连接到服务器")
                self._state = _G.ConnectState.OFFLINE
                return False
        except socketio.exceptions.ConnectionError as e:
            if "Already connected" in str(e):
                log.w(f"设备{self.name}已经连接，无需重复操作")
                return True  # 保持返回成功状态
            else:
                log.e(f"设备{self.name}连接失败: {str(e)}")
                return False
        except Exception as e:
            log.ex(e, f"设备{self.name}连接异常")
            return False

    def login(self):
        """异步登录示例"""
        g = _G._G_
        log = g.Log()
        try:
            log.i(f"设备 {self.name} 开始登录...")
            data = g.emitRet('C2S_Login', timeout=15)  # 增加登录超时时间
            if data is None:
                log.e_("登录失败，服务端无响应")
                return False
            # 登录成功，初始化任务表
            self.onLogin(data)
            log.i_("登录成功，已初始化任务表")
            self._state = _G.ConnectState.LOGIN  # 登录成功，状态设为login
            return True
        except Exception as e:
            log.ex_(e, "登录异常")
            return False

    def logout(self):
        """注销设备"""
        g = _G._G_
        log = g.Log()
        g.emit('C2S_Logout', {})
        log.i(f'设备 {self.name} 登出')
        self._state = _G.ConnectState.LOGOUT  # 登出后状态设为logout

    def onS2C_DoCmd(self, data):
        """处理客户端收到的命令"""
        g = _G._G_
        log = g.Log()
        cmd = data
        cmdName = data.get('cmd')
        try:
            g.CmdMgr().do(cmd)
            cmdName = cmd.get('cmd')
            if cmdName == 'reset':
                log.i(f'收到重置命令: {cmdName}，不发送结果')
                # 不发送结果，但也不抛出异常
                return
            result = cmd.get('result')
            return result
        except Exception as e:
            log.ex(e, f'执行命令出错: {cmdName}')
            return None

    def on_disconnect(self):
        """断开连接回调"""
        g = _G._G_
        log = g.Log()
        log.w(f'设备 {self.name} 断开连接')
        self._state = _G.ConnectState.OFFLINE  # 断开连接，状态设为offline

    def send_command(self, cmd):
        """发送命令到服务器"""
        g = _G._G_
        log = g.Log()
        log.i(f'TODO:发送命令到服务器: {cmd}')
        return True

    def onS2C_CmdResult(self, data):
        print(f'结果: {data["result"]}')

    def TakeScreenshot(self):
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
                g.emit("C2S_Screenshot", {
                       "device_id": self.name, "image": image})
        except Exception as e:
            log.ex(e, "截图失败")

    @property
    def name(self):
        """获取设备名称"""
        return self.data.get('name', '')

    @name.setter
    def name(self, value):
        """设置设备名称"""
        self.data['name'] = value
        g = _G._G_
        # 同步到Android 
        android = g.android
        if android:
            android.setName(value)

    def state(self):
        return self._state

    def _createApp(self, data: dict) -> '_App_':
        """创建App"""
        from CApp import CApp_
        return CApp_(data)

    def onLogin(self, data):
        """登录成功后初始化任务表和App列表，data为服务端返回的数据"""
        g = _G._G_
        log = g.Log()
        # log.i_(f"登录成功，初始化任务表, data: {data}")
        # 初始化任务表
        self._tasks = {}
        self._initTasks(data.get('taskList'))
        self._initApps(data.get('appList'))
        self.info = data.get('info')
        log.i_(f"客户端同步完成，应用数: {len(self.apps)}，任务数: {len(self._tasks)}")

    def _initTasks(self, taskList: list):
        """设置任务列表"""
        if taskList is None:
            return
        g = _G._G_
        log = g.Log()
        from CTask import CTask_
        for data in taskList:
            try:
                task = CTask_(data)
            except Exception as e:
                log.ex_(e, f"创建任务失败: {data}")
                continue
            self._tasks[task.id] = task

    def _initApps(self, apps: List['_App_']):
        if not apps:
            return
        g = _G._G_
        log = g.Log()
        from CApp import CApp_
        for data in apps:
            try:
                app = CApp_(data)
                app.loadConfig()
            except Exception as e:
                log.ex_(e, f"创建应用失败: {data}")
                continue
            self._apps[app.name] = app
        self._apps[_G.TOP] = CApp_({'name': _G.TOP})

    def getTask(self, key) -> 'CTask_':
        """根据ID获取任务"""
        g = _G._G_
        log = g.Log()
        try:
            # 同时支持ID和任务名
            id = g.toInt(key)
            if id:
                if id in self._tasks:
                    return self._tasks[id]
            else:
                id = key.lower()
                for t in self._tasks.values():
                    if t.name.lower() == id:
                        return t
            return None
        except Exception as e:
            log.ex(e, f'获取任务失败: {key}')
            return None

    def getTasks(self, name=None) -> List['CTask_']:
        """获取所有任务或指定名称的任务列表"""
        name = name.lower()
        if name is None:
            return list(self._tasks.values())
        return [t for t in self._tasks.values() if t.name.lower() == name]

    def curTask(self) -> 'CTask_':
        """获取当前任务"""
        return self._curTask

    def setCurTask(self, value: 'CTask_'):
        """设置当前任务"""
        self._curTask = value

    def _onProp(self, key, value):
        """CDevice特殊处理"""
        if key == 'name':
            # 同步到Android
            self.name = value

    @RPC()
    def getScreenInfo(self) -> dict:
        """RPC方法：获取客户端屏幕信息

        Returns:
            dict: RPC结果，包含屏幕信息列表或错误信息
        """
        g = _G._G_
        log = g.Log()
        try:
            tools = g.Tools()
            if not tools:
                return {'error': '工具类未初始化'}

            # 调用_Tools的getScreenInfo方法获取屏幕信息
            screenInfo = tools.getScreenInfo(refresh=True)

            if screenInfo:
                log.i(f"获取屏幕信息成功，共{len(screenInfo)}个元素")
                return {'result': screenInfo}
            else:
                return {'error': '获取屏幕信息为空'}

        except Exception as e:
            log.ex(e, "获取屏幕信息失败")
            return {'error': f'获取屏幕信息失败: {str(e)}'}

    @RPC()
    def setScreenInfo(self, screenInfos: list) -> dict:
        """RPC方法：设置客户端屏幕信息

        Args:
            screenInfos: 屏幕信息列表

        Returns:
            dict: RPC结果，包含设置结果或错误信息
        """
        g = _G._G_
        log = g.Log()
        try:
            tools = g.Tools()
            if not tools:
                return {'error': '工具类未初始化'}

            if not screenInfos:
                return {'error': '屏幕信息为空'}

            # 调用_Tools的setScreenInfo方法设置屏幕信息
            success = tools.setScreenInfo(screenInfos)

            if success:
                log.i(f"设置屏幕信息成功，共{len(screenInfos)}个元素")
                return {'result': {'success': True, 'count': len(screenInfos)}}
            else:
                return {'error': '设置屏幕信息失败'}

        except Exception as e:
            log.ex(e, "设置屏幕信息失败")
            return {'error': f'设置屏幕信息失败: {str(e)}'}
        
    def _isHome(self, appInfo: dict) -> bool:
        """判断当前是否在桌面
        通过当前应用包名判断是否在桌面，支持多种桌面应用
        Returns:
            bool: 是否在桌面
        """
        if not appInfo:
            return False
        g = _G._G_
        log = g.Log()

        if g.android is None:
            return True
        try:
            # 常见桌面应用包名列表
            LAUNCHER_PACKAGES = {
                'com.android.launcher3',         # 原生Android
                'com.google.android.apps.nexuslauncher',  # Pixel
                'com.sec.android.app.launcher',  # 三星
                'com.huawei.android.launcher',   # 华为
                'com.miui.home',                 # 小米
                'com.oppo.launcher',             # OPPO
                'com.vivo.launcher',             # vivo
                'com.realme.launcher',           # Realme
                'com.oneplus.launcher'           # 一加
            }

            # 修复: 正确处理Java的LinkedHashMap
            # 方法1: 使用Java的get方法，只传一个参数
            package_name = appInfo.get("packageName")
            if package_name is None:
                package_name = ""

            # 检查是否在已知桌面包名列表中
            if package_name in LAUNCHER_PACKAGES:
                return True

            # 检查包名是否包含launcher或home关键词
            if "launcher" in package_name.lower() or "home" in package_name.lower():
                return True
            
            return False
        except Exception as e:
            log.ex(e, "判断是否在桌面失败")
            return False

    def detectApp(self, interval) -> 'CApp_':
        """获取当前应用"""
        g = _G._G_
        log = g.Log()
        try:
            android = g.android
            if android:
                appInfo = android.getCurrentApp(interval)
                if appInfo:
                    # 将Java的LinkedHashMap转换为Python dict
                    appInfo = {
                        'packageName': str(appInfo.get('packageName')),
                        'appName': str(appInfo.get('appName')),
                    }
                    # log.i(f"当前应用: {appInfo}, type: {type(appInfo)}")
                    if self._isHome(appInfo):
                        appInfo = {'appName': _G.TOP}
            else:
                appInfo = self._curAppInfo if self._curAppInfo else {'appName': _G.TOP}
            self.setCurApp(appInfo)
            return self.currentApp
        except Exception as e:
            log.ex(e, "获取当前应用失败")
            return None

    def closeApp(self, name=None) -> bool:
        """关闭应用"""
        g = _G._G_
        log = g.Log()
        try:
            if name is None:
                name = g.CDevice().currentApp.name  # 通过cur方法获取实例名称
            name = self.matchApp(name)
            app = self.getApp(name)
            if not app:
                return False
            # 保存计数器数据
            # app._saveData()
            app.stop()
        except Exception as e:
            log.ex(e, f"关闭应用 {name} 失败")

    # 返回值:
    # bool: 是否打开成功
    # _App_: 应用实例
    def open(self, name)->Tuple[bool, '_App_']:
        """跳转到指定应用"""
        try:
            g = _G._G_
            log = g.Log()
            appName = self.matchApp(name)
            if not appName:
                log.w(f"未知应用:{name}")
                ret = self._open(name)
                return ret, None
            else:
                app = self.getApp(appName)
                if not app:
                    log.w(f"未配置应用:{appName}")
                ret = self._open(appName)
                return ret, app
        except Exception as e:
            log.ex(e, f"跳转到应用 {appName} 失败")
            return False, None

    def _open(self, appName:str)->bool:
        """跳转到指定应用"""
        g = _G._G_
        log = g.Log()
        appName = appName.strip().lower() if appName else ''
        if appName == '':
            return False
        if g.isAndroid():
            # 这里不直接setCurAppName，有detectApp()去检测
            try:
                tools = g.Tools()
                log.i(f"打开应用: {appName}, android: {g.android}")
                if appName == _G.TOP:
                    return tools.goHome()
                else:
                    # 根据系统类型选择打开方式
                    if tools.isHarmonyOS():
                        log.i(f"当前应用: {self.curAppName}, 目标应用: {appName}")
                        if appName == self.curAppName:
                            return True
                        log.i(f"返回桌面: {appName}")
                        if not tools.goHome():
                            log.e(f"返回桌面失败: {appName}")
                            return False
                        # 等待2秒, 确保回到桌面
                        time.sleep(2)
                        log.i(f"点击应用: {appName}")
                        return tools.click(appName, 'LR')
                    else:
                        # Android系统使用服务方式打开
                        opened = g.android.openApp(appName)
                return opened
            except Exception as e:
                log.ex(e, "打开应用失败")
                return False
        else:
            self.setCurApp({'appName': appName})
        return True

    def _update(self):
        """全局应用更新循环 - 客户端版本"""
        interval = 2
        g = _G._G_
        log = g.Log()
        # log.i(f"应用更新循环开始, 当前应用: {self.curAppName}, running: {self._running}")
        while self._running:
            time.sleep(interval)
            # log.i(f"应用更新循环开始, 当aaaa前应用: {self.curAppName}")
            app = self.detectApp(interval)
            if app :
                # 只更新客户端应用实例
                app.doUpdate()

    def _begin(self):
        """启动全局应用更新循环线程 - 客户端版本"""
        thread = threading.Thread(target=self._update)
        thread.start()
        self._running = True

    def _end(self):
        """结束全局应用更新循环线程 - 客户端版本"""
        self._running = False

        
    @classmethod
    def onLoad(cls, oldCls : 'CDevice_'):
        if oldCls:
            instance = oldCls.instance()
            instance.uninit()
            # 保存旧的连接信息
            old_name = instance.name
            old_server = instance.server
            # 先断开旧连接
            instance.disconnect()
            # 重置初始化状态，强制重新初始化
            instance = cls.instance()
            # 重新初始化Socket.IO实例
            instance.init(old_name, old_server)
            log = _G._G_.Log()
            log.i(f"设备 {instance.name}:{instance.server} 重置完成")
            # 重新连接
            instance.connect()


    @classmethod
    def onUnload(cls):
        cls.instance().uninit()


CDevice_.instance().onLoad(None)
