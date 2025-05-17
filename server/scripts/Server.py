import re
from flask import request, current_app
from flask_socketio import emit
from _G import _G_
from datetime import datetime
import _Log
from SDeviceMgr import deviceMgr


# 先定义一个函数，用于延迟注册事件处理器
def initSocketIO(sio):
    """初始化SocketIO事件，在_G_.socketio被设置后调用"""
    # 注册所有事件
    sio.on('connect')(handleConnect)
    sio.on('disconnect')(handleDisconnect)
    sio.on('C2S_Login')(handleC2SLogin)
    sio.on('C2S_Logout')(handleC2SLogout)
    sio.on('C2S_Screenshot')(handleC2SScreenshot)
    sio.on('C2S_Log')(handleC2SLog)
    sio.on('B2S_GetLogs')(handleB2SGetLogs)
    sio.on('C2S_StartTask')(handleC2SStartTask)
    sio.on('C2S_UpdateTask')(handleC2SUpdateTask)
    sio.on('C2S_StopTask')(handleC2SStopTask)
    sio.on('C2S_TaskEnd')(handleC2STaskEnd)
    sio.on('C2S_CancelTask')(handleC2SCancelTask)
    sio.on('2S_Cmd')(handle2SCmd)
    sio.on('C2S_CmdResult')(handleC2SCmdResult)
    sio.on('B2S_FilterLogs')(handleB2SFilterLogs)
    sio.on('B2S_GetAvailableDates')(handleB2SGetAvailableDates)
    
    # 设置_G_.socketio
    _G_.sio = sio
    log = _G_.Log()
    log.i("SocketIO事件已注册!!!")


# 定义事件处理函数（不使用装饰器）
def handleConnect(auth=None):
    """处理客户端连接"""
    try:
        deviceId = request.args.get('device_id')
        clientType = request.args.get('client_type')
        _Log._Log_.i(f'收到连接请求: {deviceId} {clientType}')

        if clientType == 'console':
            deviceMgr.addConsole(request.sid)
            # 刷新所有设备状态
            for device in deviceMgr.devices.values():
                device.refresh()
            return True

        elif deviceId:
            with current_app.app_context():
                device = deviceMgr.get(deviceId)
                if not device:
                    device = deviceMgr.add(deviceId)
                device.info['sid'] = request.sid
                device.info['connected_at'] = str(datetime.now())
                device.onConnect()  # onConnect 内部会调用 refresh
                return True

    except Exception as e:
        _Log._Log_.ex(e, '处理连接时出错')
    return False

def handleDisconnect():
    """处理客户端断开连接"""
    try:
        # _Log._Log_.i(f'Client disconnected: {request.sid}')
        # 检查是否是控制台断开
        if request.sid in deviceMgr.consoles:
            # _Log._Log_.i(f'控制台断开连接: {request.sid}')
            deviceMgr.removeConsole(request.sid)
            return
        # 设备断开处理...
        device = deviceMgr.getBySID(request.sid)
        if device:
            # _Log._Log_.i(f'设备断开连接: {device.device_id}')
            device.onDisconnect()
    except Exception as e:
        _Log._Log_.ex(e, '处理客户端断开连接失败')

def handleC2SLogin(data):
    """处理设备登录"""
    try:
        deviceId = data.get('device_id')
        if not deviceId:
            return
        device = deviceMgr.get(deviceId)
        # print(f'llllginlll device: {device}{device.device_id}')
        if not device:
            return
        ok = device.login()
        _Log._Log_.i(f'设备 {deviceId} 登录结果: {ok}')
    except Exception as e:
        _Log._Log_.ex(e, '处理设备登录失败')


def handleC2SLogout(data):
    """处理设备登出"""
    try:
        deviceId = data.get('device_id')
        if not deviceId:
            return
        device = deviceMgr.get(deviceId)
        ret = False
        if device:
            ret = device.logout()
        emit('S2C_CmdResult', {'result': ret}, room=device.info['sid'])
        return ret
    except Exception as e:
        _Log._Log_.ex(e, '处理设备登出失败')


def handleC2SScreenshot(data):
    """处理设备截图更新"""
    try:
        deviceId = data.get('device_id')
        screenshotData = data.get('image')
        if screenshotData is None:
            return
        device = deviceMgr.get(deviceId)
        if device is None:
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
    try:
        deviceId = data.get('device_id')
        appName = data.get('app_name')
        taskName = data.get('task_name')

        device = deviceMgr.get(deviceId)
        if not device:
            _Log._Log_.e(f'设备不存在: {deviceId}')
            return
        taskMgr = device.taskMgr
        task = taskMgr.getRunningTask(appName, taskName, create=True)
        taskMgr.startTask(task)
    except Exception as e:
        _Log._Log_.ex(e, '处理任务启动请求失败')

