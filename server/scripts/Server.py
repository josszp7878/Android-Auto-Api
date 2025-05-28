import re
from flask import request
from flask_socketio import emit
from datetime import datetime
import _G
import _Log
from SDeviceMgr import deviceMgr
from SDatabase import Database

# 先定义一个函数，用于延迟注册事件处理器
def initSocketIO(sio):
    """初始化SocketIO事件，在_G_.socketio被设置后调用"""
    _G._G_.sio = sio
    # 注册所有事件
    sio.on('connect')(handleConnect)
    sio.on('disconnect')(handleDisconnect)
    sio.on('C2S_Login')(handleC2SLogin)
    sio.on('C2S_Logout')(handleC2SLogout)
    sio.on('C2S_Screenshot')(handleC2SScreenshot)
    sio.on('C2S_Log')(handleC2SLog)
    sio.on('C2S_StartTask')(handleC2SStartTask)
    sio.on('C2S_UpdateTask')(handleC2SUpdateTask)
    sio.on('2S_Cmd')(handle2SCmd)
    sio.on('C2S_CmdResult')(handleC2SCmdResult)
    # 表格数据加载事件
    sio.on('B2S_loadTasks')(handleB2SLoadTasks)
    sio.on('B2S_loadDevices')(handleB2SLoadDevices)
    sio.on('B2S_loadLogs')(handleB2SLoadLogs)
    sio.on('B2S_setDeviceProp')(handleSetDeviceProp)
    # deviceMgr.registerEvents(sio)


def handleSetDeviceProp(data):
    """处理设备更新请求"""
    try:
        deviceId = data.get('deviceId')
        name = data.get('name')
        if not name:
            return
        return deviceMgr.setName(deviceId, name)
    except Exception as e:
        _Log._Log_.ex(e, '处理设备更新请求失败')


# 定义事件处理函数（不使用装饰器）
def handleConnect(auth=None)->bool:
    """处理客户端连接"""
    g = _G._G_
    log = _Log._Log_
    try:
        deviceName = request.args.get('device_id')
        device = deviceMgr.get(deviceName, True)
        log.i(f'设置当前设备: name={deviceName}, device={device}')
        if device.isConsole:
            g.setCurConsole(device.sid)
        else:
            deviceMgr.curDevice = device
        if device:
            device.onConnect(request.sid)
            device.commit()
    except Exception as e:
        log.ex(e, '处理连接时出错')
        return False
    return True

def handleDisconnect():
    """处理客户端断开连接"""
    try:
        device = deviceMgr.getBySID(request.sid)
        if device:
            device.onDisconnect()            
    except Exception as e:
        _Log._Log_.ex(e, '处理客户端断开连接失败')

def handleC2SLogin(data):
    """处理设备登录"""
    try:
        device = deviceMgr.getBySID(request.sid)
        if not device:
            return
        # 普通设备处理
        ok = device.login()
        _Log._Log_.i(f'设备 {device.name} 登录结果: {ok}')
    except Exception as e:
        _Log._Log_.ex(e, '处理设备登录失败')


def handleC2SLogout(data):
    """处理设备登出"""
    try:
        device = deviceMgr.getBySID(request.sid)
        if not device:
            return
        # 普通设备处理
        ret = False
        if device:
            ret = device.logout()
        emit('S2C_CmdResult', {'result': ret}, room=device.sid)
        return ret
    except Exception as e:
        _Log._Log_.ex(e, '处理设备登出失败')


def handleC2SScreenshot(data):
    """处理设备截图更新"""
    try:
        device = deviceMgr.getBySID(request.sid)
        if not device:
            return
        screenshotData = data.get('image')
        if screenshotData is None:
            return
        device.saveScreenshot(screenshotData)  # 保存后会自动刷新前端
    except Exception as e:
        _Log._Log_.ex(e, '处理设备截图更新失败')



def handleC2SLog(data):
    """处理客户端日志"""
    Log = _Log._Log_
    try:
        message = data.get('message')
        tag = data.get('tag')
        level = data.get('level', 'i')
        Log.log(message, tag, level)
    except Exception as e:
        Log.ex(e, '处理客户端日志失败')


def handleB2SGetLogs(data=None):
    """处理获取日志请求"""
    try:
        date = data.get('date') if data else None
        _Log._Log_.load(date)  # 这会加载日志并发送到前端
    except Exception as e:
        _Log._Log_.ex(e, '加载日志失败')


