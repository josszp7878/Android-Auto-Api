import os
from datetime import datetime
from pathlib import Path

class SDevice:
    """设备类：管理设备状态和信息"""
    
    def __init__(self, device_id, info=None):
        self.device_id = device_id
        self.status = 'offline'
        self.last_seen = datetime.now()
        self.info = info or {}
        self._ensure_screenshot_dir()
    
    def _ensure_screenshot_dir(self):
        """确保设备的截图目录存在"""
        self.screenshot_dir = Path('app/static/screenshots') / self.device_id
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    def login(self):
        self.status = 'login'
        self.last_seen = datetime.now()
        print(f'设备登录: {self.device_id}')
    
    def logout(self):
        self.status = 'online'
        self.last_seen = datetime.now()
        print(f'设备登出: {self.device_id}')
    
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