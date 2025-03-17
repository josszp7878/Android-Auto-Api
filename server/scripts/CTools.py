from __future__ import annotations
import time
import _G
import re



class RegionCheck:
    """区域检查工具类"""

    def __init__(self):
        self.region = None

    @classmethod
    def parse(cls, text: str) -> tuple['RegionCheck', str]:
        """
        支持新格式：
        - 传统格式：[x1,x2,y1,y2]
        - Y轴简写：y<min>,<max> 或 y<value>
        - X轴简写：x<min>,<max> 或 x<value>
        - 支持正负数值
        """
        check = RegionCheck()
        match = re.search(
            r'([\s\S]*?)\s*\[([\d,\-\+，x,X,y,Y,\s]+)\]',  # 支持数字、负号、加号等
            text.strip(),
            re.DOTALL
        )
        
        if not match:
            return None, text
        
        region_config = match.group(2)
        text = match.group(1)
        
        try:
            # 解析特殊格式
            if region_config.startswith(('y', 'Y')):
                # 处理Y轴简写
                y_part = region_config[1:].replace('，', ',')
                y_values = [int(v) for v in y_part.split(',') if v.strip()]
                check.region = check._toY(y_values)
            elif region_config.startswith(('x', 'X')):
                # 处理X轴简写
                x_part = region_config[1:].replace('，', ',')
                x_values = [int(v) for v in x_part.split(',') if v.strip()]
                check.region = check._toX(x_values)
            else:
                # 传统格式处理
                nums = region_config.strip('[]').split(',')
                values = [int(v) for v in nums if v.strip()]
                check.region = values + [0]*(4-len(values))
        except ValueError as e:
            # 统一处理格式错误
            log = _G._G_.Log()
            log.e(f"区域格式错误: {region_config}, {str(e)}")
            return None, text
        
        return check, text

    def _toY(self, y_values):
        """处理Y轴简写格式"""
        if len(y_values) == 1:  # y100 → y≥100
            return [0, 0, y_values[0], 0]
        elif len(y_values) == 2:  # y100,200 → 100≤y≤200
            return [0, 0, y_values[0], y_values[1]]
        else:
            raise ValueError("Y轴格式错误")

    def _toX(self, x_values):
        """处理X轴简写格式"""
        if len(x_values) == 1:  # x100 → x≥100
            return [x_values[0], 0, 0, 0]
        elif len(x_values) == 2:  # x100,200 → 100≤x≤200
            return [x_values[0], x_values[1], 0, 0]
        else:
            raise ValueError("X轴格式错误")

    def _getScreenSize(self):
        """获取屏幕尺寸"""
        try:
            if CTools_.android:
                # 尝试通过Android Context获取屏幕尺寸
                context = CTools_.android.getContext()
                if context:
                    resources = context.getResources()
                    if resources:
                        metrics = resources.getDisplayMetrics()
                        if metrics:
                            return (metrics.widthPixels, metrics.heightPixels)
        except Exception as e:
            log = _G._G_.Log()
            log.e(f"获取屏幕尺寸失败: {e}")
        
        # 默认分辨率
        return (1080, 1920)  # 默认分辨率

    def _convertValue(self, value, isX=True):
        """转换负值为屏幕相对值"""
        if value >= 0:
            return value
        screenW, screenH = self._getScreenSize()
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