def handleC2SStartTask(data):
    """处理任务启动请求"""
    log = _Log._Log_
    try:
        device = deviceMgr.getBySID(request.sid)
        if not device:
            return
        taskName = data.get('taskName')
        from STask import STask_
        task = STask_.get(device.name, taskName, date=datetime.now().date(), create=True)
        log.i(f'处理任务启动请求: {device.name}/{taskName}, task: {task}')
        if task:
            task.start()
    except Exception as e:
        log.ex(e, '处理任务启动请求失败')


def handleC2SUpdateTask(data):
    """处理任务进度更新"""
    log = _Log._Log_
    try:
        device = deviceMgr.getBySID(request.sid)
        if not device:
            return
        taskName = data.get('taskName')
        from STask import STask_
        task = STask_.get({'deviceId': device.id, 'name': taskName}, create=False)
        log.i(f'处理任务进度更新请求: {device.name}/{taskName}, task: {task}')
        if task is None:
            log.i(f'任务不存在: {device.name}/{taskName}')
            return
        task.update(data)
    except Exception as e:
        log.ex(e, '处理任务进度更新失败')


def handle2SCmd(data):
    """处理2S命令请求"""
    Log = _Log._Log_
    try:
        selectedIDs = data.get('device_ids', [])
        # _Log._Log_.i(f'目标: {selectedIDs}')
        strCommand = data.get('command', '')

        # 检查命令是否指定了executor
        clientTag = re.match(r'^\s*([^>》]*)[>》]+\s*(.+)$', strCommand)
        serverTag = re.match(r'^\s*@\s*(.+)$', strCommand)
        targets = []
        command = strCommand        
        if serverTag:
            # @开头的命令发送给服务端
            targets = [_G.ServerTag]
            command = serverTag.group(1).strip()
        elif clientTag:
            # 命令中指定了executor
            deviceList = clientTag.group(1).strip()
            deviceList = deviceList.lower()
            command = clientTag.group(2).strip()
            # 处理不同类型的执行者指定
            if not deviceList:
                # 空值，使用当前选中的设备
                targets = selectedIDs
            else:
                # 处理可能的多个执行者，用逗号分隔
                targets = re.split(r'[,，]', deviceList)
        else:
            # 没有指定执行者，使用当前选中的设备
            targets = selectedIDs if selectedIDs else [_G.ServerTag]
        params = data.get('params', {})
        # 执行命令
        deviceMgr.sendCmd(targets, command, params)

    except Exception as e:
        Log.ex(e, '执行命令失败')
        

def handleC2SCmdResult(data):
    """处理命令响应"""
    try:
        deviceMgr.handleCmdResult(data)
    except Exception as e:
        _Log._Log_.ex(e, '处理命令响应失败')


def handleB2SLoadTasks(data):
    """处理加载任务数据请求
    Args:
        data: 包含filters字段的字典，用于过滤任务
    """
    try:
        filters = data.get('filters', {})
        date = filters.get('date')
        from STask import STask_
        datas = STask_.gets(date)
        datas = [task.toSheetData() for task in datas]
        # 更新前端任务数据
        _G._G_.emit('S2B_sheetUpdate', {'type': 'tasks', 'data': datas})

    except Exception as e:
        _Log._Log_.ex(e, '处理加载任务数据请求失败')


def handleB2SLoadDevices(data):
    """处理加载设备数据请求
    
    Args:
        data: 包含filters字段的字典，用于过滤设备   
    """
    try:
        log = _Log._Log_
        # 获取普通设备数据
        from SDeviceMgr import deviceMgr
        log.i(f'获取设备数据: {deviceMgr.devices}')
        datas = [device.toSheetData() for device in deviceMgr.devices]
        log.i(f'更新前端设备数据: {datas}')
        # 更新前端设备和控制台数据
        _G._G_.emit('S2B_sheetUpdate', {'type': 'devices', 'data': datas})

    except Exception as e:
        _Log._Log_.ex(e, '处理加载设备数据请求失败')


def handleB2SLoadLogs(data):
    """处理加载日志数据请求
    
    Args:
        data: 包含filters字段的字典，用于过滤日志
    """
    try:
        log = _Log._Log_
        filters = data.get('filters', {})
        date = filters.get('date')
        def getLogs(db):    
            """获取日志数据"""
            nonlocal date
            datas = log.gets(date)
            # 在同一个数据库会话中完成数据转换
            result = []
            for log_item in datas:
                result.append(log_item.toDict())
            return result
            
        datas = Database.sql(getLogs)
        _G._G_.emit('S2B_sheetUpdate', {'type': 'logs', 'data': datas})
        return {'state': 'ok', 'message': '日志加载请求已处理'}
    except Exception as e:
        _Log._Log_.ex(e, '处理加载日志数据请求失败')
        return {'state': 'error', 'message': str(e)}



