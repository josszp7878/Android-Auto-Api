from flask import current_app
from SDevice import SDevice_
import hashlib
import time
import _G
from typing import Optional, List

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
            self.onCmdResult = None
            self.cmdTimeout = 15
            self.cmdResults = {}
            self.cmdEvents = {}

    @property
    def _devices(self) -> List['SDevice_']:
        """延迟加载设备列表"""
        if self.__devices is None:
            self.__devices = SDevice_.all()
        return self.__devices
    
    @property
    def devices(self)->List['SDevice_']:
        return [d for d in self._devices if not d.isConsole]

    def getByName(self, name: str, create=False) -> Optional[SDevice_]:
        log = _G._G_.Log()
        name = name.strip().lower()
        try:
            devices = self._devices
            # log.i(f'######%%%%%%: {name}, devices.len={len(devices)}')
            device = next((d for d in devices if d.name == name), None)
            if device is None:
                from SModels import DeviceModel_
                data = DeviceModel_.get(name, create)
                if data:
                    device = SDevice_(data)
                    devices.append(device)                
            return device
        except Exception as e:
            log.ex(e, f'获取设备失败: {name}')
            return None

    def getBySID(self, sid : str) -> Optional[SDevice_]:
        return next((d for d in self._devices if d.sid == sid), None)

    def get(self, key) -> Optional[SDevice_]:

        g = _G._G_
        log = g.Log()
        try:
            id = g.toInt(key, 0)
            if id == 0:
                key = key.lower()
            for d in self._devices:
                # log.i(f'设备: {d.id}, {d.name}, key={key}, id={id}')
                if id == d.id:
                    return d
                if d.name.lower() == key:
                    return d
            return None
        except Exception as e:
            log.ex(e, f'获取设备失败: {key}')
            return None
    
    def getTask(self, key):
        """根据ID获取任务"""
        for d in self._devices:
            task = d.getTask(key)
            if task:
                return task
        return None

    
    @property
    def curDevice(self) -> Optional[SDevice_]:
        """获取当前设备"""
        return self.devices[0]
    
    def addDevice(self, device: SDevice_):
        devices = self._devices
        exist = next((d for d in devices if d.id == device.id), None)
        log = _G._G_.Log()
        log.d_(f'添加设备fff: {device.id}, {device.name} exist={exist}')
        if exist is None:
            self._devices.append(device)
        if device.isConsole:
            _G._G_.addConsole(device.sid)
    
    def removeDevice(self, device: SDevice_):
        self._devices.remove(device)
        if device.isConsole:
            _G._G_.removeConsole(device.sid)    

   
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
            if cmd_id:
                # 特殊处理截图命令
                if cmdName == 'captureScreen':
                    if isinstance(result, str) and result.startswith('data:image'):
                        device = self.getByName(name)
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

    def _onServerCmd(self, targetID:int, command, data=None)->dict:
        """发送服务器命令"""
        cmdMgr = _G._G_.CmdMgr()
        params = {'target': targetID, 'data': data}
        cmd = {'cmd': command, 'params': params}
        return cmdMgr.do(cmd)

    def onCmd(self, target:str, command:str, data=None):
        """发送命令"""
        result = None
        log = _G._G_.Log()
        try:
            log.add(command, '', 'c')
            if target == _G.ServerTag:
                cmd = self._onServerCmd(target, command, data)
                if cmd is None:
                    log.e(f'服务器命令执行失败: target={target} command={command} data={data}')
                    return None
                result = cmd.get('result')
                # log.i(f'服务器命令结果: {result}')
            else:
                # 如果失败，就当成纯客户端指令来执行
                device = self.get(target)
                if device is None:
                    return f'e~设备不存在: {target}'
                result = device.sendClientCmd(command, data)
                # log.i(f'处理客户端命令结果: {result}')
            
            # 添加调试信息
            # log.i(f'onCmd最终返回结果: {result}，类型: {type(result)}')
            _G._G_.Log().result(result)
            return result
        except Exception as e:
            self._log.ex(e, '发送命令失败')
            return f'e~发送命令失败: {str(e)}'


deviceMgr = SDeviceMgr_()
