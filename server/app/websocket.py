from app import socketio
from flask_socketio import emit, join_room, rooms
from flask import request, current_app
from datetime import datetime
import json
from .device_manager import DeviceManager
from .models import db
from .command_history import CommandHistory
from .SCommand import SCommand
from scripts.logger import Log
from pathlib import Path
import re

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# 创建设备管理器实例
deviceMgr = DeviceManager()


@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    try:
        device_id = request.args.get('device_id')
        client_type = request.args.get('client_type')
        
        if client_type == 'console':
            # 控制台连接，记录 SID
            deviceMgr.add_console(request.sid)
            Log.i(f"控制台连接: {request.sid}")
            return True
            
        elif device_id:
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
        # 保存当前设备的日志
        Log().save(deviceMgr.curDeviceID, None)
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
    emit('command_result', {'result': ok}, room=device.info['sid'])


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
    emit('command_result', {'result': ret}, room=device.info['sid'])
    return ret



@socketio.on('send_command')
def handle_command(data):
    """处理命令请求"""
    Log.i(f'收到命令请求: {data}')
    device_id = data.get('device_id')
    command = data.get('command')
    SCommand.execute(device_id, command)


@socketio.on('command_response')
def handle_command_response(data):
    """处理命令响应"""
    try:
        result = data.get('result')
        device_id = data.get('device_id')
        level = data.get('level', 'info')
        print(f'收到命令响应: {device_id} result= {result}')
        
        response = SCommand.handle_response(device_id, result, level)
        if not response['success']:
            deviceMgr.emit_to_console('error', {'message': response['error']})
            return
        deviceMgr.emit_to_console('command_result', {
            'result': response['result'],
            'command_id': response['command_id'],
            'level': response['level'],
            'device_id': response['device_id']
        })
    except Exception as e:
        Log.ex(e, '处理命令响应出错')
        deviceMgr.emit_to_console('error', {'message': '处理响应失败'})


@socketio.on('update_screenshot')
def handle_screenshot(data):
    """处理设备截图更新"""
    device_id = data.get('device_id')
    screenshot_data = data.get('screenshot')  # 应该是base64或二进制数据
    if screenshot_data is None:
        return
    device = deviceMgr.get_device(device_id)
    if device is None:
        return
    device.save_screenshot(screenshot_data)


@socketio.on('load_command_history')
def handle_load_history(data):
    """加载命令历史"""
    device_id = data.get('device_id')
    page = data.get('page', 1)
    per_page = 30
    
    try:
        Log.i(f'加载设备 {device_id} 的历史记录, 页码: {page}')
        response_data = CommandHistory.getHistory(device_id, page, per_page)
        deviceMgr.emit_to_console('command_history', response_data)
    except Exception as e:
        Log.ex(e, '加载命令历史出错')
        deviceMgr.emit_to_console('error', {'message': '加载历史记录失败'})


@socketio.on('set_current_device')
def handle_set_current_device(data):
    """设置当前设备ID"""
    
    # 设置新的当前设备
    device_id = data.get('device_id')
    deviceMgr.curDeviceID = device_id


@socketio.on('client_log')
def handle_client_log(data):
    """处理客户端日志"""
    message = data.get('message')
    device_id = data.get('device_id')
    # print(f'$$$$收到客户端日志: {message} deviceID={device_id}')
    Log().log(device_id, message)
    # 日志消息已经包含了完整格式,直接转发
    deviceMgr.emit_to_console('add_log', {
        'message': message
    })


@socketio.on('get_logs')
def handle_get_logs(data=None):
    """处理获取日志请求"""
    try:
        data = data or {}
        device_id = data.get('device_id')
        date = data.get('date')
        page = data.get('page', 1)
        per_page = 100  # 每页日志条数
        
        # 如果没有指定设备ID,使用当前设备ID
        if device_id is None:
            device_id = deviceMgr.curDeviceID
        
        # 获取设备日志
        logs = Log().gets(device_id, date)
        if not logs:
            logs = []
        
        # 计算分页
        total = len(logs)
        start = (page - 1) * per_page
        end = start + per_page
        page_logs = logs[start:end]
        has_more = end < total
            
        deviceMgr.emit_to_console('logs_data', {
            'logs': page_logs,
            'device_id': device_id,
            'date': date,
            'is_realtime': False,
            'has_more': has_more,
            'page': page,
            'total': total,
            'message': f'找到 {len(page_logs)} 条日志记录'
        })
        
    except Exception as e:
        Log.ex(e, '获取日志失败')
        deviceMgr.emit_to_console('error', {
            'message': f'获取日志失败: {str(e)}'
        })


@socketio.on('command_result')
def handle_command_result(data):
    """处理命令执行结果"""
    try:
        command_id = data.get('command_id')
        result = data.get('result', '')
        device_id = data.get('device_id')
        
        # 使用 CommandHistory 类处理结果
        response = CommandHistory.handle_command_result(command_id, result, device_id)
        if response:
            deviceMgr.emit_to_console('command_result', response)
            
    except Exception as e:
        Log.ex(e, '处理命令结果出错')


@socketio.on('command')
def handle_command(data):
    # ... 其他代码 ...
    result = doCmd(cmd)
    emit('response', {'result': result})
