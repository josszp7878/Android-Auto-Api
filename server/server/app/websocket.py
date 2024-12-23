from app import socketio
from flask_socketio import emit
from flask import request, current_app
from datetime import datetime
import json
from .device_manager import DeviceManager
from .models import db
from .command_history import CommandHistory
from .SCommand import SCommand

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# 创建设备管理器实例
device_manager = DeviceManager()


def broadcast_device_list():
    """广播设备列表更新"""
    devices_json = json.loads(json.dumps(device_manager.to_dict(), cls=DateTimeEncoder))
    emit('device_list_update', devices_json, broadcast=True)


@socketio.on('connect')
def handle_connect(auth):
    """处理客户端连接"""
    try:
        device_id = auth.get('device_id')
        if not device_id:
            print(f'Client connected without device_id: {request.sid}')
            return
        
        print(f'Client connected: {device_id}')
        device = device_manager.get_device(device_id)
        if not device:
            device = device_manager.add_device(device_id)
        device.info.update({
            'sid': request.sid,
            'connected_at': str(datetime.now())
        })
        device_manager.update_device(device)  # 更新数据库
        # 连接时自动设置为在线状态
        # device.update_status('online')
        # broadcast_device_list()
        do_login(device)
    except Exception as e:
        print(f'处理连接时出错: {e}')

@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接"""
    print(f'Client disconnected: {request.sid}')
    device = device_manager.get_device_by_sid(request.sid)
    if device:
        device.update_status('offline')
        broadcast_device_list()

@socketio.on('device_login')
def handle_login(data):
    """处理设备登录"""
    device_id = data.get('device_id')
    if not device_id:
        return    
    device = device_manager.get_device(device_id)
    if not device:
        return
    ok = do_login(device)
    emit('command_result', {'result': ok})

def do_login(device):
    if device:
        if device.login():
            broadcast_device_list()
            return True
        else:
            return False
    return False


@socketio.on('device_logout')
def handle_logout(data):
    """处理设备登出"""
    print(f'收到登出请求: {data}')
    device_id = data.get('device_id')
    if not device_id:
        return
    device = device_manager.get_device(device_id)
    ret = False
    if device:
        ok = device.logout()
        if ok:
            broadcast_device_list()
            ret = True
    emit('command_result', {'result': ret})
    return ret



@socketio.on('send_command')
def handle_command(data):
    """处理命令请求"""
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
            emit('error', {'message': response['error']})
            return
            
        emit('command_result', {
            'result': response['result'],
            'command_id': response['command_id'],
            'level': response['level'],
            'device_id': response['device_id']
        }, broadcast=True)
    except Exception as e:
        print(f'处理命令响应出错: {e}')
        emit('error', {'message': '处理响应失败'})


@socketio.on('update_screenshot')
def handle_screenshot(data):
    """处理设备截图更新"""
    device_id = data.get('device_id')
    screenshot_data = data.get('screenshot')  # 应该是base64或二进制数据
    
    device = device_manager.get_device(device_id)
    if device and screenshot_data:
        screenshot_url = device.save_screenshot(screenshot_data)
        if screenshot_url:
            broadcast_device_list()  # 广播更新，包含新的截图URL


@socketio.on('load_command_history')
def handle_load_history(data):
    """加载命令历史"""
    device_id = data.get('device_id')
    page = data.get('page', 1)
    per_page = 30
    
    try:
        print(f'加载设备 {device_id} 的历史记录, 页码: {page}')
        response_data = CommandHistory.getHistory(device_id, page, per_page)
        
        emit('command_history', response_data)
    except Exception as e:
        print(f'加载命令历史出错: {e}')
        emit('error', {'message': '加载历史记录失败'})


@socketio.on('set_current_device')
def handle_set_current_device(data):
    """设置当前设备ID"""
    device_id = data.get('device_id')
    DeviceManager().set_device_id(device_id)


