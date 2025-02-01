from typing import Dict, List, Optional, Tuple, Callable
from task import Task, TaskState, TaskTemplate
from logger import Log
from CmdMgr import regCmd
import threading


class TaskMgr:
    """任务管理器,负责任务的调度和管理"""
    
    _instance = None
    
    @classmethod
    def instance(cls) -> 'TaskMgr':
        if not cls._instance:
            cls._instance = TaskMgr()
        return cls._instance
    
    def __init__(self):
        if TaskMgr._instance:
            raise Exception("TaskMgr is a singleton!")
        self.tasks: Dict[str, Task] = {}  # taskId -> Task
        self.templates: List[TaskTemplate] = []  # 任务模板列表
        
    def regTask(self, alias: str):
        """任务注册装饰器
        Args:
            alias: 任务别名
        Example:
            @taskManager.regTask("广告")
            def adTask():
                def init():
                    # 初始化检查器
                    return init_func
                    
                def start():
                    Log.i("开始广告任务")
                    return openApp("${appName}")
                    
                def do():
                    time.sleep(${adDuration})
                    return True
                    
                def end():
                    return click("${closeBtn}")
                    
                return start, do, end, init  # 可选返回init函数
        """
        def decorator(func: Callable[[dict], Tuple[Callable[[Task], bool], ...]]):
            # 获取函数名作为模板ID
            templateId = func.__name__
            
            # 预先调用 func 以获取返回的函数元组
            funcs = func({})
            if len(funcs) >= 4:
                startFunc, doFunc, endFunc, initFunc = funcs[:4]
            else:
                startFunc, doFunc, endFunc = funcs[:3]
                initFunc = None
            
            # 查找模板名为templateId的模板
            template = next((t for t in self.templates if t.taskName == templateId), None)
            if not template:
                # 创建模板
                template = TaskTemplate(
                    taskName=templateId,
                    alias=alias
                )            
                # 添加到模板列表
                self.templates.append(template)
            
            # 设置模板函数
            template.start = startFunc
            template.do = doFunc
            template.end = endFunc
            template.init = initFunc  # 设置init函数
            return func
            # @wraps(func)
            # def wrapper(params: dict):
            #     # 这里不再需要注册模板，只需执行任务逻辑
            #     return func(params)
            
            # return wrapper
        return decorator
    
    def getTemplate(self, templateId: str) -> Optional[TaskTemplate]:
        """获取任务模板,支持模板ID或别名"""
        for template in self.templates:
            if templateId in (template.taskName, template.alias):
                return template
        return None
        
    def addTemplate(self, template: TaskTemplate) -> bool:
        """添加任务模板"""
        # 检查是否已存在相同名称或别名的模板
        for t in self.templates:
            if template.taskName == t.taskName or template.alias == t.alias:
                return False
        self.templates.append(template)
        return True
        
    def createTask(self, appName: str, templateId: str, params: Dict[str, str] = None) -> Optional[Task]:
        """使用模板创建任务"""
        template = self.getTemplate(templateId)
        if not template:
            return None
            
        if params:
            template = TaskTemplate(
                taskName=template.taskName,
                alias=template.alias,
                start=template.start,
                do=template.do,
                end=template.end,
                params=params
            )
            
        return Task.create(appName, templateId, template)
        
    def _getTaskId(self, appName: str, templateId: str) -> str:
        """生成任务唯一标识"""
        return f"{appName}_{templateId}"
        
    def _findSameTypeTask(self, appName: str, templateId: str) -> Optional[Task]:
        """查找相同类型的任务(相同应用名和模板)"""
        taskId = self._getTaskId(appName, templateId)
        return self.tasks.get(taskId)
        
    def _runTask(self, appName: str, templateId: str, params: Optional[Dict[str, str]] = None, 
                 onResult: Optional[Callable[[bool], None]] = None) -> bool:
        """执行任务"""
        try:
            existingTask = self._findSameTypeTask(appName, templateId)
            if existingTask and existingTask.state == TaskState.RUNNING:
                Log.e(f"相同类型的任务正在执行: {appName}/{templateId}")
                return False
                
            task = self.createTask(appName, templateId)
            if not task:
                Log.e(f"创建任务失败: {appName}/{templateId}")
                return False
                
            task.lastAppName = appName
            task.onResult = onResult
            taskId = self._getTaskId(appName, templateId)
            self.tasks[taskId] = task
            
            # 在新线程中执行任务
            thread = threading.Thread(
                target=self._runTaskInThread,
                args=(task, params, taskId)
            )
            thread.daemon = True
            thread.start()
            return True
            
        except Exception as e:
            Log.ex(e, f"执行任务异常: {appName}/{templateId}")
            return False
            
    def _runTaskInThread(self, task: Task, params: Optional[Dict[str, str]], taskId: str):
        """在线程中执行任务"""
        try:
            success = task.run(params)
            if task.onResult:
                task.onResult(success)
        except Exception as e:
            Log.ex(e, f"任务执行异常: {task.taskName}")
        finally:
            if taskId in self.tasks:
                del self.tasks[taskId]
        
    def getTaskProgress(self, appName: str, templateId: str) -> Tuple[Optional[TaskState], float]:
        """获取任务进度"""
        task = self._findSameTypeTask(appName, templateId)
        if not task:
            return None, 0.0
        return task.state, task.progress
        
    def listRunningTasks(self) -> List[Tuple[str, str, TaskState, float]]:
        """获取所有运行中的任务及进度"""
        return [(task.appName, task.taskName, task.state, task.progress) 
                for task in self.tasks.values()]

