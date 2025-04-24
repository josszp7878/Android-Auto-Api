import re
from flask import request, current_app
from flask_socketio import emit
from app import socketio
from datetime import datetime
import json
import _Log
from SDeviceMgr import deviceMgr

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


@socketio.on('connect')
def handle_connect(auth=None):
    """处理客户端连接"""
    try:
        device_id = request.args.get('device_id')
        client_type = request.args.get('client_type')
        _Log._Log_.i(f'收到连接请求: {device_id} {client_type}')

        if client_type == 'console':
            deviceMgr.addConsole(request.sid)
            # 刷新所有设备状态
            for device in deviceMgr.devices.values():
                device.refresh()
            return True

        elif device_id:
            with current_app.app_context():
                device = deviceMgr.get(device_id)
                if not device:
                    device = deviceMgr.add(device_id)
                device.info['sid'] = request.sid
                device.info['connected_at'] = str(datetime.now())
                device.onConnect()  # onConnect 内部会调用 refresh
                return True

    except Exception as e:
        _Log._Log_.ex(e, '处理连接时出错')
    return False

@socketio.on('disconnect')
def handle_disconnect():
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

@socketio.on('C2S_Login')
def handle_C2S_Login(data):
    """处理设备登录"""
    try:
        device_id = data.get('device_id')
        if not device_id:
            return
        device = deviceMgr.get(device_id)
        # print(f'llllginlll device: {device}{device.device_id}')
        if not device:
            return
        ok = device.login()
        _Log._Log_.i(f'设备 {device_id} 登录结果: {ok}')
    except Exception as e:
        _Log._Log_.ex(e, '处理设备登录失败')


@socketio.on('C2S_Logout')
def handle_C2S_Logout(data):
    """处理设备登出"""
    try:
        device_id = data.get('device_id')
        if not device_id:
            return
        device = deviceMgr.get(device_id)
        ret = False
        if device:
            ret = device.logout()
        emit('S2C_CmdResult', {'result': ret}, room=device.info['sid'])
        return ret
    except Exception as e:
        _Log._Log_.ex(e, '处理设备登出失败')


@socketio.on('C2S_Screenshot')
def handle_C2S_Screenshot(data):
    """处理设备截图更新"""
    try:
        device_id = data.get('device_id')
        screenshot_data = data.get('image')
        if screenshot_data is None:
            return
        device = deviceMgr.get(device_id)
        if device is None:
            return
        device.saveScreenshot(screenshot_data)  # 保存后会自动刷新前端
    except Exception as e:
        _Log._Log_.ex(e, '处理设备截图更新失败')



@socketio.on('C2S_Log')
def handle_C2S_Log(data):
    """处理客户端日志"""
    Log = _Log._Log_
    try:
        message = data.get('message')
        tag = data.get('tag')
        level = data.get('level', 'i')
        Log.log(message, tag, level)
    except Exception as e:
        Log.ex(e, '处理客户端日志失败')


@socketio.on('B2S_GetLogs')
def handle_B2S_GetLogs(data=None):
    """处理获取日志请求"""
    try:
        date = data.get('date') if data else None
        _Log._Log_.load(date)  # 这会加载日志并发送到前端
    except Exception as e:
        _Log._Log_.ex(e, '加载日志失败')


@socketio.on('C2S_StartTask')
def handle_C2S_StartTask(data):
    """处理任务启动请求"""
    try:
        device_id = data.get('device_id')
        app_name = data.get('app_name')
        task_name = data.get('task_name')

        device = deviceMgr.get(device_id)
        if not device:
            _Log._Log_.e(f'设备不存在: {device_id}')
            return
        taskMgr = device.taskMgr
        task = taskMgr.getRunningTask(app_name, task_name, create=True)
        taskMgr.startTask(task)
    except Exception as e:
        _Log._Log_.ex(e, '处理任务启动请求失败')

@socketio.on('C2S_UpdateTask')
def handle_C2S_UpdateTask(data):
    """处理任务进度更新"""
    try:
        device_id = data.get('device_id')
        app_name = data.get('app_name')
        task_name = data.get('task_name')
        progress = data.get('progress', 0)

        device = deviceMgr.get(device_id)
        if not device:
            _Log._Log_.e(f'设备不存在: {device_id}')
            return
        device.taskMgr.updateTask(app_name, task_name, progress)
    except Exception as e:
        _Log._Log_.ex(e, '处理任务进度更新失败')


