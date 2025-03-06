from datetime import datetime
import _Log
from _CmdMgr import regCmd
from flask_socketio import emit
from SDeviceMgr import deviceMgr, SDeviceMgr
from STask import STask, TaskState
import json
from SEarningMgr import SEarningMgr
from time import sleep

class SCmds:
    @classmethod
    def OnReload(cls):
        """热更新后重新注册命令"""
        _Log.Log.w("SCmds模块热更新 重新注册命令")
        # 使用全局命令重新注册机制
        from _CmdMgr import _CmdMgr
        _CmdMgr.regAllCmds()
        _Log.Log.i("命令重新注册完成")
    
    @classmethod
    def registerCommands(cls):
        """注册服务器命令"""
        _Log.Log.i("注册SCmds模块命令...")
        
        @regCmd(r"服务器信息")
        def info():
            """获取服务器信息"""
            return {
                "version": "1.0.0",
                "timestamp": str(datetime.now()),
                "devices": len(deviceMgr.devices),
            }
        
        @regCmd(r"日期", r"(?P<format>\S+)?")
        def date(format=None):
            """获取当前日期和时间
            用法: 日期 [格式]
            默认格式: %Y-%m-%d %H:%M:%S
            """
            try:
                date_format = format or "%Y-%m-%d %H:%M:%S"
                current_time = datetime.now().strftime(date_format)
                _Log.Log.i(f"date: 当前日期和时间: {current_time}")
                deviceMgr.sendClientCmd(deviceMgr.curDeviceID, f"date {current_time}")
                return f"i->当前日期和时间: {current_time}"
            except Exception as e:
                _Log.Log.ex(e, "获取日期时间失败")
                return f"e->获取日期时间失败: {str(e)}"


        @regCmd('状态')
        def status():
            """显示服务器状态"""
            return '服务器运行正常aa'

        @regCmd('清除')
        def clearLog():
            """清除日志缓存"""
            try:
                # 清空日志缓存
                log.clear()
                # 使用覆盖模式保存
                log.save(mode='w')            
                # 通知前端清空日志显示
                emit('clear_logs')            
                return '控制台日志已清除'
            except Exception as e:
                _Log.Log.ex(e, '清除日志缓存出错')
                return '清除日志缓存失败'

        @regCmd('设备列表')
        def list_devices():
            """列出所有设备"""
            device_manager = SDeviceMgr()
            devices = device_manager.to_dict()
            return '\n'.join([
                f"{id}: {dev['status']}" 
                for id, dev in devices.items()
            ])

        @regCmd('进度', r"(?P<deviceId>[^ ]+)?(?P<appName>[^ ]+)?(?P<taskName>[^ ]+)?")
        def progress(deviceId, appName, taskName):
            """查询任务进度
            用法: 进度 <deviceId> <appName> <taskName>
            
            特殊参数:
            - deviceId 为 '_' 时使用当前设备
            - appName 为 '_' 时使用最近任务的应用名
            - taskName 为 '_' 时使用最近任务的任务名
            """
            try:
                # 处理当前设备ID
                if deviceId == '_':
                    deviceId = deviceMgr.curDeviceID
                    if not deviceId:
                        return "e->未选择设备"
                
                # 处理最近任务
                if appName == '_' or taskName == '_':
                    # 从数据库获取最近任务
                    last_task = STask.query.filter_by(
                        deviceId=deviceId
                    ).order_by(STask.time.desc()).first()
                    
                    if not last_task:
                        return "i->未找到最近任务记录"
                    
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
                    return "i->未找到正在运行的任务"
                    
                # 格式化输出任务信息（转换为百分比）
                progress_percent = task.progress * 100
                return f"i->任务进度: {progress_percent:.1f}%"
                
            except Exception as e:
                _Log.Log.ex(e, "查询任务进度失败")
                return f"e->查询任务进度失败: {str(e)}"

        @regCmd('继续')
        def resume():
            """继续当前设备的暂停任务"""
            try:
                device = deviceMgr.curDevice
                if not device:
                    return "e->未选择设备"
                    
                # 获取暂停的任务
                task = STask.query.filter_by(
                    deviceId=device.deviceID,
                    state=TaskState.PAUSED.value
                ).order_by(STask.time.desc()).first()
                if not task:
                    return "i->未找到暂停的任务"
                device.taskMgr.startTask(task)
                return f"i->已继续任务: {task.appName} {task.taskName}"
            except Exception as e:
                _Log.Log.ex(e, "继续任务失败")
                return f"e->继续任务失败: {str(e)}"

        @regCmd('调试')
        def debug():
            """显示调试信息"""
            try:
                # 获取当前设备
                device_id = deviceMgr.curDeviceID
                if not device_id:
                    return "e->未选择设备"
                    
                device = deviceMgr.get_device(device_id)
                if not device:
                    return "e->设备不存在"
                    
                # 获取设备信息
                info = device.to_dict()
                
                # 格式化输出
                debug_info = "调试信息:\n"
                debug_info += f"设备ID: {device_id}\n"
                debug_info += f"状态: {info['status']}\n"
                debug_info += f"连接时间: {info.get('connected_at', 'N/A')}\n"
                debug_info += f"最后活动: {info.get('last_activity', 'N/A')}\n"
                
                # 获取任务信息
                if device.taskMgr:
                    debug_info += f"当前应用: {device.taskMgr._currentApp or 'N/A'}\n"
                    
                    # 获取正在运行的任务
                    task = STask.query.filter_by(
                        deviceId=device_id,
                        state=TaskState.RUNNING.value
                    ).order_by(STask.time.desc()).first()
                    
                    if task:
                        debug_info += f"当前任务: {task.appName}/{task.taskName}\n"
                        debug_info += f"进度: {task.progress * 100:.1f}%\n"
                        debug_info += f"开始时间: {task.time}\n"
                
                return debug_info
                
            except Exception as e:
                _Log.Log.ex(e, "获取调试信息失败")
                return f"e->获取调试信息失败: {str(e)}"

        @regCmd('任务列表', r"(?P<deviceId>[^ ]+)?(?P<state>[^ ]+)?")
        def show_tasks(deviceId, state):
            """显示任务
            用法: 任务列表 [deviceId] [state]
            
            参数:
            - deviceId: 设备ID，默认为当前设备
            - state: 任务状态，可选值: running, paused, completed, cancelled, all
            默认为 all
            """
            try:
                # 解析参数
                device_id = deviceId if deviceId else deviceMgr.curDeviceID
                state = state.lower() if state else 'all'
                
                if not device_id:
                    return "e->未指定设备ID"
                    
                # 构建查询
                query = STask.query.filter_by(deviceId=device_id)
                
                # 根据状态过滤
                if state != 'all':
                    query = query.filter_by(state=state)
                    
                # 获取任务列表
                tasks = query.order_by(STask.time.desc()).limit(10).all()
                
                if not tasks:
                    return f"i->设备 {device_id} 没有{state}任务记录"
                    
                # 格式化输出
                result = f"设备 {device_id} 的任务列表 ({state}):\n"
                for task in tasks:
                    progress = task.progress * 100
                    result += f"{task.appName}/{task.taskName}: {progress:.1f}% [{task.state}]\n"
                    
                return result
                
            except Exception as e:
                _Log.Log.ex(e, "获取任务列表失败")
                return f"e->获取任务列表失败: {str(e)}"

        @regCmd('设置日期', r"(?P<date>[^ ]+)")
        def set_date(date):
            """设置任务管理器日期
            用法: 设置日期 YY-M-D
            """
            try:
                parts = date.split('-')
                if len(parts) != 3:
                    return "e->日期格式错误，应为: YY-M-D"
                    
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                # 补全年份
                if year < 100:
                    year += 2000
                    
                # 创建日期对象
                date_obj = datetime(year, month, day)
                
                # 设置任务管理器日期
                device_id = deviceMgr.curDeviceID
                if not device_id:
                    return "e->未选择设备"
                    
                device = deviceMgr.get_device(device_id)
                if not device or not device.taskMgr:
                    return "e->设备或任务管理器不存在"
                    
                device.taskMgr.setDate(date_obj)
                return f"i->已设置日期为: {date_obj.strftime('%Y-%m-%d')}"
                
            except ValueError as e:
                return f"e->日期格式错误: {str(e)}"
            except Exception as e:
                _Log.Log.ex(e, "设置日期失败")
                return f"e->设置日期失败: {str(e)}"

        @regCmd('停止')
        def stop():
            """停止当前设备的当前任务"""
            try:
                device_id = deviceMgr.curDeviceID
                if not device_id:
                    return "e->未选择设备"
                    
                # 获取正在运行的任务
                task = STask.query.filter_by(
                    deviceId=device_id,
                    state=TaskState.RUNNING.value
                ).order_by(STask.time.desc()).first()
                
                if not task:
                    return "i->未找到正在运行的任务"
                    
                if task.state != TaskState.RUNNING.value:
                    return 'w->当前任务不在运行状态'
                deviceMgr.sendClientCmd(device_id, f"stopTask {task.appName} {task.taskName}")
                
            except Exception as e:
                _Log.Log.ex(e, "停止任务失败")
                return f"e->停止任务失败: {str(e)}"
            
            return f"i->已发送停止命令: {task.appName} {task.taskName}"

        @regCmd('保存结果')
        def saveResult():
            """保存最近一次命令执行结果到result.json"""
            try:
                result = deviceMgr.result
                if not result:
                    return "e->没有可保存的结果"
                    
                # 保存到文件
                with open('result.json', 'w', encoding='utf-8') as f:
                    f.write(result)
                    
                return f"i->结果已保存到 result.json"
            except Exception as e:
                _Log.Log.ex(e, "保存结果失败")
                return f"e->保存结果失败: {str(e)}"

        @regCmd('分析收益')
        def analyzeEarnings():
            """分析收益"""
            try:
                # 等待截屏完成后的回调
                def parseResult(data):
                    try:
                        # 获取当前应用名称
                        appName = deviceMgr.currentApp
                        if not appName:
                            _Log.Log.e("当前没有运行的应用")
                            return
                        if SEarningMgr.Load(appName, data):
                            _Log.Log.i("收益记录导入成功")
                        else:
                            _Log.Log.e("部分收益记录导入失败")
                        
                    except Exception as e:
                        _Log.Log.ex(e, "处理截屏结果失败")
                deviceMgr.sendClientCmd(deviceMgr.curDeviceID, 'getScreen', None, 10, parseResult)
                return "i->正在分析收益..."
            except Exception as e:
                _Log.Log.ex(e, "分析收益失败")
                return f"e->分析收益失败: {str(e)}"

        @regCmd('打开', r"(?P<appName>[^ ]+)")
        def openapp(appName):
            """打开指定应用
            用法: 打开 <应用名>
            """
            try:
                from SAppMgr import appMgr
                _appName = appMgr.getApp(appName)
                if not _appName:
                    return
                # 获取当前设备
                device = deviceMgr.CurDevice()
                if device is None:
                    return
                def onOpenApp(x):
                    if _Log.Log.isError(x):
                        _Log.Log.e(x)
                        return
                    _Log.Log.i(f"打开应用回调: {x}")
                    # 设置当前应用名
                    if device.taskMgr:
                        device.taskMgr.currentApp = _appName
                    sleep(5)
                    device.takeScreenshot()
                # 发送打开应用命令
                deviceMgr.sendClientCmd(device.deviceID, f"openApp {_appName}", None, 10, onOpenApp)
                return f"i->正在打开应用[{_appName}]"
                
            except Exception as e:
                _Log.Log.ex(e, "打开应用失败")
                return f"e->打开应用失败: {str(e)}"

        @regCmd('应用列表')
        def apps():
            """列出所有应用"""
            from SAppMgr import appMgr
            return "i->" + json.dumps(appMgr.get_app_names(), ensure_ascii=False, indent=2)

        @regCmd('快照')
        def takeScreenshot():
            """对当前设备进行快照"""
            try:
                device = deviceMgr.curDevice
                if device is None:
                    _Log.Log.e('e->当前没有设备')
                else:
                    device.takeScreenshot()
            except Exception as e:
                _Log.Log.ex(e, '执行快照命令失败')

        @regCmd('@', r"(?P<command>.+)")
        def serverCommand(command):
            """执行服务器命令
            用法: @ <命令>
            """
            try:
                from _CmdMgr import _CmdMgr
                result, _ = _CmdMgr.do(command, sender=None, data=None)
                return result
            except Exception as e:
                _Log.Log.ex(e, "执行服务器命令失败")
                return f"e->执行服务器命令失败: {str(e)}"
