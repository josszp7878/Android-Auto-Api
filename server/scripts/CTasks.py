import _Log
from _Tools import TaskState
from CTask import CTask
from TaskTemplate import regTask

@regTask("看视频")
def T_watchVideo(params: dict):
    def start(task: CTask):
        _Log.Log_.i("开始看视频")
        task.duration = 10
        task.interval = 1
        return True
        # return Check.Ad_Start(task, params)
        
    def do(task: CTask) -> bool:
        _Log.Log_.i(f"看视频中{task.progress:.1f}")
        return True
        # while Check.Ad_Process(task, params):
        #     time.sleep(params['interval'] or 1)  # 使用 time.sleep 而不是 sleep
    
    def end(task: CTask) -> bool:
        # return Check.Ad_End(task, params)
        _Log.Log_.i("视频结束")
        task.state = TaskState.SUCCESS
        return True
    return start, do, end


