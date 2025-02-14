from taskmgr import regTask
from logger import Log
from task import Task, TaskState
import time  # 确保导入 time 模块


@regTask("看视频")
def T_watchVideo(params: dict):
    def start(task: Task) -> bool:
        Log.i("开始看视频")
        return True
        # return Check.Ad_Start(task, params)
        
    def do(task: Task):
        for i in range(10):
            if task.state == TaskState.CANCELED:
                return False
            Log.i(f"看视频中{i}")
            time.sleep(1)
            task.updateProgress(i/10)
        task.state = TaskState.SUCCESS
        # while Check.Ad_Process(task, params):
        #     time.sleep(params['interval'] or 1)  # 使用 time.sleep 而不是 sleep
        return True
    
    def end(task: Task) -> bool:
        # return Check.Ad_End(task, params)
        Log.i("视频结束")
        return True
    return start, do, end


