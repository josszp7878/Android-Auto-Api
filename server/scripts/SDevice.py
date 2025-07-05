from datetime import datetime
import json 
import os
from typing import TYPE_CHECKING, Dict
from SModels import DeviceModel_, TaskModel_
import _Log
import base64
import _G
from _ModelBase  import _ModelBase_
from _Device import _Device_

from RPC import RPC
from typing import Optional
if TYPE_CHECKING:
    from STask import STask_
    from SApp import SApp_

class SDevice_(_ModelBase_, _Device_):
    """设备管理类"""
    SCREENSHOTS_DIR = 'screenshots'
    def __init__(self, name):
        super().__init__(name, DeviceModel_)
        _Device_.__init__(self)  # 初始化App管理功能
        self.sid:str = None
        self._state = _G.ConnectState.OFFLINE
        self._lastScreenshot = None
        self._tasks: Dict[int, 'STask_'] = None  # 缓存当天任务列表
        self.tasksDate = None  # 当前缓存的日期
        self.debug = False  # debug开关，临时属性，不保存到数据库

    @property
    def tasks(self):
        """获取任务列表"""
        if self._tasks is None:
            self.tasksDate = datetime.now().date()
            self._loadTasks(self.tasksDate)
        return self._tasks
    
    @property
    def state(self)->_G.ConnectState:
        return self._state
    
    
    @state.setter
    def state(self, value: _G.ConnectState):
        if self._state == value:
            return
        self._state = value
        self.setDBProp('lastTime', datetime.now())
        # self._refreshTasks()
        self.commit()
        self.refresh()


    @classmethod
    def all(cls):
        """获取所有设备"""
        devices = []
        try:
            # 获取设备数据，确保不会是None
            deviceDatas = DeviceModel_.all()
            if deviceDatas is None:
                deviceDatas = []
            
            for d in deviceDatas:
                if d:  # 确保单个设备数据不是None
                    devices.append(cls(d))
        except Exception as e:
            _G._G_.Log().ex_(e, "获取所有设备失败")
            devices = []  # 异常时返回空列表
        return devices
    
    @property
    def group(self) -> str:
        """获取设备组"""
        return self.name.split(':')[0]
    
    @property
    def isConsole(self) -> bool:
        """是否是控制台设备"""
        return self.group == '@'
   
    def toSheetData(self)->dict:
        """转换为表格数据"""
        data = {
            'state': self._state,
            'debug': self.debug,  # 添加debug临时属性
            **self.data
        }
        # log = _G._G_.Log()
        # log.i(f'转换为表格数据fff: {self.name}, {data}')
        return data
    
    @classmethod
    def sendClient(cls, event: str, deviceID: int, data: dict)->bool:
        """更新客户端数据"""
        g = _G._G_
        log = g.Log()
        try:
            if data is None:
                return False
            from SDeviceMgr import deviceMgr
            device = deviceMgr.get(deviceID)
            if device:
                g.emit(event, data, device.sid)
                return True
            else:
                log.w(f'设备不存在: {deviceID}')
                return False
        except Exception as e:
            log.ex(e, '更新客户端数据失败')
            return False
    
    
    def isConnected(self) -> bool:
        return self._state != _G.ConnectState.OFFLINE
    
    @RPC()
    def getDeviceInfo(self) -> dict:
        """获取设备信息 - RPC方法"""
        try:
            return {
                'result': {
                    'id': self.id,
                    'name': self.name,
                    'state': self._state.value if self._state else 'unknown',
                    'isConnected': self.isConnected(),
                    'group': self.group,
                    'isConsole': self.isConsole,
                    'taskCount': len(self.tasks),
                    'sid': self.sid,
                    'data': self.data
                }
            }
        except Exception as e:
            return {
                'error': f"获取设备信息失败: {str(e)}"
            }
    
    def sendCommand(self, command: str, params: dict = None) -> dict:
        """发送命令到客户端 - RPC方法"""
        try:
            result = self.sendClientCmd(command, params)
            return {
                'result': {
                    'deviceId': self.id,
                    'command': command,
                    'result': result
                }
            }
        except Exception as e:
            return {
                'error': f"发送命令失败: {str(e)}"
            }
    
    @RPC()
    def captureScreen(self) -> dict:
        """截屏 - RPC方法"""
        try:
            result = self.takeScreenshot()
            return {
                'result': {
                    'deviceId': self.id,
                    'success': result,
                    'message': '截屏指令已发送' if result else '截屏失败'
                }
            }
        except Exception as e:
            return {
                'error': f"截屏失败: {str(e)}"
            }

    def onConnect(self, sid:str):
        """设备连接回调"""
        try:
            self.state = _G.ConnectState.ONLINE
            self.sid = sid
            g = _G._G_
            log = g.Log()
            log.d(f'设备连接回调: {self.name}, {sid}')
            from SDeviceMgr import deviceMgr
            deviceMgr.addDevice(self)
            return True
        except Exception as e:
            _Log._Log_.ex(e, '设备连接处理失败')
            return False
    
    def onDisconnect(self):
        """设备断开连接回调"""
        try:
            self.sid = None
            self.state = _G.ConnectState.OFFLINE
            _Log._Log_.i(f'设备 -----{self.name} 已断开连接')
            from SDeviceMgr import deviceMgr
            deviceMgr.removeDevice(self)
            return True
        except Exception as e:
            _Log._Log_.ex(e, '设备断开连接处理失败')
            return False 

    
    def _createApp(self, data: dict) -> '_App_':
        """创建SApp"""
        g = _G._G_
        log = g.Log()
        try:
            name = data.get('name', '')
            # 获取设备ID
            deviceId = getattr(self, 'id', 'default_device')
            # 创建新App（会自动创建数据库记录）
            from SApp import SApp_
            app = SApp_.get(deviceId, name, create=True)
            if app:
                # log.i(f'创建App: {name}')
                return app
            else:
                return None
        except Exception as e:
            log.ex_(e, f"创建App失败: {name}")
            return None
        
    def _loadApps(self):
        """Lazy初始化Apps - 仅服务端使用"""
        g = _G._G_
        log = g.Log()
        try:
            deviceId = getattr(self, 'id', 'default_device')            
            from SApp import SApp_
            appNames = SApp_.getAppNames()
            # log.i(f"开始创建 {len(appNames)} 个应用")            
            for name in appNames:
                # 创建SApp实例
                app = SApp_.get(deviceId, name, create=True)
                if app:
                    self._apps[name] = app
                    # log.d(f"创建App: {name}")
                else:
                    log.e(f"创建App实例失败: {name}")
            # log.i(f"服务端App初始化完成，共加载 {len(self._apps)} 个App实例")
        except Exception as e:
            log.ex_(e, "Load Apps失败")
    

    def onLogin(self)->dict:
        """设备登录"""
        g = _G._G_
        log = g.Log()
        try:
            log.i(f'设备登录: {self.name}')
            self.state = _G.ConnectState.LOGIN            
            # 初始化Apps（如果还没有初始化）
            self._loadApps()
            
            # 准备返回数据
            result = {
                "taskList": [t.toSheetData() for t in self.tasks.values()],
                "appList": [t.toSheetData() for t in self.apps.values()],
                "info": self.info
            }
            log.i(f'同步获取数据: app:{len(result["appList"])}, task:{len(result["taskList"])}')
            return result
        except Exception as e:
            log.ex(e, '设备登录失败')
            return {}  # 返回空的列表
        
    
    def onLogout(self):
        """设备登出"""
        self.state = _G.ConnectState.LOGOUT
    
    def sendClientCmd(self, command, params=None):
        """执行设备命令并等待结果
        Args:
            command: 命令名称
            params: 命令参数
            timeout: 超时时间(秒)

        Returns:
            str: 命令执行结果
        """
        try:
            g = _G._G_ 
            log = g.Log()
            if not self.isConnected():
                log.w(f'设备 {self.name} 未连接')
                return None 
            sid = self.sid
            if not sid:
                log.w(f'设备 {self.name} 会话无效')
                return None
            # 发送命令
            # log.i_(f'发送客户端命令:id={self.id}, cmd={command}, params={params}, sid={sid}')
            return g.emitRet('S2C_DoCmd', {
                'cmd': command,
                'params': params,
            }, sid=sid)
        except Exception as e:
            log.ex(e, '执行设备命令出错')
            return None
        
    def saveScreenshot(self, base64_data):
        """保存截图并刷新设备信息
        Args:
            base64_data: Base64编码的图片数据
        Returns:
            bool: 保存成功返回True
        """
        try:
            # 解码base64数据
            if base64_data.startswith('data:image'):
                image_data = base64_data.split(',', 1)[1]
                image_bytes = base64.b64decode(image_data)                
                # 生成文件名
                filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S.jpg')
                g = _G._G_
                file_path = g.dataDir(os.path.join(self.SCREENSHOTS_DIR, str(self.id), filename))
                
                # 保存文件
                with open(file_path, 'wb') as f:
                    f.write(image_bytes)
                
                # 更新截图路径
                self._lastScreenshot = file_path
                self.data['_lastScreenshotTime'] = datetime.now()
                
                # 刷新设备信息到前端
                self.refresh()
                return True
                
        except Exception as e:
            _Log._Log_.ex(e, "保存截图失败")
            return False

    def takeScreenshot(self):
        """向客户端发送截屏指令"""
        try:
            if self._state != _G.ConnectState.LOGIN:
                _Log._Log_.w(f'设备 {self.name} 未登录，无法截屏')
                return False
            self.sendClientCmd(
                'takeScreenshot'
            )
            _Log._Log_.i(f'向设备 {self.name} 发送截屏指令')
            return True
        except Exception as e:
            _Log._Log_.ex(e, f'向设备 {self.name} 发送截屏指令失败')
            return False

    def getAppOnScreen(self):
        """分析屏幕上的应用并更新数据库"""
        try:
            def parseResult(data):
                try:
                    # 空数据检查
                    if not data:
                        _Log._Log_.w("收到空屏幕数据")
                        return

                    # 移除可能存在的非法字符
                    data = data.strip().replace('\x00', '')
                    # 尝试多种解析方式
                    try:
                        screen_info = json.loads(data)
                    except json.JSONDecodeError:
                        # 尝试修复常见格式问题
                        data = data.replace("'", '"').replace("True", "true").replace("False", "false")
                        screen_info = json.loads(data)
                        
                    # 解析成功后处理应用信息
                    detected_apps = set()
                    
                    # 从屏幕信息中提取候选应用名
                    for item in screen_info:
                        text = item.get('t', '')
                        if not text:
                            continue
                        
                        # 使用应用管理器验证是否为已知应用
                        from SAppMgr import appMgr
                        exist = appMgr.app_exists(text.strip())
                        _Log._Log_.i(f'应用{text.strip()} 是否存在: {exist}')
                        if exist:
                            detected_apps.add(exist)
                    
                    # 更新数据库
                    with current_app.app_context():
                        for app_name in detected_apps:
                            record = DeviceModel_.query.filter_by(
                                name=self.name,
                                state='detected'
                            ).first()
                            
                            if not record:
                                record = DeviceModel_(
                                    name=self.name,
                                    state='detected'
                                )
                                db.session.add(record)
                            record.state = 'detected'
                        
                        db.session.commit()                        
                    _Log._Log_.i(f'成功更新{len(detected_apps)}个应用到数据库')

                except Exception as e:
                    _Log._Log_.ex(e, "处理应用分析结果失败")

            self.sendClientCmd(
                'getScreen', None, 10, parseResult)
            return True
        except Exception as e:
            _Log._Log_.ex(e, "分析屏幕应用失败")
            return False

    
    _lastScreenInfo = None
    
    @classmethod
    @RPC()
    def getScreenInfo(cls, deviceID: int, pageName: str = None) -> dict:
        """RPC方法：获取设备屏幕信息
        
        Args:
            deviceID: 设备ID
            pageName: 页面名称，用于文件缓存
            
        Returns:
            dict: RPC结果，包含屏幕信息或错误信息
        """
        g = _G._G_
        log = g.Log()
        try:
            if not pageName:
                pageName = 'Last'
            # 通过RPC调用客户端方法获取屏幕信息
            screenData = g.RPCServer(deviceID, 'CDevice_.getScreenInfo', params={'id': deviceID})            
            if not screenData:
                return None
            # 保存到文件
            pageName = pageName or 'Last'
            success = cls._saveScreenInfoToFile(pageName, screenData)
            if not success:
                log.e(f"保存屏幕信息失败: {pageName}")
                return None
            return screenData                
        except Exception as e:
            log.ex(e, "获取屏幕信息失败")
            return None

    @classmethod
    @RPC()
    def setScreenInfo(cls, deviceID: int, pageName: str = None) -> dict:
        """RPC方法：设置设备屏幕信息
        
        Args:
            deviceID: 设备ID
            pageName: 页面名称，用于从文件加载
            
        Returns:
            dict: RPC结果，包含设置结果或错误信息
        """
        g = _G._G_
        log = g.Log()
        try:
            if not pageName:
                pageName = 'Last'
            # 从文件加载屏幕信息
            screenInfo = cls._loadScreenInfoFromFile(pageName)
            if not screenInfo:
                return {'error': '屏幕信息为空或文件不存在'}
            
            # 通过RPC调用客户端方法设置屏幕信息
            result = g.RPCServer(deviceID, 'CDevice_.setScreenInfo', id=deviceID, screenInfos=screenInfo)
            
            if result and result.get('result'):
                log.i(f"设置屏幕信息成功: {pageName}")
                return {'result': {'pageName': pageName, 'success': True}}
            else:
                error = result.get('error') if result else '设置屏幕信息失败'
                return {'error': error}
                
        except Exception as e:
            log.ex(e, "设置屏幕信息失败")
            return {'error': f'设置屏幕信息失败: {str(e)}'}

    @classmethod
    def _saveScreenInfoToFile(cls, pageName: str, screenInfo) -> bool:
        """将屏幕信息保存到文件
        
        Args:
            pageName: 页面名称，用于构建文件名
            screenInfo: 屏幕信息数据
            
        Returns:
            bool: 是否保存成功
        """
        if not screenInfo:
            return False
        g = _G._G_
        log = g.Log()
        try:
            # 构建文件名
            fileName = os.path.join(g.dataDir(cls.SCREENSHOTS_DIR), f'{pageName}.json')
            
            # 确保目录存在
            os.makedirs(os.path.dirname(fileName), exist_ok=True)
            
            # 格式化JSON数据
            json_data = json.dumps(
                screenInfo, 
                ensure_ascii=False, 
                indent=4,
                sort_keys=True
            )
            
            # 保存到文件
            with open(fileName, 'w', encoding='utf-8') as f:
                f.write(json_data)
            
            cls._lastScreenInfo = json_data
            log.i(f"保存屏幕信息到文件成功: {fileName}")
            return True
        except Exception as e:
            log.ex(e, f"保存屏幕信息到文件失败: {pageName}")
            return False

    @classmethod
    def _loadScreenInfoFromFile(cls, pageName: str = None):
        """从文件加载屏幕信息
        
        Args:
            pageName: 页面名称，用于构建文件名
            
        Returns:
            屏幕信息数据或None
        """
        g = _G._G_
        log = g.Log()
        try:
            if pageName is None:
                if cls._lastScreenInfo:
                    return json.loads(cls._lastScreenInfo)
                return None
            
            # 构建文件名
            fileName = os.path.join(g.dataDir(cls.SCREENSHOTS_DIR), f'{pageName}.json')
            
            # 检查文件是否存在
            if not os.path.exists(fileName):
                log.w(f"屏幕信息文件不存在: {fileName}")
                return None
            
            # 从文件加载屏幕信息
            with open(fileName, 'r', encoding='utf-8') as f:
                return json.loads(f.read())
        except Exception as e:
            log.ex(e, f"从文件加载屏幕信息失败: {pageName}")
            return None
        
    def getTask(self, key)->'STask_':
        """根据KEY 获取任务，支持ID和任务名"""
        g = _G._G_
        log = g.Log()
        try:
            id = g.toInt(key)
            if id:
                if id in self.tasks:
                    return self.tasks[id]
            else:
                key = key.lower()
                for t in self.tasks.values():
                    if t.name.lower() == key:
                        return t
            return None
        except Exception as e:
            log.ex(e, f'获取任务失败: {key}')
            return None

    def getTasks(self, date=None):
        """获取指定日期的任务列表，默认当天，按天缓存"""
        today = datetime.now().date()
        if date is None:
            date = today
        if self._tasks and self.tasksDate == date:
            return self._tasks
        return self._loadTasks(date)
    
    def _loadTasks(self, date=None) -> Dict[int, 'STask_']:
        """获取指定日期的任务列表，默认当天，按天缓存"""
        from STask import STask_
        today = datetime.now().date()
        
        # 安全地获取任务数据，处理None情况
        try:
            task_data = TaskModel_.all(date, f"deviceId = {self.id}")
            if task_data is None:
                task_data = []
            taskList = [STask_(t) for t in task_data]
        except Exception as e:
            log = _G._G_.Log()
            log.ex_(e, "从数据库加载任务失败")
            taskList = []
        
        tasks = {}
        if len(taskList) > 0:
            # 如果任务列表不为空，则更新任务列表
            for t in taskList:
                tasks[t.id] = t
        elif date == today:
            # 如果日期为当天，则创建任务列表
            tasks = self._createTasks(today)
        # log = _G._G_.Log()
        self._tasks = tasks
        self.tasksDate = date
        return tasks
    
    def _createTasks(self, date:datetime) -> Dict[int, 'STask_']:
        """创建任务列表"""
        log = _G._G_.Log()
        try:
            tasks = {}
            from Task import Task_
            for taskName, config in Task_.getConfig().items():
                # 不存在则尝试创建（TaskModel_.get已做唯一性判定）
                data = TaskModel_.get(self.id, taskName, date, True)
                if data:
                    from STask import STask_
                    task = STask_(data)
                    # 根据CONFIG初始化任务
                    task.setDBProp('life', config.get('life', 10))
                    tasks[task.id] = task
            log.i(f'创建{date} 的任务列表: {len(tasks)}')
            return tasks
        except Exception as e:
            log.ex(e, '初始化任务列表失败')
            return {}

    # 向客户端发送命令获取收益
    @RPC()
    def getScores(self, appName:str, date:str)->dict:
        """
        功能：获取设备某应用某天的所有任务收益
        指令名: getScores
        参数: 
            target - 设备ID
            appName - 应用名称
            date - 日期(YYYY-MM-DD)
        返回: 处理结果和收益统计
        """
        g = _G._G_
        log = g.Log()
        try:
            result = g.RPCServer(self.id, 'CDevice_.getScore', appName=appName, date=date)
            if not result:
                return {
                    'error': f"从客户端获取收益数据失败"
                }
            log.i(f"@@@@@获取收益: {result}")
            # 处理收益数据并更新任务
            changedTasks = []
            for item in result:
                taskName = item.get("name", "未知任务")
                taskScore = item.get("amount", 0)  # 客户端返回的是amount字段
                date = _G.DateHelper.toDate(item.get("date", date))
                if not taskName or taskScore <= 0:
                    continue
                from STask import STask_
                # 获取或创建任务
                task = STask_.get(deviceId=self.id, name=taskName, date=date, create=True)
                if not task:
                    log.e(f"创建任务失败: {taskName}")
                    continue
                task.score = taskScore
                if task.commit():
                    changedTasks.append(task)
                    # log.d_(f"更新任务: {taskName}, 分数: {taskScore}")
            return {
                'result': changedTasks,
            }
        except Exception as e:
            return {
                'error': f"获取收益失败: {str(e)}"
            }
