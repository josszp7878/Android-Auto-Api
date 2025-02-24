from typing import Optional, List
from .STask import STask
from scripts.logger import Log
from datetime import datetime, date
from scripts.tools import Tools
from sqlalchemy import func
from .Database import db  # 导入单例的db实例
from scripts.tools import TaskState

class STaskMgr:
    """设备任务管理器"""
    
    def __init__(self, device):
        self._device = device
        self._date = date.today()
        self._current_task = None
        self.tasks = []  # 改为列表存储，按创建时间排序

    @property
    def currentTask(self) -> Optional[STask]:
        """获取当前任务"""
        return self._current_task
    @currentTask.setter
    def currentTask(self, task: Optional[STask]):
        """设置当前任务"""
        try:
            if task is None:
                # 如果当前有任务，尝试获取同类型的下一个未完成任务
                if self._current_task:
                    next_task = self.getRunningTask(
                        self._current_task.appName, 
                        self._current_task.taskName, 
                        create=False
                    )
                    self._current_task = next_task            
            else:
                if task.completed:
                    Log.e(f"任务 {task.taskName} 已完成，无法设置为当前任务")
                    return
                # 如果任务未完成，直接设置
                self._current_task = task            
            # 刷新任务状态
            if self._current_task:
                STask.refresh(self._current_task)
            
        except Exception as e:
            Log.ex(e, "设置当前任务失败")
    
    @property
    def date(self):
        return self._date
        
    @date.setter
    def date(self, value):
        """设置任务管理器日期,并刷新设备信息"""
        self._date = value
        # 日期变更后刷新设备信息
        if self._device:
            self._device.refresh()

    def getTodayScore(self) -> int:
        """获取今日任务得分"""
        try:
            today = datetime.now().date()
            today_tasks = STask.query.filter(
                STask.deviceId == self._device.id,
                STask.time >= today
            ).all()
            return sum(task.score for task in today_tasks if task.score is not None)
        except Exception as e:
            Log.ex(e, "获取今日任务得分失败")
            return 0

    def init(self,device_id:str):
        Log.i(f"初始化任务管理器########: {device_id}")
        self._device.id = device_id

    def _getTasks(self, appName: str, taskName: str, notCompleted: bool = False) -> List[STask]:
        try:
            taskId = Tools._toTaskId(appName, taskName)
            tasks = [t for t in self.tasks if t.taskId == taskId]
            if notCompleted:
                tasks = [t for t in tasks if not t.completed]
            return tasks
        except Exception as e:
            Log.ex(e, f'获取任务失败: {taskId}')
            return []

    def getRunningTask(self, appName: str, taskName: str, create: bool = False) -> Optional[STask]:
        """获取运行中的任务,如果没有且create=True则创建新任务"""
        try:
            # 先从缓存中查找未完成的同类任务
            tasks = self._getTasks(appName, taskName, True)
            if tasks:
                # 不需要重新add，直接返回
                return tasks[0]
                
            # 从数据库查询未完成的同类任务
            task = STask.query.filter(
                STask.deviceId == self._device.id,
                STask.appName == appName,
                STask.taskName == taskName,
                STask.state.in_([
                    TaskState.RUNNING.value,
                    TaskState.PAUSED.value
                ])
            ).order_by(STask.time.desc()).first()
            
            if task:
                Log.d("找到了任务，添加到缓存并返回")
                # 查询出的对象已经被session跟踪，不需要重新add
                self.tasks.append(task)
                return task
                
            # 没找到任务且需要创建
            if create:
                task = STask(self._device.id, appName, taskName)
                # 只有新创建的任务需要add
                db.session.add(task)
                db.session.commit()
                self.tasks.append(task)
                Log.i(f"设备 {self._device.id} 创建新任务: {appName}/{taskName}")
                return task
            
            return None
            
        except Exception as e:
            Log.ex(e, f'获取任务失败: {appName}/{taskName}')
            return None
        
    def getTaskStats(self) -> dict:
        """获取任务统计信息"""
        try:
            total = len(self.tasks)
            unfinished = len([t for t in self.tasks if not t.completed])
            return {
                'date': self._date.strftime('%Y-%m-%d'),
                'total': total,
                'unfinished': unfinished
            }
        except Exception as e:
            Log.ex(e, '获取任务统计失败')
            return {'date': self._date.strftime('%Y-%m-%d'), 'total': 0, 'unfinished': 0}