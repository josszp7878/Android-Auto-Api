from app import socketio
from flask_socketio import emit
from datetime import datetime
import json

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

devices = {}

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('device_login')
def handle_login(data):
    device_id = data.get('device_id')
    devices[device_id] = {
        'status': 'online',
        'last_seen': datetime.now(),
        'info': data
    }
    devices_json = json.loads(json.dumps(devices, cls=DateTimeEncoder))
    emit('device_list_update', devices_json, broadcast=True)
    print(f'设备登录: {device_id}')

@socketio.on('send_command')
def handle_command(data):
    device_id = data.get('device_id')
    command = data.get('command')
    if device_id in devices:
        print(f'发送命令到设备 {device_id}: {command}')
        emit('command', {'command': command}, room=device_id)
    else:
        emit('error', {'message': '设备不存在'})

@socketio.on('command_response')
def handle_command_response(data):
    print(f'收到命令响应: {data}')
    emit('command_result', data, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')