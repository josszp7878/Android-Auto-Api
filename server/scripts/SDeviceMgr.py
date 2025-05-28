from flask import current_app
from SDevice import SDevice_
import hashlib
import time
import _G
from typing import Optional, List
import threading

class SDeviceMgr_:
    """设备管理器：管理所有设备"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            import _Log
            self._log = _Log._Log_
            self.__devices = None  # 初始化为None
            self.initialized = True
            self.result = None
            self._curDevice = None
            self.onCmdResult = None
            self.cmdTimeout = 15
            self.pendingCmds = {}
            self.cmdResults = {}
            self.cmdEvents = {}

    @property
    def _devices(self) -> List['SDevice_']:
        """延迟加载设备列表"""
        if self.__devices is None:
            from SModels import DeviceModel
            self.__devices = DeviceModel.all(SDevice_)
        return self.__devices
    
    @property
    def devices(self):
        return [d for d in self._devices if not d.isConsole]

    def get(self, name: str, create=False) -> Optional[SDevice_]:
        try:
            devices = self._devices
            device = next((d for d in devices if d.name == name), None)
            if device is None and create:
                log = _G._G_.Log()
                log.i(f'创建设备: {name}')
                device = SDevice_(name)
                devices.append(device)
            return device
        except Exception as e:
            self._log.ex(e, f'获取设备失败: {name}')
            return None

    def getBySID(self, sid) -> Optional[SDevice_]:
        return next((d for d in self._devices if d.sid == sid), None)

    def getByID(self, id) -> Optional[SDevice_]:
        return next((d for d in self._devices if d.id == id), None)
    
    def setName(self, deviceId, name=None):
        g = _G._G_
        log = g.Log()
        try:
            device = self.getByID(deviceId)
            log.i(f'更新设备属性: {deviceId}, {name}, {device}')
            if device is None or name is None:
                return False
            exist = self.get(name)
            log.i(f'检测设备是否存在: {name},  {exist}')
            if exist:
                log.e(f'设备名字重复: {name}')
                return False
            device.setDBProp('name', name)
            log.i(f'更新设备属性@@@@: {deviceId}, dirty= {device._isDirty}')
            if device.commit():
                g.emit('S2C_updateDevice', {
                    'name': name
                }, device.sid)
                return True
            return False
        except Exception as e:
            log.ex(e, '更新设备属性失败')
            return False

    @property
    def curDevice(self) -> Optional[SDevice_]:
        """获取当前设备"""
        return self._curDevice

    @curDevice.setter
    def curDevice(self, value):
        self._curDevice = value

##########################################################
# 命令处理
##########################################################
    def handleCmdResult(self, data):
        """处理命令响应"""
        try:
            result = str(data.get('result', ''))
            name = data.get('name')
            cmdName = data.get('cmdName')
            cmd_id = data.get('cmd_id')

            # 如果有命令ID，取消对应的超时定时器并存储结果
            if cmd_id and cmd_id in self.pendingCmds:
                self.pendingCmds[cmd_id].cancel()
                del self.pendingCmds[cmd_id]

                # 特殊处理截图命令
                if cmdName == 'captureScreen':
                    if isinstance(result, str) and result.startswith('data:image'):
                        device = self.get(name)
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
            self._log.ex(e, '处理命令响应出错')

        if self.onCmdResult:
            self.onCmdResult(result)

    def genCmdId(self, name, command):
        """生成命令唯一ID"""
        # 使用设备ID、命令和时间戳生成唯一ID
        cmd_str = f"{name}:{command}:{time.time()}"
        return hashlib.md5(cmd_str.encode()).hexdigest()[:16]

    def handleCmdTimeout(self, cmd_id, command):
        """处理命令超时"""
        if cmd_id in self.pendingCmds:
            del self.pendingCmds[cmd_id]
            # 存储超时结果并设置事件
            timeout_result = f"e~命令执行超时: {command}"
            self.cmdResults[cmd_id] = timeout_result
            if cmd_id in self.cmdEvents:
                self.cmdEvents[cmd_id].set()

    def sendClientCmd(self, device, command, data=None, timeout=10):
        """执行设备命令并等待结果
        Args:
            device: 设备
            command: 命令名称
            data: 命令参数
            timeout: 超时时间(秒)

        Returns:
            str: 命令执行结果
        """
        try:
            with current_app.app_context():
                if not device.isConnected:
                    return 'w~设备未连接'
                sid = device.sid
                if not sid:
                    return 'w~设备会话无效'
                # 生成命令ID并创建事件
                cmd_id = self.genCmdId(device.name, command)
                cmd_event = threading.Event()
                self.cmdEvents[cmd_id] = cmd_event
                # 设置超时定时器
                # log.i(f'设置超时定时器: {cmd_id}, {command}, {timeout}')
                timer = threading.Timer(timeout, self.handleCmdTimeout, args=[
                                        cmd_id, command])
                timer.daemon = True
                timer.start()
                self.pendingCmds[cmd_id] = timer

                # 发送命令
                try:
                    _G._G_.sio.emit('S2C_DoCmd', {
                        'command': command,
                        'sender': current_app.config['SERVER_ID'],
                        'data': data,
                        'cmd_id': cmd_id
                    }, to=sid)
                except Exception as e:
                    self._log.ex(e, '发送命令时出错')
                    return f'e~发送命令异常{e}'

                # 等待结果或超时
                # cmd_event.wait(timeout)
                # 获取结果
                result = self.cmdResults.get(cmd_id, f"e~命令执行超时: {command}")
                # 清理资源
                if cmd_id in self.cmdEvents:
                    del self.cmdEvents[cmd_id]
                if cmd_id in self.cmdResults:
                    del self.cmdResults[cmd_id]
                return result
        except Exception as e:
            self._log.ex(e, '执行设备命令出错')
            return f'e~执行命令失败:{e}'

    def sendCmd(self, targets, command, data=None):
        """发送命令"""
        result = ''
        log = _G._G_.Log()
        try:
            if targets is None or len(targets) == 0:
                return
            for target in targets:
                if target == _G.ServerTag:
                    # 记录服务端命令日志
                    cmdID = self.genCmdId('@', command)
                    cmd = {'id': cmdID, 'data': data, 'cmd': command}
                    log.Blog(command, '', 'c')
                    cmdMgr = _G._G_.CmdMgr()
                    cmdMgr.do(cmd)
                    result = cmd.get('result', '')
                else:
                    for device in self.devices:
                        # 记录客户端命令日志
                        self._log.c(command, device.name)
                        result = self.sendClientCmd(device, command, data)
                _G._G_.SCommandHistory().add(command, target, result)
                # 如果有结果，再发送结果日志
                if result:
                    # 使用命令结果的日志级别
                    level, content = self._log._parseLevel(result, 'i')
                    if content: 
                        self._log.Blog(f"  结果： {content}", '', level)
        except Exception as e:
            self._log.ex(e, '发送命令失败')


deviceMgr = SDeviceMgr_()