@socketio.on('C2S_StopTask')
def handle_stop_task(data):
    """处理任务停止请求"""
    try:
        device_id = data.get('device_id')
        app_name = data.get('app_name')
        task_name = data.get('task_name')
        _Log._Log_.i(f'收到任务停止消息: {device_id}/{app_name}/{task_name}')
        device = deviceMgr.get(device_id)
        if not device:
            _Log._Log_.e(f'设备不存在: {device_id}')
            return
        device.taskMgr.stopTask(app_name, task_name)
    except Exception as e:
        _Log._Log_.ex(e, '处理任务停止失败')


@socketio.on('C2S_TaskEnd')
def handle_task_end(data):
    """处理任务结束消息"""
    try:
        device_id = data.get('device_id')
        app_name = data.get('app_name')
        task_name = data.get('task_name')
        score = data.get('score', 0)
        result = data.get('result', True)  # 获取执行结果

        device = deviceMgr.get(device_id)
        if not device:
            _Log._Log_.e(f'设备不存在: {device_id}')
            return
        device.taskMgr.endTask(app_name, task_name, score, result)
    except Exception as e:
        _Log._Log_.ex(e, '处理任务结束消息失败')


@socketio.on('C2S_CancelTask')
def handle_cancel_task(data):
    """处理任务取消请求"""
    try:
        device_id = data.get('device_id')
        app_name = data.get('app_name')
        task_name = data.get('task_name')
        _Log._Log_.i(f'收到任务取消消息: {device_id}/{app_name}/{task_name}')
        device = deviceMgr.get(device_id)
        if not device:
            _Log._Log_.e(f'设备不存在: {device_id}')
            return
        device.taskMgr.cancelTask(app_name, task_name)
    except Exception as e:
        _Log._Log_.ex(e, '处理任务取消失败')


@socketio.on('2S_Cmd')
def handle_2S_Cmd(data):
    """处理2S命令请求"""
    Log = _Log._Log_
    try:
        selectedIDs = data.get('device_ids', [])
        # _Log._Log_.i(f'目标: {selectedIDs}')
        strCommand = data.get('command', '')
        deviceMgr.curDeviceIDs = selectedIDs

        # 检查命令是否指定了executor
        clientTag = re.match(r'^\s*([^>》]*)[>》]+\s*(.+)$', strCommand)
        serverTag = re.match(r'^\s*@\s*(.+)$', strCommand)
        targets = []
        command = strCommand
        
        if serverTag:
            # @开头的命令发送给服务端
            targets = [_Log.TAG.Server.value]
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
            targets = selectedIDs if selectedIDs else [_Log.TAG.Server.value]
        params = data.get('params', {})
        # 执行命令
        result = deviceMgr.sendCmd(targets, command, params)

        # 如果有结果，再发送结果日志
        if result:
            # 使用命令结果的日志级别
            level, content = Log._parseLevel(result, 'i')
            Log.Blog(f"  => {content}" if content else "", None, level)
    except Exception as e:
        Log.ex(e, '执行命令失败')



@socketio.on('C2S_CmdResult')
def handle_C2S_CmdResult(data):
    """处理命令响应"""
    try:
        deviceMgr.handleCmdResult(data)
    except Exception as e:
        _Log._Log_.ex(e, '处理命令响应失败')

@socketio.on('B2S_FilterLogs')
def handle_B2S_FilterLogs(data):
    """处理日志过滤请求"""
    try:
        filter_str = data.get('filter', '')
        page = data.get('page', 1)

        # 应用过滤器
        _Log._Log_.Filter(filter_str)

        # 刷新日志显示
        _Log._Log_.show(page=page)
    except Exception as e:
        _Log._Log_.ex(e, '处理日志过滤请求失败')

@socketio.on('B2S_GetAvailableDates')
def handle_get_available_dates():
    """处理获取可用日志日期的请求"""
    try:
        from app import APP_LOGS
        import os

        # 获取日志目录中的所有日志文件
        log_files = [f for f in os.listdir(APP_LOGS) if f.endswith('.log')]

        # 提取日期（去掉.log后缀）
        dates = [f[:-4] for f in log_files]

        # 按日期排序（最新的在前）
        dates.sort(reverse=True)

        # 发送到前端
        socketio.emit('S2B_AvailableDates', {'dates': dates})
    except Exception as e:
        _Log._Log_.ex(e, '获取可用日志日期失败')



