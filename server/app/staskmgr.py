from typing import Dict, Optional
from .stask import STask, STaskState
from .database import db  # 使用统一的 db 实例
from scripts.logger import Log
from . import socketio  # 直接从当前包导入 socketio

class STaskMgr:
    """服务端任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, STask] = {}  # 只存储运行中的任务
        self._load_running_tasks()

    def _load_running_tasks(self):
        """加载所有运行中的任务"""
        try:
            running_tasks = STask.query.filter_by(
                state=STaskState.RUNNING
            ).all()
            for task in running_tasks:
                task_id = self.getTaskId(
                    task.deviceId, 
                    task.appName, 
                    task.taskName
                )
                self.tasks[task_id] = task
            Log.i(f"加载了 {len(running_tasks)} 个运行中的任务")
        except Exception as e:
            Log.ex(e, "加载运行中的任务失败")

    def getTaskId(self, deviceId: str, appName: str, taskName: str) -> str:
        """生成任务唯一标识"""
        return f"{deviceId}_{appName}_{taskName}"

    def getTask(self, deviceId: str, appName: str, taskName: str) -> Optional[STask]:
        """获取任务,如果缓存中没有则从数据库加载"""
        task_id = self.getTaskId(deviceId, appName, taskName)
        task = self.tasks.get(task_id)
        
        if not task:
            # 从数据库加载运行中的任务
            task = STask.query.filter_by(
                deviceId=deviceId,
                appName=appName,
                taskName=taskName,
                state=STaskState.RUNNING
            ).first()
            
            if task:
                self.tasks[task_id] = task
        
        return task

    def getDeviceCurrentTask(self, device_id: str) -> Optional[dict]:
        """获取设备当前任务"""
        try:
            # 查找该设备的运行中任务
            for task in self.tasks.values():
                if task.deviceId == device_id:
                    return {
                        'taskName': task.taskName,
                        'progress': task.progress,
                        'expectedScore': task.expectedScore
                    }
            return None
        except Exception as e:
            Log.ex(e, f'获取设备{device_id}当前任务失败')
            return None

    def startTask(self, device_id: str, app_name: str, task_name: str, sequence: int = 0):
        """启动任务,如果存在未完成的任务则继续执行"""
        try:
            # 先查找是否有未完成的任务
            task = self.getTask(device_id, app_name, task_name)
            if task:
                Log.i(f"继续执行任务: {task_name}, 进度: {task.progress}%")
                return task

            # 没有未完成任务,创建新任务
            task = STask(
                deviceId=device_id,
                appName=app_name,
                taskName=task_name,
                sequence=sequence
            )
            task.start()
            task_id = self.getTaskId(device_id, app_name, task_name)
            self.tasks[task_id] = task
            Log.i(f'启动任务: {device_id}/{app_name}/{task_name}')
             # 发送进度更新事件
            socketio.emit('S2B_StartTask', {
                'deviceId': device_id,
                'task': {
                    'taskName': task.taskName,
                    'appName': task.appName,
                    'expectedScore': task.expectedScore
                }
            }, broadcast=True)
            return task
        except Exception as e:
            Log.ex(e, f'启动任务失败: {task_name}')
            return None

    def updateTaskProgress(
        self, 
        deviceId: str, 
        appName: str,
        taskName: str, 
        progress: float, 
    ):
        """更新任务进度"""
        try:
            task = self.getTask(deviceId, appName, taskName)
            Log.i(f'更新任务进度: {deviceId}/{appName}/{taskName}/{progress}')
            if task:
                task.updateProgress(progress)
                # 发送进度更新事件
                socketio.emit('S2B_UpdateTask', {
                    'deviceId': deviceId,
                    'task': {
                        'taskName': task.taskName,
                        'progress': task.progress,
                    }
                }, broadcast=True)
                return True
            return False
        except Exception as e:
            Log.ex(e, f"更新任务进度失败: {taskName}")
            return False

    def completeTask(self, deviceId: str, appName: str, taskName: str, score: int):
        """完成任务"""
        try:
            task = self.getTask(deviceId, appName, taskName)
            if task:
                task.complete(score)
                # 从缓存中移除已完成的任务
                task_id = self.getTaskId(deviceId, appName, taskName)
                self.tasks.pop(task_id, None)
                db.session.commit()
        except Exception as e:
            Log.ex(e, f"完成任务失败: {taskName}")

    def cancelTask(self, deviceId: str, appName: str, taskName: str):
        """取消任务"""
        try:
            task = self.getTask(deviceId, appName, taskName)
            if task:
                task.cancel()
                # 从缓存中移除已取消的任务
                task_id = self.getTaskId(deviceId, appName, taskName)
                self.tasks.pop(task_id, None)
                db.session.commit()
        except Exception as e:
            Log.ex(e, f"取消任务失败: {taskName}")

    def resumeTask(self, deviceId: str, appName: str, taskName: str) -> Optional[dict]:
        """恢复任务执行"""
        try:
            task = self.getTask(deviceId, appName, taskName)
            if task:
                return task.resume()
            return None
        except Exception as e:
            Log.ex(e, f"恢复任务失败: {taskName}")
            return None 