# 全局任务管理器实例
taskManager = TaskMgr.instance()
regTask = taskManager.regTask

@regCmd(r'执行任务', r'(?P<appName>[\w\s]+)\s+(?P<templateId>[\w\s]+)(\s+(?P<params>.+))?')
def runTask(appName: str, templateId: str, params: str = None) -> bool:
    """执行指定任务
    用法: 执行任务 <应用名> <模板ID> [参数]
    示例: 
        执行任务 快手极速版 ad
        执行任务 快手极速版 ad duration=30,closeBtn=关闭
    """
    # 解析参数字符串
    params_dict = None
    if params:
        try:
            params_dict = dict(item.split('=') for item in params.split())
        except Exception as e:
            Log.ex(e, f"参数格式错误: {params}")
            return False
    try:
        if appName == "_":
            appName = getattr(taskManager, 'lastAppName', '')
        if not appName:
            Log.e("未设置应用名")
            return False    
        taskManager._runTask(appName, templateId, params_dict)
        return True
    except Exception as e:
        Log.ex(e, f"执行任务异常: {appName}/{templateId}")
        return False

@regCmd(r'查询任务', r'(?P<appName>[\w\s]+)\s+(?P<templateId>[\w\s]+)')
def queryTask(appName: str, templateId: str) -> bool:
    """查询任务进度
    用法: 查询任务 <应用名> <模板ID>
    示例: 查询任务 快手极速版 ad
    """
    state, progress = taskManager.getTaskProgress(appName, templateId)
    if not state:
        Log.i(f"未找到任务: {appName}/{templateId}")
        return False
        
    Log.i(f"任务状态: {state.value}")
    Log.i(f"执行进度: {progress:.1f}%")
    return True

@regCmd(r'任务列表', r'')
def listTasks() -> bool:
    """查看所有运行中的任务
    用法: 任务列表
    """
    tasks = taskManager.listRunningTasks()
    if not tasks:
        Log.i("当前没有运行中的任务")
        return True
        
    for appName, taskName, state, progress in tasks:
        Log.i(f"任务: {appName}/{taskName}")
        Log.i(f"状态: {state.value}")
        Log.i(f"进度: {progress:.1f}%")
        Log.i("---")
    return True 