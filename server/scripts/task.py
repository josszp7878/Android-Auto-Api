from datetime import datetime
from typing import Optional, Dict, Callable, List
from enum import Enum
from logger import Log
from tasktemplate import TaskTemplate
from checker import Checker


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
        
        # 添加检查列表
        self.startCheckList: List[Checker] = []
        self.doCheckList: List[Checker] = []
        self.endCheckList: List[Checker] = []
        
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
        
    def addStartCheck(self, checker: Checker) -> 'Task':
        """添加启动阶段检查器"""
        self.startCheckList.append(checker)
        return self
        
    def addDoCheck(self, checker: Checker) -> 'Task':
        """添加执行阶段检查器"""
        self.doCheckList.append(checker)
        return self
        
    def addEndCheck(self, checker: Checker) -> 'Task':
        """添加结束阶段检查器"""
        self.endCheckList.append(checker)
        return self
        
    def _runChecks(self, checkers: List[Checker]) -> bool:
        """执行检查列表
        Returns:
            bool: 所有检查都通过返回True,否则返回False
        """
        if not checkers:
            return True
            
        ret = True
        for checker in checkers:
            if not checker.check():
                ret = False
        return ret
        
    def start(self) -> bool:
        """开始任务"""
        try:
            self.startTime = datetime.now()
            Log.i(f"开始任务: {self.taskName}")
            self.state = TaskState.RUNNING
            
            # 执行启动阶段检查
            if not self._runChecks(self.startCheckList):
                Log.w(f"任务{self.taskName}启动检查未通过")
                return False
                
            fun = self.template.start
            if fun:
                return fun(self)
            return True
        except Exception as e:
            Log.ex(e, f"开始任务失败: {self.taskName}")
            self.state = TaskState.FAILED
            return False
            
    def do(self) -> bool:
        """执行任务"""
        try:
            Log.i(f"执行任务: {self.taskName}")
            self.state = TaskState.RUNNING
            while True:
                # 执行任务阶段检查
                fun = self.template.do
                if fun:
                    fun(self)
                if self._runChecks(self.doCheckList):
                    Log.w(f"任务{self.taskName}执行检查通过")
                    break              
            return True
            
        except Exception as e:
            Log.ex(e, f"执行任务失败: {self.taskName}")
            self.state = TaskState.FAILED
            return False
            
    def end(self) -> bool:
        """结束任务"""
        try:
            self.endTime = datetime.now()
            Log.i(f"结束任务: {self.taskName}")
            
            # 执行结束阶段检查
            if not self._runChecks(self.endCheckList):
                Log.w(f"任务{self.taskName}结束检查未通过")
                return False
                
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