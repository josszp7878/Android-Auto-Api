from datetime import datetime
from flask import current_app, has_request_context
from flask_socketio import emit
from .models import db
from .command_history import CommandHistory
from .device_manager import DeviceManager
from scripts.logger import Log

class SCommand:
    """服务器命令处理类"""
    
    COMMANDS = {
        '@help': ('显示帮助信息', '_cmd_help'),
        '@status': ('显示服务器状态', '_cmd_status'),
        '@clear': ('清除当前设备的所有指令历史', '_cmd_clear'),
        '@list': ('列出所有设备', '_cmd_list'),
        '@echo': ('测试日志输出', '_cmd_echo'),
        '@showlog': ('显示日志', '_cmd_showlog')
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
            Log.e('Server', f'执行命令出错: {e}')
            emit('error', {'message': '命令执行失败'})
    
    @staticmethod
    def _parse_command(command):
        """解析命令"""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        return cmd, args
    
    @staticmethod
    def _find_command(cmd):
        """模糊匹配命令,返回第一个匹配的命令"""
        cmd = cmd.lower()
        for command in SCommand.COMMANDS:
            if command.lower().startswith(cmd):
                return command
        return None
    
    @staticmethod
    def _send_response(response, device_id='Server'):
        """统一的响应发送处理"""
        # 总是打印到控制台
        Log.i(device_id, response)
        
        # 如果在Web上下文中，通过WebSocket发送
        if has_request_context():
            emit('command_result', {
                'result': response,
                'device_id': device_id
            })
    
    @staticmethod
    def _execute_server_command(command):
        """执行服务器命令"""
        try:
            cmd, args = SCommand._parse_command(command)
            matched_cmd = SCommand._find_command(cmd)
            
            if not matched_cmd:
                response = f'未知命令: {cmd}\n使用 @help 查看可用命令'
            else:
                handler_name = SCommand.COMMANDS[matched_cmd][1]
                handler = getattr(SCommand, handler_name)
                response = handler(args)
            
            SCommand._send_response(response)
            
        except Exception as e:
            error_msg = f'执行服务器命令出错: {e}'
            Log.e('Server', error_msg)
            if has_request_context():
                emit('error', {'message': '执行命令失败'})
    
    @staticmethod
    def _cmd_help(args=None):
        """显示帮助信息"""
        help_text = "可用的服务器命令:\n"
        for cmd, (desc, _) in SCommand.COMMANDS.items():
            help_text += f"{cmd}: {desc}\n"
        return help_text
    
    @staticmethod
    def _cmd_status(args):
        """显示服务器状态"""
        return '服务器运行正常'
    
    @staticmethod
    def _cmd_clear(args):
        """清除当前设备的所有指令历史"""
        device_manager = DeviceManager()
        device_id = args[0] if args and len(args) > 0 else device_manager.curDeviceID
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
    def _cmd_echo(args):
        """测试日志输出"""
        message = ' '.join(args) if args else 'Hello World!'
        # 测试不同级别的日志
        Log.i('Server', f'[INFO] {message}')
        return f"Echo: {message}"
    
    @staticmethod
    def _cmd_showlog(args):
        """显示日志
        用法: @showlog [date] - 显示服务器日志
             @showlog <device_id> [date] - 显示设备日志
        """
        try:
            date = None
            device_id = None
            
            if args:
                if args[0].startswith('@'):
                    # 服务器日志
                    if len(args) > 1:
                        date = args[1]
                else:
                    # 设备日志
                    device_id = args[0]
                    if len(args) > 1:
                        date = args[1]
            else:
                # 如果没有参数，显示当前设备的日志
                device_manager = DeviceManager()
                device_id = device_manager.curDeviceID
                if not device_id:
                    device_id = 'server'  # 如果没有当前设备，显示服务器日志
            
            logs = Log().get(device_id)
            if not logs:
                return f"没有找到{'服务器' if device_id == 'server' else device_id}在{date or '今天'}的日志"
                
            # 发送日志到前端显示
            from app import socketio
            Log.i('Server', f'正在显示{device_id}在{date or datetime.now().strftime("%Y-%m-%d")}的日志')
            socketio.emit('show_logs', {
                'logs': logs,
                'device_id': device_id,
                'date': date or datetime.now().strftime('%Y-%m-%d')
            })
            
            return f"正在显示{'服务器' if device_id == 'server' else device_id}在{date or '今天'}的日志"
            
        except Exception as e:
            Log.ex(e, "显示日志失败")
            return f"显示日志失败: {e}"
    
    @staticmethod
    def _execute_device_command(device_id, command):
        """执行设备命令"""
        Log.i('Server', f'执行设备命令: {device_id} {command}')
        try:
            with current_app.app_context():
                device_manager = DeviceManager()
                device = device_manager.get_device(device_id)
                if device is None:
                    Log.e('Server', f'设备 {device_id} 不存在')
                    emit('error', {'message': '设备不存在'})
                    return '设备不存在'
                print(f'!!!device.status: {device.status}')
                if device.status != 'login':
                    Log.w('Server', f'设备 {device_id} 未登录')
                    emit('error', {'message': '设备未登录'})
                    return '设备未登录'
                
                # 记录命令历史
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
                    # 验证 SID 是否最新
                    Log.i('Server', f'设备 {device_id} 当前 SID: {sid}')
                    
                    try:
                        # 直接通过 sid 发送命令
                        emit('command', {
                            'command': command,
                            'device_id': device_id,
                            'command_id': history.id
                        }, to=sid)
                        
                        Log.i('Server', f'命令已发送到 SID: {sid}')
                        return f'命令已发送到设备 {device_id}'
                    except Exception as e:
                        Log.ex(e, '发送命令时出错')
                        return f'发送命令失败: {e}'
                else:
                    Log.e('Server', f'设备 {device_id} 会话无效')
                    emit('error', {'message': '设备会话无效'})
                    return '设备会话无效'
                
        except Exception as e:
            Log.ex(e, '执行设备命令出错')
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
            Log.ex(e, '处理命令响应出错')
            return {'success': False, 'error': '处理响应失败'} 