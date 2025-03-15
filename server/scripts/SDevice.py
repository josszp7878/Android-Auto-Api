from datetime import datetime
from pathlib import Path
import json
import os
from flask import current_app
from SModels import db, DeviceModel, AppModel
import _Log
import base64
from STaskMgr import STaskMgr_
from SEarningMgr import SEarningMgr_
import json
from SAppMgr import appMgr  # 局部导入避免循环依赖
import _G

class SDevice_:
    """设备类：管理设备状态和信息"""
    
    def __init__(self, device_id):
        self.device_id = device_id
        self.info = {}
        self._status = 'offline'
        self._taskMgr = None  # 任务管理器
        self.last_seen = datetime.now()
        self._lastScreenshot = None
        self._ensure_screenshot_dir()
        self.apps = []  # 新增应用列表缓存
    
    @property
    def deviceID(self):
        return self.device_id
        
    def init(self, model: DeviceModel = None):
        # _Log._Log_.i(f'初始化设备&&&: {self.device_id}')
        if model:
            self.device_id = model.device_id
            self._status = model.status
            self.last_seen = model.last_seen
        self.taskMgr.init(self.device_id)
        # 新增：从数据库加载应用列表
        with current_app.app_context():
            self.apps = AppModel.query.filter_by(deviceId=self.device_id).all()

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
                deviceId=self.device_id,
                appName='',  # 空字符串表示所有应用
                earnType='score',
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            _Log._Log_.ex(e, '获取设备总分失败')
            return 0.0

    @property
    def taskMgr(self)->STaskMgr_:  # 改为小写，符合 Python 命名规范
        """懒加载任务管理器"""
        if self._taskMgr is None:
            self._taskMgr = STaskMgr_(self)  
        return self._taskMgr
    
    def _ensure_screenshot_dir(self):
        """确保设备的截图目录存在"""
        from app import SCREENSHOTS_DIR
        self.screenshot_dir = Path(SCREENSHOTS_DIR) / self.device_id
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, value):
        self._status = value
        self.last_seen = datetime.now()
        self._commit()
    
    def _commit(self):
        """同步设备状态到数据库"""
        try:
            with current_app.app_context():
                model = DeviceModel.query.filter_by(device_id=self.device_id).first()
                if model:
                    model.status = self._status
                    model.last_seen = self.last_seen
                    db.session.add(model)
                    db.session.commit()
                    # print(f'设备 {self.device_id} 状态已同步到数据库')
        except Exception as e:
            _Log._Log_.ex(e, '同步设备状态到数据库出错')

    
    def onConnect(self):
        """设备连接回调"""
        try:
            self.status = 'online'
            _Log._Log_.i(f'设备 {self.device_id} 已连接')
            self._commit()
            
            # 将刷新操作放在单独的 try-except 块中
            try:
                self.refresh()  # 统一刷新状态
            except Exception as e:
                _Log._Log_.ex(e, f'设备 {self.device_id} 刷新状态失败，但连接已建立')
                # 连接失败不影响设备连接状态
            
            return True
        except Exception as e:
            _Log._Log_.ex(e, '设备连接处理失败')
            return False
    
    def onDisconnect(self):
        """设备断开连接回调"""
        try:
            self.status = 'offline'
            _Log._Log_.i(f'设备 {self.device_id} 已断开连接')
            self._commit()
            self.refresh()  # 统一刷新状态
            return True
        except Exception as e:
            _Log._Log_.ex(e, '设备断开连接处理失败')
            return False

    def login(self):
        """设备登录"""
        try:
            self.status = 'login'
            self.info['login_time'] = str(datetime.now())
            self._commit()
            self.refresh()  # 统一刷新状态
            return True
        except Exception as e:
            _Log._Log_.ex(e, '设备登录失败')
            return False
    
    def logout(self):
        """设备登出"""
        try:
            self.status = 'logout'
            self.info['logout_time'] = str(datetime.now())
            self._commit()
            self.refresh()  # 统一刷新状态
            return True
        except Exception as e:
            _Log._Log_.ex(e, '设备登出失败')
            return False    
        
    def refresh(self):
        """刷新设备状态到前端"""
        try:
            from SDeviceMgr import deviceMgr
            # 先获取设备信息，如果出错则记录日志
            device_info = self.to_dict()
            deviceMgr.emit2B('S2B_DeviceUpdate', device_info)
            # _Log._Log_.i(f'设备 {self.device_id} 状态已刷新')
            self.taskMgr.currentTask = None
        except Exception as e:
            _Log._Log_.ex(e, '刷新设备状态失败')

    def to_dict(self):
        """返回设备信息字典"""
        try:
            screenshotTime = None
            screenshotFile = None
            
            # 获取截图信息
            if self._lastScreenshot:
                try:
                    mtime = datetime.fromtimestamp(Path(self._lastScreenshot).stat().st_mtime)
                    screenshotTime = mtime.strftime('%H:%M:%S')
                    screenshotFile = str(self._lastScreenshot).replace('\\', '/')
                    if 'static' in screenshotFile:
                        screenshotFile = '/static' + screenshotFile.split('static')[1]
                except Exception as e:
                    _Log._Log_.ex(e, '获取截图时间失败')
                    # 使用默认值
                    screenshotTime = datetime.now().strftime('%H:%M:%S')
            
            if not screenshotFile:
                screenshotFile = '/static/screenshots/default.jpg'
            
            # 获取任务分数
            try:
                todayTaskScore = self.taskMgr.getTodayScore() if hasattr(self, '_taskMgr') else 0
            except Exception as e:
                _Log._Log_.ex(e, '获取今日任务分数失败')
                todayTaskScore = 0
            
            # 获取总分
            try:
                totalScore = self.total_score
            except Exception as e:
                _Log._Log_.ex(e, '获取总分失败')
                totalScore = 0
            
            return {
                'deviceId': self.device_id,
                'status': self.status,
                'screenshot': screenshotFile,
                'screenshotTime': screenshotTime,
                'todayTaskScore': todayTaskScore,
                'totalScore': totalScore
            }
        except Exception as e:
            _Log._Log_.ex(e, '生成设备信息字典失败')
            # 返回最小化的设备信息
            return {
                'deviceId': self.device_id,
                'status': self.status
            }
    
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
                self._lastScreenshotTime = datetime.now()
                
                # 刷新设备信息到前端
                self.refresh()
                return True
                
        except Exception as e:
            _Log._Log_.ex(e, "保存截图失败")
            return False

    def takeScreenshot(self):
        """向客户端发送截屏指令"""
        try:
            if self.status != 'login':
                _Log._Log_.w(f'设备 {self.device_id} 未登录，无法截屏')
                return False
            from SDeviceMgr import deviceMgr
            deviceMgr.sendClientCmd(
                self.device_id, 
                'takeScreenshot'
            )
            _Log._Log_.i(f'向设备 {self.device_id} 发送截屏指令')
            return True
        except Exception as e:
            _Log._Log_.ex(e, f'向设备 {self.device_id} 发送截屏指令失败')
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
                        exist = appMgr.app_exists(text.strip())
                        _Log._Log_.i(f'应用{text.strip()} 是否存在: {exist}')
                        if exist:
                            detected_apps.add(exist)
                    
                    # 更新数据库
                    with current_app.app_context():
                        for app_name in detected_apps:
                            record = AppModel.query.filter_by(
                                deviceId=self.device_id,
                                appName=app_name
                            ).first()
                            
                            if not record:
                                record = AppModel(
                                    deviceId=self.device_id,
                                    appName=app_name,
                                    totalScore=0.0,
                                    income=0.0,
                                    status='detected'
                                )
                                db.session.add(record)
                            record.lastUpdate = datetime.now()
                        
                        db.session.commit()
                        self.apps = AppModel.query.filter_by(deviceId=self.device_id).all()
                        
                    _Log._Log_.i(f'成功更新{len(detected_apps)}个应用到数据库')

                except Exception as e:
                    _Log._Log_.ex(e, "处理应用分析结果失败")

            from SDeviceMgr import deviceMgr
            deviceMgr.sendClientCmd(self.device_id, 'getScreen', None, 10, parseResult)
            return True
        except Exception as e:
            _Log._Log_.ex(e, "分析屏幕应用失败")
            return False


    @classmethod
    def _screenInfoFile(cls, pageName)->str:
        from app import APP_DATA
        return f"{APP_DATA}/{pageName}.json"
    
    _lastScreenInfo = None
    @classmethod
    def setScreenInfo(cls, pageName:str, screenInfo:str)->bool:
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
    def getScreenInfo(cls, pageName)->str:
        """从文件加载屏幕信息
        
        Args:
            pageName: 页面名称，用于构建文件名
            
        Returns:
            bool: 是否加载成功
        """
        log = _G._G_.Log()
        try:
            if pageName == None:
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

   