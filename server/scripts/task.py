from datetime import datetime
from typing import Optional, Dict, Callable
from enum import Enum
from logger import Log
from tasktemplate import TaskTemplate


class TaskState(Enum):
    """任务状态"""
    INIT = "初始化"
    RUNNING = "运行中"
    SUCCESS = "已完成"
    FAILED = "失败"
    CANCELED = "已取消"


class Task:
    """任务包装类,用于管理单个任务的执行过程"""
    
    def __init__(self, appName: str, taskName: str, template: Optional[TaskTemplate] = None):
        self.appName = appName
        self.taskName = taskName
        self.template = template
        self.startTime: Optional[datetime] = None
        self.endTime: Optional[datetime] = None
        self.reward: float = 0.0
        self.state = TaskState.INIT
        self.progress: float = 0.0  # 0-100
        self.onResult: Optional[Callable[[bool], None]] = None

    @classmethod
    def create(cls, appName: str, taskName: str, template: Optional[TaskTemplate] = None) -> 'Task':
        """
        创建任务实例
        Args:
            appName: 应用名称
            taskName: 任务名称
            template: 任务模板
        Returns:
            Task: 任务实例
        """
        return cls(appName, taskName, template)
        
    def start(self) -> bool:
        """开始任务"""
        try:
            self.startTime = datetime.now()
            Log.i(f"开始任务: {self.taskName}")
            fun = self.template.start
            if fun:
                return fun(self)
            return True
        except Exception as e:
            Log.ex(e, f"开始任务失败: {self.taskName}")
            return False
            
    def do(self) -> bool:
        """执行任务"""
        try:
            Log.i(f"执行任务: {self.taskName}")
            fun = self.template.do
            if fun:
                return fun(self)
            return True
            
        except Exception as e:
            Log.ex(e, f"执行任务失败: {self.taskName}")
            return False
            
    def end(self) -> bool:
        """结束任务"""
        try:
            self.endTime = datetime.now()
            Log.i(f"结束任务: {self.taskName}")
            
            fun = self.template.end
            if fun:
                return fun(self)
            return True
            
        except Exception as e:
            Log.ex(e, f"结束任务失败: {self.taskName}")
            return False

    def updateProgress(self, progress: float):
        """更新任务进度"""
        self.progress = min(max(progress, 0), 100)
        
    def run(self, params: Optional[Dict[str, str]] = None) -> bool:
        """运行任务的完整流程"""
        try:
            Log.i(f"运行任务: {self.taskName}")
            self.state = TaskState.RUNNING
            
            if params:
                for key, value in params.items():
                    setattr(self, key, value)
            if not self.start():
                self.state = TaskState.FAILED
                return False
            if not self.do():
                self.state = TaskState.FAILED
                return False
            if not self.end():
                self.state = TaskState.FAILED
                return False
                
            self.updateProgress(100)
            self.state = TaskState.SUCCESS
            Log.i(f"任务 {self.taskName} 执行完成")
            return True
            
        except Exception as e:
            Log.ex(e, f"任务执行异常: {self.taskName}")
            self.state = TaskState.FAILED
            return False 