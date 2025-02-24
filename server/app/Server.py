from flask import request, current_app
from flask_socketio import emit, join_room, rooms
from datetime import datetime
import json
from .command_history import CommandHistory
from .SCommand import SCommand
from scripts.logger import Log
from pathlib import Path
from .SDeviceMgr import deviceMgr
import sys
import os

# 从 run.py 中导入 socketio 实例
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run import socketio

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
    

@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    try:
        device_id = request.args.get('device_id')
        client_type = request.args.get('client_type')
        Log.i(f'收到连接请求: {device_id} {client_type}')
        
        if client_type == 'console':
            deviceMgr.add_console(request.sid)
            # 刷新所有设备状态
            for device in deviceMgr.devices.values():
                device.refresh()
            return True
            
        elif device_id:
            with current_app.app_context():
                device = deviceMgr.get_device(device_id)
                if not device:
                    device = deviceMgr.add_device(device_id)
                
                device.info['sid'] = request.sid
                device.info['connected_at'] = str(datetime.now())
                device.onConnect()  # onConnect 内部会调用 refresh
                return True
                
    except Exception as e:
        Log.ex(e, '处理连接时出错')
    return False

@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接"""
    Log.i(f'Client disconnected: {request.sid}')
    
    # 检查是否是控制台断开
    if request.sid in deviceMgr.console_sids:
        deviceMgr.remove_console(request.sid)
        return
    
    # 设备断开处理...
    device = deviceMgr.get_device_by_sid(request.sid)
    if device:
        device.onDisconnect()

@socketio.on('device_login')
def handle_login(data):
    """处理设备登录"""
    device_id = data.get('device_id')
    if not device_id:
        return
        
    device = deviceMgr.get_device(device_id)
    if not device:
        return
        
    ok = device.login()  # login 内部会调用 refresh
    emit('S2B_CmdResult', {'result': ok}, room=device.info['sid'])


@socketio.on('device_logout')
def handle_logout(data):
    """处理设备登出"""
    print(f'收到登出请求: {data}')
    device_id = data.get('device_id')
    if not device_id:
        return
    device = deviceMgr.get_device(device_id)
    ret = False
    if device:
        ret = device.logout()
    emit('S2C_CmdResult', {'result': ret}, room=device.info['sid'])
    return ret



@socketio.on('B2S_DoCmd')
def handle_B2S_DoCmd(data):
    """处理命令请求"""
    Log.i(f'收到命令请求: {data}')
    device_id = data.get('device_id')
    command = data.get('command')
    SCommand.execute(device_id, command)


@socketio.on('C2S_CmdResult')
def handle_C2S_CmdResult(data):
    """处理命令响应"""
    SCommand.handCmdResult(data)


@socketio.on('C2S_UpdateScreenshot')
def handle_C2S_UpdateScreenshot(data):
    """处理设备截图更新"""
    device_id = data.get('device_id')
    screenshot_data = data.get('screenshot')
    if screenshot_data is None:
        return
    device = deviceMgr.get_device(device_id)
    if device is None:
        return
    device.saveScreenshot(screenshot_data)  # 保存后会自动刷新前端


@socketio.on('load_command_history')
def handle_load_history(data):
    """加载命令历史"""
    device_id = data.get('device_id')
    page = data.get('page', 1)
    per_page = 30
    
    try:
        Log.i(f'加载设备 {device_id} 的历史记录, 页码: {page}')
        response_data = CommandHistory.getHistory(device_id, page, per_page)
        deviceMgr.emit2Console('command_history', response_data)
    except Exception as e:
        Log.ex(e, '加载命令历史出错')
        deviceMgr.emit2Console('error', {'message': '加载历史记录失败'})


@socketio.on('set_current_device')
def handle_set_current_device(data):
    """设置当前设备ID"""
    
    # 设置新的当前设备
    device_id = data.get('device_id')
    deviceMgr.curDeviceID = device_id


@socketio.on('C2S_Log')
def handle_C2S_Log(data):
    """处理客户端日志"""
    message = data.get('message')
    # print(f'$$$$收到客户端日志: {message}')
    Log().add(message)


@socketio.on('B2S_GetLogs')
def handle_B2S_GetLogs(data=None):
    """处理获取日志请求"""
    data = data or {}
    page = data.get('page', 1)
    Log.show(page=page)


@socketio.on('C2S_StartTask')
def handle_C2S_StartTask(data):
    """处理任务启动请求"""
    try:
        device_id = data.get('device_id')
        app_name = data.get('app_name')
        task_name = data.get('task_name')
        
        device = deviceMgr.get_device(device_id)
        if not device:
            Log.e(f'设备不存在: {device_id}')
            return
            
        taskMgr = device.taskMgr
        task = taskMgr.getRunningTask(app_name, task_name, True)
        if task:
            task.start()
            taskMgr.currentTask = task
        else:
            Log.e(f'任务启动失败: {device_id}/{app_name}/{task_name}')
            
    except Exception as e:
        Log.ex(e, '处理任务启动请求失败')

@socketio.on('C2S_UpdateTask')
def handle_C2S_UpdateTask(data):
    """处理任务进度更新"""
    try:
        device_id = data.get('device_id')
        app_name = data.get('app_name')
        task_name = data.get('task_name')
        progress = data.get('progress', 0)
        
        device = deviceMgr.get_device(device_id)
        if not device:
            Log.e(f'设备不存在: {device_id}')
            return
            
        task = device.taskMgr.getRunningTask(app_name, task_name)
        if not task:
            Log.e(f'任务不存在: {device_id}/{app_name}/{task_name}')
            return
        task.update(progress)
    except Exception as e:
        Log.ex(e, '处理任务进度更新失败')


@socketio.on('C2S_StopTask')
def handle_stop_task(data):
    """处理任务停止请求"""
    try:
        device_id = data.get('device_id')
        app_name = data.get('app_name')
        task_name = data.get('task_name')
        Log.i(f'收到任务停止消息: {device_id}/{app_name}/{task_name}')
        device = deviceMgr.get_device(device_id)
        if not device:
            Log.e(f'设备不存在: {device_id}')
            return
        task = device.taskMgr.getRunningTask(app_name, task_name)
        if not task:
            Log.e(f'任务不存在: {device_id}/{app_name}/{task_name}')
            return
        task.stop()
    except Exception as e:
        Log.ex(e, '处理任务停止失败')


@socketio.on('C2S_TaskEnd')
def handle_task_end(data):
    """处理任务结束消息"""
    try:
        device_id = data.get('device_id')
        app_name = data.get('app_name')
        task_name = data.get('task_name')
        score = data.get('score', 0)
        result = data.get('result', True)  # 获取执行结果
        
        device = deviceMgr.get_device(device_id)
        if not device:
            Log.e(f'设备不存在: {device_id}')
            return
            
        task = device.taskMgr.getRunningTask(app_name, task_name)
        if not task:
            Log.e(f'任务不存在: {device_id}/{app_name}/{task_name}')
            return
            
        # 传入包含 score 和 result 的字典
        task.end({
            'score': score,
            'result': result
        })              
    except Exception as e:
        Log.ex(e, '处理任务结束消息失败')


@socketio.on('C2S_CancelTask')
def handle_cancel_task(data):
    """处理任务取消请求"""
    try:
        device_id = data.get('device_id')
        app_name = data.get('app_name')
        task_name = data.get('task_name')
        Log.i(f'收到任务取消消息: {device_id}/{app_name}/{task_name}')
        device = deviceMgr.get_device(device_id)
        if not device:
            Log.e(f'设备不存在: {device_id}')
            return

        taskMgr = device.taskMgr    
        task = taskMgr.getRunningTask(app_name, task_name)
        if not task:
            Log.e(f'任务不存在: {device_id}/{app_name}/{task_name}')
            return
        taskMgr.removeTask(task)            
    except Exception as e:
        Log.ex(e, '处理任务取消失败')


