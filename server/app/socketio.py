from flask_socketio import SocketIO
from .SCommand import SCommand

# ... 其他导入和代码 ...

@socketio.on('2S_Command')
def handle_command(data):
    try:
        device_id = data.get('device_id')
        command = data.get('command')
        
        if not device_id or not command:
            return {'error': '缺少必要参数'}
            
        # 确保命令以@开头
        if not command.startswith('@'):
            command = '@' + command
            
        # 执行命令
        result = SCommand.execute(device_id, command)
        return {'result': result}
        
    except Exception as e:
        Log.ex(e, '执行命令失败')
        return {'error': str(e)} 