from typing import Dict, List, Optional, Tuple, Callable
from CTask import CTask
from logger import Log
from CmdMgr import regCmd
import threading
from datetime import datetime
from tools import Tools,TaskState

class CTaskMgr:
    """客户端任务管理器(单例模式)"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        import CTasks
        self._initialized = True
        self.current_task = None
        self.tasks = {}  # {taskId: CTask}
        self.lastAppName = None  # 记录最后执行的应用名
        self.lastTemplateId = None  # 记录最后执行的模板ID
        # Log.i("TaskMgr初始化完成")
    
    @classmethod
    def getInstance(cls) -> 'CTaskMgr':
        """获取任务管理器实例"""
        if cls._instance is None:
            cls._instance = CTaskMgr()
        return cls._instance
    
    def getCurrentTask(self) -> Optional[dict]:
        """获取当前任务信息"""
        return self.current_task
    
    def getTask(self, appName: str, taskName: str) -> Optional[dict]:
        """获取指定任务"""
        return self.tasks.get(appName, {}).get(taskName)
    
    def createTask(self, appName: str, templateId: str) -> Optional[CTask]:
        """创建新任务"""
        try:
            # 先检查模板是否存在
            from TaskTemplate import TaskTemplate
            template = TaskTemplate.getTemplate(templateId)
            if not template:
                Log.e(f"找不到任务模板: {templateId}")
                return None
            
            # 创建 CTask 实例
            task = CTask(appName, templateId)
            task.progress = 0.0
            task.state = TaskState.RUNNING
            task.time = datetime.now()
            
            Log.i(f"创建任务: {appName}/{templateId}")
            return task
            
        except Exception as e:
            Log.ex(e, f"创建任务失败: {appName}/{templateId}")
            return None
    
    def startTask(self, appName: str, taskName: str) -> bool:
        """启动任务"""
        try:
            task = self.getTask(appName, taskName)
            if not task:
                task = self.createTask(appName, taskName)
            if not task:
                return False
                
            task['state'] = 'running'
            task['startTime'] = datetime.now()
            self.current_task = task
            
            Log.i(f"启动任务: {appName}/{taskName}")
            return True
            
        except Exception as e:
            Log.ex(e, f"启动任务失败: {appName}/{taskName}")
            return False
    
    def stopTask(self, appName: str, taskName: str):
        """停止任务"""
        try:
            task = self.getTask(appName, taskName)
            if task:
                task['state'] = 'stopped'
                if self.current_task == task:
                    self.current_task = None
                Log.i(f"停止任务: {appName}/{taskName}")
                
        except Exception as e:
            Log.ex(e, f"停止任务失败: {appName}/{taskName}")
    
    def updateProgress(self, appName: str, taskName: str, progress: float):
        """更新任务进度"""
        try:
            task = self.getTask(appName, taskName)
            if task:
                task['progress'] = progress
                Log.i(f"更新任务进度: {appName}/{taskName} -> {progress}")
                
        except Exception as e:
            Log.ex(e, f"更新任务进度失败: {appName}/{taskName}")
    
      
    def _getTask(self, appName: str, templateId: str) -> Optional[CTask]:
        """查找相同类型的任务(相同应用名和模板)"""
        taskId = Tools._toTaskId(appName, templateId)
        return self.tasks.get(taskId)

    def _stopTask(self, appName: str, templateId: str) -> bool:
        """停止指定的任务"""
        try:
            task = self.curTask
            if appName is not None and templateId is not None:
                task = self._getTask(appName, templateId)
            if task:
                task.stop()
                taskId = Tools._toTaskId(appName, templateId)
                del self.tasks[taskId]   
                return True
            else:
                # Log.w(f"未找到任务: 应用名={appName}, 模板ID={templateId}")
                return False
        except Exception as e:
            Log.ex(e, "停止任务失败")
            return False
        

    def _startTask(self, appName: str, templateId: str, data: dict = None, 
                  onResult: Optional[Callable[[bool], None]] = None) -> CTask:
        """执行任务"""
        try:
            existingTask = self._getTask(appName, templateId)
            if existingTask and existingTask.state == TaskState.RUNNING:
                Log.e(f"相同类型的任务正在执行: {appName}/{templateId}")
                return None
                
            task = self.createTask(appName, templateId)
            if not task:
                Log.e(f"创建任务失败: {appName}/{templateId}")
                return None
                
            task.lastAppName = appName
            task.onResult = onResult
            taskId = Tools._toTaskId(appName, templateId)
            self.tasks[taskId] = task
            
            # 在新线程中执行任务
            thread = threading.Thread(
                target=self._runTaskInThread,
                args=(task, taskId, data)
            )
            thread.daemon = True
            thread.start()
            self.curTask = task
            
            # 记录最后执行的任务信息
            self.lastAppName = appName
            self.lastTemplateId = templateId
            
            # 发送任务启动事件
            try:
                from CClient import client
                if client:
                    client.emit('C2S_StartTask', {
                        'app_name': appName,
                        'task_name': templateId
                    })
                    Log.i(f'任务启动成功: {appName}/{templateId}')
            except Exception as e:
                Log.ex(e, '发送任务启动事件失败')
            
            return task
            
        except Exception as e:
            Log.ex(e, f"执行任务异常: {appName}/{templateId}")
            return None
        
            
    def _runTaskInThread(self, task: CTask, taskId: str, data: dict = None):
        """在线程中执行任务"""
        try:
            Log.i(f"执行任务: {task.taskName}, 进度: {data.get('progress', 0) if data else 0}")
            state = task.run(data)
        except Exception as e:
            Log.ex(e, f"任务执行异常: {task.taskName}")
        finally:
            if taskId in self.tasks:
                del self.tasks[taskId]        
    def getTaskProgress(self, appName: str, templateId: str) -> Tuple[Optional[TaskState], float]:
        """获取任务进度"""
        task = self._getTask(appName, templateId)
        if not task:
            return None, 0.0
        return task.state, task.progress
        
    def listRunningTasks(self) -> List[Tuple[str, str, TaskState, float]]:
        """获取所有运行中的任务及进度"""
        return [(task.appName, task.taskName, task.state, task.progress) 
                for task in self.tasks.values()]
    
    def uninit(self):
        """停止所有正在运行的任务"""
        try:
            running_tasks = self.listRunningTasks()
            for appName, templateId, _, _ in running_tasks:
                self._stopTask(appName, templateId)
                Log.i(f"任务已停止: {appName}/{templateId}")
        except Exception as e:
            Log.ex(e, "停止所有任务失败")



@regCmd(r'停止任务', r'(?:(?P<appName>[\w\s]+)\s+(?P<templateId>[\w\s]+))?')
def stopTask(appName: str = None, templateId: str = None) -> bool:
    """停止指定任务或所有任务
    用法: 
        停止任务 <应用名> <模板ID> - 停止指定任务
        停止任务 - 停止所有任务
    示例: 
        停止任务 快手极速版 ad
        停止任务
    """
    try:
        if appName and templateId:
            # 停止指定任务
            task = taskMgr._getTask(appName, templateId)
            if task:
                task.stop()
                Log.i(f"任务已停止: {appName}/{templateId}")
                return True
            else:
                Log.w(f"未找到任务: {appName}/{templateId}")
                return False
        else:
            if taskMgr.curTask:
                taskMgr.curTask.stop()
                Log.i("当前任务已停止")
            return True
    except Exception as e:
        Log.ex(e, "停止任务异常")
        return False

@regCmd(r'执行任务', r'(?:(?P<appName>[\w\s]+)\s+(?P<templateId>[\w\s]+))?')
def startTask(appName: str = None, templateId: str = None, data: dict = None) -> bool:
    """执行指定任务或最近任务
    用法: 
        执行任务 <应用名> <模板ID> - 执行指定任务
        执行任务 - 执行最近任务
    """
    try:
        # 如果没有参数,尝试执行最近任务
        if not appName and not templateId:
            if not hasattr(taskMgr, 'lastAppName') or not hasattr(taskMgr, 'lastTemplateId'):
                Log.w("没有最近执行的任务")
                return False
            appName = taskMgr.lastAppName
            templateId = taskMgr.lastTemplateId
            Log.i(f"执行最近任务: {appName}/{templateId}")
           
        # 打印任务数据
        if data:
            Log.i(f"任务数据: {data}")

        # 获取初始进度
        progress = data.get('progress', 0) if data else 0
        Log.i(f"开始任务: {appName}/{templateId}, 从进度 {progress} 开始")

        # 记录本次任务信息
        taskMgr.lastAppName = appName
        taskMgr.lastTemplateId = templateId
        
        taskMgr._startTask(appName, templateId, data)
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
    state, progress = taskMgr.getTaskProgress(appName, templateId)
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
    tasks = taskMgr.listRunningTasks()
    if not tasks:
        Log.i("当前没有运行中的任务")
        return True
        
    for appName, taskName, state, progress in tasks:
        Log.i(f"任务: {appName}/{taskName}")
        Log.i(f"状态: {state.value}")
        Log.i(f"进度: {progress:.1f}%")
        Log.i("---")
    return True 

@regCmd(r'取消任务(?:\s+(?P<appName>[\w\s]+)\s+(?P<templateId>[\w\s]+))?')
def cancelTask(appName: str = None, templateId: str = None) -> bool:
    """取消指定任务或当前任务
    用法: 
        取消任务 <应用名> <模板ID> - 取消指定任务
        取消任务 - 取消当前任务
    示例: 
        取消任务 快手极速版 ad
        取消任务
    """
    try:
        task = taskMgr.curTask
        if appName and templateId:
            # 取消指定任务
            task = taskMgr._getTask(appName, templateId)
        if task:
            # 先设置任务状态为失败
            return task.cancel()
        else:
            Log.w(f"未找到任务: {appName}/{templateId}")
            return False
    except Exception as e:
        Log.ex(e, "取消任务异常")
        return False

taskMgr = CTaskMgr.getInstance()