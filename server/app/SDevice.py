from datetime import datetime
from pathlib import Path
from flask import current_app
from models import db, DeviceModel
import _Log
import base64
from STaskMgr import STaskMgr
from SEarningMgr import SEarningMgr

class SDevice:
    """设备类：管理设备状态和信息"""
    
    def __init__(self, device_id):
        self.device_id = device_id
        self.info = {}
        self._status = 'offline'
        self.last_seen = datetime.now()
        self._lastScreenshot = None
        self._ensure_screenshot_dir()
    
    @property
    def deviceID(self):
        return self.device_id
        
    def init(self, model: DeviceModel = None):
        # Log.i(f'初始化设备&&&: {self.device_id}')
        if model:
            self.device_id = model.device_id
            self._status = model.status
            self.last_seen = model.last_seen
        self.taskMgr.init(self.device_id)

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
            
            return SEarningMgr().GetEarnings(
                deviceId=self.device_id,
                appName='',  # 空字符串表示所有应用
                earnType='score',
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            _Log.Log.ex(e, '获取设备总分失败')
            return 0.0

    @property
    def taskMgr(self)->STaskMgr:  # 改为小写，符合 Python 命名规范
        """懒加载任务管理器"""
        if not hasattr(self, '_taskMgr'):
            self._taskMgr = STaskMgr(self)  
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
            _Log.Log.ex(e, '同步设备状态到数据库出错')

    
    def onConnect(self):
        """设备连接回调"""
        try:
            self.status = 'online'
            _Log.Log.i(f'设备 {self.device_id} 已连接')
            self._commit()
            
            # 将刷新操作放在单独的 try-except 块中
            try:
                self.refresh()  # 统一刷新状态
            except Exception as e:
                _Log.Log.ex(e, f'设备 {self.device_id} 刷新状态失败，但连接已建立')
                # 连接失败不影响设备连接状态
            
            return True
        except Exception as e:
            _Log.Log.ex(e, '设备连接处理失败')
            return False
    
    def onDisconnect(self):
        """设备断开连接回调"""
        try:
            self.status = 'offline'
            _Log.Log.i(f'设备 {self.device_id} 已断开连接')
            self._commit()
            self.refresh()  # 统一刷新状态
            return True
        except Exception as e:
            _Log.Log.ex(e, '设备断开连接处理失败')
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
            _Log.Log.ex(e, '设备登录失败')
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
            _Log.Log.ex(e, '设备登出失败')
            return False    
        
    def refresh(self):
        """刷新设备状态到前端"""
        try:
            from SDeviceMgr import deviceMgr
            # 先获取设备信息，如果出错则记录日志
            device_info = self.to_dict()
            deviceMgr.emit2B('S2B_DeviceUpdate', device_info)
            # Log.i(f'设备 {self.device_id} 状态已刷新')
            self.taskMgr.currentTask = None
        except Exception as e:
            _Log.Log.ex(e, '刷新设备状态失败')

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
                    _Log.Log.ex(e, '获取截图时间失败')
                    # 使用默认值
                    screenshotTime = datetime.now().strftime('%H:%M:%S')
            
            if not screenshotFile:
                screenshotFile = '/static/screenshots/default.jpg'
            
            # 获取任务分数
            try:
                todayTaskScore = self.taskMgr.getTodayScore() if hasattr(self, '_taskMgr') else 0
            except Exception as e:
                _Log.Log.ex(e, '获取今日任务分数失败')
                todayTaskScore = 0
            
            # 获取总分
            try:
                totalScore = self.total_score
            except Exception as e:
                _Log.Log.ex(e, '获取总分失败')
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
            _Log.Log.ex(e, '生成设备信息字典失败')
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
            _Log.Log.ex(e, "保存截图失败")
            return False

    def takeScreenshot(self):
        """向客户端发送截屏指令"""
        try:
            if self.status != 'login':
                _Log.Log.w(f'设备 {self.device_id} 未登录，无法截屏')
                return False
            from SDeviceMgr import deviceMgr
            deviceMgr.sendClientCmd(
                self.device_id, 
                'takeScreenshot'
            )
            _Log.Log.i(f'向设备 {self.device_id} 发送截屏指令')
            return True
        except Exception as e:
            _Log.Log.ex(e, f'向设备 {self.device_id} 发送截屏指令失败')
            return False

   