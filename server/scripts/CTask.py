from datetime import datetime
from typing import Optional, Dict, Callable, Any
from tools import TaskState, Tools
from logger import Log
import time



class CTask:
    """任务包装类,用于管理单个任务的执行过程"""
    
    def __init__(self, appName: str, taskName: str):
        self.appName = appName
        self.taskName = taskName
        self.startTime: Optional[datetime] = None
        self.reward: float = 0.0
        self.state = TaskState.RUNNING
        self.progress: float = 0.0  # 0-100
        self.onResult: Optional[Callable[[TaskState], None]] = None        
    
    @classmethod
    def create(cls, appName: str, taskName: str) -> 'CTask':
        """
        创建任务实例
        Args:
            appName: 应用名称
            taskName: 任务名称
            template: 任务模板
        Returns:
            Task: 任务实例
        """
        return cls(appName, taskName)
        
    @property
    def template(self) -> Any:
        if not hasattr(self, '_template'):
            from TaskTemplate import TaskTemplate
            self._template = TaskTemplate.getTemplate(self.taskName)
        return self._template
    
        
    def start(self) -> bool:
        """开始任务"""
        try:
            self.startTime = datetime.now()
            # Log.i(f"开始任务: {self.taskName}")
            fun = self.template.start
            if fun:
                return fun(self)
            return True
        except Exception as e:
            Log.ex(e, f"开始任务失败: {self.taskName}")
            return False
            
            
    def update(self, progress: float):
        """更新任务进度"""
        # 确保进度在0-1之间
        self.progress = min(max(progress, 0), 1)
        # 发送进度更新事件
        from CClient import client
        if client:
            client.emit('C2S_UpdateTask', {
                'app_name': self.appName,
                'task_name': self.taskName,
                'progress': self.progress  # 保持0-1的值
            })

    def getScore(self) -> int:
        """获取任务得分"""
        return 100

    def run(self, params: Optional[Dict[str, str]] = None):
        """运行任务的完整流程"""
        try:
            Log.i(f"运行任务: {self.taskName}")
            self.state = TaskState.RUNNING
            if params:
                for key, value in params.items():
                    setattr(self, key, value)                    
            if not self.start():
                self.cancel()
                return self.state
            curTime = datetime.now()
            pastTime = 0
            while pastTime < self.duration:
                if not self.template.do(self):
                    self.state = TaskState.FAILED
                    return self.state
                time.sleep(self.interval)
                pastTime = (datetime.now() - curTime).total_seconds()
                self.update(pastTime/self.duration)                
            # 只有正常完成的任务才执行end
            if self.state != TaskState.PAUSED:
               result = self.end()
               return result if result else TaskState.FAILED
            return self.state
        except Exception as e:
            Log.ex(e, f"任务执行异常: {self.taskName}")
            self.state = TaskState.FAILED
            return self.state

    def end(self) -> bool:
        result = self.template.end(self)
        # 发送任务结束消息,带上执行结果
        from CClient import client
        if client:
            client.emit('C2S_TaskEnd', {
                'app_name': self.appName,
                'task_name': self.taskName,
                'result': result,  # 添加执行结果
                'score': result and self.getScore() or 0
            })
        return result
    
    def stop(self):
        """停止任务"""
        if self.state == TaskState.RUNNING:
            self.state = TaskState.PAUSED
            Log.i(f"任务 {self.taskName} 已暂停")
            # 发送任务停止消息
            try:
                from CClient import client
                if client:
                    client.emit('C2S_StopTask', {
                        'app_name': self.appName,
                        'task_name': self.taskName
                    })
            except Exception as e:
                Log.ex(e, '发送任务停止消息失败')

    def setScore(self, score: int):
        """设置任务得分"""
        self.score = score
        Log.i(f"任务 {self.taskName} 得分: {self.score}")

    def cancel(self) -> bool:
        """取消任务"""
        try:
            if self.state == TaskState.RUNNING:
                self.state = TaskState.CANCELLED
                Log.i(f"任务 {self.taskName} 已取消")
            # 发送取消事件到服务器
            from CClient import client
            if client:
                client.emit('C2S_CancelTask', {
                    'app_name': self.appName,
                    'task_name': self.taskName
                })
                Log.i(f"已发送取消任务请求: {self.appName}/{self.taskName}")
            from CTaskMgr import taskMgr
            taskMgr.tasks.pop(Tools._toTaskId(self.appName, self.taskName))
            return True
        except Exception as e:
            Log.ex(e, "取消任务失败")
            return False
