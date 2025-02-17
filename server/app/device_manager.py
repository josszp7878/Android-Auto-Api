from flask import current_app
from .models import db, DeviceModel
from .SDevice import SDevice
from scripts.logger import Log
from datetime import datetime, timedelta
from flask_socketio import emit
import re
from sqlalchemy import func
from .stask import STask, STaskState


class DeviceManager:
    """设备管理器：管理所有设备"""
    
    _instance = None
    _devices = None  # 提前定义类变量

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.device_id = None  # 初始化当前设备ID
        return cls._instance
   
    def __init__(self):
        # 只在第一次初始化时执行
        if not hasattr(self, 'initialized'):
            self.console_sids = set()  # 存储控制台的 SID
            self.initialized = True

    @property
    def devices(self):
        # print(f'@@@@@####devices: {len(self._devices)}')
        if self._devices is None:
            self._devices = self._load_from_db()
        return self._devices

    
    def _load_from_db(self):
        try:
            deviceList = {}
            with current_app.app_context():  # 添加应用上下文
                for device_model in DeviceModel.query.all():
                    device = SDevice(device_model.device_id, device_model.info)
                    device._status = device_model.status
                    device.last_seen = device_model.last_seen
                    deviceList[device.device_id] = device
            Log.i(f'从数据库加载了 {len(deviceList)} 个设备')
            return deviceList
        except Exception as e:
            Log.ex(e, '加载数据库出错')
            return {}
    
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
            Log.ex(e, '保存数据库出错')
    
    def add_device(self, device_id):
        """添加新设备"""
        device = SDevice(device_id)
        self.devices[device_id] = device
        self._save_to_db(device)
        Log.i(f'添加设备: {device_id}')
        return device
    
    def get_device(self, device_id):
        """获取设备"""
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
            Log.ex(e, '更新设备信息失败')
    
    def get_device_scores(self, device_id):
        """获取设备的得分统计"""
        try:
            today = datetime.now().date()
            
            with current_app.app_context():
                # 获取今日该任务的总分
                if self.curDeviceID and self.devices[self.curDeviceID].currentTask:
                    current_task = self.devices[self.curDeviceID].currentTask
                    today_task_score = STask.query.filter(
                        STask.deviceId == device_id,
                        STask.time >= today,
                        STask.appName == current_task.appName,
                        STask.taskName == current_task.taskName,
                        STask.state == STaskState.SUCCESS
                    ).with_entities(func.sum(STask.score)).scalar() or 0
                else:
                    today_task_score = 0
                
                # 获取设备总分
                device = self.get_device(device_id)
                if device:
                    total_score = device.total_score
                else:
                    total_score = 0
                
                return {
                    'todayTaskScore': today_task_score,
                    'totalScore': total_score
                }
        except Exception as e:
            Log.ex(e, f'获取设备{device_id}得分统计失败')
            return {'todayTaskScore': 0, 'totalScore': 0}

    def to_dict(self):
        """转换所有设备为字典格式"""
        return {
            device_id: {
                **device.to_dict(),
                **self.get_device_scores(device_id)
            }
            for device_id, device in self.devices.items()
        }

    _curDeviceID = None
    @property
    def curDeviceID(self):
        return self._curDeviceID
    
    @curDeviceID.setter
    def curDeviceID(self, value):
        self._curDeviceID = value
        # Log.i(f'设置当前设备ID: {value}')

    def update_device(self, device):
        try:
            # 确保设备存在于内存中
            _devices = self.devices
            if not _devices.get(device.device_id):
                _devices[device.device_id] = device            
            # 更新数据库 - 使用 merge 模式
            try:
                # 尝试获取现有设备
                db_device = DeviceModel.query.get(device.device_id)
                # Log.i('DeviceManager', f"设备 {db_device}, {device.device_id}")
                if db_device:   
                    # 更新现有设备
                    Log.i(f"更新设备 {db_device}", 'DeviceManager')
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
                Log.ex(e, '数据库更新失败')
                db.session.rollback()
                raise
            
            return True
        except Exception as e:
            Log.ex(e, '更新设备失败')
            return False

    def add_console(self, sid):
        """添加控制台连接"""
        self.console_sids.add(sid)
        Log.i(f'添加控制台连接: {sid}')

    def remove_console(self, sid):
        """移除控制台连接"""
        if sid in self.console_sids:
            self.console_sids.remove(sid)
            Log.i(f'移除控制台连接: {sid}')

    def get_console_sids(self):
        """获取所有控制台的 SID"""
        return list(self.console_sids)

    def emit2Console(self, event, data):
        for sid in self.console_sids:
            emit(event, data, room=sid)
