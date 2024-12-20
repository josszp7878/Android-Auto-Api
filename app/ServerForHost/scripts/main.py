from tools import Tools
from java import jclass
import time

Log = jclass("android.util.Log")
TAG = "PythonScript"

def test_commands():
    """测试指令解析和执行"""
    Log.i(TAG, "Testing command parsing and execution")
    
    # 测试打开应用
    app_name = "河马剧场"
    Log.i(TAG, f"Opening app: {app_name}")
    open_result = Tools.openApp(app_name)
    Log.i(TAG, f"Open app result: {open_result}")
    time.sleep(10)

def main():
    """Python脚本入口函数"""
    Log.i(TAG, "Python script started")
    test_commands()