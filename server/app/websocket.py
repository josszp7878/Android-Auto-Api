from app import socketio
from flask_socketio import emit, join_room, rooms
from flask import request, current_app
from datetime import datetime
import json
from .device_manager import DeviceManager
from .models import db
from .command_history import CommandHistory
from .SCommand import SCommand
from .logger import Log

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
def handle_connect():
    """处理客户端连接"""
    try:
        # 直接从查询参数获取设备ID
        device_id = request.args.get('device_id')
        Log.i('Server', f"连接请求: device_id={device_id}, sid={request.sid}")
        
        if device_id:
            # 获取或创建设备
            device = device_manager.get_device(device_id)
            if not device:
                # Log.i('Server', f"222设备 {device_id} 不存在, 创建设备")
                device = device_manager.add_device(device_id)
            
            # 更新设备信息
            device.info['sid'] = request.sid
            device.info['connected_at'] = str(datetime.now())
            device_manager.update_device(device)
            
            Log.i('Server', f"设备 {device_id} 连接成功, SID: {request.sid}")
            
            # 自动登录设备
            do_login(device)
            return True
                
    except Exception as e:
        Log.e('Server', f'处理连接时出错: {e}')
        import traceback
        Log.e('Server', traceback.format_exc())
    
    Log.e('Server', 'Client connected without device_id')
    return True

@socketio.on('authenticate')
def handle_authenticate(auth_data):
    """处理客户端认证"""
    try:
        device_id = auth_data.get('device_id')
        Log.i('Server', f"收到认证请求: auth_data={auth_data}, sid={request.sid}")
        
        if device_id:
            # 获取或创建设备
            device = device_manager.get_device(device_id)
            if not device:
                device = device_manager.add_device(device_id)
            
            # 更新设备信息
            device.info['sid'] = request.sid
            device.info['connected_at'] = str(datetime.now())
            device_manager.update_device(device)
            
            Log.i('Server', f"设备 {device_id} 认证成功")
            emit('authenticated', {'status': 'success'})
            
            # 自动登录设备
            do_login(device)
            return True
            
    except Exception as e:
        Log.e('Server', f'处理认证请求出错: {e}')
        emit('authenticated', {'status': 'error', 'message': str(e)})
    return False

@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接"""
    Log.i('Server', f'Client disconnected: {request.sid}')
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
    Log.i('Server', f'收到命令请求: {data}')
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
        Log.i('Server', 
                  f'加载设备 {device_id} 的历史记录, 页码: {page}', 
                  'INFO')
        response_data = CommandHistory.getHistory(device_id, page, per_page)
        emit('command_history', response_data)
    except Exception as e:
        Log.e('Server', f'加载命令历史出错: {e}', 'ERROR')
        emit('error', {'message': '加载历史记录失败'})


@socketio.on('set_current_device')
def handle_set_current_device(data):
    """设置当前设备ID"""
    device_id = data.get('device_id')
    DeviceManager().set_device_id(device_id)


@socketio.on('client_log')
def handle_client_log(data):
    """处理客户端日志"""
    device_id = data.get('device_id')
    message = data.get('message')
    level = data.get('level', 'i')  # 默认为 INFO 级别
    # 根据级别调用对应的方法
    log_method = getattr(Log, level.lower()[0])  # 获取 i/w/e 方法
    # print(f'@@@@handle_client_log: {device_id} {level}  log_method={log_method}')
    log_method(device_id, message)


@socketio.on('get_logs')
def handle_get_logs(data=None):
    """处理获取日志请求"""
    try:
        # 获取最近的实时日志
        device_id = data.get('device_id') if data else None
        date = data.get('date') if data else None

        # 如果没有指定日期和设备，返回所有最新日志
        if not date and not device_id:
            # 获取服务器日志
            server_logs = Log.read_logs(None, 'server')
            # 获取所有设备的日志
            device_logs = []
            for device in DeviceManager().devices.values():
                device_logs.extend(Log.read_logs(None, device.device_id))
            
            # 合并所有日志并按时间排序
            all_logs = server_logs + device_logs
            all_logs.sort()  # 按时间戳排序
            
            emit('logs_data', {
                'logs': all_logs,
                'is_realtime': True
            })
        else:
            # 获取指定的历史日志
            logs = Log.read_logs(date, device_id)
            emit('logs_data', {
                'logs': logs,
                'device_id': device_id,
                'date': date,
                'is_realtime': False
            })
            
    except Exception as e:
        Log.e('Server', f'获取日志失败: {e}')
        emit('error', {'message': '获取日志失败'})


@socketio.on('command_result')
def handle_command_result(data):
    """处理命令执行结果"""
    try:
        command_id = data.get('command_id')
        result = data.get('result', '')
        device_id = data.get('device_id')
        
        # 记录命令结果
        Log.i(f'{device_id}', f'命令执行结果: {result}')
        
        # 更新命令历史
        if command_id:
            history = CommandHistory.query.get(command_id)
            if history:
                history.response = result
                history.response_time = datetime.now()
                db.session.commit()
        
        # 广播结果给所有连接的客户端
        emit('command_result', {
            'result': result,
            'device_id': device_id
        }, broadcast=True)
        
    except Exception as e:
        Log.e('Server', f'处理命令结果出错: {e}')


