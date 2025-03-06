from typing import Optional, List
from STask import STask
import _Log
from datetime import datetime, date, time
from Database import db  # 导入单例的db实例
from _Tools import TaskState, _Tools
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError

class STaskMgr:
    """设备任务管理器"""
    
    def __init__(self, device):
        self._device = device
        self._date = date.today()
        self._current_task = None
        self.tasks = []  # 任务列表，按创建时间排序
        self._currentApp = None  # 当前应用名称

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
                    _Log.Log.e(f"任务 {task.taskName} 已完成，无法设置为当前任务")
                    return
                # 如果任务未完成，直接设置
                self._current_task = task            
            # 刷新任务状态
            if self._current_task:
                STask.refresh(self._current_task)
            
        except Exception as e:
            _Log.Log.ex(e, "设置当前任务失败")
    
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

    @property
    def currentApp(self) -> str:
        """获取当前应用名称"""
        return self._currentApp
        
    @currentApp.setter
    def currentApp(self, value: str):
        """设置当前应用名称"""
        if value != self._currentApp:
            self._currentApp = value
            _Log.Log.i(f"当前应用切换为: {value}")

    @classmethod
    def getTodayScore(cls):
        """获取今日任务得分"""
        try:
            today_start = datetime.combine(datetime.now().date(), time.min)
            today_end = datetime.combine(datetime.now().date(), time.max)
            
            today_tasks = db.session.query(STask).filter(
                STask.time.between(today_start, today_end)
            ).all()
            
            return sum(task.score for task in today_tasks if task.score)
            
        except Exception as e:
            _Log.Log.ex(e, '获取今日任务得分失败')
            return 0

    def init(self,device_id:str):
        # Log.i(f"初始化任务管理器########: {device_id}")
        self._device.id = device_id

    def _getTasks(self, appName: str, taskName: str, notCompleted: bool = False) -> List[STask]:
        try:
            taskId = _Tools.toTaskId(appName, taskName)
            tasks = [t for t in self.tasks if t.taskId == taskId]
            if notCompleted:
                tasks = [t for t in tasks if not t.completed]
            return tasks
        except Exception as e:
            _Log.Log.ex(e, f'获取任务失败: {taskId}')
            return []

    def getRunningTask(self, appName: str, taskName: str, create: bool = False) -> Optional[STask]:
        """获取运行中的任务,如果没有且create=True则创建新任务
        同一个应用的同名任务可以有多个实例
        """
        try:
            # 更新当前应用
            self._currentApp = appName
            
            # 从缓存中查找该应用下的所有运行中任务
            running_tasks = [
                t for t in self.tasks 
                if (t.appName == appName and 
                    t.taskName == taskName and 
                    t.state in [TaskState.RUNNING.value, TaskState.PAUSED.value])
            ]
            
            if running_tasks:
                # 返回最新创建的任务
                return running_tasks[-1]
                
            # 从数据库查询该应用下的运行中任务
            tasks = STask.query.filter(
                STask.deviceId == self._device.id,
                STask.appName == appName,
                STask.taskName == taskName,
                STask.state.in_([
                    TaskState.RUNNING.value,
                    TaskState.PAUSED.value
                ])
            ).order_by(STask.time.desc()).all()
            
            if tasks:
                # 添加到缓存并返回最新的任务
                for task in tasks:
                    if task not in self.tasks:
                        self.tasks.append(task)
                return tasks[0]
                
            # 没找到任务且需要创建
            if create:
                task = STask(self._device.id, appName, taskName)
                db.session.add(task)
                db.session.commit()
                self.tasks.append(task)
                _Log.Log.i(f"设备 {self._device.id} 创建新任务: {appName}/{taskName}")
                return task
            
            return None
            
        except Exception as e:
            _Log.Log.ex(e, f'获取任务失败: {appName}/{taskName}')
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
            _Log.Log.ex(e, '获取任务统计失败')
            return {'date': self._date.strftime('%Y-%m-%d'), 'total': 0, 'unfinished': 0}

    def startTask(self, task: STask) -> bool:
        """启动任务"""
        try:
            # 获取运行中的任务
            if task:
                task.start()
                self.currentTask = task
                self.currentApp = task.appName
                return True
            return False
        except Exception as e:
            _Log.Log.ex(e, f'启动任务失败: {appName}/{taskName}')
            return False

    def pauseTask(self, appName: str, taskName: str) -> bool:
        """暂停任务"""
        try:
            task = self.getRunningTask(appName, taskName)
            if task:
                task.pause()
                return True
            else:
                _Log.Log.e(f'任务不存在: {appName}/{taskName}')
                return False
        except Exception as e:
            _Log.Log.ex(e, f'暂停任务失败: {appName}/{taskName}')
            return False
        
    def endTask(self, appName: str, taskName: str, score: int, result: str) -> bool:
        """结束任务"""
        try:
            task = self.getRunningTask(appName, taskName)
            if task:
                task.end({
                    'score': score,
                    'result': result
                })
                if self.currentTask == task:
                    self.currentTask = None
                return True
            else:
                _Log.Log.e(f'任务不存在: {appName}/{taskName}')
                return False
        except Exception as e:
            _Log.Log.ex(e, f'结束任务失败: {appName}/{taskName}')
            return False
    def stopTask(self, appName: str, taskName: str) -> bool:
        """停止任务"""
        try:
            task = self.getRunningTask(appName, taskName)
            if task:
                task.stop()
                return True
            else:
                _Log.Log.e(f'任务不存在: {appName}/{taskName}')
                return False
        except Exception as e:
            _Log.Log.ex(e, f'停止任务失败: {appName}/{taskName}')
            return False

    def cancelTask(self, appName: str, taskName: str) -> bool:
        """取消任务"""
        try:
            task = self.getRunningTask(appName, taskName)
            if task:
                task.cancel()                
                self.tasks.remove(task)
                if self.currentTask == task:
                    self.currentTask = None
                return True
            else:
                _Log.Log.e(f'任务不存在: {appName}/{taskName}')
                return False
        except Exception as e:
            _Log.Log.ex(e, f'取消任务失败: {appName}/{taskName}')
            return False
        
    def updateTask(self, appName: str, taskName: str, progress: int) -> bool:
        """更新任务进度"""
        try:
            task = self.getRunningTask(appName, taskName)
            if task:
                task.update(progress)
                return True
            else:
                _Log.Log.e(f'任务不存在: {appName}/{taskName}')
                return False
        except Exception as e:
            _Log.Log.ex(e, f'更新任务进度失败: {appName}/{taskName}/{progress}')
            return False

@contextmanager
def session_scope():
    """提供事务范围的会话，自动处理提交/回滚和异常"""
    try:
        yield db.session
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        _Log.Log.ex(e, "数据库事务执行失败")
        raise
    finally:
        db.session.remove()
