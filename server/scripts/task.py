from datetime import datetime
from typing import Optional, Dict, Callable, Any
from dataclasses import dataclass
from enum import Enum
from logger import Log


@dataclass
class TaskTemplate:
    """任务模板类,用于定义任务的基本参数和脚本"""
    
    taskName: str  # 任务名称
    alias: str  # 任务别名
    init: Optional[Callable[[Any], None]] = None  # 初始化任务的函数
    start: Optional[Callable[[Any], bool]] = None  # 开始任务的函数
    do: Optional[Callable[[Any], bool]] = None  # 执行任务的函数
    end: Optional[Callable[[Any], bool]] = None  # 结束任务的函数
    params: Dict[str, str] = None  # 脚本参数集合
    
    def __post_init__(self):
        """初始化后处理"""
        if self.params is None:
            self.params = {}
            
    def replaceParams(self, script: str) -> str:
        """替换脚本中的参数"""
        if not script:
            return script
        result = script
        for key, value in self.params.items():
            result = result.replace(f"${key}", str(value))
        return result 

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
        self.onResult: Optional[Callable[[TaskState], None]] = None        
        # 如果有模板,初始化检查器
        if self.template:
            if self.template.init:
                self.template.init(self)
    
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
            self.state = TaskState.RUNNING
            fun = self.template.do
            if fun:
                return fun(self)
        except Exception as e:
            Log.ex(e, f"执行任务失败: {self.taskName}")
            self.state = TaskState.FAILED
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
            self.state = TaskState.FAILED
            return False

    def updateProgress(self, progress: float):
        """更新任务进度"""
        self.progress = min(max(progress, 0), 100)
        # 发送进度更新事件
        try:
            from client import client
            if client:
                client.emit('C2S_UpdateTask', {
                    'app_name': self.appName,
                    'task_name': self.taskName,
                    'progress': self.progress
                })
        except Exception as e:
            Log.ex(e, '发送进度更新失败')
        

    def run(self, params: Optional[Dict[str, str]] = None) -> TaskState:
        """运行任务的完整流程"""
        try:
            Log.i(f"运行任务: {self.taskName}")
            self.state = TaskState.RUNNING
            if params:
                for key, value in params.items():
                    setattr(self, key, value)                    
            if not self.start():
                self.state = TaskState.FAILED
            while self.state == TaskState.RUNNING:
                if self.state == TaskState.CANCELED:
                    raise Exception("任务已取消")
                self.do()

            if not self.end():
                self.state = TaskState.FAILED
            self.state = TaskState.SUCCESS
            if self.onResult:
                self.onResult(self.state)
            Log.i(f"任务 {self.taskName} 执行完成")
            self.updateProgress(100)
            return self.state
        except Exception as e:
            Log.ex(e, f"任务执行异常: {self.taskName}")
        return self.state

    def stop(self):
        if self.state == TaskState.RUNNING:
            self.state = TaskState.CANCELED
            Log.i(f"任务 {self.taskName} 已停止")
            # 发送任务停止消息
            try:
                from client import client
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