class CTools_:
    Tag = "CTools"
    port = 5000
    android = None
    

    @classmethod
    def init(cls):
        try:
            if cls.android is None:
                from java import jclass
            cls.android = jclass(
                "cn.vove7.andro_accessibility_api.demo.script.PythonServices")
        except Exception as e:
            return None
    
    _screenInfoCache = None
    @classmethod
    def getScreenInfo(cls, refresh=False):
        """获取屏幕信息
        
        Args:
            refresh: 是否刷新缓存
            
        Returns:
            list: 屏幕信息列表
        """
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
    def Clone(cls, clone):
        g = _G._G_
        # log = g.Log()
        cls._screenInfoCache = clone._screenInfoCache
        # log.i(f'CTools克隆完成 android={cls.android}')
        return True

    # @classmethod
    # def init(cls):
    #     if not hasattr(cls, '_init'):
    #         log = _G._G_.Log()
    #         log.i(f'初始化CTools模块')  # 最简洁的写法
    #         try:
    #             print(f'加载java模块成功 android={cls.android}')
    #             cls._init = True
    #         except ModuleNotFoundError:
    #             log.e('java模块未找到')
    #         except Exception as e:
    #             log.ex(e, '初始化CTools模块失败')

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
        log = _G._G_.Log()
        # log.i(f'获取屏幕信息 android={cls.android}')
        try:
            if cls.android:
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
                log.i(f"获取屏幕信息 info={result}")
                # 更新缓存
                cls._screenInfoCache = result
                return result
            else:
                log.i("非Android环境，无法获取屏幕信息sss")
                return []

        except Exception as e:
            log.ex(e, "获取屏幕信息失败")
            return []

    @classmethod
    def matchScreenText(cls, str: str, refresh=False):
        try:
            # 使用缓存的屏幕信息
            screenInfo = cls.getScreenInfo(refresh)
            log = _G._G_.Log()
            # log.i(f"匹配屏幕文本: {str} in {screenInfo}")
            if not screenInfo:
                log.w("屏幕信息为空")
                return None
            # 解析区域和文本（保持原有逻辑）
            region, text = RegionCheck.parse(str)
            # 生成正则表达式（添加.*通配）
            regex = re.compile(f".*{text}.*")
            # log.i(f"正则表达式: {regex}, regioCheck={region}")
            # 遍历屏幕信息，查找匹配的文本
            # 先匹配文本，将匹配成功的项缓存
            textMatchedItems = []
            for item in screenInfo:
                t = item['t']
                if regex.search(t):
                    textMatchedItems.append(item)
            if len(textMatchedItems) == 0:
                return None
            if region:
                # 再在匹配成功的项中检查区域
                for item in textMatchedItems:
                    b = item['b']
                    bounds = [int(x) for x in b.split(',')]
                    isIn = region.isRectIn(
                        bounds[0], bounds[1], bounds[2], bounds[3])
                    if isIn:
                        log.i(f"区域匹配: {item}")
                        return item
                return None
        except Exception as e:
            log.ex(e, "FindUI 指令执行失败")
        return None

    @classmethod
    def _isHarmonyOS(cls) -> bool:
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

    lastAppName = None

    @classmethod
    def openApp(cls, appName):
        if not appName:
            return False
        if cls.android is None:
            return False
        """打开应用"""
        log = _G._G_.Log()
        try:
            # 检查应用是否已经打开
            curApp = cls.getCurrentApp()
            if curApp and curApp.get('appName') == appName:
                return "i->应用已打开"

            opened = False
            # 根据系统类型选择打开方式
            if cls._isHarmonyOS():
                log.i(f"使用鸿蒙系统方式打开应用: {appName}")
                cls.goHome()
                opened = cls.click(appName, 'LR')
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
        log = _G._G_.Log()
        try:
            if not app_name:
                app_name = cls.lastAppName
            log.i(cls.Tag, f"Closing app: {app_name}")
            if cls.android:
                return cls.android.closeApp(app_name)
            return False
        except Exception as e:
            log.ex(e, '打开应用失败')
            return False

    @classmethod
    def _openAppByClick(cls, app_name: str) -> bool:
        """通过点击方式打开应用（适用于鸿蒙系统）"""
        log = _G._G_.Log()
        try:
            nodes = cls.android.findTextNodes()
            targetNode = next(
                (node for node in nodes if app_name in node.getText()), None)
            if not targetNode:
                log.e(cls.Tag, f"App icon not found: {app_name}")
                return False

            bounds = targetNode.getBounds()
            if not cls.android.click(bounds.centerX(), bounds.centerY()):
                log.e(cls.Tag, "Failed to click app icon")
            return True

        except Exception as e:
            log.ex(e, f"Failed to open app by click: {str(e)}")
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
        log = _G._G_.Log()
        try:
            # _Log._Log_.i("获取当前应用222")
            if not cls.android:
                log.e("获取当前应用失败: 未找到Android实例")
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
            log.ex(e, "获取当前应用失败")
            return None

    @classmethod
    def isHome(cls) -> bool:
        """判断当前是否在桌面

        通过当前应用包名判断是否在桌面，支持多种桌面应用

        Returns:
            bool: 是否在桌面
        """
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
            app_info = cls.getCurrentApp()
            if not app_info:
                log.w("获取当前应用信息失败，无法判断是否在桌面")
                return False

            package_name = app_info.get("packageName", "")
            # _Log._Log_.i(f"当前应用包名: {package_name}")

            # 检查是否在已知桌面包名列表中
            if package_name in LAUNCHER_PACKAGES:
                # _Log._Log_.i(f"当前在桌面 (已知桌面包名)")
                return True

            # 检查包名是否包含launcher或home关键词
            if "launcher" in package_name.lower() or "home" in package_name.lower():
                # _Log._Log_.i(f"当前在桌面 (包名包含launcher或home)")
                return True
            # _Log._Log_.i(f"当前不在桌面")
            return False
        except Exception as e:
            log.ex(e, "判断是否在桌面失败")
            return False

    @classmethod
    def goHome(cls):
        """统一返回桌面实现"""
        if cls.android:
            return cls.android.goHome()
        time.sleep(1)
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
        log = _G._G_.Log()
        try:
            android = cls.android
            if not android:
                log.e("滑动失败:未找到Android实例")
                return False

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
                return android.swipe(startX, startY, endX, endY, duration)
            else:
                # 解析为枚举
                parts = param.split()
                direction = parts[0]
                duration = int(parts[1]) if len(
                    parts) > 1 and parts[1].isdigit() else default_duration
                # log.i(f"滑动指令: 方向({direction}), 持续时间: {duration} ms")
                return android.sweep(direction, duration)

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
    def click(cls, text: str, direction: str = 'UD') -> bool:
        """点击文本（增加重试机制）"""
        log = _G._G_.Log()
        retry = 2
        while retry > 0:
            log.i(f"点击文本: {text}")
            pos = cls.findText(text, direction)
            # log.i(f"找到文本: {text}, 位置: {pos}")
            if pos:
                x, y = pos
                return cls.android.click(x, y)
            time.sleep(1)
            retry -= 1
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
        
        # 反向映射
        opposite_dir = {
            'L': 'R',
            'R': 'L',
            'U': 'D',
            'D': 'U'
        }
        
        # 开始主方向滑动
        current_dir = primary_dir
        tries = 0
        lastScreen = None
        
        while tries < maxTry:
            # 获取当前屏幕内容用于相似度比较
            currentScreen = cls.getScreenText()
            if currentScreen is None:
                return False
            log.i(f"当前屏幕内容: {currentScreen}")
            
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
            
            log.i(f"第{tries+1}次滑动，方向: {cmd}")
            cls.swipe(f"{cmd} 500")
            time.sleep(0.5)  # 等待滑动完成
            
            # 检查滑动后是否匹配
            if matchFunc():
                log.i(f"在方向{current_dir}的第{tries+1}次滑动后找到匹配")
                return True
            
            tries += 1
        
        log.i(f"达到最大尝试次数({maxTry})，未找到匹配")
        return False

    # 增强版文本查找功能
    # return (x,y)
    @classmethod
    def findText(cls, text, searchDir=None, distance=None):
        """增强版文本查找功能
        支持在滑动屏幕过程中持续查找文字
        
        Args:
            text: 要查找的文本
            searchDir: 搜索方向，如 L/R/U/D(单向) 或 LR/UD(双向)
            distance: 搜索距离限制
            
        Returns:
            找到文本的坐标元组(x,y)或None
        """
        log = _G._G_.Log()
        
        # 尝试在当前屏幕查找
        pos = cls._findText(text, searchDir, distance)
        if pos:
            return pos
        # 如果没有指定搜索方向，只在当前屏幕查找
        if not searchDir:
            # log.i(f"未指定搜索方向，只在当前屏幕查找文本: {text}")
            return None
        # 定义匹配函数
        def matchFunc():
            nonlocal pos
            pos = cls._findText(text, searchDir, distance)
            return pos is not None
        # 使用swipeTo进行滑动查找
        found = cls.swipeTo(searchDir, matchFunc)
        return pos if found else None

    @classmethod
    def _findText(cls, text, searchDir=None, distance=None):
        """在当前屏幕尝试查找文本
        
        Args:
            text: 要查找的文本
            searchDir: 搜索方向限制
            distance: 搜索距离限制
            
        Returns:
            找到文本的坐标元组(x,y)或None
        """
        log = _G._G_.Log()
        try:
            if cls.android:
                nodes = cls.android.findTextNodes()
                if not nodes:
                    log.i("屏幕上未找到任何文本节点")
                    return None
                    
                for node in nodes:
                    nodeText = node.getText()
                    if text in nodeText:
                        bounds = node.getBounds()
                        x, y = bounds.centerX(), bounds.centerY()
                        
                        # 检查方向和距离限制
                        if searchDir and distance:
                            screenWidth = cls.android.getScreenWidth()
                            screenHeight = cls.android.getScreenHeight()
                            centerX, centerY = screenWidth // 2, screenHeight // 2
                            
                            # 检查是否在指定方向和距离内
                            if 'L' in searchDir and x > centerX:
                                continue
                            if 'R' in searchDir and x < centerX:
                                continue
                            if 'U' in searchDir and y > centerY:
                                continue
                            if 'D' in searchDir and y < centerY:
                                continue
                            
                            # 检查距离
                            dist = ((x - centerX) ** 2 + (y - centerY) ** 2) ** 0.5
                            if dist > distance:
                                continue
                        
                        log.i(f"找到文本: {text}, 位置: {x},{y}")
                        return (x, y)
            
            log.i(f"屏幕上未找到文本: {text}")
            return None
        except Exception as e:
            log.ex(e, f"查找文本异常")
            return None

    @classmethod
    def isScreenSimilar(cls, screen1, screen2, threshold=0.7):
        """判断两个屏幕内容是否相似
        
        Args:
            screen1: 第一个屏幕的文本内容列表
            screen2: 第二个屏幕的文本内容列表
            threshold: 相似度阈值(0-1)，默认0.7
            
        Returns:
            布尔值，表示是否相似
        """
        if not screen1 or not screen2:
            return False
        
        # 计算共同元素数量
        common = set(screen1).intersection(set(screen2))
        
        # 计算相似度(Jaccard相似度)
        similarity = len(common) / len(set(screen1).union(set(screen2)))
        
        return similarity >= threshold

    @classmethod
    def getScreenText(cls):
        """获取当前屏幕上的所有文本
        Returns:
            文本内容列表
        """
        log = _G._G_.Log()
        try:
            if cls.android:
                nodes = cls.android.findTextNodes()
                if nodes is not None and len(nodes) > 0:
                    return [node.getText() for node in nodes if node.getText()]
        except Exception as e:
            log.ex(e, "获取屏幕文本异常")
        log.i("获取屏幕文本失败")
        return None

CTools_.init()
