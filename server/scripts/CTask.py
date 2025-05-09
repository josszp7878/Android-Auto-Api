import json
import os
from datetime import datetime
from enum import Enum

class TaskState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused" 
    SUCCESS = "success"
    FAILED = "failed"


class CTask_:
    """客户端任务类"""
    
    # 任务配置字典
    taskConfigs = {}
    
    def __init__(self, taskName, app):
        """初始化任务"""
        self._name = taskName
        self._app = app
        self._startTime = datetime.now()
        self._endTime = None
        self._score = 0
        self._progress = 0.0
        self._state = TaskState.IDLE
        self._begin = None
        self._exit = None
        self._job = None
        
        # 从配置加载任务信息
        config = CTask_.getTask(taskName)
        if config:
            self._begin = config.get("begin", {})
            self._exit = config.get("exit")
    
    @classmethod
    def _getConfigPath(cls):
        """获取配置文件路径"""
        import _G
        configDir = os.path.join(_G.g.rootDir(), "config")
        if not os.path.exists(configDir):
            os.makedirs(configDir)
        return os.path.join(configDir, "task.json")
    
    @classmethod
    def _loadConfig(cls):
        """加载任务配置"""
        try:
            configPath = cls._getConfigPath()
            if os.path.exists(configPath):
                with open(configPath, "r", encoding="utf-8") as f:
                    cls.taskConfigs = json.load(f)
        except Exception as e:
            print(f"加载任务配置失败: {e}")
            cls.taskConfigs = {}
    
    @classmethod
    def _saveConfig(cls):
        """保存任务配置"""
        try:
            configPath = cls._getConfigPath()
            with open(configPath, "w", encoding="utf-8") as f:
                json.dump(cls.taskConfigs, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存任务配置失败: {e}")
    
    @classmethod
    def getTask(cls, taskName):
        """获取任务配置"""
        if not cls.taskConfigs:
            cls._loadConfig()
        return cls.taskConfigs.get(taskName)
    
    @classmethod
    def create(cls, taskName, app):
        """创建任务实例"""
        return CTask_(taskName, app)
    
    def _parseBeginScript(self):
        """从_begin字典中获取Job参数"""
        if not self._begin or not isinstance(self._begin, dict):
            return None, 0, 1, None
            
        # 从字典中直接获取参数
        pageName = self._begin.get("pageName")
        life = self._begin.get("life", 0)
        interval = self._begin.get("interval", 1)
        onEnd = self._exit
        
        return pageName, life, interval, onEnd
    
    def begin(self):
        """开始任务"""
        if self._state != TaskState.IDLE and self._state != TaskState.PAUSED:
            return False
            
        self._state = TaskState.RUNNING
        self._startTime = datetime.now()
        
        # 解析begin脚本获取Job参数
        pageName, life, interval, onEnd = self._parseBeginScript()
        
        # 创建Job
        from CJob import CJob_
        self._job = CJob_.Create(pageName, life, interval, onEnd)
        
        # 启动Job
        jobResult = self._job.begin(self._app, self)
        if not jobResult:
            print("启动任务Job失败")
            self._state = TaskState.FAILED
            return False
        
        # 通知服务端任务开始
        try:
            self._app.sendToServer('C2S_TaskStart', {
                'appName': self._app.name,
                'taskName': self._name
            })
        except Exception as e:
            print(f"通知服务端任务开始失败: {e}")
            
        return True
    
    def stop(self, cancel=False):
        """停止任务
        cancel: 是否取消任务，True表示取消，False表示暂停
        """
        if self._state != TaskState.RUNNING:
            return False
            
        # 停止Job
        if self._job and self._job.isRunning:
            self._job.end()
        
        if cancel:
            # 取消任务
            self._state = TaskState.IDLE
            # 通知服务端取消任务
            try:
                self._app.sendToServer('C2S_TaskCancel', {
                    'appName': self._app.name,
                    'taskName': self._name
                })
            except Exception as e:
                print(f"通知服务端取消任务失败: {e}")
        else:
            # 暂停任务
            self._state = TaskState.PAUSED
            # 通知服务端暂停任务
            try:
                self._app.sendToServer('C2S_TaskPause', {
                    'appName': self._app.name,
                    'taskName': self._name
                })
            except Exception as e:
                print(f"通知服务端暂停任务失败: {e}")
                
        return True
    
    def update(self):
        """任务更新函数，由APP的_update定期调用"""
        if self._state != TaskState.RUNNING:
            return
            
        # 更新Job
        if self._job and self._job.isRunning:
            self._job.update()
        
    def updateProgress(self, progress):
        """更新任务进度"""
        if self._state != TaskState.RUNNING:
            return False
            
        self._progress = min(max(0.0, progress), 1.0)
        
        # 通知服务端更新进度
        try:
            self._app.sendToServer('C2S_TaskUpdate', {
                'appName': self._app.name,
                'taskName': self._name,
                'progress': self._progress
            })
        except Exception as e:
            print(f"通知服务端更新任务进度失败: {e}")
            
        return True
        
    def complete(self, success=True, score=0):
        """完成任务"""
        if self._state != TaskState.RUNNING:
            return False
            
        self._state = TaskState.SUCCESS if success else TaskState.FAILED
        self._endTime = datetime.now()
        self._score = score
        
        # 通知服务端任务完成
        try:
            self._app.sendToServer('C2S_TaskEnd', {
                'appName': self._app.name,
                'taskName': self._name,
                'result': success,
                'score': score
            })
        except Exception as e:
            print(f"通知服务端任务完成失败: {e}")
                
        return True
    