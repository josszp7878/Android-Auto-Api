from datetime import datetime
from pathlib import Path
from flask import current_app
from .models import db, DeviceModel
from scripts.logger import Log
import json
import base64
from .STaskMgr import STaskMgr
class SDevice:
    """设备类：管理设备状态和信息"""
    
    def __init__(self, device_id):
        self.device_id = device_id
        self.info = {}
        self._status = 'offline'
        self.last_seen = datetime.now()
        self.total_score = 0  # 设备总分
        self._lastScreenshot = None
        self._ensure_screenshot_dir()
        
    def init(self, model: DeviceModel = None):
        Log.i(f'初始化设备&&&: {self.device_id}')
        if model:
            self.device_id = model.device_id
            self._status = model.status
            self.last_seen = model.last_seen
            self.total_score = model.total_score
        self.taskMgr.init(self.device_id)

        

    @property
    def taskMgr(self)->STaskMgr:  # 改为小写，符合 Python 命名规范
        """懒加载任务管理器"""
        if not hasattr(self, '_taskMgr'):
            self._taskMgr = STaskMgr(self)  
        return self._taskMgr
    
    def _ensure_screenshot_dir(self):
        """确保设备的截图目录存在"""
        from . import SCREENSHOTS_DIR
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
                    model.total_score = self.total_score
                    db.session.add(model)
                    db.session.commit()
                    # print(f'设备 {self.device_id} 状态已同步到数据库')
        except Exception as e:
            Log.ex(e, '同步设备状态到数据库出错')

    
    def onConnect(self):
        """设备连接回调"""
        try:
            self.status = 'online'
            Log.i(f'设备 {self.device_id} 已连接')
            self._commit()
            self.refresh()  # 统一刷新状态
            return True
        except Exception as e:
            Log.ex(e, '设备连接处理失败')
            return False
    
    def onDisconnect(self):
        """设备断开连接回调"""
        try:
            self.status = 'offline'
            Log.i(f'设备 {self.device_id} 已断开连接')
            self._commit()
            self.refresh()  # 统一刷新状态
            return True
        except Exception as e:
            Log.ex(e, '设备断开连接处理失败')
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
            Log.ex(e, '设备登录失败')
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
            Log.ex(e, '设备登出失败')
            return False    
        
    def refresh(self):
        """刷新设备状态到前端"""
        try:
            from .SDeviceMgr import deviceMgr
            # 统一使用 to_dict() 获取设备信息
            deviceMgr.emit2B('S2B_DeviceUpdate', self.to_dict())
            self.taskMgr.currentTask = None
            Log.i(f'设备 {self.device_id} 状态已刷新')

        except Exception as e:
            Log.ex(e, '刷新设备状态失败')

    def to_dict(self):
        """返回设备信息字典"""
        # 获取截图信息
        screenshotTime = None
        screenshotFile = None
        
        if self._lastScreenshot:
            try:
                mtime = datetime.fromtimestamp(Path(self._lastScreenshot).stat().st_mtime)
                screenshotTime = mtime.strftime('%H:%M:%S')
                # 确保路径格式正确
                screenshotFile = str(self._lastScreenshot).replace('\\', '/')
                if 'static' in screenshotFile:
                    screenshotFile = '/static' + screenshotFile.split('static')[1]
            except Exception as e:
                Log.ex(e, '获取截图时间失败')
        
        # 如果没有截图，使用默认截图
        if not screenshotFile:
            screenshotFile = '/static/screenshots/default.jpg'
        
        return {
            'deviceId': self.device_id,
            'status': self.status,
            'screenshot': screenshotFile,
            'screenshotTime': screenshotTime,
            'todayTaskScore': self.taskMgr.getTodayScore() if hasattr(self, 'taskMgr') else 0,
            'totalScore': self.total_score
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
            Log.ex(e, "保存截图失败")
            return False

    def add_score(self, score):
        """增加设备总分"""
        self.total_score += score
        self._save_score()
    
    def _save_score(self):
        """保存总分到数据库"""
        try:
            device_model = DeviceModel.query.get(self.device_id)
            if device_model:
                device_model.total_score = self.total_score
                db.session.commit()
        except Exception as e:
            Log.ex(e, '保存设备总分失败')

    def resumeTask(self, task):
        """继续执行暂停的任务"""
        try:
            if task.state != TaskState.PAUSED.value:
                Log.w(f"任务 {task.taskName} 不是暂停状态")
                return False
                
            # 更新任务状态
            task.state = TaskState.RUNNING.value
            commit(task)
            
            # 发送任务更新事件
            deviceMgr.emit2Console('S2B_TaskUpdate', {
                'deviceId': self.device_id,
                'task': {
                    'appName': task.appName,
                    'taskName': task.taskName,
                    'progress': task.progress,
                    'state': task.state,
                    'score': task.score
                }
            })
            
            Log.i(f"继续执行任务: {task.taskName}")
            return True
            
        except Exception as e:
            Log.ex(e, f"继续执行任务 {task.taskName} 失败")
            return False