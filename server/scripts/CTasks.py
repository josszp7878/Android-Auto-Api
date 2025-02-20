from logger import Log
from tools import TaskState
import time  # 确保导入 time 模块
from CTask import CTask
from TaskTemplate import regTask

@regTask("看视频")
def T_watchVideo(params: dict):
    def start(task: CTask):
        Log.i("开始看视频")
        task.duration = 10
        task.interval = 1
        # return Check.Ad_Start(task, params)
        
    def do(task: CTask):
        Log.i(f"看视频中{task.progress:.1f}")
        # while Check.Ad_Process(task, params):
        #     time.sleep(params['interval'] or 1)  # 使用 time.sleep 而不是 sleep
    
    def end(task: CTask):
        # return Check.Ad_End(task, params)
        Log.i("视频结束")
        task.state = TaskState.SUCCESS
    return start, do, end


