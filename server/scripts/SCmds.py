from datetime import datetime
import _Log
from SDeviceMgr import deviceMgr, SDeviceMgr_
from STask import STask_
import json
import _G
import os
from  _App import _App_

class SCmds_:

    @classmethod
    def registerCommands(cls):
        """注册服务器命令"""
        _G._G_.Log().i("注册SCmds模块命令...")
        from _CmdMgr import regCmd
        @regCmd(r"#服务器信息|fwqxx")
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


        @regCmd('#清空日志')
        def cLearLog():
            """功能：清除控制台日志缓存
            指令名：clearLog
            中文名：清除
            参数：无
            示例：清除
            """
            try:
                g = _G._G_
                # 获取日志对象
                log = g.Log()
                # 清空日志缓存
                log.clear()
                # 通知前端清空日志显示
                g.emit('clear_logs')
                return '控制台日志已清除'
            except Exception as e:
                _Log._Log_.ex(e, '清除日志缓存出错')
                return '清除日志缓存失败'


        @regCmd(r'#进度 (?P<deviceName>[^ ]+)?')
        def progress(deviceName):
            """功能：查询任务执行进度
            指令名：progress
            中文名：进度
            参数：
               deviceName - 设备名称 (可选，使用'_'表示当前设备)
            示例：进度 微信
            """
            try:
                # 通过设备名称获取设备ID
                device = deviceMgr.getByName(deviceName)
                if not device:
                    return "设备不存在"
                
                # 使用设备ID而不是名称
                task = STask_.get(deviceId=device.id, name="任务名称", create=True)
                if not task:
                    return "未找到正在运行的任务"
                progress_percent = task.progress * 100
                return f"任务进度: {progress_percent:.1f}%"
            except Exception as e:
                _Log._Log_.ex(e, "查询任务进度失败")
                return f"e~查询任务进度失败: {str(e)}"


        @regCmd(r"#任务列表|rwlb (?P<deviceId>[^ ]+)?(?P<state>[^ ]+)?")
        def showTaskS(deviceId, state):
            """功能：显示设备的任务列表
            指令名：show_tasks
            中文名：任务列表
            参数：
               deviceId - 设备ID (可选，默认为当前设备)
               state - 任务状态筛选 (可选，默认为all)
            示例：任务列表 设备1 running
            """
            try:
                if not deviceId:
                    return "e~未指定设备ID"
                device_id = int(deviceId)
                state = state.lower() if state else 'all'
                query = STask_.query.filter_by(deviceId=device_id)
                if state != 'all':
                    query = query.filter_by(state=state)
                tasks = query.order_by(STask_.time.desc()).limit(10).all()
                if not tasks:
                    return f"设备 {device_id} 没有{state}任务记录"
                result = f"设备 {device_id} 的任务列表 ({state}):\n"
                for task in tasks:
                    progress = task.progress * 100
                    result += f"{task.taskName}: {progress:.1f}% [{task.state}]\n"
                return result
            except Exception as e:
                _Log._Log_.ex(e, "获取任务列表失败")
                return f"e~获取任务列表失败: {str(e)}"        
        
        @regCmd(r"#获取收益(?P<appName>\S+)(?P<date>\S+)")
        def cGetScores(target, appName, date:str = None)->bool:
            """
            功能：获取设备某应用某天的所有任务收益
            指令名: getScores
            参数: 
                target - 设备ID
                appName - 应用名称
                date - 日期(YYYY-MM-DD)
            返回: 处理结果和收益统计
            """
            g = _G._G_
            log = g.Log()
            try:
                if not date:
                    date = datetime.now().strftime("%Y-%m-%d")                
                device = deviceMgr.get(target)
                if not device:
                    return f"e~设备不存在: {target}"
                return device.cGetScores(appName, date)
            except Exception as e:
                log.ex(e, "获取收益失败")

        @regCmd(r"#获取日志|getLogs(?P<date>\S+)?")
        def getLogs(date=None):
            """
            功能：获取服务端日志
            指令名: getLogs
            中文名: 获取日志
            参数: 
                date - 日期，支持格式: YYYYMMDD, YYYY-MM-DD 等，可选，默认为今天
            返回: 日志数据列表
            """
            g = _G._G_
            log = g.Log()
            try:
                from _Log import _Log_, DateHelper
                
                # 统一日期格式处理
                normalized_date = DateHelper.normalize(date) 
                
                logs = _Log_.gets(normalized_date)
                logData = [logItem.toSheetData() for logItem in logs]
                log.i(f'获取服务端日志: {DateHelper.format_display(normalized_date)}, {len(logData)} 条')
                return logData
                        
            except Exception as e:
                log.ex(e, f'获取服务端日志失败: {date}')
                return f"e~获取日志失败: {str(e)}"            
       
        @regCmd('#保存日志|bcrz')
        def saveLog():
            """功能：强制保存当前服务端日志缓存到文件
            指令名：saveLog
            中文名：保存日志
            参数：无
            示例：保存日志
            """
            try:
                log = _G._G_.Log()
                # 强制保存日志缓存
                log._save(True)
                return '服务端日志已保存到文件'
            except Exception as e:
                _Log._Log_.ex(e, '保存日志失败')
                return f'e~保存日志失败: {str(e)}'

        @regCmd('#保存结果|bcjg')
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
                    return "e~没有可保存的结果"

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

                return f"结果已保存到 result.json"
            except Exception as e:
                _Log._Log_.ex(e, "保存结果失败")
                return f"e~保存结果失败: {str(e)}"


        @regCmd('#快照|kz')
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
                    _Log._Log_.e('e~当前没有设备')
                else:
                    device.takeScreenshot()
            except Exception as e:
                _Log._Log_.ex(e, '执行快照命令失败')


        @regCmd('#扫描应用|smyy')
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
                    return "e~请先选择设备"
                if device.getAppOnScreen():
                    return "分析完成"
                return "e~分析指令发送失败"
            except Exception as e:
                _Log._Log_.ex(e, "执行屏幕分析失败")
                return f"e~{str(e)}"

        @regCmd(r'#截屏(?P<pageName>[^ ]+)?')
        def getScreenInfo(pageName=None):
            """功能：获取当前设备的屏幕信息并缓存
            示例：截屏 登录页
            """
            try:
                log = _G._G_.Log()
                device = deviceMgr.curDevice
                if not device:
                    return "e~请先选择设备"
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
                res = device.sendClientCmd("eval T.getScreenInfo(True)", None)
                handleScreenInfo(res)
                return "正在获取屏幕信息..."
            except Exception as e:
                log.ex(e, "获取屏幕信息失败")
                return f"e~获取屏幕信息失败: {str(e)}"

        @regCmd(r'#设置屏幕信息|szpmxx (?P<pageName>\S+)?')
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
                    return "e~请先选择设备"
                # 获取屏幕信息
                screenInfo = device.getScreenInfo(pageName)
                if not screenInfo:
                    return f"e~信息为空"

                # 使用三引号包裹多行JSON字符串
                cmd = f"eval T.setScreenInfo('''{screenInfo}''')"
                device.sendClientCmd(cmd)

                return f"i-成功设置屏幕信息: {pageName}"
            except Exception as e:
                log.ex(e, "设置屏幕信息失败")
                return f"e~设置屏幕信息失败: {str(e)}"

        @regCmd('#格式化|fjf (?P<fileName>[^ ]+)')
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
                    return f"e~文件不存在: {fileName}"

                # 读取文件内容
                with open(fileName, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 解析JSON
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    return f"e~JSON解析错误: {str(e)}"

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

                return f"文件已格式化: {fileName}"
            except Exception as e:
                log.ex(e, f"格式化JSON文件失败: {fileName}")
                return f"e~格式化失败: {str(e)}"

        @regCmd('#打印拓扑|pt')
        def printTopology():
            """功能：打印系统拓扑结构
            指令名：printTopology
            中文名：打印拓扑
            参数：无
            示例：打印拓扑
            """
            try:
                _App_.printTopology()
                return "拓扑结构已打印"
            except Exception as e:
                _Log._Log_.ex(e, "打印拓扑结构失败")
                return f"e~打印拓扑结构失败: {str(e)}"


        @regCmd('#选择设备|xzsb (?P<target>\S+)')
        def seLect(target=None):
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
            # 通知前端更新选择
            _G._G_.emit('S2B_UpdateSelection', {'device_ids': [target]})

        @regCmd(r'#设备信息|sbxx (?P<deviceID>\S+)?')
        def deviceInfo(deviceID):
            """功能：获取设备信息
            指令名：deviceInfo
            中文名：设备信息
            参数：
               deviceID - 设备ID (可选)
            示例：设备信息 设备1
            """
            try:
                device = deviceMgr.getByName(deviceID)
                if device:
                    return device.toDict()
                else:
                    return "e~设备不存在"
            except Exception as e:
                _Log._Log_.ex(e, "获取设备信息失败")
                return f"e~获取设备信息失败: {str(e)}"

        @regCmd('#任务信息|rwxx (?P<taskID>\S+)')
        def taskInfo(taskID):
            """功能：获取任务信息
            指令名：taskInfo
            中文名：任务信息
            参数：
               taskID - 任务ID
            示例：任务信息 任务1
            """
            try:
                task = STask_.query.get(taskID)
                if task:
                    return task.to_dict()
                else:
                    return "e~任务不存在"
            except Exception as e:
                _Log._Log_.ex(e, "获取任务信息失败")
                return f"e~获取任务信息失败: {str(e)}" 

        
        @regCmd('#添加设备|tjsb (?P<taskID>\S+)\s+(?P<deviceIDs>.+)')
        def addDevice(taskID, deviceIDs):
            """功能：添加设备到任务
            指令名：addDevice
            中文名：添加设备
            参数：
               taskID - 任务ID
               deviceIDs - 设备ID列表，用空格分隔
            示例：添加设备 任务1 设备1 设备2
            """
            try:
                task = STask_.query.get(taskID)
                if task:
                    device_ids = deviceIDs.split()
                    if not device_ids:
                        return "e~未指定设备ID"

                    task.addDevices(device_ids)
                    return f"已添加设备到任务: {taskID}, 设备: {', '.join(device_ids)}"
                else:
                    return "e~任务不存在"
            except Exception as e:
                _Log._Log_.ex(e, "添加设备到任务失败")
                return f"e~添加设备到任务失败: {str(e)}"

        @regCmd('#移除设备|ycsb (?P<taskID>\S+)\s+(?P<deviceIDs>.+)')
        def removeDevice(taskID, deviceIDs):
            """功能：从任务中移除设备
            示例：移除设备 任务1 设备1 设备2
            """
            try:
                task = STask_.query.get(taskID)
                if task:
                    device_ids = deviceIDs.split()
                    if not device_ids:
                        return "e~未指定设备ID"

                    task.removeDevices(device_ids)
                    return f"已从任务中移除设备: {taskID}, 设备: {', '.join(device_ids)}"
                else:
                    return "e~任务不存在"
            except Exception as e:
                _Log._Log_.ex(e, "从任务中移除设备失败")
                return f"e~从任务中移除设备失败: {str(e)}"

        @regCmd(r"#设备列表|sblb(?P<state>\S+)?")
        def showDevices(state=None):
            """
            功能：列举设备信息
            指令名: showDevices
            中文名: 设备列表
            参数: state - 设备状态(可选)，不指定则显示所有设备
            示例: 设备列表 [online]
            """
            g = _G._G_
            log = g.Log()
            try:
                # 获取设备列表
                devices = deviceMgr.devices
                if state:
                    state = state.upper()
                    devices = [d for d in devices if d.state == state]
                
                if not devices:
                    return "没有找到符合条件的设备"
                
                # 格式化输出，输出成表格形式，表格的列名：设备ID，名称，状态，需要对tab齐
                result = '\n\t\t\t'.join(["设备ID", "名称", "状态"]) + '\n'
                for device in devices:
                    result += '\t\t\t'.join([str(device.id), device.name, device.state]) + '\n'
                return result
            except Exception as e:
                log.ex(e, "列举设备失败")
                return f"e~列举设备失败: {str(e)}"
