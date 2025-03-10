from flask import current_app
from models import db, DeviceModel
from SDevice import SDevice
import _Log
from datetime import datetime
from flask_socketio import emit
from sqlalchemy import func
from typing import Dict, Optional, Callable
import threading
import hashlib
import time

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
            self.cmdTimeout = 10  # 命令超时时间(秒)
            self.pendingCmds = {}  # 存储待处理的命令 {cmd_id: timer}
    @property
    def devices(self):
        if self._devices is None:
            self._devices = self._load()
        return self._devices
    
    def _load(self):
        try:
            deviceList = {}
            # _Log.Log_.i('加载数据库设备列表')
            with current_app.app_context():  # 添加应用上下文
                for device_model in DeviceModel.query.all():
                    device = SDevice(device_model.device_id)
                    device.init(device_model)
                    deviceList[device.device_id] = device
            _Log.Log_.i(f'从数据库加载了 {len(deviceList)} 个设备')

            return deviceList
        except Exception as e:
            _Log.Log_.ex(e, '加载数据库出错')
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
            _Log.Log_.ex(e, '保存数据库出错')
    
    def add_device(self, device_id):
        """添加新设备"""
        device = SDevice(device_id)
        device.init()
        self.devices[device_id] = device
        self._save_to_db(device)
        _Log.Log_.i(f'添加设备: {device_id}')
        return device
    
    def get_device(self, device_id)->Optional[SDevice]:
        """获取设备"""
        return self.devices.get(device_id)

    def get_device_by_sid(self, sid)->Optional[SDevice]:
        """根据sid获取设备"""
        for device in self.devices.values():
            if device.info.get('sid') == sid:
                return device
        return None
    
    def commit(self, device):
        """更新设备信息"""
        try:
            db.session.commit()
            _Log.Log_.i('Server', f'设备 {device.device_id} 信息已更新')
        except Exception as e:
            _Log.Log_.ex(e, '更新设备信息失败')
    
    

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
        if not self._curDeviceID:
            for device_id, device in self.devices.items():
                if device.status == 'online':
                    self._curDeviceID = device_id
                    break
        return self._curDeviceID
        
    def SetCurDevice(self, deviceID: str, refresh:bool=True):
        """设置当前设备ID"""
        if deviceID != self._curDeviceID:
            self._curDeviceID = deviceID
            _Log.Log_.i(f"当前设备切换为: {deviceID}")
            if refresh:
                self.emit2B('S2B_SetCurDev', {'device_id': deviceID})
    

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
            _Log.Log_.ex(e, "获取当前应用失败")
            return None
    
    @property
    def curDevice(self)->Optional[SDevice]:
        return self.devices.get(self._curDeviceID)
    
    def CurDevice(self, showLog:bool=True)->Optional[SDevice]:
        device = None
        try:
            device = self.get_device(self._curDeviceID)
        except Exception as e:
            _Log.Log_.ex(e, "获取当前设备失败")
        if device is None and showLog:
            _Log.Log_.e("当前设备不存在")
        return device

    def update_device(self, device):
        try:
            with session_scope() as session:
                # 确保设备存在于内存中
                _devices = self.devices
                if not _devices.get(device.device_id):
                    _devices[device.device_id] = device
                    
                # 更新数据库
                db_device = session.query(DeviceModel).get(device.device_id)
                if db_device:
                    db_device.status = device.status
                    db_device.info = device.info
                    db_device.last_seen = datetime.now()
                else:
                    db_device = DeviceModel.from_device(device)
                    session.add(db_device)
                    
            return True
        except Exception as e:
            _Log.Log_.ex(e, '更新设备失败')
            return False

    def add_console(self, sid):
        """添加控制台连接"""
        self.console_sids.add(sid)
        _Log.Log_.i(f'添加控制台连接: {sid}')

    def remove_console(self, sid):
        """移除控制台连接"""
        if sid in self.console_sids:
            self.console_sids.remove(sid)
            _Log.Log_.i(f'移除控制台连接: {sid}')

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
                _Log.Log_.w(f'事件 {event} 数据无法序列化，已转换为字符串')
                data = str(data)
            
            # 发送事件 - 将集合转换为列表
            for sid in self.console_sids:
                try:
                    socketio.emit(event, data, room=sid)
                except Exception as e:
                    _Log.Log_.w(f'向控制台 {sid} 发送事件 {event} 失败: {e}')
        except Exception as e:
            _Log.Log_.ex(e, f'向控制台发送事件 {event} 失败')

##########################################################
# 命令处理
##########################################################
    def handCmdResult(self, data):
        """处理命令响应"""
        try:
            result = data.get('result')
            result = str(result)
            device_id = data.get('device_id')
            command = data.get('command')
            cmdName = data.get('cmdName')  # 获取命令方法名
            cmd_id = data.get('cmd_id')  # 获取命令ID
            
            # 如果有命令ID，取消对应的超时定时器
            if cmd_id and cmd_id in self.pendingCmds:
                self.pendingCmds[cmd_id].cancel()
                del self.pendingCmds[cmd_id]
            
            # 替换单引号为双引号
            self.result = result.replace("'", '"')
            
            # 根据命令方法名处理响应
            if cmdName == 'captureScreen':  # 使用方法名而不是命令文本判断
                if isinstance(result, str) and result.startswith('data:image'):
                    device = self.get_device(device_id)
                    if device is None:
                        _Log.Log_.e(f'设备 {device_id} 不存在')
                        return
                    if device.saveScreenshot(result):
                        result = '截图已更新'
                    else:
                        result = '截图更新失败'
            # _Log.Log_.i(f'命令响应: {device_id} -> {command} = {result}', _Log.TAG.CMD.value)
        except Exception as e:
            _Log.Log_.ex(e, '处理命令响应出错')
        
        
        if self.onCmdResult:
            self.onCmdResult(result)
        
        _Log.Log_.log(result, device_id)

    def genCmdId(self, device_id, command):
        """生成命令唯一ID"""
        # 使用设备ID、命令和时间戳生成唯一ID
        cmd_str = f"{device_id}:{command}:{time.time()}"
        return hashlib.md5(cmd_str.encode()).hexdigest()[:16]

    def handleCmdTimeout(self, cmd_id, device_id, command):
        """处理命令超时"""
        if cmd_id in self.pendingCmds:
            _Log.Log_.w(f"命令执行超时: {device_id} -> {command}", _Log.TAG.CMD.value)
            # 从待处理命令中移除
            del self.pendingCmds[cmd_id]
            # 调用结果回调
            if self.onCmdResult:
                self.onCmdResult(f"e->命令执行超时: {command}")
            # 记录日志
            _Log.Log_.log(f"{device_id}:{command} => 命令执行超时", 'e', _Log.TAG.CMD.value)

    def CmdTimeout(self, timeout, device_id, command)->str:
        """设置超时定时器"""
        # 生成命令ID
        cmd_id = self.genCmdId(device_id, command)
        timeout = timeout if timeout else self.cmdTimeout
        timer = threading.Timer(timeout, self.handleCmdTimeout, args=[cmd_id, device_id, command])
        timer.daemon = True
        timer.start()
        return cmd_id
    
    def doServerCmd(self, deviceID, command, data):
        from _CmdMgr import _CmdMgr
        result, _ = _CmdMgr.do(command, deviceID, data=data)
        _Log.Log_.log(result, _Log.TAG.SCMD.value)
        return result
    
    def sendClientCmd(self, device_id, command, data=None, timeout:int=10, callback:Callable[[str], None]=None):
        """执行设备命令"""
        try:
            self.onCmdResult = callback
            with current_app.app_context():
                # _Log.Log_.d(f'发送客户端命令: {device_id} -> {command}, DATA: {data}')
                device = self.get_device(device_id)
                if device is None:
                    _Log.Log_.e(f'设备 {device_id} 不存在')
                    return '设备不存在'
                if device.status != 'login':
                    _Log.Log_.w('Server', f'设备 {device_id} 未登录')
                    return '设备未登录'
                sid = device.info.get('sid')
                # _Log.Log_.i('Server', f'设备 SID: {sid}， 命令: {command}， 数据: {data}')
                if sid:
                    try:
                        cmd_id = self.CmdTimeout(timeout, device_id, command)
                        # 通过 sid 发送命令，包含 data 参数和命令ID
                        emit('S2C_DoCmd', {
                            'command': command,
                            'sender': current_app.config['SERVER_ID'],
                            'data': data,  # 添加 data 参数
                            'cmd_id': cmd_id  # 添加命令ID
                        }, to=sid)
                        # _Log.Log_.d('Server', f'命令已发送到设备 {device_id}')
                        return f'命令已发送到设备 {device_id}'
                    except Exception as e:
                        _Log.Log_.ex(e, '发送命令时出错')
                        return f'发送命令失败: {e}'
                else:
                    _Log.Log_.e('Server', f'设备 {device_id} 会话无效')
                    return '设备会话无效'
                
        except Exception as e:
            _Log.Log_.ex(e, '执行设备命令出错')
            return '执行命令失败'       
##########################################################


deviceMgr = SDeviceMgr()
