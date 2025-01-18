from datetime import datetime
from typing import Optional
from tools import LogD, LogE

class Task:
    """任务包装类,用于管理单个任务的执行过程"""
    def __init__(self, appName: str, taskName: str):
        self.appName = appName
        self.taskName = taskName
        self.startTime: Optional[datetime] = None
        self.endTime: Optional[datetime] = None
        self.reward: float = 0.0
        
    @classmethod
    def create(cls, appName: str, taskName: str) -> 'Task':
        """
        创建任务实例
        Args:
            appName: 应用名称
            taskName: 任务名称
        Returns:
            Task: 任务实例
        """
        return cls(appName, taskName)
        
    def start(self) -> bool:
        """
        开始任务
        Returns:
            bool: 是否成功开始任务
        """
        try:
            self.startTime = datetime.now()
            LogD("Task", f"Enter task: {self.taskName}")
            return True
        except Exception as e:
            LogE("Task", f"Failed to enter task: {str(e)}")
            return False
            
    def do(self) -> bool:
        """
        执行任务
        Returns:
            bool: 是否成功执行任务
        """
        try:
            LogD("Task", f"Doing task: {self.taskName}")
            return True
        except Exception as e:
            LogE("Task", f"Failed to do task: {str(e)}")
            return False
            
    def end(self) -> bool:
        """
        结束任务
        Returns:
            bool: 是否成功结束任务
        """
        try:
            self.endTime = datetime.now()
            LogD("Task", f"End task: {self.taskName}")
            return True
        except Exception as e:
            LogE("Task", f"Failed to end task: {str(e)}")
            return False 