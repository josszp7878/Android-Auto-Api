from __future__ import annotations
import time
import _G
import re
from typing import Optional, TYPE_CHECKING, Any
import _Tools

if TYPE_CHECKING:
    import _App

    

class RegionCheck:
    """区域检查工具类"""

    def __init__(self):
        self.region = None

    @classmethod
    def parse(cls, text: str) -> tuple['RegionCheck', str]:
        check = RegionCheck()
        text1, coords = _Tools._Tools_.toPos(text)
        if coords is None:
            return None, text
        check.region = (coords[0] if coords[0] is not None else 0,
                        coords[1] if coords[1] is not None else 0,
                        coords[2] if coords[2] is not None else 0,
                        coords[3] if coords[3] is not None else 0)
        return check, text1

    def __str__(self):
        return f"RegionCheck(region={self.region})"

   
    def _convertValue(self, value, isX=True):
        """转换负值为屏幕相对值"""
        if value >= 0:
            return value
        screenW, screenH = CTools_.screenSize
        base = screenW if isX else screenH
        return base + value  # 负值相加等于减去绝对值

    def isIn(self, x, y):
        """判断坐标是否在区域内（支持负值）"""
        # 转换负值坐标
        x_min = self._convertValue(self.region[0], True)
        x_max = self._convertValue(self.region[1], True)
        y_min = self._convertValue(self.region[2], False)
        y_max = self._convertValue(self.region[3], False)
        log = _G._G_.Log()
        x_ok = True
        if x_min > 0:
            x_ok = x >= x_min
        if x_max > 0:
            x_ok = x_ok and x <= x_max

        y_ok = True
        if y_min > 0:
            y_ok = y >= y_min
        if y_max > 0:
            y_ok = y_ok and y <= y_max
        if x_ok and y_ok:
            return True
        else:
            log.w(f"判断坐标:{x},{y} 不在区域: {x_min},{x_max},{y_min},{y_max} 内")
            return False

    def isRectIn(self, x1, y1, x2, y2):
        """判断矩形是否在区域内"""
        return self.isIn(x1, y1) and self.isIn(x2, y2)


