from flask import current_app
from .models import db, DeviceModel
from .SDevice import SDevice
from scripts.logger import Log
from datetime import datetime, timedelta
from flask_socketio import emit
from sqlalchemy import func
from typing import Dict, Optional, Callable
from scripts.tools import TAG

class SDeviceMgr:
    """设备管理器：管理所有设备"""
    
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
   
    def __init__(self):
        # 只在第一次初始化时执行
        if not hasattr(self, 'initialized'):
            self._devices = None  # 初始化为None，通过property懒加载
            self.console_sids = set()  # 存储控制台的 SID
            self._curDeviceID = None
            self.initialized = True
            self.result = None
            self.onCmdResult: Callable[[str], None] = None
    @property
    def devices(self):
        if self._devices is None:
            self._devices = self._load()
        return self._devices
    
    def _load(self):
        try:
            deviceList = {}
            # Log.i('加载数据库设备列表')
            with current_app.app_context():  # 添加应用上下文
                for device_model in DeviceModel.query.all():
                    device = SDevice(device_model.device_id)
                    device.init(device_model)
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
        device.init()
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
    
    

    def to_dict(self):
        """转换所有设备为字典格式"""
        return {
            device_id: {
                **device.to_dict()
            }
            for device_id, device in self.devices.items()
        }

    @property
    def curDeviceID(self) -> str:
        """获取当前设备ID"""
        return self._curDeviceID
        
    @curDeviceID.setter
    def curDeviceID(self, value: str):
        """设置当前设备ID"""
        if value != self._curDeviceID:
            self._curDeviceID = value
            Log.i(f"当前设备切换为: {value}")
            
    @property
    def currentApp(self) -> Optional[str]:
        """获取当前设备的当前应用名称"""
        try:
            if not self._curDeviceID:
                return None
            device = self.get_device(self._curDeviceID)
            if not device:
                return None
            return device.taskMgr.currentApp
        except Exception as e:
            Log.ex(e, "获取当前应用失败")
            return None
    
    @property
    def curDevice(self):
        return self.devices.get(self._curDeviceID)


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

    def emit2B(self, event, data=None):
        """向所有控制台发送事件"""
        try:
            from app import socketio
            if not self.console_sids:
                # 没有控制台连接，不发送
                return
            
            # 确保数据可序列化
            import json
            try:
                # 尝试序列化数据
                json.dumps(data)
            except TypeError:
                # 如果序列化失败，转换为字符串
                Log.w(f'事件 {event} 数据无法序列化，已转换为字符串')
                data = str(data)
            
            # 发送事件 - 将集合转换为列表
            for sid in self.console_sids:
                try:
                    socketio.emit(event, data, room=sid)
                except Exception as e:
                    Log.w(f'向控制台 {sid} 发送事件 {event} 失败: {e}')
        except Exception as e:
            Log.ex(e, f'向控制台发送事件 {event} 失败')


    def handCmdResult(self, data):
        """处理命令响应"""
        try:
            result = data.get('result')
            result = str(result)
            device_id = data.get('device_id')
            command = data.get('command')
            cmdName = data.get('cmdName')  # 获取命令方法名
            # sender = "@"
            level = result.split('#')[0] if '#' in result else 'i'
            # 替换单引号为双引号
            self.result = result.replace("'", '"')
            # 添加调试日志
            # Log.i('Server', f'收到命令响应: {device_id} -> {command} = {result}')
            
            # 根据命令方法名处理响应
            if cmdName == 'captureScreen':  # 使用方法名而不是命令文本判断
                if isinstance(result, str) and result.startswith('data:image'):
                    device = self.get_device(device_id)
                    if device is None:
                        Log.e(f'设备 {device_id} 不存在')
                        return
                    if device.saveScreenshot(result):
                        result = '截图已更新'
                    else:
                        result = '截图更新失败'
            Log.i(f'命令响应: {device_id} -> {command} = {result}', TAG.CMD)
        except Exception as e:
            Log.ex(e, '处理命令响应出错')
        # 解析level
        if isinstance(result, str) and '##' in result:
            level = result.split('##')[0]
            if level in ['w', 'e', 'i', 'd']:
                result = result.split('##')[1:]
            else:
                level = 'i'
        else:
            level = 'i'
        if self.onCmdResult:
            self.onCmdResult(result)
        Log()._log(f"{device_id}:{command}  => {result}", level, TAG.CMD)

    def sendClientCmd(self, device_id, command, data=None, callback: Callable[[str], None]=None):
        """执行设备命令"""
        try:
            self.onCmdResult = callback
            with current_app.app_context():
                Log.i(f'发送客户端命令: {device_id} -> {command}, DATA: {data}')
                device = self.get_device(device_id)
                if device is None:
                    Log.e(f'设备 {device_id} 不存在')
                    return '设备不存在'
                if device.status != 'login':
                    Log.w('Server', f'设备 {device_id} 未登录')
                    return '设备未登录'
                sid = device.info.get('sid')
                # Log.i('Server', f'设备 SID: {sid}')
                if sid:
                    try:
                        # 通过 sid 发送命令，包含 data 参数
                        emit('S2C_DoCmd', {
                            'command': command,
                            'sender': current_app.config['SERVER_ID'],
                            'data': data  # 添加 data 参数
                        }, to=sid)
                        
                        Log.i('Server', f'命令已发送到设备 {device_id}')
                        return f'命令已发送到设备 {device_id}'
                    except Exception as e:
                        Log.ex(e, '发送命令时出错')
                        return f'发送命令失败: {e}'
                else:
                    Log.e('Server', f'设备 {device_id} 会话无效')
                    return '设备会话无效'
                
        except Exception as e:
            Log.ex(e, '执行设备命令出错')
            return '执行命令失败'        


deviceMgr = SDeviceMgr()
