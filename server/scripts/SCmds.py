from datetime import datetime
import _Log
from _CmdMgr import regCmd
from flask_socketio import emit
from SDeviceMgr import deviceMgr, SDeviceMgr_
from STask import STask_, TaskState
import json
from SEarningMgr import SEarningMgr_
from time import sleep
import _G
import os
from _App import _App_

class SCmds_:
    @classmethod
    def OnReload(cls):
        """热更新后重新注册命令"""
        log = _G._G_.Log()
        log.w("SCmds模块热更新 重新注册命令")
        cls.registerCommands()
        # 使用全局命令重新注册机制
        log.i("命令重新注册完成")
    
    @classmethod
    def registerCommands(cls):
        """注册服务器命令"""
        log = _G._G_.Log()
        log.i("注册SCmds模块命令...")
        
        @regCmd(r"(?:服务器信息|fwqxx)")
        def serverInfo():
            """
            功能：获取服务器信息
            指令名: serverInfo-sI
            中文名: 服务器信息
            参数: 无
            示例: 服务器信息
            """
            return {
                "version": "1.0.0",
                "timestamp": str(datetime.now()),
                "devices": len(deviceMgr.devices),
            }
        
        @regCmd(r"日期(?P<format>\S+)?")
        def date(format=None):
            """功能：获取当前日期和时间
            指令名：date
            中文名：日期
            参数：
              format - 日期格式字符串 (可选)
            示例：日期 %Y年%m月%d日
            """
            try:
                date_format = format or "%Y-%m-%d %H:%M:%S"
                current_time = datetime.now().strftime(date_format)
                return f"当前日期和时间: {current_time}"
            except Exception as e:
                _Log._Log_.ex(e, "获取日期时间失败")
                return f"e-获取日期时间失败: {str(e)}"


        @regCmd('状态', sAlias="zt")
        def status():
            """功能：显示服务器运行状态
            指令名：status
            中文名：状态
            参数：无
            示例：状态
            """
            return '服务器运行正常aa'

        @regCmd('清除', sAlias="qc")
        def clearLog():
            """功能：清除控制台日志缓存
            指令名：clearLog
            中文名：清除
            参数：无
            示例：清除
            """
            try:
                # 清空日志缓存
                log.clear()
                # 使用覆盖模式保存
                log.save(mode='w')            
                # 通知前端清空日志显示
                emit('clear_logs')            
                return '控制台日志已清除'
            except Exception as e:
                _Log._Log_.ex(e, '清除日志缓存出错')
                return '清除日志缓存失败'

        @regCmd(r"(?:设备列表|sblb)")
        def deviceList():
            """
            功能：获取已连接设备列表
            指令名: deviceList-dL
            中文名: 设备列表
            参数: 无
            示例: 设备列表
            """
            device_manager = SDeviceMgr_()
            devices = device_manager.toDict()
            return '\n'.join([
                f"{id}: {dev['status']}" 
                for id, dev in devices.items()
            ])

        @regCmd(r"进度(?P<deviceId>[^ ]+)?(?P<appName>[^ ]+)?(?P<taskName>[^ ]+)?")
        def progress(deviceId, appName, taskName):
            """功能：查询任务执行进度
            指令名：progress
            中文名：进度
            参数：
              deviceId - 设备ID (可选，使用'_'表示当前设备)
              appName - 应用名称 (可选，使用'_'表示最近任务)
              taskName - 任务名称 (可选，使用'_'表示最近任务)
            示例：进度 _ 微信 签到
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
                    last_task = STask_.query.filter_by(
                        deviceId=deviceId
                    ).order_by(STask_.time.desc()).first()
                    
                    if not last_task:
                        return "i->未找到最近任务记录"
                    
                    if appName == '_':
                        appName = last_task.appName
                    if taskName == '_':
                        taskName = last_task.taskName
                
                # 从数据库查询任务
                task = STask_.query.filter_by(
                    deviceId=deviceId,
                    appName=appName,
                    taskName=taskName,
                ).order_by(STask_.time.desc()).first()
                
                if not task:
                    return "i->未找到正在运行的任务"
                    
                # 格式化输出任务信息（转换为百分比）
                progress_percent = task.progress * 100
                return f"i->任务进度: {progress_percent:.1f}%"
                
            except Exception as e:
                _Log._Log_.ex(e, "查询任务进度失败")
                return f"e->查询任务进度失败: {str(e)}"


        @regCmd('调试', sAlias="ts")
        def debug():
            """功能：显示当前设备的详细调试信息
            指令名：debug
            中文名：调试
            参数：无
            示例：调试
            """
            try:
                # 获取当前设备
                device_id = deviceMgr.curDeviceID
                if not device_id:
                    return "e->未选择设备"
                    
                device = deviceMgr.get(device_id)
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
                    task = STask_.query.filter_by(
                        deviceId=device_id,
                        state=TaskState.RUNNING.value
                    ).order_by(STask_.time.desc()).first()
                    
                    if task:
                        debug_info += f"当前任务: {task.appName}/{task.taskName}\n"
                        debug_info += f"进度: {task.progress * 100:.1f}%\n"
                        debug_info += f"开始时间: {task.time}\n"
                
                return debug_info
                
            except Exception as e:
                _Log._Log_.ex(e, "获取调试信息失败")
                return f"e->获取调试信息失败: {str(e)}"

        @regCmd(r"任务列表(?P<deviceId>[^ ]+)?(?P<state>[^ ]+)?")
        def show_tasks(deviceId, state):
            """功能：显示设备的任务列表
            指令名：show_tasks
            中文名：任务列表
            参数：
               deviceId - 设备ID (可选，默认为当前设备)
               state - 任务状态筛选 (可选，默认为all)
            示例：任务列表 设备1 running
            """
            try:
                # 解析参数
                device_id = deviceId if deviceId else deviceMgr.curDeviceID
                state = state.lower() if state else 'all'
                
                if not device_id:
                    return "e->未指定设备ID"
                    
                # 构建查询
                query = STask_.query.filter_by(deviceId=device_id)
                
                # 根据状态过滤
                if state != 'all':
                    query = query.filter_by(state=state)
                    
                # 获取任务列表
                tasks = query.order_by(STask_.time.desc()).limit(10).all()
                
                if not tasks:
                    return f"i->设备 {device_id} 没有{state}任务记录"
                    
                # 格式化输出
                result = f"设备 {device_id} 的任务列表 ({state}):\n"
                for task in tasks:
                    progress = task.progress * 100
                    result += f"{task.appName}/{task.taskName}: {progress:.1f}% [{task.state}]\n"
                    
                return result
                
            except Exception as e:
                _Log._Log_.ex(e, "获取任务列表失败")
                return f"e->获取任务列表失败: {str(e)}"

        @regCmd(r'设置日期(?P<date>[^ ]+)')
        def set_date(date):
            """功能：设置任务管理器的执行日期
            指令名：set_date
            中文名：设置日期
            参数：
               date - 日期字符串，格式为YY-M-D
            示例：设置日期 23-11-30
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
                    
                device = deviceMgr.get(device_id)
                if not device or not device.taskMgr:
                    return "e->设备或任务管理器不存在"
                    
                device.taskMgr.setDate(date_obj)
                return f"i->已设置日期为: {date_obj.strftime('%Y-%m-%d')}"
                
            except ValueError as e:
                return f"e->日期格式错误: {str(e)}"
            except Exception as e:
                _Log._Log_.ex(e, "设置日期失败")
                return f"e->设置日期失败: {str(e)}"

        @regCmd(r"(?:停止|tz)(?P<taskName>[^ ]+)?")
        def stop(taskName=None):
            """功能：停止当前设备正在运行的任务
            指令名：stop
            中文名：停止
            参数：
              taskName - 任务名称 (可选，默认为当前任务)
            示例：停止 签到
            """
            try:
                device_id = deviceMgr.curDeviceID
                if not device_id:
                    return "e->未选择设备"
                    
                # 获取正在运行的任务
                task = STask_.query.filter_by(
                    deviceId=device_id,
                    state=TaskState.RUNNING.value
                ).order_by(STask_.time.desc()).first()
                
                if not task:
                    return "i->未找到正在运行的任务"
                    
                if task.state != TaskState.RUNNING.value:
                    return 'w->当前任务不在运行状态'
                deviceMgr.sendClientCmd(device_id, f"stopTask {task.appName} {task.taskName}")
                
            except Exception as e:
                _Log._Log_.ex(e, "停止任务失败")
                return f"e->停止任务失败: {str(e)}"
            
            return f"i->已发送停止命令: {task.appName} {task.taskName}"

        @regCmd(r"(?:保存结果|bcjg)")
        def saveResult():
            """功能：保存最近一次命令执行结果到JSON文件
            指令名：saveResult
            中文名：保存结果
            参数：无
            示例：保存结果
            """
            try:
                g = _G._G_
                result = g.lastResult
                if not result:
                    return "e->没有可保存的结果"
                    
                # 尝试将结果转换为JSON格式
                try:
                    # 如果结果已经是字典或列表，直接使用
                    if isinstance(result, (dict, list)):
                        data = result
                    else:
                        # 尝试解析为JSON
                        data = json.loads(result)
                except (json.JSONDecodeError, TypeError):
                    # 如果不是JSON，则将结果转换为字符串并包装在字典中
                    data = {"result": str(result)}
                    
                # 使用漂亮的格式序列化
                formatted_json = json.dumps(
                    data, 
                    ensure_ascii=False, 
                    indent=4,
                    sort_keys=True
                )
                
                # 保存到文件
                with open("result.json", "w", encoding="utf-8") as f:
                    f.write(formatted_json)
                    
                return f"i->结果已保存到 result.json"
            except Exception as e:
                _Log._Log_.ex(e, "保存结果失败")
                return f"e->保存结果失败: {str(e)}"

       
        @regCmd(r"(?:快照|kz)")
        def takeScreenshot():
            """功能：对当前设备进行屏幕截图
            指令名：takeScreenshot
            中文名：快照
            参数：无
            示例：快照
            """
            try:
                device = deviceMgr.curDevice
                if device is None:
                    _Log._Log_.e('e->当前没有设备')
                else:
                    device.takeScreenshot()
            except Exception as e:
                _Log._Log_.ex(e, '执行快照命令失败')


        @regCmd(r"(?:扫描应用|smyy)")
        def scanApp():
            """功能：分析当前设备屏幕上的应用信息
            指令名：scanApp
            中文名：扫描应用
            参数：无
            示例：扫描应用
            """
            try:
                device = deviceMgr.curDevice
                if not device:
                    return "e->请先选择设备"
                if device.getAppOnScreen():
                    return "分析完成"
                return "e->分析指令发送失败"
            except Exception as e:
                _Log._Log_.ex(e, "执行屏幕分析失败")
                return f"e->{str(e)}"

        @regCmd(r'截屏(?P<pageName>[^ ]+)?')
        def getScreenInfo(pageName=None):
            """功能：获取当前设备的屏幕信息并缓存
            指令名：getScreenInfo
            中文名：截屏
            参数：
               pageName - 保存的页面名称 (可选，默认为'Last')
            示例：截屏 登录页
            """
            try:
                log = _G._G_.Log()
                device = deviceMgr.curDevice
                if not device:
                    return "e->请先选择设备"
                pageName = pageName or 'Last'
                
                # 回调函数处理客户端返回的屏幕信息
                def handleScreenInfo(result):
                    try:
                        if _Log._Log_.isError(result):
                            log.e(f"获取屏幕信息失败: {result}")
                            return
                        
                        # 检查结果是否为空
                        if not result or result == "None" or result == "[]":
                            log.e("获取到空的屏幕信息")
                            return
                            
                        # 保存到设备对象中
                        device.setScreenInfo(pageName, result)
                        # log.i(f"屏幕信息保存成功: {pageName}, 共{len(result)}个元素")
                    except Exception as e:
                        log.ex(e, "处理屏幕信息失败")
                
                # 发送客户端命令获取屏幕信息
                res = deviceMgr.sendClientCmd(device.deviceID, "eval T.getScreenInfo(True)", None, 10)
                handleScreenInfo(res)
                return "i->正在获取屏幕信息..."
            except Exception as e:
                log.ex(e, "获取屏幕信息失败")
                return f"e->获取屏幕信息失败: {str(e)}"

        @regCmd(r"(?:设置屏幕|szpm)(?P<pageName>[^ ]+)?")
        def setScreenInfo(pageName=None):
            """功能：将服务端缓存的屏幕信息发送到客户端
            指令名：setScreenInfo
            中文名：设置屏幕
            参数：
               pageName - 页面名称 (可选，默认使用最近获取的屏幕)
            示例：设置屏幕 登录页
            """
            try:
                log = _G._G_.Log()
                device = deviceMgr.curDevice
                if not device:
                    return "e-请先选择设备"
                # 获取屏幕信息
                screenInfo = device.getScreenInfo(pageName)
                if not screenInfo:
                    return f"e-屏幕信息为空"
                    
                # 使用三引号包裹多行JSON字符串
                cmd = f"eval T.setScreenInfo('''{screenInfo}''')"
                deviceMgr.sendClientCmd(device.deviceID, cmd)
                
                return f"i-成功设置屏幕信息: {pageName}"
            except Exception as e:
                log.ex(e, "设置屏幕信息失败")
                return f"e-设置屏幕信息失败: {str(e)}"

        @regCmd(r"(?:格式化|fjf)(?P<fileName>[^ ]+)")
        def formatJsonFile(fileName):
            """功能：格式化指定的JSON文件使其更易读
            指令名：formatJsonFile
            中文名：格式化JSON
            参数：
               fileName - JSON文件名
            示例：格式化JSON config.json
            """
            try:
                log = _G._G_.Log()
                
                # 检查文件是否存在
                if not os.path.exists(fileName):
                    return f"e-文件不存在: {fileName}"
                    
                # 读取文件内容
                with open(fileName, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 解析JSON
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    return f"e->JSON解析错误: {str(e)}"
                    
                # 使用漂亮的格式重新序列化
                formatted_json = json.dumps(
                    data, 
                    ensure_ascii=False, 
                    indent=4,
                    sort_keys=True
                )
                
                # 保存回文件
                with open(fileName, 'w', encoding='utf-8') as f:
                    f.write(formatted_json)
                    
                return f"i->文件已格式化: {fileName}"
            except Exception as e:
                log.ex(e, f"格式化JSON文件失败: {fileName}")
                return f"e->格式化失败: {str(e)}"

        @regCmd(r"(?:打印拓扑|pt)")
        def printTopology():
            """功能：打印系统拓扑结构
            指令名：printTopology
            中文名：打印拓扑
            参数：无
            示例：打印拓扑
            """
            try:
                _App_.printTopology()
                return "i->拓扑结构已打印"
            except Exception as e:
                _Log._Log_.ex(e, "打印拓扑结构失败")
                return f"e->打印拓扑结构失败: {str(e)}"

        @regCmd(r"(?:加载|jz)")
        def load():
            """功能：加载环境配置
            指令名：load
            中文名：无 (使用函数名)
            参数：无
            示例：load
            """
            _G._G_.load()

        @regCmd(r'选择(?P<target>.*)?')
        def select(target=None):
            """功能：根据目标描述选择设备
            指令名：select
            中文名：选择
            参数：
               target - 目标描述 (可选)
            
            target 解析规则:
            1. 为空: 只打印当前选中的设备名，不做选择动作
            2. @: 表示选择服务端
            3. 其它: 先当成设备ID查找，如果存在就选择该设备
                     如果不存在，当成group名查找，选择该group所有设备
                     如果还不存在，报错
            示例：
              选择           # 显示当前选中的设备
              选择 @         # 选择服务端
              选择 device001 # 选择指定设备
              选择 测试组     # 选择指定分组的所有设备
            """
            from SDeviceMgr import deviceMgr            
            target = target.strip() if target else ''
            # 如果目标是@，选择服务端
            if target == "@" or target == '':
                #清空当前选择，表示选择服务端
                deviceMgr.curDeviceIDs =[]
            elif target == '?':
                return f"选中设备为: {deviceMgr.curDeviceIDs}"
            elif target == 'all':
                deviceMgr.curDeviceIDs = list(deviceMgr.devices.keys())
            else:                
                # 尝试作为设备ID查找
                device = deviceMgr.get(target)
                if device:
                    deviceMgr.curDeviceIDs = [target]
                else:
                    # 尝试作为分组名查找
                    if target == 'def':
                        target = ''
                    group_devices = list(deviceMgr.GetByGroup(target).keys())
                    if group_devices:
                        deviceMgr.curDeviceIDs = group_devices
                    else:
                        return f"e->无效目标: {target}"
            
            # 通知前端更新选择
            deviceMgr.emit2B('S2B_UpdateSelection', {'device_ids': deviceMgr.curDeviceIDs})
