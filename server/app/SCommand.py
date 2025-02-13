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
        '@clearCmd': ('清除当前设备的所有指令历史', '_cmd_clearCmd'),
        '@clearLog': ('清除当前设备的日志缓存', '_cmd_clearLog'),
        '@list': ('列出所有设备', '_cmd_list'),
        '@echo': ('测试日志输出', '_cmd_echo'),
        '@log': ('手动打印日志，用法: @log <level> <content>', '_cmd_log'),
        '@show': ('显示日志，用法: @show [filter]', 'filterLogs')

    }
    
    @staticmethod
    def execute(device_id, command):
        """执行命令"""
        try:
            if command.startswith('@'):
                return SCommand._doSeverCmd(command)
            else:
                return SCommand._doClientCmd(device_id, command)
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
        

    
    @staticmethod
    def _doSeverCmd(command):
        """执行服务器命令"""
        response = ''
        try:
            cmd, args = SCommand._parse_command(command)
            matched_cmd = SCommand._find_command(cmd)
            
            if not matched_cmd:
                response = f'未知命令: {cmd}\n使用 @help 查看可用命令'
            else:
                handler_name = SCommand.COMMANDS[matched_cmd][1]
                handler = getattr(SCommand, handler_name)
                response = handler(args)
        except Exception as e:
            response = f'执行服务器命令出错: {e}'
        # 如果在Web上下文中，通过WebSocket发送
        if has_request_context():
            DeviceManager().emit2Console('S2B_CmdResult', {
                'result': response,
                'device_id': '@'
            })
        else:
            print(response)
    
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
    def _cmd_clearLog(args):
        """清除控制台日志缓存"""
        try:
            # 清空日志缓存
            Log().clear()
            # 使用覆盖模式保存
            Log().save(mode='w')            
            # 通知前端清空日志显示
            emit('clear_logs')            
            return '控制台日志已清除'
        except Exception as e:
            Log.ex(e, '清除日志缓存出错')
            return '清除日志缓存失败'
    
    @staticmethod
    def _cmd_clearCmd(args):
        """清除当前设备的所有指令历史"""
        device_manager = DeviceManager()
        device_id = (args[0] if args and len(args) > 0 
                    else device_manager.curDeviceID)
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
        return '\n'.join([
            f"{id}: {dev['status']}" 
            for id, dev in devices.items()
        ])
    
    @staticmethod
    def _cmd_echo(args):
        """测试日志输出"""
        message = ' '.join(args) if args else 'Hello World!'
        # 测试不同级别的日志
        Log.i('Server', f'[INFO] {message}')
        return f"Echo: {message}"

    @staticmethod
    def _cmd_log(args):
        """手动打印日志
        用法: @log <level> <content>
        level: i/w/e (info/warning/error)
        """
        if len(args) < 2:
            return "用法: @log <level> <content>"
        
        level = args[0].lower()
        content = ' '.join(args[1:])
        
        if level not in ['i', 'w', 'e']:
            return "日志级别必须是 i/w/e 之一"
            
        # 调用对应的日志方法
        if level == 'i':
            Log.i(content)
        elif level == 'w':
            Log.w(content)
        else:
            Log.e(content)
            
        return f"日志已打印: [{level}] {content}"
    
    
    @staticmethod
    def _doClientCmd(device_id, command):
        """执行设备命令"""
        try:
            with current_app.app_context():
                device_manager = DeviceManager()
                device = device_manager.get_device(device_id)
                if device is None:
                    Log.e('Server', f'设备 {device_id} 不存在')
                    return '设备不存在'
                if device.status != 'login':
                    Log.w('Server', f'设备 {device_id} 未登录')
                    return '设备未登录'
                
                sid = device.info.get('sid')
                if sid:
                    try:
                        # 直接通过 sid 发送命令
                        emit('S2C_DoCmd', {
                            'command': command,
                            'device_id': device_id,
                            'sender': current_app.config['SERVER_ID']
                        }, to=sid)
                        
                        return f'命令已发送到设备 {device_id}'
                    except Exception as e:
                        Log.ex(e, '发送命令时出错')
                        return f'发送命令失败: {e}'
                else:
                    Log.e('Server', f'设备 {device_id} 会话无效')
                    return '设备会话无效'
                
        except Exception as e:
            Log.ex(e, '执行设备命令出错')
            return '执行命令失败'
    
    # @staticmethod
    # def Add(device_id, result, level='info'):
    #     """处理命令响应"""
    #     try:
    #         history = CommandHistory(
    #             sender=current_app.config['SERVER_ID'],
    #             target=device_id,
    #             response=result,
    #             level=level
    #         )
    #         db.session.add(history)
    #         db.session.commit()
    #         print(f'命令响应已保存: {result}')
            
    #         return {
    #             'success': True,
    #             'result': result,
    #             'command_id': history.id if history else None,
    #             'level': level,
    #             'device_id': device_id
    #         }
    #     except Exception as e:
    #         Log.ex(e, '处理命令响应出错')
    #         return {'success': False, 'error': '处理响应失败'} 
    
    @staticmethod
    def filterLogs(filter_str=''):
        """显示日志
        用法: @show [filter]
        filter: 过滤条件
            - 空: 显示当天全部日志
            - 日期(YYYY-MM-DD): 显示指定日期的日志
            - 其他: 按TAG过滤当前日志
        """
        from .device_manager import DeviceManager
        
        logs = Log.show(filter_str.strip() if filter_str else None)
        if not logs:
            return "w##未找到匹配的日志"
        
        DeviceManager().emit2Console('show_logs', {
            'logs': logs,
            'filter': filter_str
        })
    
    @staticmethod
    def handCmdResult(data):
        """处理命令响应"""
        try:
            result = data.get('result')
            result = str(result)
            device_id = data.get('device_id')
            command = data.get('command')
            cmdName = data.get('cmdName')  # 获取命令方法名
            sender = "@"
            level = result.split('#')[0] if '#' in result else 'i'
            
            deviceMgr = DeviceManager()
            # 根据命令方法名处理响应
            if cmdName == 'captureScreen':  # 使用方法名而不是命令文本判断
                if isinstance(result, str) and result.startswith('data:image'):
                    device = deviceMgr.get_device(device_id)
                    if device is None:
                        Log.e(f'设备 {device_id} 不存在')
                        return
                    if device.saveScreenshot(result):
                        result = '截图已更新'
                    else:
                        result = '截图更新失败'
            # # 创建命令历史记录
            # CommandHistory.create(
            #     sender=sender,
            #     target=device_id,
            #     command=command,
            #     level=level,
            #     response=result
            # )
                
        except Exception as e:
            result = Log.formatEx('处理命令响应出错', e)
        # 解析level
        if isinstance(result, str) and '##' in result:
            level = result.split('##')[0]
            if level in ['w', 'e', 'i', 'd']:
                result = result.split('##')[1:]
            else:
                level = 'i'
        else:
            level = 'i'
        Log().log(f"{device_id}:{command}  => {result}", level, 'CMD')
        
        # 发送结果到控制台
        # deviceMgr.emit2Console('S2B_CmdResult', {
        #     'result': result,
        #     'level': level,
        # })    