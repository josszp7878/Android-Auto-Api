
import time
import socketio
import _G
from concurrent.futures import ThreadPoolExecutor
from typing import cast, List, TYPE_CHECKING, Optional, Tuple
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
        self._server = None
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._state = _G.ConnectState.OFFLINE  # 新增，维护设备状态
        self._tasks = {}  # 任务字典，key为任务ID
        self._curTask = None
        # 统一使用data字典
        self.initialized = False

    @classmethod
    def instance(cls, reset=False):
        """获取单例实例"""
        if reset:
            cls._instance = None
        if cls._instance is None or reset:
            cls._instance = cls()
        return cls._instance

    @property
    def server(self):
        return self._server

    def get(self, key):
        """获取设备数据"""
        return self.data.get(key)

    def init(self, deviceID=None, server=None):
        if self.initialized:
            return
        self.name = deviceID
        self._server = server
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
        sio.on('S2C_updateTask')(self.onS2C_updateTask)
        sio.on('S2C_updateDevice')(self.onS2C_updateDevice)
        sio.on('S2C_SetProp')(self.onS2C_SetProp)
        sio.on('disconnect')(self.on_disconnect)
        _G._G_.setIO(sio)
        self.initialized = True

    def uninit(self):
        """释放资源"""
        print('客户端 设备 uninit')
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
                    'currentTask': self._curTask.name if self._curTask else None,
                    'server': self._server
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
            connect_url = f"{g.Tools().getServerURL(self._server)}?device_id={self.name}"
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
        log.w(f'设备 {self._deviceID} 断开连接')
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
                       "device_id": self._deviceID, "image": image})
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
        # 同步到Android SharedPreferences
        self._setName(value)

    def _setName(self, deviceName):
        """同步设备名称到Android SharedPreferences"""
        g = _G._G_
        log = g.Log()
        # 方案1: 通过反射调用Android API
        if g.android:
            # 获取Context
            context = g.android.getContext()
            if context:
                # 获取SharedPreferences
                prefs = context.getSharedPreferences(
                    "device_config", 0)  # 0 = MODE_PRIVATE
                editor = prefs.edit()
                editor.putString("DEVICE_NAME_KEY", deviceName)
                editor.apply()
                log.i(f"设备名称已同步到Android: {deviceName}")
                return True

        # 方案2: 如果上面失败，尝试通过脚本引擎执行
        try:
            # 构造JavaScript代码调用Android API
            jsCode = f'''
            try {{
                var prefs = getPrefs();
                prefs.edit().putString("DEVICE_NAME_KEY", "{deviceName}").apply();
                true;
            }} catch(e) {{
                console.log("同步设备名称失败: " + e.message);
                false;
            }}
            '''

            # 如果有脚本引擎，执行JavaScript代码
            if hasattr(g, 'scriptEngine') and g.scriptEngine:
                result = g.scriptEngine.eval(jsCode)
                if result:
                    log.i(f"通过脚本引擎同步设备名称成功: {deviceName}")
                    return True

        except Exception as e:
            log.w(f"脚本引擎同步失败: {e}")
            return False

    def onS2C_updateTask(self, data):
        g = _G._G_
        log = g.Log()
        try:
            if not data:
                return
            id = data.get('id')
            task = self.getTask(id)
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

    def onS2C_updateDevice(self, data):
        """处理设备更新请求"""
        g = _G._G_
        log = g.Log()
        try:
            self.data.update(data)
            return True
        except Exception as e:
            log.ex(e, '处理设备更新请求失败')
            return False

    def state(self):
        return self._state

    def _createApp(self, data: dict) -> '_App_':
        """创建App"""
        from CApp import CApp_
        return CApp_(data)

    def onLogin(self, data):
        """登录成功后初始化任务表和App列表，data为服务端返回的数据"""
        from CTask import CTask_
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

    def onS2C_SetProp(self, data):
        """统一的属性更新处理器 - 客户端版本"""
        g = _G._G_
        log = g.Log()
        try:
            log.i(f'收到属性更新: {data}')

            entityType = data.get('type')
            targetID = data.get('target')
            params = data.get('params')

            if not params or not entityType or not targetID:
                log.w('属性更新参数不完整')
                return False

            # 获取目标对象并调用setProp
            target = None
            if entityType == 'devices':
                target = self  # 当前设备实例
            elif entityType == 'tasks':
                target = self.getTask(targetID)
            else:
                log.w(f'不支持的实体类型: {entityType}')
                return False

            if target is None:
                log.e(f'目标不存在: {entityType} {targetID}')
                return False

            # 调用setProp统一处理
            return target.setProp(params)

        except Exception as e:
            log.ex(e, '处理属性更新失败')
            return False

    def _onProp(self, key, value):
        """CDevice特殊处理"""
        if key == 'name':
            # 同步到Android
            self._setName(value)

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

    def detectApp(self) -> Tuple['CApp_', str]:
        """获取当前应用"""
        g = _G._G_
        log = g.Log()
        tools = g.Tools()
        try:
            detectedApp = tools.curApp()
            self.setCurApp(detectedApp)
            return self.currentApp, detectedApp
        except Exception as e:
            log.ex(e, "获取当前应用失败")
            return None, None

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

    def open(self, name) -> "CApp_":
        """跳转到指定应用"""
        try:
            g = _G._G_
            log = g.Log()
            appName = self.matchApp(name)
            if not appName:
                log.w(f"未知应用:{name}")
                return None
            app = self.getApp(appName)
            if not app:
                log.w(f"未配置应用:{appName}")
                return None
            tools = g.Tools()
            currentApp = self.currentApp
            if currentApp and appName == currentApp.name:
                return app
            if g.isAndroid():
                if not tools.openApp(appName):
                    return None
            else:
                self.setCurApp(appName)
            return app
        except Exception as e:
            log.ex(e, f"跳转到应用 {appName} 失败")
            return None

    @classmethod
    def onLoad(cls, oldCls):
        if oldCls:
            oldInstance = oldCls.instance()
            instance = cls.instance(reset=True)
            instance._server = oldInstance._server
            instance.name = oldInstance.name
            log = _G._G_.Log()
            log.i(
                f"设备 {instance.name} 重新加载: server={instance._server}, deviceID={instance.name}")
            instance.init()
            instance.connect()

    @classmethod
    def onUnload(cls):
        cls.instance().uninit()


CDevice_.instance().onLoad(None)
