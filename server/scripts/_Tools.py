from __future__ import annotations
import json
from enum import Enum
import re
from typing import Any, Tuple, Optional
import _G
import time

class RegionCheck:
    """区域检查工具类"""

    def __init__(self):
        self.region = None

    @classmethod
    def parse(cls, text: str) -> Tuple[Optional["RegionCheck"], str]:
        check = RegionCheck()
        text1, coords = _Tools_.toPos(text)
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
        screenW, screenH = _Tools_.screenSize
        base = screenW if isX else screenH
        return base + value  # 负值相加等于减去绝对值

    def isIn(self, x, y):
        """判断坐标是否在区域内（支持负值）"""
        # 转换负值坐标
        x_min = self._convertValue(self.region[0], True)
        x_max = self._convertValue(self.region[2], True)
        y_min = self._convertValue(self.region[1], False)
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
    

class _Tools_:

    _TopStr = ["top", "主屏幕", "桌面"]
    
    # 工具类基本属性
    Tag = "Tools"
    port = 5000
    # android对象由_G._G_管理，不再在这里维护
    screenSize: tuple[int, int] = (1080, 1920)
    _fixFactor = 0
    _screenInfoCache = None
    
    # 为了兼容性添加android属性
    @classmethod
    def _getG(cls):
        """获取_G._G_单例（避免循环引用）"""
        import _G
        return _G._G_
    
    @classmethod
    def isTop(cls, appName: str) -> bool:
        """判断是否是主屏幕"""
        return appName.lower() in cls._TopStr
    
    _RootStr = ["app", "应用", "root"]
    @classmethod
    def isRoot(cls, appName: str) -> bool:
        """判断是否是应用"""
        return appName.lower() in cls._RootStr

    @classmethod
    def toTaskId(cls, appName: str, templateId: str) -> str:
        """生成任务唯一标识"""
        return f"{appName}_{templateId}"
    
    @classmethod
    def getServerURL(cls, serverIP=None):
        """获取服务器URL"""
        if serverIP is None:
            import socket
            serverIP = socket.gethostbyname(socket.gethostname())
        print(f"服务器IP: {serverIP}")
        return f"http://{serverIP}:{cls.port}"

    @classmethod
    def printCallStack(cls):
        """打印调用栈"""
        import traceback
        print('\n保存日志调用栈:')
        for line in traceback.format_stack()[:-1]:
            print(line.strip())

    @classmethod
    def reloadModule(cls, moduleName: str):
        import sys
        import importlib
        # print(f"重新加载模块: {moduleName}")
        if moduleName in sys.modules:
            del sys.modules[moduleName]
        importlib.import_module(moduleName)

    import math, json, re, datetime, time
    gl = {
        'math': math,
        'json': json,
        're': re,
        'datetime': datetime,
        'time': time,
    }


    @classmethod
    def _replaceVars(cls, this, s: str) -> str:
        """替换字符串中的$变量（安全增强版）"""
        # 添加空值防御
        if s is None:
            return s
        log = _G._G_.Log()
        # 正则处理 
        def replacer(match):
            code = match.group(1)
            try:
                val = cls.do(this, code)
                return str(val)
            except Exception as e:
                log.ex(e, f"执行变量代码失败: {code}")
                return match.group(0)        
        return re.sub(r'\$\s*([\w\.\(\)]+)', replacer, s)

    @classmethod
    def check(cls, this, str:str)->bool:
        ret = cls.do(this, str, False)
        return cls.toBool(ret)
    
    @classmethod
    def do(cls, this, str:str, doAction:bool=True):
        """执行规则（内部方法）"""
        try:
            str = str.strip() if str else ''
            if str == '':
                return False
            g = _G._G_
            log = g.Log()
            firstChar = str[0]
            result = None
            if firstChar == '@':
                code = str[1:]
                if code == '':
                    return False
                try:
                     # 创建安全的执行环境
                    locals = {
                        'app': g.App(),
                        'T': g.Tools(),
                        'ct': g.Tools(),
                        'log': g.Log(),
                        'this': this,
                        'g': g,
                        'click': g.Tools().click,
                    }
                    result = eval(code, cls.gl, locals)
                except Exception as e:
                    log.ex(e, f"执行规则失败: {str}")
            elif firstChar == '>':
                #代码规则
                code = str[1:]
                result = g.App().gotoPage(code)
            else:
                #非代码规则
                if doAction:
                    result = g.Tools().click(str)
                else:
                    #执行text检查
                    result = g.Tools().matchTexts(str)
            return result
        except Exception as e:
            log.ex(e, f"执行规则失败: {str}")
            return False
        
    
    @classmethod
    def toNetStr(cls, result):
        """将对象转换为字符串"""
        log = _G._G_.Log()
        if result is not None and not isinstance(result, str):
            try:
                # 尝试将JSON对象转换为字符串
                if isinstance(result, (dict, list)):
                    result = json.dumps(result, ensure_ascii=False)
                    # result = result.replace('\n', ' ').replace('\r', '')
                else:
                    # 其他类型直接转字符串
                    result = str(result)
            except Exception as e:
                log.ex(e, f"结果转换为字符串失败: {result}")
                return None
        return result
        
    @classmethod
    def strToPos(cls, strPos: str) -> tuple:
        """将位置字符串转换为坐标"""
        if strPos is None:
            return None
        import re
        match = re.match(r'(\d+)[\s,xX](\d+)', strPos)
        if match:
            return int(match.group(1)), int(match.group(2))
        return None
        
    @classmethod
    def fromStr(cls, str: str) -> Any:
        """将位置字符串转换为坐标"""
        if str is None:
            return None
        str = cls.replaceSymbols(str)
        try:
            if ':' in str:
                return str.split(':')
            if ',' in str:
                try:
                    return [int(x) for x in str.split(',')]
                except ValueError:
                    s = str.split(',')
                    if len(s) >= 2:
                        return int(s[0]), int(s[1])
            if ' ' in str:
                s = str.split(' ', 1)
                if isinstance(s, list) and len(s) >= 2:
                    try:
                        return int(s[0]), int(s[1])
                    except ValueError:
                        pass
            try:
                return int(str)
            except ValueError:
                try:
                    return float(str)
                except ValueError:
                    return str
        except Exception as e:
            # cls.log.e(f"fromStr error: {e}")
            return str

    @classmethod
    def toBool(cls, value, default=False):
        """将字符串转换为布尔值"""
        if value is None:
            return default
        return value.lower() in ['true', '1', 'yes', 'y', 'on','开']

   
    @classmethod
    def toPos(cls, strPos: str) -> Tuple[str, tuple]:
        """解析位置字符串，支持多种格式
        
        格式说明:
        - 纯坐标: "100,200" -> (None, (100,200,None,None))
        - 文本+坐标: "文本100,-50" -> ("文本", (100,-50,None,None))
        - 单轴坐标: "文本y-100" -> ("文本", (None,-100,None,None))
        - 单轴多值: "文本y-100,50" -> ("文本", (None,-100,None,50)) (50也解析为y轴)
        - 双轴坐标: "文本x100,y-50" -> ("文本", (100,-50,None,None))
        - 多坐标: "文本100,200,300,400" -> ("文本", (100,200,300,400))
        
        Args:
            strPos: 位置字符串，支持有无括号
            
        Returns:
            (text, (x0,y0,x1,y1)): 文本和坐标元组，坐标不存在的部分为None
        """
        try:
            if not strPos or not strPos.strip():
                return None, None
            
            # 1. 预处理：去掉所有括号和空格
            text = strPos.strip()
            # 去掉所有括号
            text = re.sub(r'[\(（\)）]', '', text)
            
            # 2. 检查是否是纯坐标形式 (如 "100,200")
            if re.match(r'^\d+\s*,\s*\d+$', text):
                values = [int(v.strip()) for v in text.split(',')]
                return None, (values[0], values[1], None, None)
            
            # 3. 查找第一个坐标标识出现的位置
            coords_match = re.search(r'([xXyY][-+]?\d+)|(\d+,)', text)
            
            if not coords_match:
                # 检查是否有单个数字结尾
                num_match = re.search(r'(\d+)$', text)
                if num_match:
                    # 提取文本和坐标
                    pos = num_match.start()
                    coord_part = text[pos:]
                    text_part = text[:pos].strip()
                    
                    # 处理单个数字结尾
                    values = [int(coord_part), None, None, None]
                    return text_part, tuple(values)
                # 无坐标信息
                return text, None
                
            # 4. 分离文本和坐标
            pos = coords_match.start()
            coord_part = text[pos:]
            text_part = text[:pos].strip()
            
            # 5. 初始化坐标数组
            coords = [None, None, None, None]
            
            # 6. 查找所有轴标识和数字
            axis_values = re.findall(r'([xXyY])([-+]?\d+)', coord_part)
            
            # 7. 处理所有轴标识
            has_x = False
            has_y = False
            
            for axis, value in axis_values:
                value = int(value)
                if axis.upper() == 'X':
                    has_x = True
                    # 放入第一个空的X轴位置
                    if coords[0] is None:
                        coords[0] = value
                    elif coords[2] is None:
                        coords[2] = value
                else:  # Y轴
                    has_y = True
                    # 放入第一个空的Y轴位置
                    if coords[1] is None:
                        coords[1] = value
                    elif coords[3] is None:
                        coords[3] = value
            
            # 8. 正确提取纯数字
            # 排除跟在x或y后面的数字，只提取独立的数字
            all_numbers = re.findall(r'([-+]?\d+)', coord_part)
            axis_numbers = [match[1] for match in axis_values]  # 已处理的带轴标识的数字
            
            # 只保留不是轴标识一部分的数字
            plain_values = []
            for num in all_numbers:
                if num not in axis_numbers:
                    plain_values.append(num)
            
            # 9. 处理这些数字
            if plain_values:
                # 单轴模式
                if has_x and not has_y:
                    # 只有X轴，其他数字也视为X轴
                    x_idx = 0 if coords[0] is None else 2
                    for val in plain_values:
                        if x_idx <= 2:
                            coords[x_idx] = int(val)
                            x_idx += 2
                elif has_y and not has_x:
                    # 只有Y轴，其他数字也视为Y轴
                    y_idx = 1 if coords[1] is None else 3
                    for val in plain_values:
                        if y_idx <= 3:
                            coords[y_idx] = int(val)
                            y_idx += 2
                else:
                    # 无轴或双轴模式，按顺序填充
                    idx = 0
                    for val in plain_values:
                        while idx < 4 and coords[idx] is not None:
                            idx += 1
                        if idx < 4:
                            coords[idx] = int(val)
                            idx += 1
            
            # 10. 返回结果
            return text_part, tuple(coords)
            
        except Exception as e:
            _G._G_.Log().ex(e, f"解析位置字符串失败: {strPos}")
            return None, None

    @classmethod
    def getSimilarity(cls, tarText, text) -> float:
        """获取两个文本的相似度
        
        按字符顺序比较两个字符串，计算它们的相似程度。
        对于不匹配的字符会跳过，继续寻找后续可能匹配的部分。
        
        Args:
            tarText: 目标文本
            text: 待比较文本
            
        Returns:
            float: 相似度，范围0.0-1.0，1.0表示完全匹配
        """
        if not tarText or not text:
            return 0.0
        
        # 如果两个字符串完全相同，直接返回1.0
        if tarText == text:
            return 1.0
        
        # 最长公共子序列算法
        len1, len2 = len(tarText), len(text)
        
        # 创建动态规划表
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        # 填充动态规划表
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if tarText[i-1] == text[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        # 计算最长公共子序列的长度
        lcs_length = dp[len1][len2]
        
        # 计算相似度：最长公共子序列长度 / 较长字符串的长度
        similarity = lcs_length / max(len1, len2)
        
        return similarity
    

    @classmethod
    def similarMatch(cls, tarText, items, threshold=0)->Tuple[Any, float]:
        log = _G._G_.Log()
        log.i(f"wildMatch: {tarText}, threshold={threshold}")
        retItem = None
        maxSim = 0
        for item in items:
            if isinstance(item, str):
                text = item
            else:
                text = item['t']
            sim = cls.getSimilarity(tarText, text)
            if sim < threshold:
                continue
            if retItem is None:
                retItem = item
                maxSim = sim
            else:
                if sim > maxSim:
                    retItem = item
                    maxSim = sim
        return retItem, maxSim
    
    @classmethod
    def regexMatch(cls, pattern, items):
        """在列表中查找匹配正则表达式的项目
        
        Args:
            pattern: 正则表达式
            items: 要匹配的列表
            
        Returns:
            list: 匹配的项目列表
        """
        try:
            if not pattern or not items:
                return []
            matches = []
            pattern = pattern.strip().lower()
            
            for item in items:
                t = item.get('t', '')
                if not t:
                    continue
                    
                if pattern in t:
                    matches.append(item)
            return matches
        except Exception as e:
            log = _G._G_.Log()
            log.ex(e, f"正则匹配失败: {pattern}")
            return []
    
    @classmethod
    def regexMatchItems(cls, pattern, items):
        """正则匹配项目列表
        Args:
            pattern: 正则表达式
            items: 项目列表
        Returns:
            list: 匹配的项目列表
        """
        try:
            if not pattern or not items:
                return []
            matches = []
            pattern = pattern.strip().lower()
            
            for item in items:
                t = item.get('t', '')
                if not t:
                    continue
                t = t.lower().strip()
                if pattern in t:
                    matches.append(item)
            return matches
        except Exception as e:
            log = _G._G_.Log()
            log.ex(e, f"正则匹配失败: {pattern}")
            return []

    @classmethod
    def replaceSymbols(cls, text: str, symbol_map: dict = None) -> str:
        """替换文本中的特殊符号
        
        Args:
            text: 要处理的文本
            symbol_map: 自定义符号映射表
            
        Returns:
            处理后的文本
        """
        if not text:
            return text
        
        # 默认符号映射
        default_map = {
            '＜': '<',
            '＞': '>',
            '（': '(',
            '）': ')',
            '，': ',',
            '：': ':',
            '；': ';',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '！': '!',
            '？': '?',
            '～': '~',
            '｜': '|',
            '＠': '@',
            '＃': '#',
            '＄': '$',
            '％': '%',
            '＆': '&',
            '＊': '*',
            '＋': '+',
            '－': '-',
            '／': '/',
            '＝': '=',
            '［': '[',
            '］': ']',
            '｛': '{',
            '｝': '}',
            '｀': '`',
            '　': ' ',  # 全角空格替换为半角空格
        }
        
        # 使用自定义映射更新默认映射
        if symbol_map:
            default_map.update(symbol_map)
            
        # 执行替换
        for full, half in default_map.items():
            text = text.replace(full, half)
            
            return text
        
    # 从CTools_类添加的系统相关方法
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
            if cls._G.android is None:
                opened = cls.click(appName)
            else:
                # 根据系统类型选择打开方式
                if cls.isHarmonyOS():
                    opened = cls.click(f'{appName}(y-150)', 'LR')
                else:
                    # Android系统使用服务方式打开
                    opened = cls._G.android.openApp(appName)
            return opened
        except Exception as e:
            log.ex(e, "打开应用失败")
            return False

    @classmethod
    def closeApp(cls, app_name: str = None) -> bool:
        log = _G._G_.Log()
        try:
            if cls._G.android:
                return cls._G.android.closeApp(app_name)
            return True
        except Exception as e:
            log.ex(e, '关闭应用失败')
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
            if cls._G.android:
                cls._G.android.toast(str(msg),
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
        android = cls._G.android
        if android is None:
            return None
        try:
            # 获取当前应用信息
            appInfo = android.getCurrentApp(200)
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
        if cls._G.android is None:
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
            if cls.isTop(appName):
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
        if cls._G.android:
            if not cls._G.android.goHome():
                return False
        return True     

    @classmethod
    def goBack(cls)->bool:
        """统一返回上一页实现"""
        log = _G._G_.Log()
        log.i("<<")
        if cls._G.android:
            return cls._G.android.goBack()
        else:
            return True

    # 从CTools_类添加的屏幕相关方法
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
            if cls._G.android:
                # 尝试通过Android Context获取屏幕尺寸
                context = cls._G.android.getContext()
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
    
    @classmethod
    def getScreenInfo(cls, refresh=False)->list[dict]:
        """获取并解析屏幕信息,支持缓存"""
        g = _G._G_
        log = g.Log()
        try:
            android = g.android
            if not android:
                return cls._screenInfoCache
            
            info = android.getScreenInfo()
            if info is None:
                log.e("获取屏幕信息失败")
                return cls._screenInfoCache
                
            size = info.size()
            result = []
            
            for i in range(size):
                item = info.get(i)
                t = item.get('t').replace('\n', ' ').replace('\r', '')
                if t.strip('') == '':
                    continue
                bound = item.get('b')
                # 校验bounds
                if not bound:
                    continue
                # 添加到结果列表
                result.append({
                    't': t,
                    'b': bound
                })
                
            cls._screenInfoCache = result
            return result
        except Exception as e:
            log.ex(e, "获取屏幕信息失败")
            return []   
            
    @classmethod
    def setScreenInfo(cls, screenInfo):
        """设置屏幕信息缓存
        
        Args:
            screenInfo: 屏幕信息，可以是JSON字符串或对象
        """
        log = _G._G_.Log()
        try:
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
            log.ex(e, "设置屏幕信息失败")
            return False

    @classmethod
    def addScreenInfo(cls, text, bound):
        """添加模拟屏幕文字块
        Args:
            text: 文字内容
            bound: 边界坐标，格式为"x,y,width,height"
        Returns:
            bool: 是否成功添加
        """
        log = _G._G_.Log()
        try:
            if cls._screenInfoCache is None:
                cls._screenInfoCache = []
            
            # 解析边界坐标
            bounds = None
            if bound:
                bound = bound.strip(' ').strip('(').strip(')')
                bounds = [int(x) for x in bound.split(',')]
                l = len(bounds)
                if l < 2:
                    log.e(f"边界坐标格式错误: {bound}")
                    return False
                elif l == 2:
                    bounds.append(bounds[0])
                    bounds.append(bounds[1])
                elif l == 3:
                    bounds.append(bounds[2])

            # 创建屏幕信息对象
            screenInfo = {
                "t": text,
                "b": bounds
            }
            # 添加到缓存
            cls._screenInfoCache.append(screenInfo)
            log.i(f"屏幕信息:\n {cls._screenInfoCache}")
            return True
        except Exception as e:
            log.ex(e, "添加屏幕信息失败")
            return False
    
    @classmethod
    def toPos(cls, item: dict):
        # bounds = [int(x) for x in item['b'].split(',')]
        bounds = item['b']
        centerX = (bounds[0] + bounds[2]) // 2
        centerY = (bounds[1] + bounds[3]) // 2
        return (centerX, centerY)

    @classmethod
    def refreshScreenInfos(cls) -> list:
        """获取并解析屏幕信息,支持缓存"""
        log = _G._G_.Log()
        try:
            android = _G._G_.android
            if not android:
                return cls._screenInfoCache

            info = android.getScreenInfo()
            if info is None:
                log.e("获取屏幕信息失败")
                return []
                
            size = info.size()
            result = []
            
            for i in range(size):
                item = info.get(i)
                t = item.get('t').replace('\n', ' ').replace('\r', '')
                if t.strip('') == '':
                    continue
                b = item.get('b')
                if b:
                    try:
                        b = [int(d) for d in b.split(',')]
                    except Exception as e:
                        log.ex(e, f"解析边界坐标失败: {b}")
                        b = None
                result.append({
                    't': t,
                    'b': b or ''
                })
            # 更新缓存
            cls._screenInfoCache = result
            return result
        except Exception as e:
            log.ex(e, "获取屏幕信息失败")
            return []

    # 从CTools_类添加的文本匹配相关方法
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
                
            g = _G._G_
            log = g.Log()
            
            # 解析区域信息，使用本地定义的RegionCheck类
            region, text = RegionCheck.parse(str)
            
            # 获取屏幕信息
            items = cls.getScreenInfo(refresh)
            if not items or len(items) == 0:
                # log.w("屏幕信息为空")
                return None if cls._G.android else g.PASS
                
            # 先匹配文本
            matchedItems = cls.regexMatchItems(text, items)            
            # 没有匹配到文本
            if not matchedItems:
                # log.w(f"未找到匹配文本: {text}")
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
                    isIn = region.isRectIn(b[0], b[1], b[2], b[3])
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

    # 添加交互相关方法
    _screenText = None
            
    @classmethod
    def swipe(cls, param: str) -> bool:
        """滑动屏幕
        
        Args:
            param: 滑动参数，格式为"方向"或"x1,y1,x2,y2"
            
        Returns:
            bool: 是否成功滑动
        """
        log = _G._G_.Log()
        try:
            if not param:
                return False
                
            # 判断是否为简单方向参数
            param = param.upper()
            if param in ["UP", "DOWN", "LEFT", "RIGHT", "U", "D", "L", "R"]:
                if cls._G.android:
                    return cls._G.android.swipe(param)
                else:
                    log.i(f"模拟滑动: {param}")
                    return True
                    
            # 判断是否为坐标形式
            if "," in param:
                coords = [int(x.strip()) for x in param.split(",")]
                if len(coords) == 4:
                    x1, y1, x2, y2 = coords
                    if cls._G.android:
                        return cls._G.android.swipePos(x1, y1, x2, y2)
                    else:
                        log.i(f"模拟滑动: ({x1},{y1}) -> ({x2},{y2})")
                        return True
                        
            log.e(f"无效的滑动参数: {param}")
            return False
        except Exception as e:
            log.ex(e, f"滑动失败: {param}")
            return False
            
    @classmethod
    def switchScreen(cls, direction: str):
        """切换屏幕（上一屏/下一屏）
        
        Args:
            direction: 方向，"prev"表示上一屏，"next"表示下一屏
            
        Returns:
            bool: 是否成功切换
        """
        log = _G._G_.Log()
        try:
            direction = direction.lower()
            if direction == "prev":
                return cls.swipe("RIGHT")
            elif direction == "next":
                return cls.swipe("LEFT")
            else:
                log.e(f"无效的屏幕切换方向: {direction}")
                return False
        except Exception as e:
            log.ex(e, f"切换屏幕失败: {direction}")
            return False
            
    @classmethod
    def click(cls, text: str, direction: str = None, waitTime: int = 1) -> bool:
        """点击屏幕上的文本
        
        Args:
            text: 要点击的文本或坐标
            direction: 如果找不到文本，滑动方向继续查找
            waitTime: 点击后等待时间（秒）
            
        Returns:
            bool: 是否成功点击
        """
        log = _G._G_.Log()
        try:
            g = _G._G_
            # 获取文本位置
            pos = cls.findTextPos(text, direction)
            if not pos:
                log.w(f"未找到文本: {text}")
                return cls._G.android is None
                
            # 点击位置
            cls.clickPos(pos)
            
            # 等待指定时间
            if waitTime > 0:
                time.sleep(waitTime)
                
            return True
        except Exception as e:
            log.ex(e, f"点击文本失败: {text}")
            return False
            
    @classmethod
    def clickPos(cls, pos, offset=(0, 0)):
        """点击指定坐标
        
        Args:
            pos: 坐标元组(x,y)
            offset: 偏移量元组(dx,dy)
            
        Returns:
            bool: 是否成功点击
        """
        log = _G._G_.Log()
        try:
            x, y = pos
            x += offset[0]
            y += offset[1]
            
            if cls._G.android:
                return cls._G.android.click(x, y)
            else:
                log.i(f"模拟点击: ({x},{y})")
                return True
        except Exception as e:
            log.ex(e, f"点击位置失败: {pos}")
            return False
    
    @classmethod
    def swipeTo(cls, direction, matchFunc, maxTry=3):
        """滑动屏幕直到条件匹配
        
        Args:
            direction: 滑动方向
            matchFunc: 匹配函数，返回True表示找到
            maxTry: 最大尝试次数
            
        Returns:
            bool: 是否找到
        """
        log = _G._G_.Log()
        try:
            # 首先检查当前屏幕是否已匹配
            if matchFunc():
                return True
                
            # 记录起始屏幕内容用于比较
            startScreen = cls._screenInfoCache

            # 尝试滑动并检查
            for i in range(maxTry):
                # 滑动屏幕
                if not cls.swipe(direction):
                    log.e(f"滑动失败: {direction}")
                    return False
                    
                # 刷新屏幕信息
                cls.refreshScreenInfos()
                
                # 检查新屏幕是否与起始屏幕相似（判断是否到达边界）
                if i > 0 and cls.isScreenSimilar(startScreen, cls._screenInfoCache):
                    log.w("屏幕内容未变化，可能已到达边界")
                    return False
                    
                # 应用匹配函数
                if matchFunc():
                    return True
                    
                # 更新起始屏幕（用于下次比较）
                startScreen = cls._screenInfoCache
                
            # 达到最大尝试次数仍未找到
            log.w(f"滑动{maxTry}次后未找到匹配内容")
            return False
        except Exception as e:
            log.ex(e, f"滑动查找失败: {direction}")
            return False
            
    @classmethod
    def findTextPos(cls, text, searchDir=None):
        """查找文本位置
        
        Args:
            text: 要查找的文本
            searchDir: 如果当前屏幕未找到，滑动方向继续查找
            
        Returns:
            tuple: 文本位置坐标(x,y)，未找到则返回None
        """
        if searchDir:
            # 定义匹配函数
            def matchFunc():
                pos = cls._findTextPos(text)
                return pos is not None
                
            # 滑动查找
            found = cls.swipeTo(searchDir, matchFunc)
            if not found:
                return None
                
        # 在当前屏幕查找
        return cls._findTextPos(text)
        
    @classmethod
    def _findTextPos(cls, text):
        """在当前屏幕查找文本位置（内部方法）"""
        log = _G._G_.Log()
        try:
            # 匹配文本
            item = cls.matchText(text, True)
            if not item:
                return None
                
            # 获取中心坐标
            bounds = item['b']
            if not bounds:
                return None
                
            centerX = (bounds[0] + bounds[2]) // 2
            centerY = (bounds[1] + bounds[3]) // 2

            # 应用坐标修正
            if cls._fixFactor > 0:
                # 根据y位置线性调整x坐标
                offsetX = int(centerY * cls._fixFactor)
                centerX -= offsetX
                log.d(f"坐标修正: ({centerX+offsetX},{centerY}) -> ({centerX},{centerY})")
                
            return (centerX, centerY)
        except Exception as e:
            log.ex(e, f"查找文本位置失败: {text}")
            return None
            
    @classmethod
    def isScreenSimilar(cls, screen1, screen2):
        """判断两个屏幕内容是否相似
        
        Args:
            screen1: 第一个屏幕内容
            screen2: 第二个屏幕内容
            
        Returns:
            bool: 是否相似
        """
        if not screen1 or not screen2:
            return False
            
        def to_hashable(items):
            """将屏幕内容转换为可哈希结构用于比较"""
            result = set()
            for item in items:
                text = item.get('t', '').strip()
                if text:
                    result.add(text)
            return result
            
        # 转换为可比较的集合
        texts1 = to_hashable(screen1)
        texts2 = to_hashable(screen2)
        
        # 如果其中一个为空，返回False
        if not texts1 or not texts2:
            return False
            
        # 计算交集比例
        intersection = texts1.intersection(texts2)
        similarity = len(intersection) / max(len(texts1), len(texts2))
        
        # 相似度阈值可调整
        return similarity > 0.8
    
        
    @classmethod
    def onLoad(cls, old):
        """模块加载时的回调"""
        # 保留原有状态
        if old:
            cls.screenSize = old.screenSize
            cls._fixFactor = old._fixFactor
            cls._screenInfoCache = old._screenInfoCache
        
        # 初始化屏幕尺寸(如果android对象已由_G_初始化)
        if _G._G_.android:
            cls._initScreenSize()
            
    @classmethod
    def getScreenInfoCache(cls):
        """获取屏幕信息缓存"""
        return cls._screenInfoCache
    
    @classmethod
    def isAndroid(cls):
        """检查是否是Android环境"""
        return _G._G_.android is not None