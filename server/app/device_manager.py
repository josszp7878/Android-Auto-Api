from flask import current_app
from .models import db, DeviceModel
from .SDevice import SDevice
from .logger import Log
from datetime import datetime


class DeviceManager:
    """设备管理器：管理所有设备"""
    
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.device_id = None  # 初始化当前设备ID
        return cls._instance

    def __init__(self):
        self.devices = {}
        self.initialized = False
        # 移除在初始化时的数据库检查，因为此时可能还没有应用上下文
    
    def ensure_initialized(self):
        """确保已从数据库加载数据"""
        if not self.initialized:
            with current_app.app_context():
                try:
                    # 在这里进行数据库检查
                    count = DeviceModel.query.count()
                    Log.i('DeviceManager', f"数据库中设备数量: {count}")
                    self._load_from_db()
                except Exception as e:
                    Log.e('DeviceManager', f"数据库初始化失败: {e}")
            self.initialized = True
    
    def _load_from_db(self):
        """从数据库加载设备"""
        try:
            for device_model in DeviceModel.query.all():
                device = SDevice(device_model.device_id, device_model.info)
                device._status = device_model.status
                device.last_seen = device_model.last_seen
                self.devices[device.device_id] = device
            Log.i('Server', f'从数据库加载了 {len(self.devices)} 个设备')
        except Exception as e:
            Log.e('Server', f'加载数据库出错: {e}')
    
    def _save_to_db(self, device):
        """保存设备到数据库"""
        try:
            with current_app.app_context():
                device_model = DeviceModel.query.filter_by(
                    device_id=device.device_id
                ).first()
                if not device_model:
                    device_model = DeviceModel.from_device(device)
                    db.session.add(device_model)
                else:
                    device_model.status = device.status
                    device_model.last_seen = device.last_seen
                    device_model.info = device.info
                db.session.commit()
        except Exception as e:
            Log.e('Server', f'保存数据库出错: {e}')
    
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
    
    def commit(self, device):
        """更新设备信息"""
        try:
            db.session.commit()
            Log.i('Server', f'设备 {device.device_id} 信息已更新')
        except Exception as e:
            Log.e('Server', f'更新设备信息失败: {e}')
    
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
        Log.i('Server', f'设置当前设备ID: {device_id}')

    def get_device_id(self):
        """获取当前设备ID"""
        Log.i('Server', f'获取当前设备ID: {self.device_id}')
        return self.device_id

    def update_device(self, device):
        try:
            Log.i('DeviceManager', f"更新设备 {device.device_id}")
            # 确保设备存在于内存中
            if not self.devices.get(device.device_id):
                self.devices[device.device_id] = device            

            # 检查数据库连接
            try:
                # 检查数据库中的所有设备
                all_devices = DeviceModel.query.all()
                Log.i('DeviceManager', f"数据库中的所有设备: {[d.device_id for d in all_devices]}")
                
                # 直接使用 filter_by 查询特定设备
                test_device = DeviceModel.query.filter_by(device_id=device.device_id).first()
                Log.i('DeviceManager', f"通过 filter_by 查询设备: {test_device}")
            except Exception as e:
                Log.e('DeviceManager', f"数据库查询测试失败: {e}")

            # 更新数据库 - 使用 merge 模式
            try:
                # 尝试获取现有设备
                db_device = DeviceModel.query.get(device.device_id)
                Log.i('DeviceManager', f"设备 {db_device}, {device.device_id}")
                
                if db_device:   
                    # 更新现有设备
                    Log.i('DeviceManager', f"更新设备 {db_device}")
                    db_device.status = device.status
                    db_device.info = device.info
                    db_device.last_seen = datetime.now()
                else:
                    # 创建新设备
                    db_device = DeviceModel(
                        device_id=device.device_id,
                        status=device.status,
                        info=device.info,
                        last_seen=datetime.now()
                    )
                    Log.i('DeviceManager', f"创建新设备 {db_device}")
                    db.session.add(db_device)
                
                # 提交更改
                db.session.commit()
                
            except Exception as e:
                Log.e('DeviceManager', f"数据库更新失败: {e}")
                db.session.rollback()
                raise
            
            return True
        except Exception as e:
            Log.e('DeviceManager', f'更新设备失败: {e}')
            return False