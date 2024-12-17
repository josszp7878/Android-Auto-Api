from typing import Optional
import android.util.Log as ALog

TAG = "PythonScript"

class TaskManager:
    def __init__(self):
        self.tasks = {}
    
    def register_task(self, name: str, task_func):
        """注册一个任务"""
        self.tasks[name] = task_func
        
    def run_task(self, name: str) -> Optional[str]:
        """运行指定任务"""
        if name not in self.tasks:
            ALog.e(TAG, f"Task {name} not found")
            return None
            
        try:
            return self.tasks[name]()
        except Exception as e:
            ALog.e(TAG, f"Task {name} failed: {str(e)}")
            return None

# 全局任务管理器
task_manager = TaskManager()

def example_task():
    """示例任务"""
    ALog.i(TAG, "Running example task")
    # TODO: 实现具体任务逻辑
    return "Example task completed"

def main():
    """
    Python脚本入口函数
    在这里实现具体的业务逻辑初始化
    """
    ALog.i(TAG, "Python script started")
    
    # 注册任务
    task_manager.register_task("example", example_task)
    
    # 可以在这里直接运行某些初始任务
    # task_manager.run_task("example")