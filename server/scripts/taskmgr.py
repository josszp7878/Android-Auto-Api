from typing import Dict, List, Optional
from datetime import datetime
import json
import os
from task import Task


class TaskMgr:
    """任务管理器,负责任务的调度和管理"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}  # taskName -> Task
        self.runningTask: Optional[Task] = None
        self.taskHistory: List[Dict] = []  # 任务执行历史
        self.configPath = "tasks.json"  # 任务配置文件路径
        
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
        
    def run(self, taskName: str) -> bool:
        """运行指定任务"""
        task = self.get(taskName)
        if not task or self.runningTask:
            return False
            
        self.runningTask = task
        success = False
        try:
            if task.enter() and task.do() and task.end():
                success = True
                self._addHistory(task, success)
        except Exception as e:
            print(f"Task execution failed: {str(e)}")
        finally:
            self.runningTask = None
        return success
        
    def runTasks(self, taskNames: List[str]) -> Dict[str, bool]:
        """批量运行任务
        Returns:
            Dict[str, bool]: 任务名称 -> 执行结果
        """
        results = {}
        for taskName in taskNames:
            results[taskName] = self.run(taskName)
        return results
        
        def getRunning(self) -> Optional[Task]:
        """获取当前运行的任务"""
        return self.runningTask
        
    def _addHistory(self, task: Task, success: bool):
        """添加任务执行历史"""
        history = {
            "taskName": task.taskName,
            "appName": task.appName,
            "startTime": task.startTime.isoformat() if task.startTime else None,
            "endTime": task.endTime.isoformat() if task.endTime else None,
            "reward": task.reward,
            "success": success
        }
        self.taskHistory.append(history)
        
    def getHistory(self, taskName: Optional[str] = None) -> List[Dict]:
        """获取任务执行历史
        Args:
            taskName: 可选,指定任务名称
        """
        if not taskName:
            return self.taskHistory
        return [h for h in self.taskHistory if h["taskName"] == taskName]
        
    def save(self) -> bool:
        """保存任务配置到文件"""
        try:
            data = {
                "tasks": [
                    {
                        "appName": task.appName,
                        "taskName": task.taskName,
                        "reward": task.reward
                    }
                    for task in self.tasks.values()
                ],
                "history": self.taskHistory
            }
            with open(self.configPath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Save tasks failed: {str(e)}")
            return False
            
    def load(self) -> bool:
        """从文件加载任务配置"""
        if not os.path.exists(self.configPath):
            return False
            
        try:
            with open(self.configPath, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # 加载任务
            self.tasks.clear()
            for taskData in data.get("tasks", []):
                task = Task.create(
                    taskData["appName"],
                    taskData["taskName"]
                )
                task.reward = taskData["reward"]
                self.tasks[task.taskName] = task
                
            # 加载历史记录
            self.taskHistory = data.get("history", [])
            return True
        except Exception as e:
            print(f"Load tasks failed: {str(e)}")
            return False

    def clearHistory(self):
        """清空任务执行历史"""
        self.taskHistory.clear() 