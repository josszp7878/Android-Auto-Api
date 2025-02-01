from taskmgr import regTask
from logger import Log, android
from task import Task, TaskTemplate
from checkers import Check
import time  # 确保导入 time 模块


@regTask("看视频")
def Task_watch_video(params: dict):
    def start(task: Task) -> bool:
        return Check.Ad_Start(task, params)
        
    def do(task: Task):
        while Check.Ad_Process(task, params):
            time.sleep(params['interval'] or 1)  # 使用 time.sleep 而不是 sleep
        return True
    
    def end(task: Task) -> bool:
        return Check.Ad_End(task, params)
    
    return start, do, end


