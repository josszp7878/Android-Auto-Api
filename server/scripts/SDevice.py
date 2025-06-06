from datetime import datetime
from pathlib import Path
import json
import os
from flask import current_app
from SModels import DeviceModel_, TaskModel_
import _Log
import base64
from SEarningMgr import SEarningMgr_
import _G
from SModelBase import SModelBase_

class SDevice_(SModelBase_):
    """设备管理类"""
    SCREENSHOTS_DIR = os.path.join(_G.g.rootDir(), 'data', 'screenshots')
    
    def __init__(self, name):
        super().__init__(name, DeviceModel_)
        self.sid = None
        self._state = _G.ConnectState.OFFLINE
        self._lastScreenshot = None
        self._ensure_screenshot_dir()
        self.apps = []
        self._tasks = None  # 缓存当天任务列表
        self.tasksDate = None  # 当前缓存的日期

    @property
    def tasks(self):
        """获取任务列表"""
        return self._tasks
    
    @classmethod
    def all(cls):
        """获取所有设备"""
        devices = []
        for d in DeviceModel_.all():
            devices.append(cls(d))
        return devices
    
    @property
    def group(self) -> str:
        """获取设备组"""
        return self.name.split(':')[0]
    
    @property
    def isConsole(self) -> bool:
        """是否是控制台设备"""
        return self.group == '@'
    
    def setName(self, name: str):
        """设置设备名称"""
        if self.setDBProp('name', name):
            self.commit()
            self.refresh()
   
    def toSheetData(self)->dict:
        """转换为表格数据"""
        data = {
            'state': self._state,
            **self.data
        }
        log = _G._G_.Log()
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
            device = deviceMgr.getByID(deviceID)
            if device:
                g.emit(event, data, device.sid)
                return True
            else:
                log.w(f'设备不存在: {deviceID}')
                return False
        except Exception as e:
            log.ex(e, '更新客户端数据失败')
            return False
    
    @property
    def total_score(self) -> float:
        """获取设备总积分
        Returns:
            float: 设备的总积分
        """
        try:
            # 获取从开始到现在的所有积分
            start_date = datetime(2000, 1, 1)  # 一个足够早的日期
            end_date = datetime.now()
            
            return SEarningMgr_().GetEarnings(
                deviceId=self.id,
                appName='',  # 空字符串表示所有应用
                earnType='score',
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            _Log._Log_.ex(e, '获取设备总分失败')
            return 0.0
    
    def _ensure_screenshot_dir(self):
        """确保设备的截图目录存在"""
        self.screenshot_dir = Path(self.SCREENSHOTS_DIR) / (str(self.id))
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def isConnected(self) -> bool:
        return self._state != _G.ConnectState.OFFLINE

    def onConnect(self, sid):
        """设备连接回调"""
        try:
            self._state = _G.ConnectState.ONLINE
            self.setDBProp('lastTime', datetime.now())
            self.sid = sid
            log = _G._G_.Log()
            log.d_(f'设备连接回调: {self.name}, {sid}')
            from SDeviceMgr import deviceMgr
            deviceMgr.addDevice(self)
            self.commit()
            self.refresh()
            return True
        except Exception as e:
            _Log._Log_.ex(e, '设备连接处理失败')
            return False
    
    def onDisconnect(self):
        """设备断开连接回调"""
        try:
            self._state = _G.ConnectState.OFFLINE
            self.setDBProp('lastTime', datetime.now())
            _Log._Log_.i(f'设备 -----{self.name} 已断开连接')
            self.commit()
            self.refresh()  # 统一刷新状态
            from SDeviceMgr import deviceMgr
            deviceMgr.removeDevice(self)
            return True
        except Exception as e:
            _Log._Log_.ex(e, '设备断开连接处理失败')
            return False

    def login(self):
        """设备登录"""
        try:
            log = _G._G_.Log()
            log.i(f'设备登录: {self.name}')
            self._state = _G.ConnectState.LOGIN
            self.setDBProp('lastTime', datetime.now())
            self.commit()
            self.refresh()  # 统一刷新状态
            self._initTasks()
            return True
        except Exception as e:
            _Log._Log_.ex(e, '设备登录失败')
            return False
    
    def logout(self):
        """设备登出"""
        try:
            self._state = _G.ConnectState.LOGOUT
            self.setDBProp('lastTime', datetime.now())
            self.commit()
            self.refresh()  # 统一刷新状态
            return True
        except Exception as e:
            _Log._Log_.ex(e, '设备登出失败')
            return False    
    
    def sendClientCmd(self, command, data=None):
        """执行设备命令并等待结果
        Args:
            command: 命令名称
            data: 命令参数
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
            # log.i(f'发送客户端命令: {self.name}, {command}, {data}， sid={sid}')
            return g.emitRet('S2C_DoCmd', {
                'command': command,
                'sender': current_app.config['SERVER_ID'],
                'data': data,
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
                
                # 确保目录存在
                self._ensure_screenshot_dir()
                
                # 生成文件名
                filename = datetime.now().strftime('%Y%m%d_%H%M%S.jpg')
                file_path = self.screenshot_dir / filename
                
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
                        self.apps = DeviceModel_.query.filter_by(
                            name=self.name).all()
                        
                    _Log._Log_.i(f'成功更新{len(detected_apps)}个应用到数据库')

                except Exception as e:
                    _Log._Log_.ex(e, "处理应用分析结果失败")

            self.sendClientCmd(
                'getScreen', None, 10, parseResult)
            return True
        except Exception as e:
            _Log._Log_.ex(e, "分析屏幕应用失败")
            return False

    @classmethod
    def _screenInfoFile(cls, pageName) -> str:
        return f"{cls.SCREENSHOTS_DIR}/{pageName}.json"
    
    _lastScreenInfo = None
    
    @classmethod
    def setScreenInfo(cls, pageName: str, screenInfo: str) -> bool:
        """将屏幕信息保存到文件
        
        Args:
            pageName: 页面名称，用于构建文件名
            screenInfo: 屏幕信息数据
            
        Returns:
            bool: 是否保存成功
        """
        if not screenInfo:
            return False
        log = _G._G_.Log()
        try:
            # 构建文件名
            fileName = cls._screenInfoFile(pageName)
            # 确保目录存在
            os.makedirs(os.path.dirname(fileName), exist_ok=True)
            # 尝试解析JSON并重新格式化
            try:
                if screenInfo is None or screenInfo.strip() == '':
                    return False
                cls._lastScreenInfo = screenInfo
                json_data = json.loads(screenInfo)
                # 换成美观的json格式
                screenInfo = json.dumps(
                    json_data, 
                    ensure_ascii=False, 
                    indent=4,
                    sort_keys=True
                )
                # 将屏幕信息保存到文件
                with open(fileName, 'w', encoding='utf-8') as f:
                    f.write(screenInfo)
            except Exception as e:
                log.ex(e, f"保存屏幕信息到文件失败: {pageName}")
                return False
            log.i(f"保存屏幕信息到文件成功: {fileName}")
            return True
        except Exception as e:
            log.ex(e, f"保存屏幕信息到文件失败: {pageName}")
            return False

    @classmethod
    def getScreenInfo(cls, pageName) -> str:
        """从文件加载屏幕信息
        
        Args:
            pageName: 页面名称，用于构建文件名
            
        Returns:
            bool: 是否加载成功
        """
        log = _G._G_.Log()
        try:
            if pageName is None:
                return cls._lastScreenInfo
            # 构建文件名
            fileName = cls._screenInfoFile(pageName)            
            # 检查文件是否存在
            if not os.path.exists(fileName):
                return None
            # 从文件加载屏幕信息
            with open(fileName, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            log.ex(e, f"从文件加载屏幕信息失败: {pageName}")
            return None

    def getTasks(self, date=None):
        """获取指定日期的任务列表，默认当天，按天缓存"""
        from SModels import TaskModel_
        from STask import STask_
        from datetime import datetime
        if date is None:
            date = datetime.now().date()
        if self._tasks is not None and self.tasksDate == date:
            return list(self._tasks.values())
        # 重新加载
        self._tasks = {}
        self.tasksDate = date
        tasks = [STask_(t) for t in TaskModel_.all(date, f"deviceId = {self.id}")]
        for t in tasks:
            self._tasks[t.id] = t
        return tasks

    
    def _initTasks(self):
        """初始化今天任务列表"""
        log = _G._G_.Log()
        try:
            from datetime import datetime
            today = datetime.now().date()
            tasks = self.getTasks(today)
            if len(tasks) == 0:
                from Task import TaskBase
                from STask import STask_
                for taskName, config in TaskBase.getConfig().items():
                    # 先查缓存
                    task = next((t for t in tasks if t.name == taskName), None)
                    if not task:
                        # 不存在则尝试创建（TaskModel_.get已做唯一性判定）
                        data = TaskModel_.get(self.id, taskName, today, True)
                        if data:
                            task = STask_(data)
                            self._tasks[task.id] = task
            log.i(f'初始化任务列表: 任务数 {len(self._tasks)}')
        except Exception as e:
            log.ex(e, '初始化任务列表失败')


 

    



      
