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
    _G._G_.setIO(sio)
    # 注册所有事件
    sio.on('connect')(onConnect)
    sio.on('disconnect')(onDisconnect)
    sio.on('C2S_Login')(onC2S_Login)
    sio.on('C2S_Logout')(onC2S_Logout)
    sio.on('C2S_Screenshot')(onC2S_Screenshot)
    sio.on('C2S_Log')(onC2S_Log)
    sio.on('C2S_StartTask')(onC2S_StartTask)
    sio.on('C2S_UpdateTask')(onC2S_UpdateTask)
    sio.on('2S_Cmd')(on2S_Cmd)
    sio.on('C2S_CmdResult')(onC2S_CmdResult)
    # 表格数据加载事件
    sio.on('B2S_loadDatas')(onB2S_loadDatas)
    sio.on('B2S_setProp')(onB2S_setProp)


def onB2S_setProp(data):
    """处理设备更新请求"""
    log = _Log._Log_
    try:
        type = data.get('type')
        targetID = data.get('target')
        params = data.get('params')
        log.i(f'更新设备属性: {type}, {targetID}, {params}')
        if not params:
            return
        target = None
        if type == 'devices':
            target = deviceMgr.getByID(targetID)
        elif type == 'tasks':
            from SDeviceMgr import deviceMgr
            target = deviceMgr.getTaskByID(targetID)
        # log.i(f'更新设备属性11: {type}, {targetID}, {params}, {target}')    
        if target is None:
            log.e(f'更新属性失败, 目标：{type} {targetID} 不存在')
            return False
        return target.setProp(params)
    except Exception as e:
        _Log._Log_.ex(e, '处理设备更新请求失败')


# 定义事件处理函数（不使用装饰器）
def onConnect(auth=None)->bool:
    """处理客户端连接"""
    g = _G._G_
    log = _Log._Log_
    try:
        deviceName = request.args.get('device_id')
        device = deviceMgr.get(deviceName, True)
        if device:
            device.onConnect(request.sid)
    except Exception as e:
        log.ex(e, '处理连接时出错ddddddd')
        return False
    return True

def onDisconnect():
    """处理客户端断开连接"""
    try:
        device = deviceMgr.getBySID(request.sid)
        if device:
            device.onDisconnect()            
    except Exception as e:
        _Log._Log_.ex(e, '处理客户端断开连接失败')

def onC2S_Login(data):
    """处理设备登录"""
    log = _Log._Log_
    try:
        device = deviceMgr.getBySID(request.sid)
        log.i(f'处理设备登录: {device}')
        if not device:
            return False
        # 普通设备处理
        ok = device.login()
        return ok
    except Exception as e:
        log.ex(e, '处理设备登录失败')
        return False


def onC2S_Logout(data):
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


def onC2S_Screenshot(data):
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



def onC2S_Log(data):
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


def onC2S_StartTask(data):
    """处理任务启动请求"""
    log = _Log._Log_
    try:
        device = deviceMgr.getBySID(request.sid)
        if not device:
            return []
        taskName = data.get('taskName')
        from STask import STask_
        task = STask_.get(device.id, taskName, date=datetime.now().date(), create=True)
        log.i(f'处理任务启动请求: {device.name}/{taskName}, task: {task}')
        if task:
            from STask import TaskState
            task.update({'state': TaskState.RUNNING.value})
            return task.toClientData()
        return []
    except Exception as e:
        log.ex(e, '处理任务启动请求失败')
        return []

def onC2S_UpdateTask(data):
    """处理任务进度更新"""
    log = _Log._Log_
    try:
        device = deviceMgr.getBySID(request.sid)
        if not device:
            return
        taskID = data.get('id')
        from STask import STask_
        task = STask_.getByID(taskID)
        log.i(f'任务进度更新: {device.name}/{taskID}')
        if task is None:
            log.w(f'任务不存在: {device.name}/{taskID}')
            return
        task.update(data)
    except Exception as e:
        log.ex(e, '处理任务进度更新失败')


def on2S_Cmd(data):
    """处理2S命令请求"""
    Log = _Log._Log_
    try:
        targets = data.get('targets', None)
        command = data.get('command', '')
        Log.i(f'处理2S命令请求: {targets}, {command}')
        if targets is None or command.strip() == '':
            return
        params = data.get('params')
        ret = {}
        for target in targets:
            ret[target] = deviceMgr.onCmd(target, command, params)
        return ret

    except Exception as e:
        Log.ex(e, '执行命令失败')
        

def onC2S_CmdResult(data):
    """处理命令响应"""
    try:
        deviceMgr.handleCmdResult(data)
    except Exception as e:
        _Log._Log_.ex(e, '处理命令响应失败')



def onB2S_loadDatas(data):
    """处理加载设备数据请求
    
    Args:
        data: 包含filters字段的字典，用于过滤设备   
    """
    try:
        log = _Log._Log_
        type = data.get('type')
        filters = data.get('filters', {})
        date = filters.get('date')
        if type == 'devices':
            from SDeviceMgr import deviceMgr
            datas = [device.toSheetData() for device in deviceMgr.devices]
        elif type == 'tasks':
            log.i(f'获取任务数据: {date}')
            from SDeviceMgr import deviceMgr
            from datetime import datetime
            if date is None:
                date = datetime.now().date()
            else:
                date = datetime.strptime(date, '%Y-%m-%d').date()
            devices = deviceMgr.devices
            # 在线设备优先
            devices = sorted(devices, key=lambda d: not d.isConnected)
            datas = []
            for device in devices:
                tasks = device.getTasks(date)
                for task in tasks:
                    datas.append(task.toSheetData())
        elif type == 'logs':
            from _Log import _Log_  
            datas = [log.toSheetData() for log in _Log_.gets(date)]
        else:
            return []
        return datas
    except Exception as e:
        _Log._Log_.ex(e, '处理加载设备数据请求失败')
        return []



