from app import socketio
from flask_socketio import emit
from flask import request
from datetime import datetime
import json
from .manager import DeviceManager

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
    print(f'收到登录请求: {data}')
    device_id = data.get('device_id')
    if not device_id:
        return    
    device = device_manager.get_device(device_id)
    do_login(device)

def do_login(device):
    if device:
        device.login()
        print(f'设备登录: {device.device_id}')
        broadcast_device_list()


@socketio.on('device_logout')
def handle_logout(data):
    """处理设备登出"""
    print(f'收到登出请求: {data}')
    device_id = data.get('device_id')
    if not device_id:
        return
    
    device = device_manager.get_device(device_id)
    if device:
        device.logout()
        print(f'设备登出: {device_id}')
        broadcast_device_list()


@socketio.on('send_command')
def handle_command(data):
    device_id = data.get('device_id')
    command = data.get('command')
    print(f'服务器收到命令请求: device_id={device_id}, command={command}')
    
    device = device_manager.get_device(device_id)
    if device and device.status == 'login':
        sid = device.info.get('sid')  # 获取设备的 sid
        if sid:
            print(f'发送命令到设备 {device_id}(sid={sid}): {command}')
            emit('command', {'command': command}, room=sid)  # 使用 sid 作为 room
        else:
            print(f'设备 {device_id} 没有有效的 sid')
            emit('error', {'message': '设备会话无效'})
    else:
        print(f'设备不存在或离线: {device_id}')
        emit('error', {'message': '设备不存在或离线'})


@socketio.on('command_response')
def handle_command_response(data):
    print(f'服务器收到命令响应: {data}')
    emit('command_result', data, broadcast=True)


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

