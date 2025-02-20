from typing import Dict, Optional
from .STask import STask
from scripts.tools import TaskState
from .database import commit
from scripts.logger import Log
from datetime import datetime
from flask import current_app
from scripts.tools import Tools

class STaskMgr:
    """设备任务管理器"""
    
    def __init__(self):
        self.tasks = {}  # taskId -> STask
        self._current_task = None  # 私有变量存储当前任务

    @property
    def currentTask(self) -> Optional[STask]:
        """获取当前任务"""
        return self._current_task

    @currentTask.setter
    def currentTask(self, task: Optional[STask]):
        """设置当前任务，并通知界面更新
        Args:
            task: 要设置的任务，None表示清除当前任务
        """
        if not task:
            # 如果任务为空，则获取最近的未结束任务
            task = self.getRunningTask(self.currentTask.appName, self.currentTask.taskName)
        self._current_task = task
        Log.i(f"设置当前任务: {task}")
        STask.refresh(task)
        
    def init(self,device_id:str):
        self.device_id = device_id
        self._load()

    def _load(self):
        """从数据库加载该设备的未完成任务"""
        try:
            # 加载所有未完成的任务（运行中或暂停的）
            unfinished_tasks = STask.query.filter(
                STask.deviceId == self.device_id,
                STask.state.in_([TaskState.RUNNING.value, TaskState.PAUSED.value])
            ).order_by(STask.time.desc()).all()
            
            for task in unfinished_tasks:
                task_id = Tools._toTaskId(task.appName, task.taskName)
                self.tasks[task_id] = task
                
            # 设置最近的任务为当前任务
            if unfinished_tasks:
                self.currentTask = unfinished_tasks[0]
                # 设置为暂停状态
                self.currentTask.state = TaskState.PAUSED.value
                commit(self.currentTask)
                
            Log.i(f"设备 {self.device_id} 加载了 {len(unfinished_tasks)} 个未完成任务")
        except Exception as e:
            Log.ex(e, f'加载设备 {self.device_id} 的任务失败')


    def _getRunningTask(self, task_id: str) -> Optional[STask]:
        """根据任务ID查找未结束的任务"""
        task = self.tasks.get(task_id)
        Log.i(f"当前任务数量: {len(self.tasks)}")
        if task and task.state in [TaskState.RUNNING.value, TaskState.PAUSED.value]:
            return task
        return None

    def getRunningTask(self, appName: str, taskName: str, create: bool = False) -> Optional[STask]:
        """获取正在运行的任务,如果没有且create=True则创建新任务
        
        Args:
            appName: 应用名称
            taskName: 任务名称
            create: 是否在任务不存在时创建新任务
            
        Returns:
            STask: 任务实例，如果没有找到且不创建则返回 None
        """
        task_id = Tools._toTaskId(appName, taskName)
        task = self._getRunningTask(task_id)
        Log.i(f"获取未结束的任务: {task_id}, 结果: {task}")
        if task:
            return task
        with current_app.app_context():
            # 只查询运行中或暂停的任务
            task = STask.query.filter(
                STask.deviceId == self.device_id,
                STask.appName == appName,
                STask.taskName == taskName,
                STask.state.in_([TaskState.RUNNING.value, TaskState.PAUSED.value])
            ).order_by(STask.time.desc()).first()  # 取最新的未结束任务
            
            if task is None and create:
                # 创建新任务
                task = STask(self.device_id, appName, taskName)
                if task:
                    self.tasks[task_id] = task
                    commit(task)
                    Log.i(f"设备 {self.device_id} 创建新任务: {appName}/{taskName}")
            if task:
                # 缓存已存在的任务
                self.tasks[task_id] = task
        return task

    def getCurrentTask(self) -> Optional[dict]:
        """获取当前任务信息"""
        if self.currentTask:
            return {
                'taskName': self.currentTask.taskName,
                'appName': self.currentTask.appName,
                'progress': self.currentTask.progress,
                'state': self.currentTask.state,
                'expectedScore': self.currentTask.expectedScore
            }
        return None
    
    def removeTask(self, task:STask):
        """删除任务"""
        if task:
            task_id = Tools._toTaskId(task.appName, task.taskName)
            self.tasks.pop(task_id, None)
            task.cancel()