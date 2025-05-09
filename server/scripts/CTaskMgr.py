from typing import List, Optional, Tuple, Callable
from CTask import CTask_
import _G
import _Log
import threading
from datetime import datetime
from _Tools import TaskState, _Tools_

class CTaskMgr_:
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
        # _Log._Log_.i("TaskMgr初始化完成")
    
    @classmethod
    def getInstance(cls) -> 'CTaskMgr_':
        """获取任务管理器实例"""
        if cls._instance is None:
            cls._instance = CTaskMgr_()
        return cls._instance
    
    def getCurrentTask(self) -> Optional[dict]:
        """获取当前任务信息"""
        return self.current_task
    
    def getTask(self, appName: str, taskName: str) -> Optional[dict]:
        """获取指定任务"""
        return self.tasks.get(appName, {}).get(taskName)
    
    def createTask(self, appName: str, templateId: str) -> Optional[CTask_]:
        """创建新任务"""
        try:
            # 先检查模板是否存在
            from TaskTemplate import TaskTemplate_
            template = TaskTemplate_.getTemplate(templateId)
            if not template:
                _Log._Log_.e(f"找不到任务模板: {templateId}")
                return None
            
            # 创建 CTask 实例
            task = CTask_(appName, templateId)
            task.progress = 0.0
            task.state = TaskState.RUNNING
            task.time = datetime.now()
            
            _Log._Log_.i(f"创建任务: {appName}/{templateId}")
            return task
            
        except Exception as e:
            _Log._Log_.ex(e, f"创建任务失败: {appName}/{templateId}")
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
            
            _Log._Log_.i(f"启动任务: {appName}/{taskName}")
            return True
            
        except Exception as e:
            _Log._Log_.ex(e, f"启动任务失败: {appName}/{taskName}")
            return False
    
    def stopTask(self, appName: str, taskName: str):
        """停止任务"""
        try:
            task = self.getTask(appName, taskName)
            if task:
                task['state'] = 'stopped'
                if self.current_task == task:
                    self.current_task = None
                _Log._Log_.i(f"停止任务: {appName}/{taskName}")
                
        except Exception as e:
            _Log._Log_.ex(e, f"停止任务失败: {appName}/{taskName}")
    
    def updateProgress(self, appName: str, taskName: str, progress: float):
        """更新任务进度"""
        try:
            task = self.getTask(appName, taskName)
            if task:
                task['progress'] = progress
                _Log._Log_.i(f"更新任务进度: {appName}/{taskName} -> {progress}")
                
        except Exception as e:
            _Log._Log_.ex(e, f"更新任务进度失败: {appName}/{taskName}")
    
      
    def _getTask(self, appName: str, templateId: str) -> Optional[CTask_]:
        """查找相同类型的任务(相同应用名和模板)"""
        taskId = _Tools_.toTaskId(appName, templateId)
        return self.tasks.get(taskId)

    def _stopTask(self, appName: str, templateId: str) -> bool:
        """停止指定的任务"""
        try:
            task = self.curTask
            if appName is not None and templateId is not None:
                task = self._getTask(appName, templateId)
            if task:
                task.stop()
                taskId = _Tools_.toTaskId(appName, templateId)
                del self.tasks[taskId]   
                return True
            else:
                # _Log._Log_.w(f"未找到任务: 应用名={appName}, 模板ID={templateId}")
                return False
        except Exception as e:
            _Log._Log_.ex(e, "停止任务失败")
            return False
        

    def _startTask(self, appName: str, templateId: str, data: dict = None, 
                  onResult: Optional[Callable[[bool], None]] = None) -> CTask_:
        """执行任务"""
        try:
            existingTask = self._getTask(appName, templateId)
            if existingTask and existingTask.state == TaskState.RUNNING:
                _Log._Log_.e(f"相同类型的任务正在执行: {appName}/{templateId}")
                return None
                
            task = self.createTask(appName, templateId)
            if not task:
                _Log._Log_.e(f"创建任务失败: {appName}/{templateId}")
                return None
                
            task.lastAppName = appName
            task.onResult = onResult
            taskId = _Tools_.toTaskId(appName, templateId)
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
                    _Log._Log_.i(f'任务启动成功: {appName}/{templateId}')
            except Exception as e:
                _Log._Log_.ex(e, '发送任务启动事件失败')
            
            return task
            
        except Exception as e:
            _Log._Log_.ex(e, f"执行任务异常: {appName}/{templateId}")
            return None
        
            
    def _runTaskInThread(self, task: CTask_, taskId: str, data: dict = None):
        """在线程中执行任务"""
        try:
            _Log._Log_.i(f"执行任务: {task.taskName}, 进度: {data.get('progress', 0) if data else 0}")
            state = task.run(data)
        except Exception as e:
            _Log._Log_.ex(e, f"任务执行异常: {task.taskName}")
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
                _Log._Log_.i(f"任务已停止: {appName}/{templateId}")
        except Exception as e:
            _Log._Log_.ex(e, "停止所有任务失败")

    @classmethod
    def registerCommands(cls):
        """注册任务管理相关命令"""
        log = _G._G_.Log()
        log.i("注册CTaskMgr模块命令...")
        from _CmdMgr import regCmd
        
        @regCmd(r"#任务列表")
        def taskList():
            """
            功能：获取任务列表
            """
            # 命令实现...
        
        @regCmd(r"#启动任务(?P<taskName>.+)")
        def startTasK(taskName):
            """
            功能：启动指定任务
            指令名: startTask-sT
            中文名: 启动任务
            参数: taskName - 任务名称
            示例: 启动任务 每日签到
            """
            # 命令实现...
        


taskMgr = CTaskMgr_.getInstance()