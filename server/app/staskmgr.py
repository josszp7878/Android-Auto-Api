from typing import Dict, Optional
from .stask import STask, STaskState
from .database import commit  # 使用统一的 db 实例
from scripts.logger import Log
from datetime import datetime

class STaskMgr:
    """服务端任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, STask] = {}  # 只存储运行中的任务
        self._loadTasksFromDB()

    def _loadTasksFromDB(self):
        """从数据库加载任务"""
        try:
            running_tasks = STask.query.filter_by(state=STaskState.RUNNING).all()
            for task in running_tasks:
                task_id = self.getTaskId(task.deviceId, task.appName, task.taskName)
                self.tasks[task_id] = task
            Log.i(f"从数据库加载了 {len(running_tasks)} 个运行中的任务")
        except Exception as e:
            Log.ex(e, "加载任务数据失败")

    def getTaskId(self, deviceId: str, appName: str, taskName: str) -> str:
        """生成任务唯一标识"""
        return f"{deviceId}_{appName}_{taskName}"

    def getTask(self, deviceId: str, appName: str, taskName: str, create: bool = False) -> Optional[STask]:
        """获取任务,如果缓存中没有则从数据库加载"""
        task_id = self.getTaskId(deviceId, appName, taskName)
        task = self.tasks.get(task_id)
        # Log.i(f'1任务: {task}')
        if not task:
            # 从数据库加载运行中的任务
            task = STask.query.filter_by(
                deviceId=deviceId,
                appName=appName,
                taskName=taskName,
                state=STaskState.RUNNING
            ).first()
            # Log.i(f'2任务: {task} create:{create}')
            if task is None and create:
                task = STask(
                    deviceId=deviceId,
                    appName=appName,
                    taskName=taskName,
                    progress=0.0,
                    time=datetime.now()
                )
                commit(task, True)
                Log.i(f"新建任务 {task.taskName} 已添加到数据库")
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