class CTools_(_Tools._Tools_):
    Tag = "CTools"
    port = 5000
    android = None
    

    screenSize: tuple[int, int] = (1080, 1920)
    # 坐标修正范围,不知道为什么，文字识别拷屏后的位置和实际位置有偏差，而且不是固定的
    # 从屏幕上方到下发，偏差逐步增大，所以需要定义一个修正范围。获取坐标是根据y坐标来修正的
    # 来线性修正范围从0到PoxFixScope
    _fixFactor = 0
    @classmethod
    def setPosFixScope(cls, scope):
        log = _G._G_.Log()
        cls._fixFactor = scope/cls.screenSize[1]
        log.i(f"@@@坐标修正范围: {scope}, 修正比例: {cls._fixFactor}")
    @classmethod
    def _initScreenSize(cls)->tuple[int, int]:
        """获取屏幕尺寸"""
        screenSize = (1080, 1920)
        log = _G._G_.Log()
        try:

            if CTools_.android:
                # 尝试通过Android Context获取屏幕尺寸
                context = CTools_.android.getContext()
                if context:
                    resources = context.getResources()
                    if resources:
                        metrics = resources.getDisplayMetrics()
                        if metrics:
                            screenSize = (metrics.widthPixels, metrics.heightPixels)
        except Exception as e:
            log.e(f"获取屏幕尺寸失败: {e}")
        cls.screenSize = screenSize
        cls.setPosFixScope(140)
        return screenSize
    
    # 简化的输入处理函数
    @classmethod
    def onInput(cls, inputText):
        _G._G_().CmdMgr().do(inputText)
        
    
    _screenInfoCache = None
    @classmethod
    def getScreenInfo(cls, refresh=False)->list[dict]:
        """获取屏幕信息
        Args:
            refresh: 是否刷新缓存
            
        Returns:
            list: 屏幕信息列表
        """
        log = _G._G_.Log()
        log.log_(f"获取屏幕信息 android={cls.android} refresh={refresh}")
        if cls.android is None:
            return cls._screenInfoCache
        if cls._screenInfoCache is None or refresh:
            cls._screenInfoCache = cls.refreshScreenInfos()
        return cls._screenInfoCache

    @classmethod
    def setScreenInfo(cls, screenInfo):
        """设置屏幕信息缓存
        
        Args:
            screenInfo: 屏幕信息，可以是JSON字符串或对象
        """
        try:
            log = _G._G_.Log()
            if screenInfo is None or screenInfo.strip() == '':
                return False
            # 如果是字符串，尝试解析为JSON
            import json
            try:
                screenInfo = json.loads(screenInfo)
            except json.JSONDecodeError as e:
                log.e(f"JSON解析错误: {e} \n json=\n{screenInfo}")
                return False
            
            # 保存到缓存
            cls._screenInfoCache = screenInfo
            log.i(f"屏幕信息已设置，共{len(screenInfo)}个元素")
            return True
        except Exception as e:
            log = _G._G_.Log()
            log.ex(e, "设置屏幕信息失败")
            return False


    @classmethod
    def toPos(cls, item: dict):
        bounds = [int(x) for x in item['b'].split(',')]
        centerX = (bounds[0] + bounds[2]) // 2
        centerY = (bounds[1] + bounds[3]) // 2
        return (centerX, centerY)

    @classmethod
    def refreshScreenInfos(cls) -> list:
        """获取并解析屏幕信息,支持缓存"""
        log = _G._G_.Log()
        # log.i(f'获取屏幕信息 android={cls.android}')
        try:
            android = cls.android
            if not android:
                return cls._screenInfoCache

            info = cls.android.getScreenInfo()
            if info is None:
                log.e("获取屏幕信息失败")
                return []
            size = info.size()
            result = []
            # print(f"获取屏幕信息 size={size}")
            for i in range(size):
                item = info.get(i)
                result.append({
                    't': item.get('t').replace('\n', ' ').replace('\r', ''),
                    'b': item.get('b')
                })
            # log.i(f"获取屏幕信息 info={result}")
            # 更新缓存
            cls._screenInfoCache = result
            return result
        except Exception as e:
            log.ex(e, "获取屏幕信息失败")
            return []

    @classmethod
    def matchTexts(cls, str: str, refresh=False) -> bool:
        """匹配多个文本条件
        
        Args:
            str: 要匹配的文本条件，支持&(与)和|(或)连接符
            refresh: 是否刷新屏幕信息
            
        Returns:
            bool: 是否匹配成功
        """
        log = _G._G_.Log()
        try:
            # 如果没有连接符，直接调用matchText
            if '&' not in str and '|' not in str:
                return cls.matchText(str, refresh) is not None
            
            # 处理OR条件
            orParts = str.split('|')
            for orPart in orParts:
                # 处理AND条件
                andParts = orPart.split('&')
                allMatch = True
                
                for andPart in andParts:
                    part = andPart.strip()
                    if not part:
                        continue
                    
                    if not cls.matchText(part, refresh):
                        allMatch = False
                        break
                
                # 如果一个OR部分的所有AND条件都满足，则返回True
                if allMatch:
                    return True
            
            # 所有OR部分都不满足
            return False
        except Exception as e:
            log.ex(e, f"匹配多个文本条件失败: {str}")
            return False

    @classmethod
    def matchText(cls, str: str, refresh=False):
        """匹配文本，并可选择在特定区域内查找
        
        Args:
            str: 要匹配的文本或带区域的文本表达式
            refresh: 是否刷新屏幕信息
            
        Returns:
            匹配成功的第一个元素或None
        """
        try:
            if not str or str.strip() == '':
                return None
                
            log = _G._G_.Log()
            
            # 解析区域信息
            region, text = RegionCheck.parse(str)
            
            # 获取屏幕信息
            items = cls.getScreenInfo(refresh)
            if not items or len(items) == 0:
                log.w("屏幕信息为空")
                return None
                
            # 先匹配文本
            matchedItems = cls.regexMatchItems(text, items)            
            # 没有匹配到文本
            if not matchedItems:
                log.w(f"未找到匹配文本: {text}")
                return None
                
            # 确保matchedItems是列表
            if not isinstance(matchedItems, list):
                matchedItems = [matchedItems]
                
            # 如果需要区域过滤
            if region:
                # 过滤在指定区域内的项
                inRegionItems = []
                for item in matchedItems:
                    b = item['b']
                    bounds = [int(x) for x in b.split(',')]
                    isIn = region.isRectIn(bounds[0], bounds[1], bounds[2], bounds[3])
                    if isIn:
                        inRegionItems.append(item)
                        
                matchedItems = inRegionItems
                if len(matchedItems) == 0:
                    log.w("区域匹配失败")
                    return None
                log.i(f"区域匹配成功，共{len(matchedItems)}个结果")
            
            # 打印调试信息，如果匹配到多个结果
            if len(matchedItems) > 1:
                log.i(f"匹配到多个文本: {[item.get('t') for item in matchedItems]}")
            
            # 返回第一个匹配项
            if matchedItems:
                log.i(f"匹配到文本: {matchedItems[0].get('t')}")
                return matchedItems[0]
            return None
            
        except Exception as e:
            log.ex(e, f"匹配文本失败: {str}")
            return None

    


    @classmethod
    def isHarmonyOS(cls) -> bool:
        """检查是否是鸿蒙系统"""
        log = _G._G_.Log()
        try:
            # 检查系统属性中是否包含鸿蒙特征
            from android.os import Build
            manufacturer = Build.MANUFACTURER.lower()
            return "huawei" in manufacturer or "honor" in manufacturer
        except Exception as e:
            log.ex(e, '检查系统类型失败')
            return False


    # 打开应用返回值
    # 0: 打开失败
    # 1: 打开成功
    # 2: 打开未知应用
    @classmethod
    def openApp(cls, appName:str) ->bool:
        if not appName:
            return False
        g = _G._G_
        log = g.Log()
        opened = False
        appName = appName.strip().lower()
        try:
            if appName == _G.TOP:
                return cls.goHome()
            if cls.android is None:
                opened = cls.click(appName)
            else:
                # 根据系统类型选择打开方式
                if cls.isHarmonyOS():
                    opened = cls.click(f'{appName}(y-150)', 'LR')
                else:
                    # Android系统使用服务方式打开
                    opened = cls.android.openApp(appName)
            return opened
        except Exception as e:
            log.ex(e, "打开应用失败")
            return False

    @classmethod
    def closeApp(cls, app_name: str = None) -> bool:
        log = _G._G_.Log()
        try:
            # log.i(cls.Tag, f"Closing app: {app_name}")
            if cls.android:
                return cls.android.closeApp(app_name)
            return True
        except Exception as e:
            log.ex(e, '打开应用失败')
            return False

   
    # 添加Toast常量
    TOAST_LENGTH_SHORT = 0  # Toast.LENGTH_SHORT
    TOAST_LENGTH_LONG = 1   # Toast.LENGTH_LONG
    TOAST_GRAVITY_TOP = 48    # Gravity.TOP
    TOAST_GRAVITY_CENTER = 17  # Gravity.CENTER
    TOAST_GRAVITY_BOTTOM = 80  # Gravity.BOTTOM

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
                cls.android.toast(str(msg),
                                      duration or cls.TOAST_LENGTH_LONG,
                                      gravity or cls.TOAST_GRAVITY_BOTTOM,
                                      xOffset, yOffset)
            else:
                print(f"Toast: {msg}")
        except Exception as e:
            print(f"显示Toast失败: {e}")
            print(msg)
            


    @classmethod
    def getCurrentAppInfo(cls) -> Optional[dict]:
        """获取当前运行的应用信息
        
        Returns:
            dict: 应用信息，包含包名等
        """
        g = _G._G_
        log = g.Log()
        android = g.Tools().android    
        # log.i(f'获取当前应用信息 android={android}')
        if android is None:
            return None
        try:
            # 获取当前应用信息
            appInfo = android.getCurrentApp(200)
            # log.i(f'获取当前应用信息 appInfo={appInfo}')
            return appInfo
        except Exception as e:
            log.ex(e, "获取当前应用信息失败")
            return None
        
    @classmethod
    def isHome(cls) -> bool:
        """判断当前是否在桌面
        通过当前应用包名判断是否在桌面，支持多种桌面应用
        Returns:
            bool: 是否在桌面
        """
        if cls.android is None:
            return True
        log = _G._G_.Log()
        try:
            # 常见桌面应用包名列表
            LAUNCHER_PACKAGES = {
                'com.android.launcher3',         # 原生Android
                'com.google.android.apps.nexuslauncher',  # Pixel
                'com.sec.android.app.launcher',  # 三星
                'com.huawei.android.launcher',   # 华为
                'com.miui.home',                 # 小米
                'com.oppo.launcher',             # OPPO
                'com.vivo.launcher',             # vivo
                'com.realme.launcher',           # Realme
                'com.oneplus.launcher'           # 一加
            }

            # 获取当前应用信息
            app_info = cls.getCurrentAppInfo()
            if not app_info:
                log.w("获取当前应用信息失败，无法判断是否在桌面")
                return False

            # 修复: 正确处理Java的LinkedHashMap
            # 方法1: 使用Java的get方法，只传一个参数
            package_name = app_info.get("packageName")
            if package_name is None:
                package_name = ""
            

            # 检查是否在已知桌面包名列表中
            if package_name in LAUNCHER_PACKAGES:
                return True

            # 检查包名是否包含launcher或home关键词
            if "launcher" in package_name.lower() or "home" in package_name.lower():
                return True
            
            return False
        except Exception as e:
            log.ex(e, "判断是否在桌面失败")
            return False

    @classmethod
    def curAppIs(cls, appName: str) -> bool:
        """判断当前应用是否是目标应用"""
        try:
            tools = _G._G_.CTools()
            if tools.isTop(appName):
                return cls.isHome()
            curApp = cls.getCurrentAppInfo()
            if not curApp:
                return False
            if '.' in appName:
                return curApp.get('packageName') == appName
            else:
                return curApp.get('appName') == appName
        except Exception as e:
            _G._G_.Log().ex(e, "判断当前应用失败")
            return False
        
    @classmethod
    def goHome(cls)->bool:
        """统一返回桌面实现"""
        if cls.android:
            if not cls.android.goHome():
                return False
        return True     

    @classmethod
    def goBack(cls)->bool:
        """统一返回上一页实现"""
        log = _G._G_.Log()
        log.i("<<")
        if cls.android:
            return cls.android.goBack()
        else:
            return True
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
        log = _G._G_.Log()
        # log.i(f"<>: {param}")
        try:
            android = cls.android
            # 默认持续时间为0.5秒
            default_duration = 500

            # 使用正则表达式解析参数
            match = re.match(
                r"(?P<start>\d+,\d+)\s*>\s*(?P<end>\d+,\d+)(?:\s+(?P<duration>\d+))?", param)
            if match:
                # 解析为坐标
                start = match.group("start")
                end = match.group("end")
                duration_str = match.group("duration")

                # 检查 duration 是否为数字
                duration = int(
                    duration_str) if duration_str and duration_str.isdigit() else default_duration
                startX, startY = map(int, start.split(','))
                endX, endY = map(int, end.split(','))
                # log.i(f"滑动指令: 开始位置({startX}, {startY}), 结束位置({endX}, {endY}), 持续时间: {duration} ms")
                if android:
                    return android.swipe(startX, startY, endX, endY, duration)
                else:
                    return False
            else:
                # 解析为枚举
                parts = param.split()
                direction = parts[0]
                duration = int(parts[1]) if len(
                    parts) > 1 and parts[1].isdigit() else default_duration
                # log.i(f"滑动指令: 方向({direction}), 持续时间: {duration} ms")
                if android:
                    return android.sweep(direction, duration)
                else:
                    return False

        except Exception as e:
            log.ex(e, "滑动失败")
            return False

    @classmethod
    def switchScreen(cls, direction: str):
        """切换屏幕
        
        Args:
            direction: 滑动方向 ('CL'/'CR'/'CU'/'CD')
            
        Returns:
            bool: 是否切换成功
        """
        if not cls.isHome():
            log.i("当前不在桌面, 不能切屏")
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
    def click(cls, text: str, direction: str = None, waitTime: int = 1) -> bool:
        """点击文本（支持偏移）
        """
        
        log = _G._G_.Log()
        # 尝试使用parsePos解析带括号的格式
        parsed_text, coords = _Tools._Tools_.toPos(text)
        offset = (0, 0)
        log.i(f"click: {text} 解析结果: {parsed_text}, {coords}")
        if parsed_text is None:
            #纯坐标
            if coords is None:
                log.w(f"click:  {text} 解析失败")
                return False
            else:
                x = coords[0] if len(coords) > 0 else 0
                y = coords[1] if len(coords) > 1 else 0
                pos = (x, y)
        else:
            offset = None
            if coords:
                offset = (coords[0], coords[1])
            # 查找文本位置
            pos = cls.findTextPos(parsed_text, direction)
            if pos is None:
                log.w(f"{parsed_text} 位置未找到")
                return cls.android is None
        return cls.clickPos(pos, offset)
    
    @classmethod
    def clickPos(cls, pos, offset=(0, 0)):
        """点击文本（支持偏移）"""
        log = _G._G_.Log()
        try:
            log.i(f"点击位置: {pos}，偏移:{offset}")
            x = pos[0]
            y = pos[1]
            if offset:
                x += offset[0] or 0
                y += offset[1] or 0
            android = cls.android
            if android:
                return android.click(x, y)
            else:
                return True
        except Exception as e:
            log.ex(e,f"点击失败")
            return False

    @classmethod
    def switchToProfile(cls):
        """跳转到个人页示例"""
        cls.swipe("CD 800")  # 向下滑动

    @classmethod
    def swipeTo(cls, direction, matchFunc, maxTry=3):
        """智能滑动查找
        
        Args:
            direction: 滑动方向，支持单向(L/R/U/D)和双向(LR/UD)
            matchFunc: 匹配函数，接收无参数并返回匹配结果，找到返回True
            maxTry: 最大尝试次数，默认10次
            
        Returns:
            bool: 是否找到匹配内容
        """
        direction = direction.upper()
        log = _G._G_.Log()        
        # 检查初始屏幕是否匹配
        if matchFunc():
            return True
        
        # 解析方向
        primary_dir = direction[0]  # 主方向
        has_secondary = len(direction) > 1  # 是否有次方向
        secondary_dir = direction[1] if has_secondary else None
        
        # 方向映射到滑动命令
        dir_to_cmd = {
            'L': 'CL',
            'R': 'CR',
            'U': 'CU',
            'D': 'CD'
        }
        
        # 开始主方向滑动
        current_dir = primary_dir
        tries = 0
        lastScreen = None
        
        while tries < maxTry:
            # 获取当前屏幕内容用于相似度比较
            currentScreen = cls.refreshScreenInfos()
            if currentScreen is None:
                tries += 1
                continue
            # log.i(f"当前屏幕内容: {currentScreen}")
            
            # 检查是否已经到达边界(屏幕内容相似度高)
            if lastScreen and cls.isScreenSimilar(currentScreen, lastScreen):
                log.i(f"方向{current_dir}已到达边界")
                
                # 如果支持双向且当前是主方向，切换到次方向
                if has_secondary and current_dir == primary_dir:
                    current_dir = secondary_dir
                    log.i(f"切换到次方向: {current_dir}")
                    lastScreen = None  # 重置屏幕比较
                    tries = 0  # 重置尝试次数
                    continue
                else:
                    # 单向或已尝试次方向，结束查找
                    log.i("所有方向都已尝试，未找到匹配")
                    return False
            
            lastScreen = currentScreen            
            # 执行滑动
            cmd = dir_to_cmd.get(current_dir)
            if not cmd:
                log.e(f"无效的滑动方向: {current_dir}")
                return False
            
            # log.i(f"第{tries+1}次滑动，方向: {cmd}")
            cls.swipe(f"{cmd} 500")
            time.sleep(2)  # 等待滑动完成
            # 检查滑动后是否匹配
            if matchFunc():
                log.i(f"在方向{current_dir}的第{tries+1}次滑动后找到匹配")
                return True
            tries += 1
        
        log.i(f"达到最大尝试次数({maxTry})，未找到匹配")
        return False

    # return (x,y)
    @classmethod
    def findTextPos(cls, text, searchDir=None):
        """增强版文本查找功能
        支持在滑动屏幕过程中持续查找文字
        
        Args:
            text: 要查找的文本
            searchDir: 搜索方向，如 L/R/U/D(单向) 或 LR/UD(双向)
        Returns:
            找到文本的坐标元组(x,y)或None
        """
        # 尝试在当前屏幕查找
        log = _G._G_.Log()
        log.i(f"查找文本: {text}")
        pos = cls._findTextPos(text)
        if pos is None:
            return None
        # _Log.c.i(f"findTextPos: {pos}")
        if pos or not searchDir:
            return pos
        # 定义匹配函数
        def matchFunc():
            nonlocal pos
            pos = cls._findTextPos(text)
            return pos is not None
        # 使用swipeTo进行滑动查找
        found = cls.swipeTo(searchDir, matchFunc)
        # _Log.c.i(f"findTextPos: {pos}")
        return pos if found else None
    
    
    @classmethod
    def _findTextPos(cls, text):
        """在当前屏幕尝试查找文本
        Args:
            text: 要查找的文本
        Returns:
            找到文本的坐标元组(x,y)或None
        """
        text = text.strip() if text else ''
        if text == '':
            return None
        log = _G._G_.Log()
        try:
            # 使用matchText查找文本
            result = cls.matchText(text, True)
            # log.i(f"匹配{text}结果: {result}")
            if result:
                # 从匹配结果中获取坐标
                bounds = [int(x) for x in result['b'].split(',')]
                x = (bounds[0] + bounds[2]) // 2
                y = (bounds[1] + bounds[3]) // 2
                # log.i(f"修正比例: {cls._fixFactor}")
                fixY = int(cls._fixFactor*y)
                # log.i(f"修正Y坐标: {fixY}")
                return (x, y + fixY)
            # log.i(f"屏幕上未找到文本: {text}")
            return None
        except Exception as e:
            log.ex(e, f"查找文本异常")
            return None

    @classmethod
    def isScreenSimilar(cls, screen1, screen2):
        """
        比较两个屏幕文本是否相似，考虑文本内容和位置
        """
        if not screen1 or not screen2:
            return False
        
        # 创建可哈希的元组表示每个文本项
        def to_hashable(items):
            return [tuple([item.get('t', ''), item.get('b', '')]) for item in items]
        
        hashable1 = to_hashable(screen1)
        hashable2 = to_hashable(screen2)
        
        # 使用可哈希的元组进行集合操作
        common = set(hashable1).intersection(set(hashable2))
        
        # 计算相似度
        total = len(set(hashable1).union(set(hashable2)))
        if total == 0:
            return False
        
        similarity = len(common) / total
        return similarity > 0.7  # 相似度阈值

    @classmethod
    def onLoad(cls, old):
        if old:
            cls._screenInfoCache = old._screenInfoCache
        log = _G._G_.Log()
        try:
            android = cls.android
            from java import jclass
            android = jclass(
                "cn.vove7.andro_accessibility_api.demo.script.PythonServices")
            android.onInput(cls.onInput)
            cls.android = android
            # log.i(f'初始化CTools模块2222 {cls.android}')
            cls._initScreenSize()
        except Exception as _:
            pass    
        return True
   
CTools_.onLoad(None)
