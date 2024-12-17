from typing import Optional, Callable, Dict
from java import jclass

# 获取Android的Log类
Log = jclass("android.util.Log")
TAG = "TaskManager"

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Callable] = {}
    
    def register_task(self, name: str, task_func: Callable) -> None:
        """注册一个任务"""
        self.tasks[name] = task_func
        Log.d(TAG, f"Registered task: {name}")
        
    def run_task(self, name: str) -> Optional[str]:
        """运行指定任务"""
        if name not in self.tasks:
            Log.e(TAG, f"Task {name} not found")
            return None
            
        try:
            Log.i(TAG, f"Running task: {name}")
            return self.tasks[name]()
        except Exception as e:
            Log.e(TAG, f"Task {name} failed: {str(e)}")
            return None 