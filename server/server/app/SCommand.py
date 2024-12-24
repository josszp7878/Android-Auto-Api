from datetime import datetime
from flask import current_app
from flask_socketio import emit
from .models import db
from .command_history import CommandHistory
from .device_manager import DeviceManager

class SCommand:
    """服务器命令处理类"""
    
    COMMANDS = {
        '@help': ('显示帮助信息', '_cmd_help'),
        '@status': ('显示服务器状态', '_cmd_status'),
        '@clear': ('清除当前设备的所有指令历史', '_cmd_clear'),
        '@list': ('列出所有设备', '_cmd_list')
    }
    
    @staticmethod
    def execute(device_id, command):
        """执行命令"""
        try:
            
            if command.startswith('@'):
                return SCommand._execute_server_command(command)
            else:
                return SCommand._execute_device_command(device_id, command)
        except Exception as e:
            print(f'执行命令出错: {e}')
            emit('error', {'message': '命令执行失败'})
    
    @staticmethod
    def _parse_command(command):
        """解析命令"""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        return cmd, args
    
    @staticmethod
    def _execute_server_command(command):
        """执行服务器命令"""
        try:
            device_manager = DeviceManager()
            cmd, args = SCommand._parse_command(command)
            
            if cmd not in SCommand.COMMANDS:
                response = f'未知命令: {cmd}\n使用 @help 查看可用命令'
            else:
                handler_name = SCommand.COMMANDS[cmd][1]
                handler = getattr(SCommand, handler_name)
                response = handler(args)
            
            emit('command_result', {
                'result': response,
                'device_id': current_app.config['SERVER_ID']
            })
            
        except Exception as e:
            print(f'执行服务器命令出错: {e}')
            emit('error', {'message': '执行命令失败'})
    
    # 命令处理方法
    @staticmethod
    def _cmd_help(args):
        """显示帮助信息"""
        return '\n'.join([f'{cmd}: {desc[0]}' for cmd, desc in SCommand.COMMANDS.items()])
    
    @staticmethod
    def _cmd_status(args):
        """显示服务器状态"""
        return '服务器运行正常'
    
    @staticmethod
    def _cmd_clear(args):
        """清除当前设备的所有指令历史"""
        device_manager = DeviceManager()
        device_id = args[0] if args and len(args) > 0 else device_manager.get_device_id()
        if device_id is None:
            return '未指定设备ID'
        
        try:
            CommandHistory.query.filter(
                (CommandHistory.sender == device_id) | 
                (CommandHistory.target == device_id)
            ).delete()
            db.session.commit()
            
            emit('clear_history', {'device_id': device_id})
            
            return f'设备 {device_id} 的指令历史已清除'
        except Exception as e:
            print(f'清除历史记录出错: {e}')
            return '清除历史记录失败'
    
    @staticmethod
    def _cmd_list(args):
        """列出所有设备"""
        device_manager = DeviceManager()
        devices = device_manager.to_dict()
        return '\n'.join([f"{id}: {dev['status']}" for id, dev in devices.items()])
    
    @staticmethod
    def _execute_device_command(device_id, command):
        """执行设备命令"""
        try:
            with current_app.app_context():
                device_manager = DeviceManager()
                device = device_manager.get_device(device_id)
                if device is None:
                    emit('error', {'message': '设备不存在'})
                    return '设备不存在'
                
                if device.status != 'login':
                    emit('error', {'message': '设备不在线'})
                    return '设备不在线'
                
                history = CommandHistory(
                    sender=current_app.config['SERVER_ID'],
                    target=device_id,
                    command=command,
                    level='info'
                )
                db.session.add(history)
                db.session.commit()
                
                sid = device.info.get('sid')
                if sid:
                    emit('command', {
                        'command': command,
                        'device_id': device_id,
                        'command_id': history.id
                    }, room=sid)
                    return f'命令已发送到设备 {device_id}'
                else:
                    emit('error', {'message': '设备会话无效'})
                    return '设备会话无效'
                
        except Exception as e:
            print(f'执行设备命令出错: {e}')
            emit('error', {'message': '执行命令失败'})
            return '执行命令失败'
    
    @staticmethod
    def handle_response(device_id, result, level='info'):
        """处理命令响应"""
        try:
            history = CommandHistory.query.filter_by(
                sender=current_app.config['SERVER_ID'],
                target=device_id,
                response=None
            ).order_by(CommandHistory.created_at.desc()).first()
            
            if history:
                history.response = result
                history.level = level
                db.session.commit()
                print(f'命令响应已保存: {result}')
            
            return {
                'success': True,
                'result': result,
                'command_id': history.id if history else None,
                'level': level,
                'device_id': device_id
            }
        except Exception as e:
            print(f'处理命令响应出错: {e}')
            return {'success': False, 'error': '处理响应失败'} 