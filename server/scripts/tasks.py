from taskmgr import regTask
from logger import Log
from task import Task
from tasktemplate import TaskTemplate
from checker import Checker

# 使用新的装饰器定义任务
@regTask("打印")
def printTask():
    def init(task: Task):
        """初始化打印任务的检查器"""
        # 添加启动阶段检查 - 检查是否有打印机就绪提示
        task.addStartCheck(
            Checker.create([
                "打印机就绪",
                "准备打印"
            ])
        )
        
        # 添加执行阶段检查 - 检查打印进度
        task.addDoCheck(
            Checker.create([
                r"正在打印第(?P<page>\d+)页",
                r"打印进度:(?P<progress>\d+)%"
            ])
        )
        
        # 添加结束阶段检查 - 检查打印完成提示
        task.addEndCheck(
            Checker.create([
                "打印完成",
                "打印任务结束"
            ])
        )
    
    def start(task: Task):
        # 检查打印机状态
        if task.startCheckList[0].check(lambda c: True):
            Log.i("打印机已就绪")
            return True
        Log.w("打印机未就绪")
        return False
        
    def do(task: Task):
        msg = getattr(task, 'Msg', '')
        if msg:
            Log.i(f"打印内容: {msg}")
            
        # 检查打印进度
        if task.doCheckList[0].check(lambda c: 
            # 更新任务进度
            for pattern, item in c.matched:
                if "progress" in pattern.pattern:
                    match = pattern.search(item['t'])
                    if match:
                        progress = int(match.group('progress'))
                        task.updateProgress(progress)
                        return True
            return False
        ):
            return True
            
        return False
        
    def end(task: Task):
        # 检查打印完成状态
        if task.endCheckList[0].check(lambda c: True):
            Log.i("打印任务已完成")
            return True
        Log.w("打印任务未正常完成")
        return False
        
    return TaskTemplate(
        taskName="打印任务",
        alias="print_task",
        init=init,
        start=start,
        do=do,
        end=end
    )

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

def initAdTask(task: Task):
    """初始化广告任务"""
    # 添加启动阶段检查
    task.addStartCheck(
        Checker.create("观看广告|点击观看")
    )
    
    # 添加执行阶段检查
    task.addDoCheck(
        Checker.create([
            r"广告剩余(?P<seconds>\d+)秒",
            r"正在播放广告"
        ])
    )
    
    # 添加结束阶段检查
    task.addEndCheck(
        Checker.create("领取成功|观看完成")
    )

def startAdTask(task: Task) -> bool:
    """开始广告任务"""
    return task.startCheckList[0].check(lambda c: "观看广告" in c.matched[0][1]['t'])

def doAdTask(task: Task) -> bool:
    """执行广告任务"""
    while True:
        if task.doCheckList[0].check(lambda c: True):
            break
    return True

def endAdTask(task: Task) -> bool:
    """结束广告任务"""
    return task.endCheckList[0].check(lambda c: "领取成功" in c.matched[0][1]['t'])

# 定义任务模板
adTemplate = TaskTemplate(
    taskName="广告任务",
    alias="ad_task",
    init=initAdTask,
    start=startAdTask,
    do=doAdTask,
    end=endAdTask
)

# 注册任务模板
taskTemplates = {
    "ad_task": adTemplate
}

