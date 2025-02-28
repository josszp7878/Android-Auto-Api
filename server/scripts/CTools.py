from logger import Log
from typing import Pattern, List
import time

class CTools:
    TAG = "CTools"
    port = 5000
    _screenInfoCache = None

    @classmethod
    def android(cls): # 获取Android对象
        if not hasattr(cls, '_android'):
            try:
                from java import jclass            
                cls._android = jclass("cn.vove7.andro_accessibility_api.demo.script.PythonServices")
            except ImportError:
                # 非Android环境，返回None
                Log.i("非Android环境，无法加载java模块")
                cls._android = None
        return cls._android

    runFromAndroid = True   
    @classmethod
    def getLocalIP(cls):
        """获取本机IP地址"""
        import socket
        return socket.gethostbyname(socket.gethostname())

    @classmethod
    def toPos(cls, item: dict):
        bounds = [int(x) for x in item['b'].split(',')]
        centerX = (bounds[0] + bounds[2]) // 2
        centerY = (bounds[1] + bounds[3]) // 2
        return (centerX, centerY)
    
    @classmethod
    def refreshScreenInfos(cls) -> list:
        """获取并解析屏幕信息,支持缓存"""
        try:
            android = cls.android()
            if android:
                info = android.getScreenInfo()
                Log.i(f"获取屏幕信息 info={info}")
                if info is None:
                    Log.e("获取屏幕信息失败ss")
                    return []
                size = info.size()
                result = []
                # print(f"获取屏幕信息 size={size}")
                for i in range(size):
                    item = info.get(i)
                    result.append({
                        't': item.get('t'),
                        'b': item.get('b')
                    })
                    
                # 更新缓存
                cls._screenInfoCache = result
                return result
            else:
                Log.i("非Android环境，无法获取屏幕信息sss")
                return []
            
        except Exception as e:
            Log.ex(e, "获取屏幕信息失败")
            return []
    
    @classmethod
    def matchScreenText(cls, regex: Pattern, region: List[int] = None):
        """查找匹配文本的位置
        Args:
            pattern: 匹配模式(正则表达式)
            region: 搜索区域[left, top, right, bottom], None表示全屏搜索
            forceUpdate: 是否强制更新缓存
        Returns:
            tuple: (x, y) 匹配文本的中心坐标,未找到返回None
        """
        try:
            # 使用缓存的屏幕信息
            screenInfo = cls._screenInfoCache        
            # 遍历屏幕信息，查找匹配的文本
            for item in screenInfo:
                # 解析当前文本的边界
                bounds = [int(x) for x in item['b'].split(',')]
                
                # 如果指定了区域,检查文本是否在区域内
                if region is not None:
                    # 检查是否有重叠
                    if (bounds[2] < region[0] or  # 文本在区域左边
                        bounds[0] > region[2] or  # 文本在区域右边
                        bounds[3] < region[1] or  # 文本在区域上边
                        bounds[1] > region[3]):   # 文本在区域下边
                        continue
                match = regex.search(item['t'])
                if match:
                    return match, item
            return None, None
            
        except Exception as e:
            Log.ex(e, "FindUI 指令执行失败")
            return None, None    
        
    @classmethod
    def _isHarmonyOS(cls) -> bool:
        """检查是否是鸿蒙系统"""
        try:
            # 检查系统属性中是否包含鸿蒙特征
            from android.os import Build
            manufacturer = Build.MANUFACTURER.lower()
            return "huawei" in manufacturer or "honor" in manufacturer
        except Exception as e:
            Log.ex(e, '检查系统类型失败')
            return False

    lastAppName = None
    @classmethod
    def openApp(cls, app_name: str) -> bool:
        Log.i(cls.TAG, f"Opening app: {app_name}")
        try:
            ret = False
            # 检查系统类型
            if cls._isHarmonyOS():
                Log.i(cls.TAG, "Using HarmonyOS method (click)")
                ret = cls._openAppByClick(app_name)
            else:
                Log.i(cls.TAG, "Using Android method (service)")
                ret = cls.android().openApp(app_name)
            if ret:
                cls.lastAppName = app_name
            return ret
        except Exception as e:
            Log.ex(e, '打开应用失败')
            return False

    @classmethod
    def closeApp(cls, app_name: str = None) -> bool:
        try:
            if not app_name:
                app_name = cls.lastAppName
            Log.i(cls.TAG, f"Closing app: {app_name}")
            android = cls.android()
            if android:
                return android.closeApp(app_name)
            return False
        except Exception as e:
            Log.ex(e, '打开应用失败')
            return False

    @classmethod
    def _openAppByClick(cls, app_name: str) -> bool:
        """通过点击方式打开应用（适用于鸿蒙系统）"""
        try:
            if not cls.android().goHome():
                Log.e(cls.TAG, "Failed to go home")
                return False
            time.sleep(0.5)
            nodes = cls.android().findTextNodes()
            targetNode = next((node for node in nodes if app_name in node.getText()), None)
            
            if not targetNode:
                Log.e(cls.TAG, f"App icon not found: {app_name}")
                return False
            
            bounds = targetNode.getBounds()
            if not cls.android().click(bounds.centerX(), bounds.centerY()):
                Log.e(cls.TAG, "Failed to click app icon")
                return False
            return True
            
        except Exception as e:
            Log.ex(e, f"Failed to open app by click: {str(e)}")
            return False

        # 添加Toast常量
    TOAST_LENGTH_SHORT = 0  # Toast.LENGTH_SHORT
    TOAST_LENGTH_LONG = 1   # Toast.LENGTH_LONG
    TOAST_GRAVITY_TOP = 48    # Gravity.TOP
    TOAST_GRAVITY_CENTER = 17 # Gravity.CENTER
    TOAST_GRAVITY_BOTTOM = 80 # Gravity.BOTTOM
    @classmethod
    def toast(cls, msg, duration=None, gravity=None, xOffset=0, yOffset=100):
        """在手机上显示Toast消息
        Args:
            msg: 要显示的消息
            duration: 显示时长，可选值：TOAST_LENGTH_SHORT(2秒)，TOAST_LENGTH_LONG(3.5秒)
            gravity: 显示位置，可选值：TOAST_GRAVITY_TOP, TOAST_GRAVITY_CENTER, TOAST_GRAVITY_BOTTOM
            xOffset: X轴偏移量
            yOffset: Y轴偏移量
        """
        try:
            android = cls.android()
            if android:
                android.showToast(str(msg), 
                                duration or cls.TOAST_LENGTH_LONG,
                                gravity or cls.TOAST_GRAVITY_BOTTOM,
                                xOffset, yOffset)
            else:
                print(f"Toast: {msg}")
        except Exception as e:
            print(f"显示Toast失败: {e}")
            print(msg)

def requireAndroid(func):
    def wrapper(*args, **kwargs):
        if not Log().isAndroid():
            return "w##Android指令，当前环境不支持"
        return func(*args, **kwargs)
    # 保持原始函数的属性
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper