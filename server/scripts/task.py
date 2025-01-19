from datetime import datetime
from typing import Optional
from logger import Log
from tasktemplate import TaskTemplate


class Task:
    """任务包装类,用于管理单个任务的执行过程"""
    
    def __init__(self, appName: str, taskName: str, template: Optional[TaskTemplate] = None):
        self.appName = appName
        self.taskName = taskName
        self.template = template
        self.startTime: Optional[datetime] = None
        self.endTime: Optional[datetime] = None
        self.reward: float = 0.0

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
            
            # 如果有模板和开始脚本,则执行
            if self.template and self.template.startScript:
                script = self.template.replaceParams(self.template.startScript)
                return exec(script)
            return True
            
        except Exception as e:
            Log.ex(e, f"开始任务失败: {self.taskName}")
            return False
            
    def do(self) -> bool:
        """执行任务"""
        try:
            Log.i(f"执行任务: {self.taskName}")
            
            # 如果有模板和执行脚本,则执行
            if self.template and self.template.doScript:
                script = self.template.replaceParams(self.template.doScript)
                return exec(script)
            return True
            
        except Exception as e:
            Log.ex(e, f"执行任务失败: {self.taskName}")
            return False
            
    def end(self) -> bool:
        """结束任务"""
        try:
            self.endTime = datetime.now()
            Log.i(f"结束任务: {self.taskName}")
            
            # 如果有模板和结束脚本,则执行
            if self.template and self.template.endScript:
                script = self.template.replaceParams(self.template.endScript)
                return exec(script)
            return True
            
        except Exception as e:
            Log.ex(e, f"结束任务失败: {self.taskName}")
            return False 

    def run(self) -> bool:
        """运行任务的完整流程"""
        try:
            Log.i(f"运行任务: {self.taskName}")
            
            # 按顺序执行任务流程
            if not self.start():
                Log.e("任务开始失败")
                return False
                
            if not self.do():
                Log.e("任务执行失败")
                return False
                
            if not self.end():
                Log.e("任务结束失败")
                return False
                
            Log.i(f"任务 {self.taskName} 执行完成")
            return True
            
        except Exception as e:
            Log.ex(e, f"任务执行异常: {self.taskName}")
            return False 