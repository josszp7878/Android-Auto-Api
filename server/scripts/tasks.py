from tasktemplate import TaskTemplate

# 简单打印任务
PRINT_TEMPLATE = TaskTemplate(
    taskName="打印任务",
    startScript="""
Log.i("开始打印任务")
Log.i(f"任务参数: {${message}}")
return True
""",
    doScript="""
Log.i("正在执行打印任务...")
Log.i("打印内容: ${message}")
return True
""",
    endScript="""
Log.i("打印任务结束")
return True
""",
    params={
        "message": "Hello World"  # 默认打印内容
    }
)

# 延时任务
DELAY_TEMPLATE = TaskTemplate(
    taskName="延时任务",
    startScript="""
import time
Log.i("开始延时任务")
Log.i(f"延时时间: ${seconds}秒")
return True
""",
    doScript="""
import time
Log.i("开始延时...")
time.sleep(${seconds})
Log.i("延时结束")
return True
""",
    endScript="""
Log.i("延时任务结束")
return True
""",
    params={
        "seconds": "3"  # 默认延时3秒
    }
)

# 点击任务
CLICK_TEMPLATE = TaskTemplate(
    taskName="点击任务",
    startScript="""
Log.i(f"准备点击: ${text}")
return True
""",
    doScript="""
Log.i(f"尝试点击文本: ${text}")
result = click("${text}")
Log.i("点击" + ("成功" if result else "失败"))
return result
""",
    endScript="""
Log.i("点击任务结束")
return True
""",
    params={
        "text": ""  # 要点击的文本
    }
) 