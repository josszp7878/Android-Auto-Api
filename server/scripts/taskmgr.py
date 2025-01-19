from typing import Dict, List, Optional
from task import Task
from tasktemplate import TaskTemplate
from logger import Log
from CmdMgr import regCmd


class TaskMgr:
    """任务管理器,负责任务的调度和管理"""
    
    _instance = None
    
    @classmethod
    def instance(cls) -> 'TaskMgr':
        """获取单例实例"""
        if not cls._instance:
            cls._instance = TaskMgr()
        return cls._instance
    
    def __init__(self):
        if TaskMgr._instance:
            raise Exception("TaskMgr is a singleton!")
        self.tasks: Dict[str, Task] = {}
        self.templates: Dict[str, TaskTemplate] = {}
        self.runningTask: Optional[Task] = None
        
    def addTemplate(self, templateId: str, template: TaskTemplate) -> bool:
        """添加任务模板"""
        if templateId in self.templates:
            return False
        self.templates[templateId] = template
        return True
        
    def getTemplate(self, templateId: str) -> Optional[TaskTemplate]:
        """获取任务模板"""
        return self.templates.get(templateId)
        
    def createTask(self, appName: str, taskName: str, templateId: str, params: Dict[str, str] = None) -> Optional[Task]:
        """使用模板创建任务"""
        template = self.getTemplate(templateId)
        if not template:
            return None
            
        # 创建新的模板实例并更新参数
        if params:
            template = TaskTemplate(
                taskName=template.taskName,
                startScript=template.startScript,
                doScript=template.doScript,
                endScript=template.endScript,
                params=params
            )
            
        return Task.create(appName, taskName, template)
        
    @regCmd(r'执行任务', r'(?P<taskName>[\w\s]+)')
    def runTask(self, taskName: str) -> bool:
        """执行指定任务"""
        try:
            task = self.get(taskName)
            if not task:
                Log.e(f"未找到任务: {taskName}")
                return False
                
            if self.runningTask:
                Log.e("有其他任务正在运行")
                return False
                
            Log.i(f"开始执行任务: {taskName}")
            self.runningTask = task
            
            try:
                success = task.run()
                if success:
                    Log.i(f"任务 {taskName} 执行成功")
                else:
                    Log.e(f"任务 {taskName} 执行失败")
                return success
            finally:
                self.runningTask = None
                
        except Exception as e:
            Log.ex(e, f"执行任务失败: {taskName}")
            self.runningTask = None
            return False
        
    def add(self, task: Task) -> bool:
        """添加任务"""
        if task.taskName in self.tasks:
            return False
        self.tasks[task.taskName] = task
        return True
        
    def remove(self, taskName: str) -> bool:
        """移除任务"""
        if taskName not in self.tasks:
            return False
        del self.tasks[taskName]
        return True
        
    def get(self, taskName: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(taskName)
        
    def listTasks(self) -> List[str]:
        """获取所有任务名称"""
        return list(self.tasks.keys())
        
    def getRunning(self) -> Optional[Task]:
        """获取当前运行的任务"""
        return self.runningTask 