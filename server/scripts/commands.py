from Command import command, parse_command

@command(r"移动鼠标\s+(?P<x>\d+)\s+(?P<y>\d+)")
def move_mouse(x, y):
    x = int(x)
    y = int(y)
    return f"移动鼠标到 ({x}, {y})"

@command(r"点击鼠标Test")
def click_mouse():
    return "点击鼠标"

@command(r"查找文本\s+(?P<pattern>.+)")
def find_text(pattern):
    return f"查找文本 {pattern}"

@command(r"点击文本\s+(?P<text>.+)")
def click_text(text):
    return f"点击文本 {text}"

def do(cmdText):
    """执行命令文本并返回结果字符串"""
    return parse_command(cmdText)

