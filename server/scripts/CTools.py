from _Log import _Log
from typing import Pattern, List
import time

class CTools:
    Tag = "CTools"
    port = 5000
    _screenInfoCache = None

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
                _Log.i(f"获取屏幕信息 info={info}")
                if info is None:
                    _Log.e("获取屏幕信息失败ss")
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
                _Log.i("非Android环境，无法获取屏幕信息sss")
                return []
            
        except Exception as e:
            _Log.ex(e, "获取屏幕信息失败")
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
            _Log.ex(e, "FindUI 指令执行失败")
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
            _Log.ex(e, '检查系统类型失败')
            return False

    lastAppName = None
    @classmethod
    def openApp(cls, app_name: str) -> bool:
        _Log.i(cls.Tag, f"Opening app: {app_name}")
        try:
            ret = False
            # 检查系统类型
            if cls._isHarmonyOS():
                _Log.i(cls.Tag, "Using HarmonyOS method (click)")
                ret = cls._openAppByClick(app_name)
            else:
                _Log.i(cls.Tag, "Using Android method (service)")
                ret = cls.android().openApp(app_name)
            if ret:
                cls.lastAppName = app_name
            return ret
        except Exception as e:
            _Log.ex(e, '打开应用失败')
            return False

    @classmethod
    def closeApp(cls, app_name: str = None) -> bool:
        try:
            if not app_name:
                app_name = cls.lastAppName
            _Log.i(cls.Tag, f"Closing app: {app_name}")
            android = cls.android()
            if android:
                return android.closeApp(app_name)
            return False
        except Exception as e:
            _Log.ex(e, '打开应用失败')
            return False

    @classmethod
    def _openAppByClick(cls, app_name: str) -> bool:
        """通过点击方式打开应用（适用于鸿蒙系统）"""
        try:
            global android
            if not android.goHome():
                _Log.e(cls.Tag, "Failed to go home")
                return False
            time.sleep(0.5)
            nodes = android.findTextNodes()
            targetNode = next((node for node in nodes if app_name in node.getText()), None)
            
            if not targetNode:
                _Log.e(cls.Tag, f"App icon not found: {app_name}")
                return False
            
            bounds = targetNode.getBounds()
            if not android.click(bounds.centerX(), bounds.centerY()):
                _Log.e(cls.Tag, "Failed to click app icon")
                return False
            return True
            
        except Exception as e:
            _Log.ex(e, f"Failed to open app by click: {str(e)}")
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
            from CMain import android
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

    @classmethod
    def getRecentApps(cls, limit=5):
        """获取最近打开的应用列表（纯Python实现）
        
        Args:
            limit: 返回的应用数量限制，默认5个
            
        Returns:
            list: 最近打开的应用列表，每项包含包名和应用名
        """
        try:
            from CMain import runFromAndroid
            # 检查是否在Android环境
            if not runFromAndroid:
                _Log.e("获取最近应用失败: 非Android环境")
                return []
            
            # 导入Java类
            from java.lang import System
            from java.util import Collections
            from java.util import ArrayList
            from java.util.concurrent import TimeUnit
            from android.content import Context
            from android.app.usage import UsageStatsManager
            from android.content import Intent
            from android.provider import Settings
            from android.content.pm import PackageManager
            from org.json import JSONArray, JSONObject
            
            # 获取Android上下文
            android = cls.android()
            if not android:
                _Log.e("获取最近应用失败: 未找到Android实例")
                return []
            
            context = android.getContext()
            if not context:
                _Log.e("获取最近应用失败: 未找到Context")
                return []
            
            # 获取UsageStatsManager
            usageStatsManager = context.getSystemService(Context.USAGE_STATS_SERVICE)
            if not usageStatsManager:
                _Log.e("获取最近应用失败: 未找到UsageStatsManager")
                return []
            
            # 获取过去24小时的应用使用情况
            endTime = System.currentTimeMillis()
            startTime = endTime - 24 * 60 * 60 * 1000  # 24小时
            
            # 查询应用使用情况
            usageStatsList = usageStatsManager.queryUsageStats(
                UsageStatsManager.INTERVAL_DAILY, startTime, endTime)
            
            if not usageStatsList or usageStatsList.isEmpty():
                # 可能需要权限
                intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS)
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                _Log.w("需要授予使用情况访问权限")
                return []
            
            # 转换为Python列表
            stats_list = []
            for i in range(usageStatsList.size()):
                stats_list.append(usageStatsList.get(i))
            
            # 按最后使用时间排序
            stats_list.sort(key=lambda x: x.getLastTimeUsed(), reverse=True)
            
            # 获取PackageManager
            pm = context.getPackageManager()
            
            # 构建结果列表
            result = []
            count = 0
            
            for stats in stats_list:
                if count >= limit:
                    break
                
                packageName = stats.getPackageName()
                
                # 跳过系统应用
                if (packageName.startswith("com.android") or 
                    packageName.startswith("android") or
                    packageName == context.getPackageName()):
                    continue
                
                try:
                    appInfo = pm.getApplicationInfo(packageName, 0)
                    appName = pm.getApplicationLabel(appInfo).toString()
                    
                    result.append({
                        "packageName": packageName,
                        "appName": appName,
                        "lastUsed": stats.getLastTimeUsed()
                    })
                    
                    count += 1
                except Exception as e:
                    # 跳过无法获取信息的应用
                    pass
                
            return result
        except Exception as e:
            _Log.ex(e, "获取最近应用失败")
            return []

    @classmethod
    def getCurrentApp(cls):
        """获取当前正在运行的应用信息（纯Python实现）
        
        Returns:
            dict: 包含包名(packageName)和应用名(appName)的字典，失败返回None
        """
        try:
            # 检查是否在Android环境
            from CMain import runFromAndroid
            if not runFromAndroid:
                _Log.e("获取当前应用失败: 非Android环境")
                return None
            
            # 导入Java类
            from java.lang import System
            from java.util import Collections
            from android.content import Context
            from android.app.usage import UsageStatsManager
            from android.content.pm import PackageManager
            
            # 获取Android上下文
            android = cls.android()
            if not android:
                _Log.e("获取当前应用失败: 未找到Android实例")
                return None
            
            context = android.getContext()
            if not context:
                _Log.e("获取当前应用失败: 未找到Context")
                return None
            
            # 获取UsageStatsManager
            usageStatsManager = context.getSystemService(Context.USAGE_STATS_SERVICE)
            if not usageStatsManager:
                _Log.e("获取当前应用失败: 未找到UsageStatsManager")
                return None
            
            # 获取最近1分钟的应用使用情况
            endTime = System.currentTimeMillis()
            startTime = endTime - 60 * 1000  # 1分钟
            
            # 查询应用使用情况
            usageStatsList = usageStatsManager.queryUsageStats(
                UsageStatsManager.INTERVAL_DAILY, startTime, endTime)
            
            if not usageStatsList or usageStatsList.isEmpty():
                _Log.w("需要授予使用情况访问权限")
                return None
            
            # 找出最近使用的应用
            recentStats = None
            maxLastUsed = 0
            
            for i in range(usageStatsList.size()):
                stats = usageStatsList.get(i)
                if stats.getLastTimeUsed() > maxLastUsed:
                    maxLastUsed = stats.getLastTimeUsed()
                    recentStats = stats
            
            if not recentStats:
                return None
            
            packageName = recentStats.getPackageName()
            pm = context.getPackageManager()
            
            try:
                appInfo = pm.getApplicationInfo(packageName, 0)
                appName = pm.getApplicationLabel(appInfo).toString()
                
                return {
                    "packageName": packageName,
                    "appName": appName,
                    "lastUsed": recentStats.getLastTimeUsed()
                }
            except Exception as e:
                _Log.e(f"获取应用信息失败: {e}")
                return None
        except Exception as e:
            _Log.ex(e, "获取当前应用失败")
            return None

    @classmethod
    def OnPreload(cls):
        """热更新前的预处理"""
        _Log.i("CTools模块热更新前预处理")
        # 可以在这里保存一些状态
        return True
        
    @classmethod
    def OnReload(cls):
        """热更新后的处理"""
        _Log.i("CTools模块热更新完成")
        # 可以在这里恢复一些状态或执行初始化
        return True

def requireAndroid(func):
    def wrapper(*args, **kwargs):
        if not _Log().isAndroid():
            return "w->Android指令，当前环境不支持"
        return func(*args, **kwargs)
    # 保持原始函数的属性
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper