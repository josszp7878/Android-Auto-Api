from flask import current_app
from SModels import db, DeviceModel
from SDevice import SDevice_
import _Log
from datetime import datetime
from flask_socketio import emit
from typing import Optional, Callable, List
import threading
import hashlib
import time
import _G
from typing import cast

class SDeviceMgr_:
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
            self.consoles = set()  # 存储控制台的 SID
            self.curDeviceIDs = []
            self.initialized = True
            self.result = None
            self.onCmdResult: Callable[[str], None] = None
            self.cmdTimeout = 10  # 命令超时时间(秒)
            self.pendingCmds = {}  # 存储待处理的命令 {cmd_id: timer}
            self.cmdResults = {}  # 存储命令结果 {cmd_id: result}
            self.cmdEvents = {}   # 存储命令完成事件 {cmd_id: Event}

    @property
    def devices(self):
        if self._devices is None:
            self._devices = self._load()
        return self._devices

    def _load(self):
        try:
            deviceList = {}
            # _Log._Log_.i('加载数据库设备列表')
            with current_app.app_context():  # 添加应用上下文
                for device_model in DeviceModel.query.all():
                    device = SDevice_(device_model.device_id)
                    device.init(device_model)
                    deviceList[device.device_id] = device
            _Log._Log_.i(f'从数据库加载了 {len(deviceList)} 个设备')

            return deviceList
        except Exception as e:
            _Log._Log_.ex(e, '加载数据库出错')
            return {}

    def _save(self, device):
        """保存设备到数据库"""
        try:
            with current_app.app_context():
                device_model = DeviceModel.query.filter_by(
                    device_id=device.device_id.lower()
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
            _Log._Log_.ex(e, '保存数据库出错')

    def add(self, id):
        """添加新设备"""
        id = id.lower()
        device = SDevice_(id)
        device.init()
        self.devices[id] = device
        self._save(device)
        _Log._Log_.i(f'添加设备: {id}')
        return device

    def get(self, id) -> Optional[SDevice_]:
        """获取设备"""
        return self.devices.get(id.lower())
    
    def gets(self, idOrGroup) -> List[SDevice_]:
        """获取设备"""
        if idOrGroup is None or idOrGroup == '':
            return []
        device = self.devices.get(idOrGroup)
        if device:
            return [device]
        return self.GetByGroup(idOrGroup)
    
    def getBySID(self, sid) -> Optional[SDevice_]:
        """根据sid获取设备"""
        for device in self.devices.values():
            if device.info.get('sid') == sid:
                return device
        return None

    def commit(self, device):
        """更新设备信息"""
        try:
            db.session.commit()
            _Log._Log_.i('Server', f'设备 {device.device_id} 信息已更新')
        except Exception as e:
            _Log._Log_.ex(e, '更新设备信息失败')

    def toDict(self):
        """转换所有设备为字典格式"""
        return {
            device_id: {
                **device.to_dict()
            }
            for device_id, device in self.devices.items()
        }

    @property
    def curDeviceID(self):
        """获取当前设备ID"""
        return self.curDeviceIDs[0] if self.curDeviceIDs and len(self.curDeviceIDs) > 0 else None

    @property
    def currentApp(self) -> Optional[str]:
        """获取当前设备的当前应用名称"""
        try:
            if not self.curDeviceID:
                return None
            device = self.get(self.curDeviceID)
            if not device:
                return None
            return device.taskMgr.currentApp
        except Exception as e:
            _Log._Log_.ex(e, "获取当前应用失败")
            return None

    @property
    def curDevice(self) -> Optional[SDevice_]:
        return self.devices.get(self.curDeviceID)

    def update(self, device):
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
            _Log._Log_.ex(e, '更新设备失败')
            return False

    def addConsole(self, sid):
        """添加控制台连接"""
        self.consoles.add(sid)
        _Log._Log_.i(f'添加控制台连接: {sid}')

    def removeConsole(self, sid):
        """移除控制台连接"""
        if sid in self.consoles:
            self.consoles.remove(sid)
            _Log._Log_.i(f'移除控制台连接: {sid}')

    def emit2B(self, event, data=None):
        """向所有控制台发送事件"""
        try:
            from app import socketio
            if not self.consoles:
                # 没有控制台连接，不发送
                return

            # 确保数据可序列化
            import json
            try:
                # 尝试序列化数据
                json.dumps(data)
            except TypeError:
                # 如果序列化失败，转换为字符串
                _Log._Log_.w(f'事件 {event} 数据无法序列化，已转换为字符串')
                data = str(data)

            # 发送事件 - 将集合转换为列表
            for sid in self.consoles:
                try:
                    socketio.emit(event, data, room=sid)
                except Exception as e:
                    _Log._Log_.w(f'向控制台 {sid} 发送事件 {event} 失败: {e}')
        except Exception as e:
            _Log._Log_.ex(e, f'向控制台发送事件 {event} 失败')

##########################################################
# 命令处理
##########################################################
    def handleCmdResult(self, data):
        """处理命令响应"""
        try:
            result = str(data.get('result', ''))
            device_id = data.get('device_id')
            cmdName = data.get('cmdName')
            cmd_id = data.get('cmd_id')

            # 如果有命令ID，取消对应的超时定时器并存储结果
            if cmd_id and cmd_id in self.pendingCmds:
                self.pendingCmds[cmd_id].cancel()
                del self.pendingCmds[cmd_id]

                # 特殊处理截图命令
                if cmdName == 'captureScreen':
                    if isinstance(result, str) and result.startswith('data:image'):
                        device = self.get(device_id)
                        if device:
                            if device.saveScreenshot(result):
                                result = '截图已更新'
                            else:
                                result = '截图更新失败'

                # 存储结果并设置事件
                self.cmdResults[cmd_id] = result
                if cmd_id in self.cmdEvents:
                    self.cmdEvents[cmd_id].set()
        except Exception as e:
            _Log._Log_.ex(e, '处理命令响应出错')

        if self.onCmdResult:
            self.onCmdResult(result)

    def genCmdId(self, device_id, command):
        """生成命令唯一ID"""
        # 使用设备ID、命令和时间戳生成唯一ID
        cmd_str = f"{device_id}:{command}:{time.time()}"
        return hashlib.md5(cmd_str.encode()).hexdigest()[:16]

    def handleCmdTimeout(self, cmd_id, command):
        """处理命令超时"""
        if cmd_id in self.pendingCmds:
            del self.pendingCmds[cmd_id]
            # 存储超时结果并设置事件
            timeout_result = f"e->命令执行超时: {command}"
            self.cmdResults[cmd_id] = timeout_result
            if cmd_id in self.cmdEvents:
                self.cmdEvents[cmd_id].set()
            
    def sendClientCmd(self, deviceID, command, data=None, timeout=10):
        if deviceID is None:
            return False
        device = self.get(deviceID)
        if device is None:
            return False
        return self._sendClientCmd(device, command, data, timeout)

    def _sendClientCmd(self, device, command, data=None, timeout=10):
        """执行设备命令并等待结果

        Args:
            device: 设备
            command: 命令名称
            data: 命令参数
            timeout: 超时时间(秒)

        Returns:
            str: 命令执行结果
        """
        log = _G._G_.Log()
        try:
            device = cast(SDevice_, device)
            with current_app.app_context():
                if not device.isConnected:
                    return 'w->设备未连接'
                sid = device.info.get('sid')
                if not sid:
                    return 'w->设备会话无效'
                # 生成命令ID并创建事件
                cmd_id = self.genCmdId(device.device_id, command)
                cmd_event = threading.Event()
                self.cmdEvents[cmd_id] = cmd_event
                # 设置超时定时器
                timer = threading.Timer(timeout, self.handleCmdTimeout, args=[
                                        cmd_id, command])
                timer.daemon = True
                timer.start()
                self.pendingCmds[cmd_id] = timer

                # 发送命令
                try:
                    emit('S2C_DoCmd', {
                        'command': command,
                        'sender': current_app.config['SERVER_ID'],
                        'data': data,
                        'cmd_id': cmd_id
                    }, to=sid)
                except Exception as e:
                    log.ex(e, '发送命令时出错')
                    return f'e->发送命令异常{e}'

                # 等待结果或超时
                cmd_event.wait(timeout)
                # 获取结果
                result = self.cmdResults.get(cmd_id, f"e->命令执行超时: {command}")
                # 清理资源
                if cmd_id in self.cmdEvents:
                    del self.cmdEvents[cmd_id]
                if cmd_id in self.cmdResults:
                    del self.cmdResults[cmd_id]
                return result
        except Exception as e:
            log.ex(e, '执行设备命令出错')
            return f'e->执行命令失败:{e}'

    def GetByGroup(self, group_name) -> List[SDevice_]:
        """按分组获取设备列表
        
        Args:
            group_name: 分组名称
            
        Returns:
            list: 设备列表
        """
        try:
            result = []
            for device_id, device in self.devices.items():
                if device.group == group_name:
                    result.append(device)
            return result
        except Exception as e:
            _Log._Log_.ex(e, f"获取分组 {group_name} 的设备失败")
            return []
        
    def GetAllGroups(self):
        """获取所有设备分组
        
        Returns:
            list: 分组名称列表
        """
        try:
            groups = set()
            for device in self.devices.values():
                if device.group:  # 只添加非空分组
                    groups.add(device.group)
            return sorted(list(groups))
        except Exception as e:
            _Log._Log_.ex(e, "获取所有设备分组失败")
            return []

    def SetDeviceGroup(self, device_id, group_name):
        """设置设备分组

        Args:
            device_id: 设备ID
            group_name: 分组名称

        Returns:
            bool: 是否设置成功
        """
        try:
            device = self.get(device_id)
            if device:
                device.group = group_name
                _Log._Log_.i(f"设备 {device_id} 已分配到分组 {group_name}")
                return True
            return False
        except Exception as e:
            _Log._Log_.ex(e, f"设置设备 {device_id} 分组失败")
            return False

    def sendCmd(self, targets, command, data=None)->str:
        """发送命令"""
        result = ''            
        try:
            g = _G._G_
            log = g.Log()
            cmdMgr = g.getClass('_CmdMgr')
            for target in targets:
                if target == _Log.TAG.Server.value:
                    result, _ = cmdMgr.do(command, None, data)
                    g.SCommandHistory().add(command, target, result)
                else:
                    devices = self.gets(target) 
                    if len(devices) == 0:
                        log.w(f'设备 {target} 不存在')
                        continue
                    for device in devices:
                        result = self._sendClientCmd(device, command, data)
                        g.SCommandHistory().add(command, target, result)
            return result
        except Exception as e:
            log.ex(e, '发送命令失败')
            return None

    def addDevice(self, device):
        """添加新设备"""
        self.devices[device.device_id] = device
        device.last_seen = datetime.now()  # 更新连接时间
        self._save(device)
        _Log._Log_.i(f'新设备连接: {device.device_id}')
        return True


deviceMgr = SDeviceMgr_()
