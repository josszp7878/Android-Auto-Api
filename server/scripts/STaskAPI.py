# from flask import Blueprint, jsonify, request
# from SDeviceMgr import deviceMgr
# import _G
# from datetime import datetime
# from flask_socketio import emit

# # 创建任务API蓝图
# task_bp = Blueprint('task_api', __name__)

# @task_bp.route('/api/tasks', methods=['GET'])
# def get_tasks():
#     """获取所有任务"""
#     tasks = []
    
#     # 从设备中获取任务数据
#     for deviceId, device in deviceMgr.devices.items():
#         if hasattr(device, 'taskMgr') and device.taskMgr and hasattr(device.taskMgr, 'tasks'):
#             for task in device.taskMgr.tasks:
#                 # 计算任务进度
#                 progress = 0
#                 if hasattr(task, 'progress') and hasattr(task, 'total'):
#                     if task.total > 0:
#                         progress = int((task.progress / task.total) * 100)
                
#                 # 收集任务数据
#                 task_data = {
#                     'id': task.taskId if hasattr(task, 'taskId') else '',
#                     'group': task.group if hasattr(task, 'group') else '',
#                     'deviceId': task.deviceId if hasattr(task, 'deviceId') else '',
#                     'taskName': task.displayName if hasattr(task, 'displayName') else task.__class__.__name__,
#                     'progress': progress,
#                     'status': task.state if hasattr(task, 'state') else 'pending',
#                     'life': task.life if hasattr(task, 'life') else 100,
#                     'score': task.score if hasattr(task, 'score') else 0,
#                     'date': task.date.strftime('%Y-%m-%d') if hasattr(task, 'date') else ''
#                 }
#                 tasks.append(task_data)
    
#     return jsonify(tasks)

# @task_bp.route('/api/tasks/daily/<date_str>', methods=['GET'])
# def get_daily_tasks(date_str):
#     """获取指定日期的任务"""
#     log = _G._G_.Log()
#     log.i('TaskAPI', f'获取{date_str}的任务数据')
    
#     try:
#         # 解析日期字符串
#         target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
#         tasks = []
#         # 从设备中获取指定日期的任务数据
#         for deviceId, device in deviceMgr.devices.items():
#             if hasattr(device, 'taskMgr') and device.taskMgr and hasattr(device.taskMgr, 'tasks'):
#                 for task in device.taskMgr.tasks:
#                     # 检查任务日期是否匹配
#                     task_date = task.date.date() if hasattr(task, 'date') else None
#                     if task_date == target_date:
#                         # 计算任务进度
#                         progress = 0
#                         if hasattr(task, 'progress') and hasattr(task, 'total'):
#                             if task.total > 0:
#                                 progress = int((task.progress / task.total) * 100)
                        
#                         # 收集任务数据
#                         task_data = {
#                             'id': task.taskId if hasattr(task, 'taskId') else '',
#                             'group': task.group if hasattr(task, 'group') else '',
#                             'deviceId': task.deviceId if hasattr(task, 'deviceId') else '',
#                             'taskName': task.displayName if hasattr(task, 'displayName') else task.__class__.__name__,
#                             'progress': progress,
#                             'status': task.state if hasattr(task, 'state') else 'pending',
#                             'life': task.life if hasattr(task, 'life') else 100,
#                             'score': task.score if hasattr(task, 'score') else 0,
#                             'date': task.date.strftime('%Y-%m-%d') if hasattr(task, 'date') else ''
#                         }
#                         tasks.append(task_data)
        
#         return jsonify(tasks)
#     except Exception as e:
#         log.e('TaskAPI', f'获取日期任务数据失败: {str(e)}')
#         return jsonify([]), 500

   

# @task_bp.route('/api/devices', methods=['GET'])
# def get_devices():
#     """获取所有设备"""
#     devices = deviceMgr.toDict()
#     return jsonify(devices)

# @task_bp.route('/api/task/<task_id>/execute', methods=['POST'])
# def execute_task(task_id):
#     """执行任务"""
#     log = _G._G_.Log()
    
#     # 解析任务ID，找到相应的设备和任务
#     parts = task_id.split('_')
#     if len(parts) < 2:
#         return jsonify({
#             'success': False,
#             'message': f'任务ID格式错误: {task_id}'
#         }), 400
    
#     deviceId = parts[0]
#     taskName = '_'.join(parts[1:])
    
#     # 获取设备
#     device = deviceMgr.get(deviceId)
#     if not device or not hasattr(device, 'taskMgr'):
#         log.e('TaskAPI', f'执行任务失败: 设备{deviceId}不存在或没有任务管理器')
#         return jsonify({
#             'success': False,
#             'message': f'设备{deviceId}不存在或没有任务管理器'
#         }), 404
    
#     # 执行任务
#     try:
#         # 获取或创建任务
#         task = device.taskMgr.getRunningTask(taskName, create=True)
#         if not task:
#             return jsonify({
#                 'success': False,
#                 'message': f'无法创建任务: {taskName}'
#             }), 500
            
#         # 启动任务
#         success = device.taskMgr.startTask(task)
#         if success:
#             log.i('TaskAPI', f'任务{task_id}开始执行')
#             return jsonify({
#                 'success': True,
#                 'message': f'任务{task_id}已开始执行'
#             })
#         else:
#             return jsonify({
#                 'success': False,
#                 'message': f'启动任务失败'
#             }), 500
#     except Exception as e:
#         log.e('TaskAPI', f'执行任务{task_id}失败: {str(e)}')
#         return jsonify({
#             'success': False,
#             'message': f'执行任务失败: {str(e)}'
#         }), 500

# @task_bp.route('/api/task/<task_id>/pause', methods=['POST'])
# def pause_task(task_id):
#     """暂停任务"""
#     log = _G._G_.Log()
    
#     # 解析任务ID，找到相应的设备和任务
#     parts = task_id.split('_')
#     if len(parts) < 2:
#         return jsonify({
#             'success': False,
#             'message': f'任务ID格式错误: {task_id}'
#         }), 400
    
#     deviceId = parts[0]
#     taskName = '_'.join(parts[1:])
    
#     # 获取设备
#     device = deviceMgr.get(deviceId)
#     if not device or not hasattr(device, 'taskMgr'):
#         log.e('TaskAPI', f'暂停任务失败: 设备{deviceId}不存在或没有任务管理器')
#         return jsonify({
#             'success': False,
#             'message': f'设备{deviceId}不存在或没有任务管理器'
#         }), 404
    
#     # 暂停任务
#     try:
#         appName = "" # 在新的实现中不需要appName参数
#         success = device.taskMgr.pauseTask(appName, taskName)
#         if success:
#             log.i('TaskAPI', f'任务{task_id}已暂停')
#             return jsonify({
#                 'success': True,
#                 'message': f'任务{task_id}已暂停'
#             })
#         else:
#             return jsonify({
#                 'success': False,
#                 'message': f'暂停任务失败'
#             }), 500
#     except Exception as e:
#         log.e('TaskAPI', f'暂停任务{task_id}失败: {str(e)}')
#         return jsonify({
#             'success': False,
#             'message': f'暂停任务失败: {str(e)}'
#         }), 500

# @task_bp.route('/api/task/<task_id>/cancel', methods=['POST'])
# def cancel_task(task_id):
#     """取消任务"""
#     log = _G._G_.Log()
    
#     # 解析任务ID，找到相应的设备和任务
#     parts = task_id.split('_')
#     if len(parts) < 2:
#         return jsonify({
#             'success': False,
#             'message': f'任务ID格式错误: {task_id}'
#         }), 400
    
#     deviceId = parts[0]
#     taskName = '_'.join(parts[1:])
    
#     # 获取设备
#     device = deviceMgr.get(deviceId)
#     if not device or not hasattr(device, 'taskMgr'):
#         log.e('TaskAPI', f'取消任务失败: 设备{deviceId}不存在或没有任务管理器')
#         return jsonify({
#             'success': False,
#             'message': f'设备{deviceId}不存在或没有任务管理器'
#         }), 404
    
#     # 取消任务
#     try:
#         appName = "" # 在新的实现中不需要appName参数
#         success = device.taskMgr.cancelTask(appName, taskName)
#         if success:
#             log.i('TaskAPI', f'任务{task_id}已取消')
#             return jsonify({
#                 'success': True,
#                 'message': f'任务{task_id}已取消'
#             })
#         else:
#             return jsonify({
#                 'success': False,
#                 'message': f'取消任务失败'
#             }), 500
#     except Exception as e:
#         log.e('TaskAPI', f'取消任务{task_id}失败: {str(e)}')
#         return jsonify({
#             'success': False,
#             'message': f'取消任务失败: {str(e)}'
#         }), 500

# @task_bp.route('/api/task/<task_id>/life', methods=['PUT'])
# def update_task_life(task_id):
#     """更新任务生命值"""
#     log = _G._G_.Log()
    
#     # 获取请求数据
#     data = request.json
#     if not data or 'life' not in data:
#         return jsonify({
#             'success': False,
#             'message': '请提供生命值'
#         }), 400
    
#     new_life = data['life']
#     try:
#         new_life = int(new_life)
#     except ValueError:
#         return jsonify({
#             'success': False,
#             'message': '生命值必须是整数'
#         }), 400
    
#     # 解析任务ID，找到相应的设备和任务
#     parts = task_id.split('_')
#     if len(parts) < 2:
#         return jsonify({
#             'success': False,
#             'message': f'任务ID格式错误: {task_id}'
#         }), 400
    
#     deviceId = parts[0]
#     taskName = '_'.join(parts[1:])
    
#     # 获取设备
#     device = deviceMgr.get(deviceId)
#     if not device or not hasattr(device, 'taskMgr'):
#         log.e('TaskAPI', f'更新任务生命值失败: 设备{deviceId}不存在或没有任务管理器')
#         return jsonify({
#             'success': False,
#             'message': f'设备{deviceId}不存在或没有任务管理器'
#         }), 404
    
#     # 获取任务
#     task = device.taskMgr.getRunningTask(taskName)
#     if not task:
#         log.e('TaskAPI', f'更新任务生命值失败: 任务{taskName}不存在')
#         return jsonify({
#             'success': False,
#             'message': f'任务{taskName}不存在'
#         }), 404
    
#     # 更新生命值
#     try:
#         task.life = new_life
#         log.i('TaskAPI', f'任务{task_id}生命值已更新为{new_life}')
#         return jsonify({
#             'success': True,
#             'message': f'任务{task_id}生命值已更新为{new_life}'
#         })
#     except Exception as e:
#         log.e('TaskAPI', f'更新任务{task_id}生命值失败: {str(e)}')
#         return jsonify({
#             'success': False,
#             'message': f'更新任务生命值失败: {str(e)}'
#         }), 500 