from taskmgr import regTask
from logger import Log
from task import Task
# 使用新的装饰器定义任务
@regTask("打印")
def printTask():
    def start(task: Task):
        # Log.i("开始打印任务")
        return True
        
    def do(task: Task):
        # Log.i("正在执行打印任务...")
        msg = getattr(task, 'Msg', '')
        if msg:
            Log.i(f"打印内容: {msg}")
        return True
        
    def end(task: Task):
        Log.i("打印任务结束")
        return True
        
    return start, do, end

@regTask("延时")
def delayTask():
    def start(task: Task):
        # Log.i("开始延时任务")
        count = getattr(task, 'count', 0)
        Log.i(f"延时时间: {count}秒")
        return True
        
    def do(task: Task):
        Log.i("开始延时...")
        import time
        
        # 安全地获取并转换参数
        try:
            total = int(getattr(task, 'time', '0'))
            if total <= 0:
                return True
            interval = int(getattr(task, 'interval', '1'))
            if interval <= 0:
                interval = 1
        except ValueError:
            Log.e("无效的时间参数")
            return False
            
        count = int(total / interval)
        for i in range(count):
            time.sleep(interval)
            Log.i(f"beat {i+1}")
            progress = ((i+1) / count) * 100
            task.updateProgress(progress)
        return True
        
    def end(task: Task):
        Log.i("延时任务结束")
        return True
        
    return start, do, end

