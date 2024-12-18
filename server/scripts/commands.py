from Command import command, parse_command
from java import jclass

# 导入Java类
PythonServices = jclass("cn.vove7.andro_accessibility_api.demo.script.PythonServices")

@command(r"点击\s+(?P<x>\d+)\s+(?P<y>\d+)")
def click(x, y):
    try:
        x, y = int(x), int(y)
        result = PythonServices.clickPosition(x, y)
        return f"点击位置 ({x}, {y}) 结果: {result}"
    except Exception as e:
        return f"Error calling clickPosition: {e}"

@command(r"屏幕内容")
def getScreenText():
    try:
        screen_text = PythonServices.getScreenText()
        return f"屏幕文本: {screen_text}"
    except Exception as e:
        return f"Error calling getScreenText: {e}"



