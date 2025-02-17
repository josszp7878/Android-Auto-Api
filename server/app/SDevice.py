from datetime import datetime
from pathlib import Path
from flask import current_app
from .models import db, DeviceModel
from scripts.logger import Log
import json
import base64

class SDevice:
    """设备类：管理设备状态和信息"""
    
    def __init__(self, device_id, info=None):
        self.device_id = device_id
        self.info = info or {}
        self._status = 'offline'
        self.last_seen = datetime.now()
        self.total_score = 0  # 设备总分
        self.currentTask = None
        self._lastScreenshot = None
        self._ensure_screenshot_dir()
    
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
                device_model = DeviceModel.query.filter_by(device_id=self.device_id).first()
                if device_model:
                    device_model.status = self._status
                    device_model.last_seen = self.last_seen
                    device_model.total_score = self.total_score
                    db.session.add(device_model)
                    db.session.commit()
                    # print(f'设备 {self.device_id} 状态已同步到数据库')
        except Exception as e:
            Log.ex(e, '同步设备状态到数据库出错')

    
    def onConnect(self):
        try:
            self.status = 'online'
            Log.i(f'设备 {self.device_id} 已连接')
            self._commit()
            self.refresh()
            return True
        except Exception as e:
            Log.ex(e, '设备 {self.device_id} 连接处理失败')
            return False
    
    def onDisconnect(self):
        try:
            self.status = 'offline'
            Log.i(f'设备 {self.device_id} 已断开连接')
            self._commit()
            self.refresh()
            return True
        except Exception as e:
            Log.ex(e, '设备 {self.device_id} 断开连接处理失败')
            return False
    def login(self):
        Log.i(f'设备 {self.device_id} 登录')
        try:
            self.status = 'login'
            self.info['login_time'] = str(datetime.now())
            self._commit()
            self.refresh()
            return True
        except Exception as e:
            Log.ex(e, '设备 {self.device_id} 登录失败')
            return False
    
    def logout(self):
        Log.w(f'设备 {self.device_id} 登出')
        try:
            self.status = 'logout'
            self.info['logout_time'] = str(datetime.now())
            self._commit()
            self.refresh()
            return True
        except Exception as e:
            Log.ex(e, '设备 {self.device_id} 登出失败')
            return False    
        
    def to_dict(self):
        """返回设备信息字典
        Returns:
            dict: {
                deviceId: 设备ID,
                status: 设备状态,
                screenshot: 截图路径,
                screenshotTime: 截图时间(HH:MM:SS)
            }
        """
        # 获取截图文件的最后修改时间
        screenshotTime = None
        screenshotFile = None
        
        if self._lastScreenshot:
            try:
                # 获取文件时间
                mtime = datetime.fromtimestamp(Path(self._lastScreenshot).stat().st_mtime)
                screenshotTime = mtime.strftime('%H:%M:%S')
                # 从绝对路径中提取相对路径(从static开始)
                screenshotFile = '/static' + str(self._lastScreenshot).replace('\\', '/').split('static')[1]
            except Exception as e:
                Log.ex(e, '获取截图时间失败')
        
        return {
            'deviceId': self.device_id,
            'status': self.status,
            'screenshot': screenshotFile,
            'screenshotTime': screenshotTime
        }
    
    def refresh(self): 
        try:
            from .device_manager import DeviceManager
            DeviceManager().emit2Console('refresh_device', self.to_dict())
        except Exception as e:
            Log.ex(e, '刷新设备状态失败')    
        
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