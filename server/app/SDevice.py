import os
from datetime import datetime
from pathlib import Path
from flask import current_app
from .models import db, DeviceModel

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
        self._sync_to_db()
    
    def _sync_to_db(self):
        """同步设备状态到数据库"""
        try:
            with current_app.app_context():
                device_model = DeviceModel.query.filter_by(device_id=self.device_id).first()
                if device_model:
                    device_model.status = self._status
                    device_model.last_seen = self.last_seen
                    db.session.add(device_model)
                    db.session.commit()
                    print(f'设备 {self.device_id} 状态已同步到数据库')
        except Exception as e:
            print(f'同步设备状态到数据库出错: {e}')
    
    def login(self):
        self.status = 'login'
        print(f'设备{self.device_id}登录:')
        return True
    
    def logout(self):
        self.status = 'online'
        print(f'设备{self.device_id}登出:')
        return True
    
    def update_status(self, status):
        """更新设备状态"""
        self.status = status
    
    def get_latest_screenshot(self):
        """获取最新的截图URL"""
        try:
            screenshots = list(self.screenshot_dir.glob('SC*.jpg'))
            if not screenshots:
                return '/static/screenshots/default.jpg'
            latest = max(screenshots, key=lambda x: x.stat().st_mtime)
            return f'/static/screenshots/{self.device_id}/{latest.name}'
        except Exception as e:
            print(f'获取截图出错: {e}')
            return '/static/screenshots/default.jpg'
    
    def save_screenshot(self, screenshot_data):
        """保存新的截图"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'SC{timestamp}.jpg'
            filepath = self.screenshot_dir / filename
            with open(filepath, 'wb') as f:
                f.write(screenshot_data)
            return f'/static/screenshots/{self.device_id}/{filename}'
        except Exception as e:
            print(f'保存截图出错: {e}')
            return None
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'status': self.status,
            'last_seen': self.last_seen,
            'info': self.info,
            'screenshot': self.get_latest_screenshot()
        } 
    
    