from java import jclass
from commands import parse_command

# 获取Android的Log类
Log = jclass("android.util.Log")
TAG = "PythonScript"

def test_commands():
    """测试指令解析和执行"""
    Log.i(TAG, "Testing command parsing and execution")
    
    # 测试点击指令
    command_text = "点击 400 500"
    result = parse_command(command_text)
    Log.i(TAG, f"Command result: {result}")
    
    # 测试获取屏幕内容指令
    command_text = "屏幕内容"
    result = parse_command(command_text)
    Log.i(TAG, f"Command result: {result}")

def main():
    """Python脚本入口函数"""
    Log.i(TAG, "Python script started")
    
    # 测试指令接口
    test_commands()