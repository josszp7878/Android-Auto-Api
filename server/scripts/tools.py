try:
    from logger import Log
except:
    from scripts.logger import Log

from typing import Pattern, List
from enum import Enum
import time

class TaskState(Enum):
    """任务状态"""
    CANCELLED = "cancelled"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCESS = "success"
    FAILED = "failed"

    @staticmethod
    def values():
        """返回所有状态值"""
        return [state.value for state in TaskState]
    
class TAG(Enum):
    """标签"""
    CMD = "CMD"
    Server = "@"


class Tools:
    _instance = None
    TAG = "Tools"
    port = 5000
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            _instance = super(Tools, cls).__new__(cls)
            _instance._screenInfoCache = ""
            cls._instance = _instance
        return cls._instance
    
    @staticmethod
    def _toTaskId(appName: str, templateId: str) -> str:
        """生成任务唯一标识"""
        return f"{appName}_{templateId}"

    @staticmethod
    def getLocalIP():
        """获取本机IP地址"""
        import socket
        return socket.gethostbyname(socket.gethostname())

    @staticmethod
    def printCallStack():
        """打印调用栈"""
        import traceback
        print('\n保存日志调用栈:')
        for line in traceback.format_stack()[:-1]:
            print(line.strip())


    @staticmethod
    def toPos(item: dict):
        bounds = [int(x) for x in item['b'].split(',')]
        centerX = (bounds[0] + bounds[2]) // 2
        centerY = (bounds[1] + bounds[3]) // 2
        return (centerX, centerY)
    
    ##############################
    # 屏幕文字相关
    ##############################
    def screenInfos(self):
        return self._screenInfoCache

    def refreshScreenInfos(self) -> list:
        """获取并解析屏幕信息,支持缓存"""
        try:
            info = Log.android.getScreenInfo()
            size = info.size()
            result = []
            
            for i in range(size):
                item = info.get(i)
                result.append({
                    't': item.get('t'),
                    'b': item.get('b')
                })
                
            # 更新缓存
            self._screenInfoCache = result
            return result
            
        except Exception as e:
            Log.ex(e, "获取屏幕信息失败")
            return []
    
    def matchScreenText(self, regex: Pattern, region: List[int] = None):
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
            screenInfo = self.screenInfos()        
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
        
    @staticmethod
    def isHarmonyOS() -> bool:
        """检查是否是鸿蒙系统"""
        try:
            # 检查系统属性中是否包含鸿蒙特征
            from android.os import Build
            manufacturer = Build.MANUFACTURER.lower()
            return "huawei" in manufacturer or "honor" in manufacturer
        except Exception as e:
            Log.ex(e, '检查系统类型失败')
            return False

    @staticmethod
    def openApp(app_name: str) -> bool:
        """智能打开应用，根据系统类型选择不同的打开方式
        
        Args:
            app_name: 应用名称
            
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
                from PythonServices import PythonServices
                return PythonServices.openApp(app_name)
        except Exception as e:
            Log.ex(e, '打开应用失败')
            return False

    @staticmethod
    def _openAppByClick(app_name: str) -> bool:
        """通过点击方式打开应用（适用于鸿蒙系统）"""
        try:
            from PythonServices import PythonServices
            
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
            if not PythonServices.click(bounds.centerX(), bounds.centerY()):
                Log.e(Tools.TAG, "Failed to click app icon")
                return False
            return True
            
        except Exception as e:
            Log.ex(e, f"Failed to open app by click: {str(e)}")
            return False

tools = Tools()
