from datetime import datetime,date
from flask import current_app, has_request_context
from flask_socketio import emit
from sqlalchemy import func  # 添加这行导入
from .models import db
from .command_history import CommandHistory
from .SDeviceMgr import SDeviceMgr
from scripts.logger import Log
from scripts.tools import TaskState  # 使用统一的 TaskState
from .STask import STask 


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
        '@show': ('显示日志，用法: @show [filter]', 'filterLogs'),
        '@progress': ('查询任务进度，用法: @progress <deviceId> <appName> <taskName>', '_cmd_progress'),
        '@resume': ('继续当前设备的暂停任务', '_cmd_resume'),
        '@debug': ('显示调试信息', '_cmd_debug'),
        '@tasks': ('显示任务', '_cmd_show_tasks'),
        '@date': ('设置任务管理器日期，格式: YY-M-D', '_cmd_set_date'),
        '@stop': ('停止当前设备的当前任务', '_cmd_stop'),
    }
    
    @staticmethod
    def execute(device_id, command):
        """执行命令"""
        try:
            if command.startswith('@'):
                return SCommand._doSeverCmd(command)
            else:
                return SCommand._sendClientCmd(device_id, command)
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
        Log.log(response)
       
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
        device_manager = SDeviceMgr()
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
        device_manager = SDeviceMgr()
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
    def _sendClientCmd(device_id, command, data=None):
        """执行设备命令"""
        try:
            with current_app.app_context():
                device_manager = SDeviceMgr()
                Log.i(f'发送客户端命令: {device_id} -> {command}, DATA: {data}')
                
                device = device_manager.get_device(device_id)
                if device is None:
                    Log.e(f'设备 {device_id} 不存在')
                    return '设备不存在'
                
                if device.status != 'login':
                    Log.w('Server', f'设备 {device_id} 未登录')
                    return '设备未登录'
                
                sid = device.info.get('sid')
                # Log.i('Server', f'设备 SID: {sid}')
                
                if sid:
                    try:
                        # 通过 sid 发送命令，包含 data 参数
                        emit('S2C_DoCmd', {
                            'command': command,
                            'sender': current_app.config['SERVER_ID'],
                            'data': data  # 添加 data 参数
                        }, to=sid)
                        
                        Log.i('Server', f'命令已发送到设备 {device_id}')
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
        from .SDeviceMgr import SDeviceMgr
        
        logs = Log.show(filter_str.strip() if filter_str else None)
        if not logs:
            return "w##未找到匹配的日志"
        
        SDeviceMgr().emit2B('show_logs', {
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
            # sender = "@"
            level = result.split('#')[0] if '#' in result else 'i'
            
            deviceMgr = SDeviceMgr()
            # 添加调试日志
            Log.i('Server', f'收到命令响应: {device_id} -> {command} = {result}')
            
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
            Log.i(f'命令响应: {device_id} -> {command} = {result}', 'CMD')
        except Exception as e:
            Log.ex(e, '处理命令响应出错')
        # 解析level
        if isinstance(result, str) and '##' in result:
            level = result.split('##')[0]
            if level in ['w', 'e', 'i', 'd']:
                result = result.split('##')[1:]
            else:
                level = 'i'
        else:
            level = 'i'
        Log()._log(f"{device_id}:{command}  => {result}", level, 'CMD')

    @staticmethod
    def _cmd_progress(args):
        """查询任务进度
        用法: @progress <deviceId> <appName> <taskName>
        """
        try:
            # 检查参数个数
            if len(args) != 3:
                return "e##用法: @progress <deviceId> <appName> <taskName>"
            
            deviceId, appName, taskName = args
            
            # 处理当前设备ID
            if deviceId == '_':
                deviceMgr = SDeviceMgr()
                deviceId = deviceMgr.curDeviceID
                if not deviceId:
                    return "e##未选择设备"
            
            # 处理最近任务
            if appName == '_' or taskName == '_':
                # 从数据库获取最近任务
                last_task = STask.query.filter_by(
                    deviceId=deviceId
                ).order_by(STask.time.desc()).first()
                
                if not last_task:
                    return "i##未找到最近任务记录"
                
                if appName == '_':
                    appName = last_task.appName
                if taskName == '_':
                    taskName = last_task.taskName
            
            # 从数据库查询任务
            task = STask.query.filter_by(
                deviceId=deviceId,
                appName=appName,
                taskName=taskName,
            ).order_by(STask.time.desc()).first()
            
            if not task:
                return "i##未找到正在运行的任务"
                
            # 格式化输出任务信息（转换为百分比）
            progress_percent = task.progress * 100
            return f"i##任务进度: {progress_percent:.1f}%"
            
        except Exception as e:
            Log.ex(e, "查询任务进度失败")
            return f"e##查询任务进度失败: {str(e)}"    

    @staticmethod
    def _cmd_resume(args):
        """继续当前设备的暂停任务"""
        try:
            deviceMgr = SDeviceMgr()
            device_id = deviceMgr.curDeviceID
            if not device_id:
                return "e##未选择设备"
            
            device = deviceMgr.get_device(device_id)
            if not device:
                return "e##设备不存在"
                
            # 获取当前任务
            task = device.taskMgr.currentTask
            if not task:
                return "i##当前设备没有任务"
                
            # 检查任务状态
            if task.state != TaskState.PAUSED.value:
                return f"i##当前任务状态为 {task.state}，不是暂停状态"
            Log.i(f'继续任务: {task.appName} {task.taskName}, progress: {task.progress}')
            # 向客户端发送启动任务消息，包含 progress 参数
            SCommand._sendClientCmd(device_id, f"startTask {task.appName} {task.taskName}", data={'progress': task.progress})
            
        except Exception as e:
            Log.ex(e, "继续任务失败")
            return f"e##继续任务失败: {str(e)}"
        
    @staticmethod
    def _cmd_stop(args) -> str:
        """停止当前设备的当前任务
        Args:
            device_id: 设备ID
            args: 参数列表(不需要)
        Returns:
            str: 执行结果
        """
        try:
            deviceMgr = SDeviceMgr()
            device_id = deviceMgr.curDeviceID
            if not device_id:
                return "e##未选择设备"
            device = deviceMgr.get_device(device_id)
            if not device:
                return 'e##设备不存在'
                
            task = device.taskMgr.currentTask
            if not task:
                return 'w##当前没有运行中的任务'
            Log.i(f'停止任务@@@ 状态: {task.state}', 'Server')
            if task.state != TaskState.RUNNING.value:
                return 'w##当前任务不在运行状态'
            SCommand._sendClientCmd(device_id, f"stopTask {task.appName} {task.taskName}")
            
        except Exception as e:
            Log.ex(e, "停止任务失败")
            return f"e##停止任务失败: {str(e)}"           

    @staticmethod
    def _cmd_debug(args):
        """显示调试信息"""
        try:
            device_manager = SDeviceMgr()
            info = {
                '当前设备': device_manager.curDeviceID,
                '设备列表': list(device_manager.to_dict().keys()),
                '日志状态': Log().isEnabled(),
                '日志缓存数': len(Log().cache) if hasattr(Log(), 'cache') else 'Unknown'
            }
            return '\n'.join([f"{k}: {v}" for k, v in info.items()])
        except Exception as e:
            return f"调试信息获取失败: {str(e)}"    

    @staticmethod
    def _cmd_show_tasks(args):
        """显示当前设备的任务列表
        用法: @tasks [参数]
        参数:
          - 空: 显示未完成的任务
          - 所有: 显示今天所有任务
        """
        try:
            deviceMgr = SDeviceMgr()
            device_id = deviceMgr.curDeviceID
            if not device_id:
                return "e##未选择设备"
            
            device = deviceMgr.get_device(device_id)
            if not device:
                return "e##设备不存在"
            
            # 获取任务管理器的当前日期
            target_date = device.taskMgr.date  # 使用属性而不是直接访问 _date
            if not target_date:
                return "e##任务管理器日期未设置"
            
            # 基础查询条件
            query = STask.query.filter(
                STask.deviceId == device_id,
                func.date(STask.time) == target_date
            )
            # 根据参数决定是否只查询未完成任务
            show_all = len(args) > 0 and args[0] == "所有"
            if not show_all:
                query = query.filter(STask.state.in_([
                    TaskState.RUNNING.value,
                    TaskState.PAUSED.value
                ]))
            
            # 按时间倒序获取任务
            tasks = query.order_by(STask.time.desc()).all()
            
            if not tasks:
                date_str = target_date.strftime('%Y-%m-%d')
                return f"i##{date_str}没有{'' if show_all else '未完成的'}任务"
            
            # 构建JSON格式的任务列表
            task_list = []
            for task in tasks:
                progress = f"{task.progress * 100:.1f}" if task.progress else "0"
                task_list.append({
                    "应用": task.appName,
                    "任务": task.taskName,
                    "状态": task.state,
                    "进度": progress,
                    "时间": task.time.strftime("%H:%M:%S")
                })
            
            import json
            return "i##" + json.dumps(task_list, ensure_ascii=False, indent=2)
            
        except Exception as e:
            Log.ex(e, "获取任务列表失败")
            return f"e##获取任务列表失败: {str(e)}"    

    @staticmethod
    def _cmd_set_date(args):
        """设置任务管理器日期
        用法: @date YY-M-D
        示例: @date 25-1-23 表示2025年1月23日
        """
        try:
            # 如果没有参数，使用今天的日期
            target_date = date.today()
            
            if args:  # 有参数才尝试解析
                try:
                    # 解析日期字符串
                    yy, m, d = map(int, args[0].split('-'))
                    # 转换为完整年份
                    year = 2000 + yy if yy < 100 else yy
                    # 创建日期对象
                    target_date = datetime(year, m, d).date()
                except ValueError:
                    return "e##日期格式错误，请使用 YY-M-D 格式"
            
            # 获取当前设备
            deviceMgr = SDeviceMgr()
            device_id = deviceMgr.curDeviceID
            if not device_id:
                return "e##未选择设备"
            
            device = deviceMgr.get_device(device_id)
            if not device:
                return "e##设备不存在"
            
            # 使用属性设置日期,会自动触发刷新
            device.taskMgr.date = target_date
            return f"i##已设置任务管理器日期为: {target_date.strftime('%Y-%m-%d')}"
                
        except Exception as e:
            Log.ex(e, "设置日期失败")
            return f"e##设置日期失败: {str(e)}"    

   