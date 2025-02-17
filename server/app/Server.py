from app import socketio, app
from flask_socketio import emit, join_room, rooms
from flask import request, current_app
from datetime import datetime
import json
from .models import db
from .command_history import CommandHistory
from .SCommand import SCommand
from scripts.logger import Log
from pathlib import Path
import re
from .device_manager import DeviceManager
from .staskmgr import STaskMgr

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
    

deviceMgr = None
task_manager = None

def initServer():
    """初始化服务器"""
    global deviceMgr, task_manager
    with current_app.app_context():  # 使用 current_app 替代 app
        deviceMgr = DeviceManager()
        task_manager = STaskMgr()

@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    try:
        Log.i(f"新的连接请求 - SID: {request.sid}")
        Log.i(f"连接参数: {request.args}")
        Log.i(f"连接头信息: {request.headers}")
        Log.i(f"连接认证信息: {request.args.to_dict()}")
        
        device_id = request.args.get('device_id')
        client_type = request.args.get('client_type')
        
        if client_type == 'console':
            # 控制台连接，记录 SID
            deviceMgr.add_console(request.sid)
            return True
            
        elif device_id:
            with current_app.app_context():  # 使用 current_app 替代 app
                # 设备连接
                device = deviceMgr.get_device(device_id)
                if not device:
                    device = deviceMgr.add_device(device_id)
                
                device.info['sid'] = request.sid
                device.info['connected_at'] = str(datetime.now())
                deviceMgr.update_device(device)
                
                # 处理设备连接
                device.onConnect()            
                # 自动登录设备
                device.login()
                return True
                
    except Exception as e:
        Log.ex(e, '处理连接时出错')
    
    Log.e('未知的客户端连接')
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
    device_id = data.get('device_id')
    print(f'收到登录请求: {device_id}')
    if not device_id:
        return    
    device = deviceMgr.get_device(device_id)
    if not device:
        return
    ok = device.login()
    # 向设备发送结果
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
def handle_start_task(data):
    """处理开始任务请求(包含恢复未完成任务)"""
    # 获取设备ID、应用名称、任务名称和序列号
    device_id = data.get('device_id')
    app_name = data.get('app_name')
    task_name = data.get('task_name')
    sequence = data.get('sequence', 0)
    Log.i(f'收到开始任务请求: {device_id}/{app_name}/{task_name}/{sequence}')
    if not all([device_id, app_name, task_name]):
        return {'status': 'error', 'message': '缺少必要的任务信息'}

    task = task_manager.startTask(device_id, app_name, task_name, sequence)
    # 启动任务
    if not task:
    # 如果任务启动失败，返回错误信息
        return {'status': 'error', 'message': '任务启动失败'}
        
    return {
    # 返回任务信息
        'status': 'success',
        'task_id': task.id,
        'progress': task.progress,
        'message': (
            f'继续执行任务: {task_name}' if task.progress > 0 
            else f'开始新任务: {task_name}'
        )
    }



@socketio.on('C2S_UpdateTask')
def handle_C2S_UpdateTask(data):
    """处理任务进度更新"""
    try:
        device_id = data.get('device_id')
        app_name = data.get('app_name')
        task_name = data.get('task_name')
        progress = data.get('progress', 0)
        Log.i(f'收到任务进度更新消息: {device_id}/{app_name}/{task_name}/{progress}')
        if not all([device_id, app_name, task_name]):
            return {'status': 'error', 'message': '缺少必要的任务信息'}

        success = task_manager.updateTaskProgress(
            device_id, app_name, task_name, progress
        )
        
        return {
            'status': 'success' if success else 'error',
            'message': '进度更新成功' if success else '进度更新失败'
        }
    except Exception as e:
        Log.ex(e, '处理任务进度更新失败')
        return {'status': 'error', 'message': str(e)}


@socketio.on('C2S_StopTask')
def handle_stop_task(data):
    """处理任务停止请求"""
    try:
        device_id = data.get('device_id')
        app_name = data.get('app_name')
        task_name = data.get('task_name')
        
        Log.i(f'收到任务停止消息: {device_id}/{app_name}/{task_name}')
        
        if not all([device_id, app_name, task_name]):
            return {'status': 'error', 'message': '缺少必要的任务信息'}
            
        # 广播任务停止消息到所有控制台
        deviceMgr.emit2Console('S2B_TaskStop', {
            'deviceId': device_id,
            'task': {
                'appName': app_name,
                'taskName': task_name
            }
        })
        
        return {'status': 'success', 'message': '任务停止成功'}
    except Exception as e:
        Log.ex(e, '处理任务停止失败')
        return {'status': 'error', 'message': str(e)}


