from datetime import datetime
from flask import current_app
from .models import db, DeviceModel
from .SDevice import SDevice

class DeviceManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DeviceManager, cls).__new__(cls, *args, **kwargs)
            cls._instance.device_id = None  # 初始化当前设备ID
        return cls._instance

    """设备管理器：管理所有设备"""
    
    def __init__(self):
        self.devices = {}
        self.initialized = False
    
    def ensure_initialized(self):
        """确保已从数据库加载数据"""
        if not self.initialized:
            with current_app.app_context():
                self._load_from_db()
            self.initialized = True
    
    def _load_from_db(self):
        """从数据库加载设备"""
        try:
            for device_model in DeviceModel.query.all():
                device = SDevice(device_model.device_id, device_model.info)
                device._status = device_model.status  # 直接设置状态属性
                device.last_seen = device_model.last_seen
                self.devices[device.device_id] = device
            print(f'从数据库加载了 {len(self.devices)} 个设备')
        except Exception as e:
            print(f'加载数据库出错: {e}')
    
    def _save_to_db(self, device):
        """保存设备到数据库"""
        try:
            with current_app.app_context():
                device_model = DeviceModel.query.filter_by(device_id=device.device_id).first()
                if not device_model:
                    device_model = DeviceModel.from_device(device)
                    db.session.add(device_model)
                else:
                    device_model.status = device.status
                    device_model.last_seen = device.last_seen
                    device_model.info = device.info
                db.session.commit()
                # print(f'设备 {device.device_id} 已保存到数据库')
        except Exception as e:
            print(f'保存数据库出错: {e}')
    
    def add_device(self, device_id, info=None):
        """添加设备"""
        self.ensure_initialized()
        device = SDevice(device_id, info)
        self.devices[device_id] = device
        self._save_to_db(device)
        return device
    
    def get_device(self, device_id):
        """获取设备"""
        self.ensure_initialized()
        return self.devices.get(device_id)

    def get_device_by_sid(self, sid):
        """根据sid获取设备"""
        for device in self.devices.values():
            if device.info.get('sid') == sid:
                return device
        return None
    
    def update_device(self, device):
        """更新设备状态"""
        self.ensure_initialized()
        if device.device_id in self.devices:
            self._save_to_db(device)
    
    def to_dict(self):
        """转换所有设备为字典格式"""
        self.ensure_initialized()
        return {
            device_id: device.to_dict()
            for device_id, device in self.devices.items()
        } 

    def set_device_id(self, device_id):
        """设置当前设备ID"""
        self.device_id = device_id
        print(f'@@@ set_device_id: {device_id}')


    def get_device_id(self):
        """获取当前设备ID"""
        print(f'@@@ get_device_id: {self.device_id}')
        return self.device_id