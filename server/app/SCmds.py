from datetime import datetime
from scripts.logger import Log
from scripts.CmdMgr import regCmd
from flask_socketio import emit
from .SDeviceMgr import deviceMgr, SDeviceMgr
from .models import db
from .STask import STask, TaskState
import json
from .SEarningMgr import SEarningMgr
from scripts.CmdMgr import CmdMgr


def OnReload():
    Log.w("Cmds模块热更新 清理命令列表")
    CmdMgr.clear()

# 修改命令注册，使用中文命令名和参数匹配模式
@regCmd('日期', r"(?P<format>[^ ]+)?", '显示当前日期和时间')
def date(format):
    """显示当前日期和时间
    用法: 日期 [format]
    format: 可选的日期格式，默认为 %Y-%m-%d %H:%M:%S
    """
    try:
        Log.i(f"date: 日期: {format}")
        # 解析参数
        date_format = format if format else "%Y-%m-%d %H:%M:%S"
        # 获取当前日期和时间
        current_time = datetime.now().strftime(date_format)
        Log.i(f"date: 当前日期和时间: {current_time}")
        deviceMgr.sendClientCmd(deviceMgr.curDeviceID, f"date {current_time}")
        return f"i##当前日期和时间: {current_time}"
    except Exception as e:
        Log.ex(e, "获取日期时间失败")
        return f"e##获取日期时间失败: {str(e)}"

@regCmd('帮助', None, '显示帮助信息')
def help():
    """显示帮助信息"""
    from .SCommand import SCommand
    help_text = "可用的服务器命令:\n"
    for cmd, (desc, _) in SCommand.COMMANDS.items():
        help_text += f"{cmd}: {desc}\n"
    return help_text

@regCmd('状态', None, '显示服务器状态')
def status():
    """显示服务器状态"""
    return '服务器运行正常'

@regCmd('清除', None, '清除日志')
def clearLog():
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

@regCmd('设备列表', None, '列出所有设备')
def list_devices():
    """列出所有设备"""
    device_manager = SDeviceMgr()
    devices = device_manager.to_dict()
    return '\n'.join([
        f"{id}: {dev['status']}" 
        for id, dev in devices.items()
    ])

@regCmd('日志', r"(?P<level>[iwe])\s+(?P<content>.+)", '手动打印日志')
def log(level, content):
    """手动打印日志
    用法: 日志 <level> <content>
    level: i/w/e (info/warning/error)
    """
    if level not in ["i", "w", "e"]:
        return "日志级别必须是 i/w/e 之一"
        
    # 调用对应的日志方法
    if level == 'i':
        Log.i(content)
    elif level == 'w':
        Log.w(content)
    else:
        Log.e(content)
        
    return f"日志已打印: [{level}] {content}"

@regCmd('进度', r"(?P<deviceId>[^ ]+)?(?P<appName>[^ ]+)?(?P<taskName>[^ ]+)?", '查询任务进度')
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

@regCmd('继续', None, '继续当前设备的暂停任务')
def resume():
    """继续当前设备的暂停任务"""
    try:
        device_id = deviceMgr.curDeviceID
        if not device_id:
            return "e##未选择设备"
            
        # 获取暂停的任务
        task = STask.query.filter_by(
            deviceId=device_id,
            state=TaskState.PAUSED.value
        ).order_by(STask.time.desc()).first()
        
        if not task:
            return "i##未找到暂停的任务"
            
        # 发送继续命令
        deviceMgr.sendClientCmd(device_id, f"resumeTask {task.appName} {task.taskName}")
        
        # 更新任务状态
        task.state = TaskState.RUNNING.value
        db.session.commit()
        
        return f"i##已继续任务: {task.appName} {task.taskName}"
        
    except Exception as e:
        Log.ex(e, "继续任务失败")
        return f"e##继续任务失败: {str(e)}"

@regCmd('调试', None, '显示调试信息')
def debug():
    """显示调试信息"""
    try:
        # 获取当前设备
        device_id = deviceMgr.curDeviceID
        if not device_id:
            return "e##未选择设备"
            
        device = deviceMgr.get_device(device_id)
        if not device:
            return "e##设备不存在"
            
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
        Log.ex(e, "获取调试信息失败")
        return f"e##获取调试信息失败: {str(e)}"

@regCmd('任务列表', r"(?P<deviceId>[^ ]+)?(?P<state>[^ ]+)?", '显示任务')
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
            return "e##未指定设备ID"
            
        # 构建查询
        query = STask.query.filter_by(deviceId=device_id)
        
        # 根据状态过滤
        if state != 'all':
            query = query.filter_by(state=state)
            
        # 获取任务列表
        tasks = query.order_by(STask.time.desc()).limit(10).all()
        
        if not tasks:
            return f"i##设备 {device_id} 没有{state}任务记录"
            
        # 格式化输出
        result = f"设备 {device_id} 的任务列表 ({state}):\n"
        for task in tasks:
            progress = task.progress * 100
            result += f"{task.appName}/{task.taskName}: {progress:.1f}% [{task.state}]\n"
            
        return result
        
    except Exception as e:
        Log.ex(e, "获取任务列表失败")
        return f"e##获取任务列表失败: {str(e)}"

