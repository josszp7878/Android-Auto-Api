from cmath import log
from typing import Pattern, List
import time
import _Log
import _G
import re

class CTools_:
    Tag = "CTools"
    port = 5000
    _screenInfoCache = None
    android = None
    
    @classmethod
    def init(cls):
        if not hasattr(cls, '_init'):
            _Log.Log_.i(f'初始化CTools模块')  # 最简洁的写法
            try:
                from java import jclass     
                cls.android = jclass("cn.vove7.andro_accessibility_api.demo.script.PythonServices")
                print(f'加载java模块成功 android={cls.android}')
                cls._init = True
            except ModuleNotFoundError:
                _Log.Log_.i('java模块未找到')
            except Exception as e:
                _Log.Log_.ex(e, '初始化CTools模块失败')

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
        _Log.Log_.i(f'获取屏幕信息 android={cls.android}')
        try:
            if cls.android:
                info = cls.android.getScreenInfo()
                _Log.Log_.i(f"获取屏幕信息 info={info}")
                if info is None:
                    _Log.Log_.e("获取屏幕信息失败ss")
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
                _Log.Log_.i("非Android环境，无法获取屏幕信息sss")
                return []
            
        except Exception as e:
            _Log.Log_.ex(e, "获取屏幕信息失败")
            return []
    
    @classmethod
    def matchScreenText(cls, str: str):
        try:
            # 使用缓存的屏幕信息
            screenInfo = cls._screenInfoCache
            if not screenInfo:
                return None, None
            # 解析区域和文本（保持原有逻辑）
            region = None
            text = str            
            # 匹配形如"金币[12,0,0,30]"的格式
            match = re.search(r'(.*?)\[(\d+),(\d+),(\d+),(\d+)\]', str)
            if match:
                text = match.group(1)
                region = [int(match.group(2)), int(match.group(3)),
                          int(match.group(4)), int(match.group(5))]
            
            # 生成正则表达式（添加.*通配）
            regex = re.compile(f".*{text}.*")
            
            # 遍历屏幕信息，查找匹配的文本
            for item in screenInfo:
                # 解析当前文本的边界
                bounds = [int(x) for x in item['b'].split(',')]
                
                # 区域检查
                if region is not None:
                    if (bounds[2] < region[0] or  # 文本在区域左边
                        bounds[0] > region[2] or  # 文本在区域右边
                        bounds[3] < region[1] or  # 文本在区域上边
                        bounds[1] > region[3]):   # 文本在区域下边
                        continue
                
                # 执行正则匹配
                if regex.search(item['t']):
                    return True, item
            return None, None
            
        except Exception as e:
            _Log.Log_.ex(e, "FindUI 指令执行失败")
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
            _Log.Log_.ex(e, '检查系统类型失败')
            return False

    lastAppName = None
    @classmethod
    def openApp(cls, appName):
        if not appName:
            return False
        if cls.android is None:
            return False
        """打开应用"""
        log = _Log.Log_
        try:
            # 检查应用是否已经打开
            curApp = cls.getCurrentApp()
            if curApp and curApp.get('appName') == appName:
                return "i->应用已打开"
            
            # 根据系统类型选择打开方式
            if cls._isHarmonyOS():
                log.i(f"使用鸿蒙系统方式打开应用: {appName}")
                cls.goHome()
                cls.click(appName, 'LR', 500)                
                # # 尝试在不同屏幕上查找并打开应用
                # opened = False
                # direction = 'CL'  # 先向左滑动
                
                # # 防止无限循环，最多尝试8个屏幕
                # max_screens = 8
                # screen_count = 0
                
                # while not opened and screen_count < max_screens:
                #     # 尝试点击打开应用
                #     ret = cls._openAppByClick(appName)
                #     if ret:
                #         log.i(f"成功点击打开应用: {appName}")
                #         opened = True
                #         break
                    
                #     # 应用未找到，尝试滑动到下一屏
                #     log.i(f"应用未找到，滑动屏幕: {direction}")
                #     ok = cls.switchScreen(direction)
                    
                #     # 滑动成功，继续在新屏幕上查找
                #     if ok:
                #         screen_count += 1
                #         continue
                    
                #     # 滑动失败或屏幕内容未变化，尝试反方向
                #     if direction == 'CL':
                #         direction = 'CR'  # 改为向右滑动
                #         screen_count = 0  # 重置计数
                #     else:
                #         # 两个方向都尝试过，退出循环
                #         log.i("左右滑屏都失败，无法找到应用")
                #         break
            else:
                # Android系统使用服务方式打开
                log.i(f"使用Android系统服务打开应用: {appName}")
                opened = cls.android.openApp(appName)
            if opened:
                cls.lastAppName = appName
            return opened
        except Exception as e:
            log.ex(e, "打开应用失败")
            return False

    @classmethod
    def closeApp(cls, app_name: str = None) -> bool:
        try:
            if not app_name:
                app_name = cls.lastAppName
            _Log.Log_.i(cls.Tag, f"Closing app: {app_name}")
            if cls.android:
                return cls.android.closeApp(app_name)
            return False
        except Exception as e:
            _Log.Log_.ex(e, '打开应用失败')
            return False

    @classmethod
    def _openAppByClick(cls, app_name: str) -> bool:
        """通过点击方式打开应用（适用于鸿蒙系统）"""
        try:
            nodes = cls.android.findTextNodes()
            targetNode = next((node for node in nodes if app_name in node.getText()), None)
            if not targetNode:
                _Log.Log_.e(cls.Tag, f"App icon not found: {app_name}")
                return False
            
            bounds = targetNode.getBounds()
            if not cls.android.click(bounds.centerX(), bounds.centerY()):
                _Log.Log_.e(cls.Tag, "Failed to click app icon")
            return True
            
        except Exception as e:
            _Log.Log_.ex(e, f"Failed to open app by click: {str(e)}")
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
            if cls.android:
                cls.android.showToast(str(msg), 
                                duration or cls.TOAST_LENGTH_LONG,
                                gravity or cls.TOAST_GRAVITY_BOTTOM,
                                xOffset, yOffset)
            else:
                print(f"Toast: {msg}")
        except Exception as e:
            print(f"显示Toast失败: {e}")
            print(msg)

    @classmethod
    def getCurrentApp(cls, period=60):
        """获取当前正在运行的应用信息
        
        Args:
            period: 查询最近使用应用的时间范围(秒)，默认60秒
            
        Returns:
            dict: 包含包名(packageName)和应用名(appName)的字典，失败返回None
        """
        try:
            # _Log.Log_.i("获取当前应用222")
            if not cls.android:
                _Log.Log_.e("获取当前应用失败: 未找到Android实例")
                return None
            
            # 显式传递period参数
            result = cls.android.getCurrentApp(period)
            if result is None:
                return None
            
            return {
                "packageName": result.get("packageName"),
                "appName": result.get("appName"),
                "lastUsed": result.get("lastUsed")
            }
        except Exception as e:
            _Log.Log_.ex(e, "获取当前应用失败")
            return None

    @classmethod
    def isHome(cls) -> bool:
        """判断当前是否在桌面
        
        通过当前应用包名判断是否在桌面，支持多种桌面应用
        
        Returns:
            bool: 是否在桌面
        """
        log = _G.G.Log()
        try:
            # 常见桌面应用包名列表
            LAUNCHER_PACKAGES = {
                'com.android.launcher3',         # 原生Android
                'com.google.android.apps.nexuslauncher', # Pixel
                'com.sec.android.app.launcher',  # 三星
                'com.huawei.android.launcher',   # 华为
                'com.miui.home',                 # 小米
                'com.oppo.launcher',             # OPPO
                'com.vivo.launcher',             # vivo
                'com.realme.launcher',           # Realme
                'com.oneplus.launcher'           # 一加
            }
            
            # 获取当前应用信息
            app_info = cls.getCurrentApp()
            if not app_info:
                log.w("获取当前应用信息失败，无法判断是否在桌面")
                return False
            
            package_name = app_info.get("packageName", "")
            # _Log.Log_.i(f"当前应用包名: {package_name}")
            
            # 检查是否在已知桌面包名列表中
            if package_name in LAUNCHER_PACKAGES:
                # _Log.Log_.i(f"当前在桌面 (已知桌面包名)")
                return True
            
            # 检查包名是否包含launcher或home关键词
            if "launcher" in package_name.lower() or "home" in package_name.lower():
                # _Log.Log_.i(f"当前在桌面 (包名包含launcher或home)")
                return True
            # _Log.Log_.i(f"当前不在桌面")
            return False
        except Exception as e:
            log.ex(e, "判断是否在桌面失败")
            return False

    @classmethod
    def goHome(cls):
        """统一返回桌面实现"""
        if cls.android:
            return cls.android.goHome()
        return False

    @classmethod
    def goBack(cls):
        """统一返回上一页实现"""
        if cls.android:
            return cls.android.goBack()
        return False
    _screenText = None
    @classmethod
    def swipe(cls, param: str) -> bool:
        """统一处理滑动操作
        支持两种格式:
        1. 坐标格式: "x1,y1 > x2,y2 [duration]"
        2. 方向枚举: "方向 [duration]"
        
        支持的方向:
        CR - 从中心向右滑动
        CL - 从中心向左滑动  
        CU - 从中心向上滑动
        CD - 从中心向下滑动
        ER - 从左边缘向右滑动
        EL - 从右边缘向左滑动
        EU - 从底部向上滑动
        ED - 从顶部向下滑动
        """
        log = _Log.Log_
        try:
            android = cls.android
            if not android:
                log.e("滑动失败:未找到Android实例")
                return False
                
            # 默认持续时间为0.5秒
            default_duration = 500

            # 使用正则表达式解析参数
            match = re.match(r"(?P<start>\d+,\d+)\s*>\s*(?P<end>\d+,\d+)(?:\s+(?P<duration>\d+))?", param)
            if match:
                # 解析为坐标
                start = match.group("start")
                end = match.group("end")
                duration_str = match.group("duration")
                
                # 检查 duration 是否为数字
                duration = int(duration_str) if duration_str and duration_str.isdigit() else default_duration
                startX, startY = map(int, start.split(','))
                endX, endY = map(int, end.split(','))
                # log.i(f"滑动指令: 开始位置({startX}, {startY}), 结束位置({endX}, {endY}), 持续时间: {duration} ms")
                return android.swipe(startX, startY, endX, endY, duration)
            else:
                # 解析为枚举
                parts = param.split()
                direction = parts[0]
                duration = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else default_duration
                # log.i(f"滑动指令: 方向({direction}), 持续时间: {duration} ms")
                return android.sweep(direction, duration)
                
        except Exception as e:
            log.ex(e, "滑动失败")
            return False

    # @classmethod
    # def switchScreen(cls, direction: str):
        """切换屏幕
        
        Args:
            direction: 滑动方向 ('CL'/'CR'/'CU'/'CD')
            
        Returns:
            bool: 是否切换成功
        """
        if not cls.isHome():
            _Log.Log_.i("当前不在桌面, 不能切屏")
            return False

        # 使用 swipe 方法进行滑动
        if not cls.swipe(f"{direction} 500"):
            return False

        time.sleep(0.5)
        
        # 检查屏幕内容变化
        text = cls.android.getScreenText()
        similarity = 0
        
        # 计算屏幕内容变化的相似度
        if cls._screenText is None:
            similarity = 0
        elif cls._screenText == text:
            similarity = 1
        else:
            # 计算文本相似度
            oldTexts = set(cls._screenText.split())
            newTexts = set(text.split())
            # 计算交集和并集
            intersection = oldTexts.intersection(newTexts)
            union = oldTexts.union(newTexts)
            # 计算Jaccard相似度
            similarity = len(intersection) / len(union) if union else 1.0
            
        # 如果相似度低于0.9，说明屏幕内容有显著变化
        screenChanged = similarity < 0.9
        if screenChanged:
            cls._screenText = text
            return True
        return False

    @classmethod
    def clickText(cls, text: str, region=None) -> bool:
        """点击文本（增加重试机制）"""
        retry = 3
        while retry > 0:
            match, item = cls.matchScreenText(text, region)
            if match:
                x, y = cls.toPos(item)
                return cls.android.click(x, y)
            time.sleep(1)
            retry -= 1
        return False

    @classmethod 
    def switchToProfile(cls):
        """跳转到个人页示例"""
        cls.swipe("CD 800")  # 向下滑动

    @classmethod
    def findText(cls, text, searchDir=None, distance=None):
        """增强版文字查找，支持滑动查找
        Args:
            text: 要查找的文字
            searchDir: 滑动方向 L/R/U/D/LR/UD
            distance: 滑动距离（像素）
        Returns: (x,y) 或 None
        """
        try:
            log = _Log.Log_
            maxTry = 8  # 最大尝试次数
            triedDirs = set()
            lastText = ""
            
            def tryFind():
                nonlocal lastText
                cls.refreshScreenInfos()
                match, item = cls.matchScreenText(text)
                if match: 
                    return cls.toPos(item)
                # 计算屏幕内容相似度
                curText = cls.android.getScreenText() if cls.android else ""
                similarity = cls._calcSimilarity(lastText, curText)
                lastText = curText
                return None, similarity

            # 首次尝试
            pos, _ = tryFind()
            if pos: return pos
            if searchDir is None:
                return None
            # 解析滑动方向
            dirs = []
            if 'L' in searchDir: dirs.append('CL')
            if 'R' in searchDir: dirs.append('CR')
            if 'U' in searchDir: dirs.append('CU') 
            if 'D' in searchDir: dirs.append('CD')
            
            # 自动设置滑动距离
            if not distance:
                metrics = cls.android.getDisplayMetrics() if cls.android else (1080, 1920)
                distance = int(metrics[0]*0.3) if searchDir in ('L','R','LR') else int(metrics[1]*0.3)

            for _ in range(maxTry):
                for dir in dirs:
                    if dir in triedDirs: continue
                    
                    log.i(f"向{dir}方向滑动{distance}px查找[{text}]")
                    cls.swipe(f"{dir} {distance}")
                    time.sleep(0.5)
                    
                    pos, similarity = tryFind()
                    if pos: return pos
                    if similarity >= 0.95: 
                        triedDirs.add(dir)  # 该方向已到头
                        log.i(f"{dir}方向滑动无效")
            return None
        except Exception as e:
            log.ex(e, "文字查找失败")
            return None
    
    @classmethod
    def inRect(cls, text, region):
        """判断文本是否在指定区域内"""
        try:
            pos = cls.findText(text)
            if pos:
                x, y = pos
            left, top, right, bottom = region
            if left > 0 and not (left <= x <= right):
                return False
            if top > 0 and not (top <= y <= bottom):
                return False
                return True
            return False
        except Exception as e:
            log.ex(e, "判断文本是否在指定区域内失败")
            return False
    
    @classmethod    
    def click(cls, text, searchDir=None, distance=None) -> bool:
        """点击文本（增加重试机制）"""
        pos = cls.findText(text, searchDir, distance)
        if pos:
            return cls.android.click(pos[0], pos[1])
        return False
    

    @classmethod
    def _calcSimilarity(cls, text1, text2):
        """计算文本相似度"""
        if not text1 or not text2: return 0
        set1 = set(text1.split())
        set2 = set(text2.split())
        intersection = set1 & set2
        union = set1 | set2
        return len(intersection)/len(union) if union else 0

def requireAndroid(func):
    def wrapper(*args, **kwargs):
        if not _Log.Log_.isAndroid():
            return "w->Android指令，当前环境不支持"
        return func(*args, **kwargs)
    # 保持原始函数的属性
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

CTools_.init()

