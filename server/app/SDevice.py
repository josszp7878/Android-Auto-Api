import os
from datetime import datetime
from pathlib import Path
from flask import current_app
from .models import db, DeviceModel
from scripts.logger import Log
import json

class SDevice:
    """设备类：管理设备状态和信息"""
    
    def __init__(self, device_id, info=None):
        self.device_id = device_id
        self._status = 'offline'
        self.last_seen = datetime.now()
        self.info = info or {}
        self._ensure_screenshot_dir()
    
    def _ensure_screenshot_dir(self):
        """确保设备的截图目录存在"""
        self.screenshot_dir = Path('app/static/screenshots') / self.device_id
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
                    db.session.add(device_model)
                    db.session.commit()
                    # print(f'设备 {self.device_id} 状态已同步到数据库')
        except Exception as e:
            Log.ex(e, '同步设备状态到数据库出错')
    

    _lastScreenshot = '/static/screenshots/default.jpg'
    def screenshot(self, screenshot_data):
        """保存新的截图"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'SC{timestamp}.jpg'
            filepath = self.screenshot_dir / filename
            self._lastScreenshot = filepath
            with open(filepath, 'wb') as f:
                f.write(screenshot_data)
            self.refresh()    
        except Exception as e:
            Log.ex(e, '保存截图出错')
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'status': self.status,
            'last_seen': self.last_seen,
            'info': self.info,
            'screenshot': self._lastScreenshot
        } 
    
   
    def refresh(self): 
        try:
            # 获取设备管理器实例
            from .device_manager import DeviceManager
            # 发送设备状态更新
            # print(f'@@@@@refresh_device: {self.device_id}, {self.status}')
            DeviceManager().emit_to_console('refresh_device', {
                'device_id': self.device_id,
                'status': self.status,
                'timestamp': datetime.now().isoformat(),
                'screenshot': self._lastScreenshot
            })
        except Exception as e:
            Log.ex(e, '刷新设备状态失败')
    
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
            # 保存并关闭日志文件
            Log().save(self.device_id)
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