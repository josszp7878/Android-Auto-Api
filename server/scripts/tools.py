import time
import builtins  # 导入 builtins 模块

try:
    from java import jclass
    # 获取必要的 Java 类
    Log = jclass("android.util.Log")
    PythonServices = jclass("cn.vove7.andro_accessibility_api.demo.script.PythonServices")
    Build = jclass("android.os.Build")
except ImportError:
    pass

class Tools:
    _instance = None
    TAG = "Tools"

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Tools, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    @staticmethod
    def isHarmonyOS() -> bool:
        """检查是否是鸿蒙系统"""
        try:
            # 检查系统属性中是否包含鸿蒙特征
            manufacturer = Build.MANUFACTURER.lower()
            return "huawei" in manufacturer or "honor" in manufacturer
        except Exception as e:
            Log.e(Tools.TAG, f"Failed to check system type: {str(e)}")
            return False

    @staticmethod
    def openApp(app_name: str) -> bool:
        """智能打开应用，根据系统类型选择不同的打开方式
        
        Args:
            app_name: 应用名称
            go_back: 是否在打开后返回
            
        Returns:
            bool: 是否成功打开
        """
        Log.i(Tools.TAG, f"Opening app: {app_name}")
        
        try:
            # 检查系统类型
            if Tools.isHarmonyOS():
                Log.i(Tools.TAG, "Using HarmonyOS method (click)")
                return Tools._openAppByClick(app_name)
            else:
                Log.i(Tools.TAG, "Using Android method (service)")
                return PythonServices.openApp(app_name)
        except Exception as e:
            Log.e(Tools.TAG, f"Failed to open app: {str(e)}")
            return False

    @staticmethod
    def _openAppByClick(app_name: str) -> bool:
        """通过点击方式打开应用（原来的实现移到这里）"""
        try:
            if not PythonServices.goHome():
                Log.e(Tools.TAG, "Failed to go home")
                return False
                
            time.sleep(0.5)
            
            nodes = PythonServices.findTextNodes()
            targetNode = next((node for node in nodes if app_name in node.getText()), None)
            
            if not targetNode:
                Log.e(Tools.TAG, f"App icon not found: {app_name}")
                return False
            
            bounds = targetNode.getBounds()
            if not PythonServices.clickPosition(bounds.centerX(), bounds.centerY()):
                Log.e(Tools.TAG, "Failed to click app icon")
                return False
            return True
            
        except Exception as e:
            Log.e(Tools.TAG, f"Failed to open app by click: {str(e)}")
            return False