def handleC2SUpdateTask(data):
    """处理任务进度更新"""
    try:
        deviceId = data.get('device_id')
        appName = data.get('app_name')
        taskName = data.get('task_name')
        progress = data.get('progress', 0)

        device = deviceMgr.get(deviceId)
        if not device:
            _Log._Log_.e(f'设备不存在: {deviceId}')
            return
        device.taskMgr.updateTask(appName, taskName, progress)
    except Exception as e:
        _Log._Log_.ex(e, '处理任务进度更新失败')


def handleC2SStopTask(data):
    """处理任务停止请求"""
    try:
        deviceId = data.get('device_id')
        appName = data.get('app_name')
        taskName = data.get('task_name')
        _Log._Log_.i(f'收到任务停止消息: {deviceId}/{appName}/{taskName}')
        device = deviceMgr.get(deviceId)
        if not device:
            _Log._Log_.e(f'设备不存在: {deviceId}')
            return
        device.taskMgr.stopTask(appName, taskName)
    except Exception as e:
        _Log._Log_.ex(e, '处理任务停止失败')


def handleC2STaskEnd(data):
    """处理任务结束消息"""
    try:
        deviceId = data.get('device_id')
        appName = data.get('app_name')
        taskName = data.get('task_name')
        score = data.get('score', 0)
        result = data.get('result', True)  # 获取执行结果

        device = deviceMgr.get(deviceId)
        if not device:
            _Log._Log_.e(f'设备不存在: {deviceId}')
            return
        device.taskMgr.endTask(appName, taskName, score, result)
    except Exception as e:
        _Log._Log_.ex(e, '处理任务结束消息失败')


def handleC2SCancelTask(data):
    """处理任务取消请求"""
    try:
        deviceId = data.get('device_id')
        appName = data.get('app_name')
        taskName = data.get('task_name')
        _Log._Log_.i(f'收到任务取消消息: {deviceId}/{appName}/{taskName}')
        device = deviceMgr.get(deviceId)
        if not device:
            _Log._Log_.e(f'设备不存在: {deviceId}')
            return
        device.taskMgr.cancelTask(appName, taskName)
    except Exception as e:
        _Log._Log_.ex(e, '处理任务取消失败')


def handle2SCmd(data):
    """处理2S命令请求"""
    Log = _Log._Log_
    try:
        g = _G_
        selectedIDs = data.get('device_ids', [])
        # _Log._Log_.i(f'目标: {selectedIDs}')
        strCommand = data.get('command', '')
        strCommand = g.replaceSymbols(strCommand)
        deviceMgr.curDeviceIDs = selectedIDs

        # 解析命令格式：执行者列表 : 指令
        targets = []
        command = strCommand.strip()
        
        # 检查是否有执行者列表
        if ':' in command:
            parts = [part.strip() for part in command.split(':', 1)]
            executorList = parts[0].replace(' ', '')
            command = parts[1]
            if executorList == '@':
                targets = [_Log.TAG.Server.value]
            elif executorList:
                targets = re.split(r',', executorList.lower())
        
        # 如果没有指定执行者，使用当前选中的设备
        if not targets:
            targets = selectedIDs if selectedIDs else [_Log.TAG.Server.value]
        params = data.get('params', {})
        # 执行命令
        result = deviceMgr.sendCmd(targets, command, params)
        # 如果有结果，再发送结果日志
        if result:
            # 使用命令结果的日志级别
            level, content = Log._parseLevel(result, 'i')
            if content: 
                Log.Blog(f"  => {content}", None, level)
    except Exception as e:
        Log.ex(e, '执行命令失败')



def handleC2SCmdResult(data):
    """处理命令响应"""
    try:
        deviceMgr.handleCmdResult(data)
    except Exception as e:
        _Log._Log_.ex(e, '处理命令响应失败')

def handleB2SFilterLogs(data):
    """处理日志过滤请求"""
    try:
        filterStr = data.get('filter', '')
        page = data.get('page', 1)

        # 应用过滤器
        _Log._Log_.Filter(filterStr)

        # 刷新日志显示
        _Log._Log_.show(page=page)
    except Exception as e:
        _Log._Log_.ex(e, '处理日志过滤请求失败')
        

def handleB2SGetAvailableDates():
    """处理获取可用日志日期的请求"""
    log = _G_.Log()
    try:
        import os
        from pathlib import Path
        
        # 获取日志目录
        log_dir = Path(_Log._Log_.APP_LOGS)
        
        # 查找所有日志文件
        dates = []
        if log_dir.exists():
            for file in os.listdir(log_dir):
                if file.endswith('.log'):
                    # 从文件名提取日期
                    date = file[:-4]  # 去掉.log后缀
                    dates.append(date)
        
        # 按日期排序
        dates.sort(reverse=True)
        
        # 发送到前端
        _G_.socketio.emit('S2B_AvailableDates', {'dates': dates})
    except Exception as e:
        log.ex(e, '获取可用日志日期失败')



