from java import jclass

# 获取Android的Log类
Log = jclass("android.util.Log")
TAG = "PythonScript"

# 导入Java类
PythonServices = jclass("cn.vove7.andro_accessibility_api.demo.script.PythonServices")

def test_services():
    """测试直接调用Java服务接口"""
    Log.i(TAG, "Testing direct Java service calls")
    
    # 调用clickPosition方法
    try:
        click_result = PythonServices.clickPosition(400, 500)
        Log.i(TAG, f"Click position result: {click_result}")
    except Exception as e:
        Log.e(TAG, f"Error calling clickPosition: {e}")
    
    # 调用getScreenText方法
    try:
        screen_text = PythonServices.getScreenText()
        Log.i(TAG, f"Screen text: {screen_text}")
    except Exception as e:
        Log.e(TAG, f"Error calling getScreenText: {e}")

def main():
    """Python脚本入口函数"""
    Log.i(TAG, "Python script started")
    
    # 测试服务接口
    test_services()