@regCmd('设置日期', r"(?P<date>[^ ]+)", '设置任务管理器日期')
def set_date(date):
    """设置任务管理器日期
    用法: 设置日期 YY-M-D
    """
    try:
        parts = date.split('-')
        if len(parts) != 3:
            return "e##日期格式错误，应为: YY-M-D"
            
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        # 补全年份
        if year < 100:
            year += 2000
            
        # 创建日期对象
        date_obj = datetime(year, month, day)
        
        # 设置任务管理器日期
        device_id = deviceMgr.curDeviceID
        if not device_id:
            return "e##未选择设备"
            
        device = deviceMgr.get_device(device_id)
        if not device or not device.taskMgr:
            return "e##设备或任务管理器不存在"
            
        device.taskMgr.setDate(date_obj)
        return f"i##已设置日期为: {date_obj.strftime('%Y-%m-%d')}"
        
    except ValueError as e:
        return f"e##日期格式错误: {str(e)}"
    except Exception as e:
        Log.ex(e, "设置日期失败")
        return f"e##设置日期失败: {str(e)}"

@regCmd('停止', None, '停止当前设备的当前任务')
def stop():
    """停止当前设备的当前任务"""
    try:
        device_id = deviceMgr.curDeviceID
        if not device_id:
            return "e##未选择设备"
            
        # 获取正在运行的任务
        task = STask.query.filter_by(
            deviceId=device_id,
            state=TaskState.RUNNING.value
        ).order_by(STask.time.desc()).first()
        
        if not task:
            return "i##未找到正在运行的任务"
            
        if task.state != TaskState.RUNNING.value:
            return 'w##当前任务不在运行状态'
        deviceMgr.sendClientCmd(device_id, f"stopTask {task.appName} {task.taskName}")
        
    except Exception as e:
        Log.ex(e, "停止任务失败")
        return f"e##停止任务失败: {str(e)}"
    
    return f"i##已发送停止命令: {task.appName} {task.taskName}"

@regCmd('保存结果', None, '保存最近一次命令执行结果')
def saveResult():
    """保存最近一次命令执行结果到result.json"""
    try:
        result = deviceMgr.result
        if not result:
            return "e##没有可保存的结果"
            
        # 保存到文件
        with open('result.json', 'w', encoding='utf-8') as f:
            f.write(result)
            
        return f"i##结果已保存到 result.json"
    except Exception as e:
        Log.ex(e, "保存结果失败")
        return f"e##保存结果失败: {str(e)}"

@regCmd('分析收益', None, '分析收益')
def analyzeEarnings():
    """分析收益"""
    try:
        # 等待截屏完成后的回调
        def parseResult(data):
            try:
                # 获取当前应用名称
                appName = deviceMgr.currentApp
                if not appName:
                    Log.e("当前没有运行的应用")
                    return
                if SEarningMgr.Load(appName, data):
                    Log.i("收益记录导入成功")
                else:
                    Log.e("部分收益记录导入失败")
                
            except Exception as e:
                Log.ex(e, "处理截屏结果失败")
        deviceMgr.sendClientCmd(deviceMgr.curDeviceID, 'getScreen', None, parseResult)
        return "i##正在分析收益..."
    except Exception as e:
        Log.ex(e, "分析收益失败")
        return f"e##分析收益失败: {str(e)}"

@regCmd('打开应用', r"(?P<appName>[^ ]+)", '打开指定应用')
def openapp(appName):
    """打开指定应用
    用法: 打开应用 <应用名>
    """
    try:
        # 使用模糊匹配查找应用
        
        # 使用模糊匹配查找应用
        from .SAppMgr import appMgr
        _appName = appMgr.getApp(appName)
        
        if not _appName:
            return f"e##找不到匹配的应用[{appName}]"
        
        # 获取当前设备
        device_id = deviceMgr.curDeviceID
        if not device_id:
            return "e##未选择设备"
        
        device = deviceMgr.get_device(device_id)
        if not device:
            return "e##设备不存在"
        
        # 发送打开应用命令
        deviceMgr.sendClientCmd(device_id, f"打开 {_appName}")
        
        # 设置当前应用名
        if device.taskMgr:
            device.taskMgr._currentApp = _appName
            
        return f"i##正在打开应用[{_appName}]"
        
    except Exception as e:
        Log.ex(e, "打开应用失败")
        return f"e##打开应用失败: {str(e)}"

@regCmd('应用列表', None, '列出所有应用')
def apps():
    """列出所有应用"""
    from .SAppMgr import appMgr
    return "i##" + json.dumps(appMgr.get_app_names(), ensure_ascii=False, indent=2)
