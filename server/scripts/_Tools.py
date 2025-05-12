from __future__ import annotations
import json
from enum import Enum
import re
from typing import Any, Tuple, Optional, List, TYPE_CHECKING
import _G
import time

if TYPE_CHECKING:
    from _Page import _Page_

class RegionCheck:
    """区域检查工具类"""

    def __init__(self):
        self.region = None

    @classmethod
    def parse(cls, text: str) -> Tuple[Optional["RegionCheck"], str]:
        text1, coords = _Tools_.toPos(text)
        if coords is None:
            return None, text
        check = RegionCheck()
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

    class eRet(Enum):
        none = ''
        # 退出，执行退出逻辑
        exit = 'exit'
        # 取消并退出，不执行退出逻辑
        cancel = 'cancel'
        # 出错，会退出，不执行退出逻辑
        error = 'error'


    class eCmd(Enum):
        back = '<-' # 返回上一页
        backWith = '<-(.+)' # 返回指定的页面，参数为返回的页面
        home = '<<' # 返回主页
        goto = '>(.+)' # 跳转，参数为要跳转的页面
        click = 'click|c(?:\s*\(([^\)]*)\))?[\s,]*(\S*)?' # 点击，参数1为要点击的元素，参数2为调试指令
        collect = '\+(.+)' # 收集,参数为要收集的元素
        end = 'end' # 结束

    _TopStr = ["top", "主屏幕", "桌面"]
    # 工具类基本属性
    Tag = "Tools"
    port = 5000
    # android对象由_G._G_管理，不再在这里维护
    screenSize: tuple[int, int] = (1080, 1920)
    _fixFactor = 0
    _screenInfoCache = None
    
    # 文本查找计数的键名常量
    FINDCOUNT_KEY = 'findCount'
    
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
    def check(cls, this, str: str) -> Tuple[bool, Any]:
        """检查多条件逻辑（改造后版本）
        
        Args:
            this: 调用上下文
            str: 条件字符串
            
        Returns:
            Tuple[bool, Any]: 检查结果和附加数据
        """
        g = _G._G_
        log = g.Log()
        str = str.strip() if str else ''
        if str == '':
            return True, None
        segments = cls._parseSegments(str, '&')
        if not segments:
            return False, None        
        def call(condition, region):
            ret = cls._do(this, condition, False, log)
            if not isinstance(ret, tuple):
                return cls.toBool(ret), ret
            else:
                result, data = ret
                return cls.toBool(result), data
        success, data = cls._evalSegments(segments, call, True)
        return success, data    
    
    @classmethod
    def do(cls, this, str: str):
        """执行多条件逻辑（改造后版本）
        Args:
            this: 调用上下文
            str: 条件字符串
        Returns:
            Tuple[bool, Any]: 检查结果和附加数据
        """
        g = _G._G_
        log = g.Log()
        try:
            segments = cls._parseSegments(str, '&')
            if not segments:
                return None
            ret = None
            def call(condition, region):
                global ret
                ret = cls._do(this, condition, True, log)
            cls._evalSegments(segments, call)
            return ret
        except Exception as e:
            log.ex(e, f"执行多条件逻辑失败: {str}")
            return None

    @classmethod
    def _parseSegments(cls, expr: str, default_op: str = None) -> list:
        """解析逻辑表达式为段列表（通用版本）
        
        Args:
            expr: 逻辑表达式字符串
            default_op: 默认操作符（如 '&' 或 '|'）
            
        Returns:
            list: 解析后的段列表，每个段包含操作符、条件和区域信息
        """
        expr = expr.strip() if expr else ''
        if expr == '':
            return None
        
        segments = []
        last_region = None
        
        # 分割表达式
        parts = re.split(r'([&|])', expr)
        parts = [p.strip() for p in parts if p.strip()]
        
        # 处理第一个段
        if parts and parts[0] not in '&|':
            region, condition = RegionCheck.parse(parts[0])
            segments.append({'op': default_op, 'condition': condition, 'region': region})
            last_region = region
            parts = parts[1:]
        
        # 处理剩余段
        for i in range(0, len(parts), 2):
            if i+1 >= len(parts):
                break
            op, expr = parts[i], parts[i+1]
            region = None
            if not expr.startswith('@'):
                inherit = '()' in expr            
                region, expr = RegionCheck.parse(expr)
                if inherit and last_region and not region:
                    region = last_region
            segments.append({'op': op, 'condition': expr, 'region': region})
            if region:
                last_region = region
        
        return segments

    @classmethod
    def _evalSegments(cls, segments: list, func: callable, logicOpt: bool = False) -> Any:
        """评估段列表的匹配结果（通用版本）
        
        Args:
            segments: 解析后的段列表，每个段包含操作符、条件和区域信息，~开头的条件表示测试指令，只在PC平台有效。
            func: 评估函数，接受条件字符串和区域信息，返回匹配结果   
            logicOpt: 是否启用逻辑优化
        Returns:
            Any: 评估结果，具体类型由 func 决定
        """
        result = None 
        for seg in segments:
            # 评估当前条件
            code = seg['condition']
            if code.startswith('~'):
                # 如果当前是安卓平台，则跳过~开始的测试指令。
                if cls.isAndroid():
                    continue
                code = code[1:]
            result = func(code, seg['region'])
            if logicOpt:
                bResult = cls.toBool(result) 
                logic = seg['op']
                if (not bResult and logic == '&') or (bResult and logic == '|'):
                    if isinstance(result, tuple):
                        result = (bResult, result[1])
                    else:
                        result = bResult
                    break
        return result

    # 处理特殊命令
    @classmethod
    def _doCmd(cls, this: "_Page_", cmd: str) -> '_Tools_.eRet':
        """处理特殊命令
        Args:
            this: 调用上下文
            cmd: 特殊命令字符串
        Returns:
            DoRet: 命令执行结果
        """
        g = _G._G_
        log = g.Log()        
        cmd = cmd.strip() if cmd else ''
        if cmd == '':
            return cls.eRet.none
        cmd = cmd.lower()
        #匹配 cmd 是否符合 eCmd 的格式
        cmdID = None
        for eCmd in cls.eCmd:
            try:
                match = re.match(eCmd.value, cmd, re.IGNORECASE)
                if match:
                    cmdID = eCmd
                    break
            except Exception as e:
                log.ex(e, f"匹配命令异常: {eCmd.value} => {cmd}")
                return cls.eRet.error
        if cmdID is None:
            return cls.eRet.error
        app = g.App()
        # 处理返回特定状态的命令
        if cmdID == cls.eCmd.backWith:
            ret_str = match.group(1)
            try:
                return cls.eRet(f'{ret_str}')
            except ValueError:
                log.e(f"无效的DoRet值: {ret_str}")
                return cls.eRet.none
        # 处理返回操作
        elif cmdID == cls.eCmd.back:
            app.last().back()
            return cls.eRet.none
        # 处理回到主页
        elif cmdID == cls.eCmd.home:
            app.home()
            return cls.eRet.none
        elif cmdID == cls.eCmd.end:
            return this.end()
        # 处理点击指令
        elif cmdID == cls.eCmd.click:
            p1 = match.group(1)
            p2 = match.group(2)
            p2 = p2.strip() if p2 else ''
            if p2 == '':
                p2 = '<-'
            this.click(p1, p2)
            return cls.eRet.none
        elif cmdID == cls.eCmd.collect:
            # 收获金币
            coinStr = match.group(1)
            coins = 0
            try:
                coins = int(coinStr)
            except ValueError:
                # 如果不是数字，尝试从页面数据中获取
                if hasattr(this, coinStr):
                    coins = getattr(this, coinStr)
                    try:
                        coins = int(coins)
                    except (ValueError, TypeError):
                        coins = 0
            
            if coins > 0:
                log.d(f"PC平台模拟: 收获 {coins} 金币")
        # 处理页面跳转指令 ->pageName
        elif cmdID == cls.eCmd.goto:
            # 提取目标页面名称
            pageName = match.group(1)
            if pageName:
                log.d(f"跳转到页面: {pageName}")
                # 尝试页面跳转
                result = g.App().gotoPage(pageName)
                if result:
                    # 跳转成功后返回cancel
                    return cls.eRet.cancel
                else:
                    log.e(f"跳转到页面 {pageName} 失败")
            return cls.eRet.none
        else:
            # 未知命令，返回unknown
            return cls.eRet.error
    
    # 执行特殊脚本
    # 特殊脚本开头字符代表的含义：
    # ： ：       执行特殊命令
    # @  ：        执行脚本
    # 其它字符：执行点击或者是文字匹配
    # &和|：       指令分隔符，如果是返回判定结果的指令，则&和|表示逻辑与和或的关系
    # # ：         表示页面引用
    @classmethod
    def _do(cls, this: "_Page_", cmd: str, doAction: bool, log: _G._G_.Log):
        """执行规则（内部方法）"""
        g = _G._G_
        try:
            tools = g.Tools()
            cmd = cmd.strip() if cmd else ''
            if cmd == '':
                return cls.eRet.none                
            ret = None
            # 处理@开头的脚本执行
            if cmd.startswith('@'):
                cmd = cmd[1:].strip()
                if cmd == '':
                    return cls.eRet.none
                return cls._eval(this, cmd, log)             
            #如果cmd 和eCmd里面的value任何一个匹配，则执行cls._doCmd(this, cmd)
            elif cmd in [e.value for e in cls.eCmd]:
                return cls._doCmd(this, cmd)
            elif cmd.startswith(':'):
                cmd = cmd[1:].strip()
                if cmd == '':
                    return cls.eRet.none
                return cls._doCmd(this, cmd)
            else:
                # 当文字匹配时，执行点击
                if doAction:
                    ret = tools.click(cmd)
                else:
                    # 执行text检查
                    ret = tools.matchText(cmd, this)
            return ret
        except Exception as ex:
            log.ex(ex, f"执行失败: {cmd}")
            return False
        
    @classmethod
    def _eval(cls, this, code: str, log: _G._G_.Log):
        """执行脚本
        
        在脚本中，使用result变量存储最终结果，例如:
        result = True  # 这个值会作为执行结果返回
        
        不支持在顶层代码中使用return语句，因为在Python的非函数上下文中不允许return。
        """
        g = _G._G_
        try:
            # 创建安全的执行环境
            locals = {
                'app': g.App(),
                'curApp': g.App().last(),
                't': g.Tools(),
                'log': g.Log(),
                'this': this,
                'g': g,
                'click': g.Tools().click,
                'R': _Tools_.eRet,
                'r': None  # 用于存储结果
            }
            # 使用exec执行代码
            exec(code, cls.gl, locals)
            # 返回result变量的值
            ret = locals.get('r', cls.eRet.none)
            # log.i(f"执行脚本结果: {ret}")
            return ret
        except Exception as ex:
            log.ex(ex, f"执行规则失败: {code}")
            return None
        

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
        except Exception:
            return str

    @classmethod
    def toBool(cls, value, default=False):
        """将字符串转换为布尔值"""
        if value is None:
            return default
        if isinstance(value, str):
            return value.lower() in ['true', '1', 'yes', 'y', 'on', '开']
        if isinstance(value, tuple):
            return cls.toBool(value[0])
        if isinstance(value, cls.eRet):
            return value == cls.eRet.none
        return bool(value)
   
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
    def wildMatchText(cls, pattern, items):
        """在列表中查找包含指定文本的项目
        Args:
            pattern: 要匹配的文本
            items: 要匹配的列表
            
        Returns:
            list: 匹配的项目
        """
        try:
            if not pattern or not items:
                return []
            matches = []
            pattern = pattern.strip().lower()            
            for item in items:
                if pattern in item:
                    matches.append(item)
            return matches
        except Exception as e:
            log = _G._G_.Log()
            log.ex(e, f"正则匹配失败: {pattern}")
            return []
    
    @classmethod
    def matchItems(cls, pattern, items):
        """正则匹配项目列表
        
        使用正则表达式进行匹配，直接返回匹配的项目和匹配结果组成的元组列表
        
        Args:
            pattern: 正则表达式模式字符串
            items: 项目列表
            
        Returns:
            list: 包含元组(item, match)的列表，item是匹配的项目，match是正则表达式匹配结果
        """
        log = _G._G_.Log()
        try:
            if not pattern or not items:
                return []
            # 编译正则表达式
            regex = re.compile(pattern, re.IGNORECASE)
            # 存储匹配结果的元组列表
            matches = []
            for item in items:
                t = item.get('t', '')
                if not t:
                    continue                    
                # 执行正则表达式匹配
                m = regex.search(t)
                if m:
                    # 将匹配的项目和匹配结果添加到列表中
                    matches.append((item, m))
            return matches
        except Exception as e:
            log.ex(e, f"正则匹配失败: {pattern}")
            # 不再容错处理，让错误传递出去
            raise

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
            if g.android is None:
                opened = cls.click(appName)
            else:
                # 根据系统类型选择打开方式
                if cls.isHarmonyOS():
                    opened = cls.click(f'{appName}(y-150)', 'LR')
                else:
                    # Android系统使用服务方式打开
                    opened = g.android.openApp(appName)
            return opened
        except Exception as e:
            log.ex(e, "打开应用失败")
            return False

    @classmethod
    def closeApp(cls, app_name: str = None) -> bool:
        g = _G._G_
        log = g.Log()
        try:
            if g.android:
                return g.android.closeApp(app_name)
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
        g = _G._G_
        log = g.Log()
        try:
            if g.android:
                g.android.toast(str(msg),
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
        android = g.android
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
        g = _G._G_
        log = g.Log()
        if g.android is None:
            return True
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
    def curApp(cls) -> str:
        """获取当前应用名称"""
        g = _G._G_
        log = g.Log()
        try:
            if g.isAndroid():
                appInfo = cls.getCurrentAppInfo()
                if not appInfo:
                    return None
                if cls.isHome():
                    return _G.TOP
                return appInfo.get("appName") 
            else:
                App = g.App()
                return App.curName()
        except Exception as e:
            log.ex(e, "获取当前应用名称失败")
            return ''

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
        g = _G._G_
        log = g.Log()
        log.i("返回桌面")
        if g.android:
            if not g.android.goHome():
                return False
        return True     

    @classmethod
    def goBack(cls)->bool:
        """统一返回上一页实现"""
        g = _G._G_
        if g.android:
            return g.android.goBack()
        else:
            return True

    # 从CTools_类添加的屏幕相关方法
    @classmethod
    def setPosFixScope(cls, scope):
        g = _G._G_
        log = g.Log()
        cls._fixFactor = scope/cls.screenSize[1]
        log.i(f"@@@坐标修正范围: {scope}, 修正比例: {cls._fixFactor}")
        
    @classmethod
    def _initScreenSize(cls)->tuple[int, int]:
        """获取屏幕尺寸"""
        screenSize = (1080, 1920)
        log = _G._G_.Log()
        try:
            if g.android:
                # 尝试通过Android Context获取屏幕尺寸
                context = g.android.getContext()
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
    def clearScreenInfo(cls):
        """清除屏幕信息"""
        cls._screenInfoCache = []
        return True
    
    @classmethod
    def delScreenInfo(cls, content:str):
        """删除屏幕信息"""
        log = _G._G_.Log()
        try:
            if cls._screenInfoCache is None:
                return False
            cls._screenInfoCache = [item for item in cls._screenInfoCache if item['t'] != content]
            # log.i(f"删除屏幕信息: {content} \n info={cls._screenInfoCache}")
            return True
        except Exception as e:
            log.ex(e, "删除屏幕信息失败")
            return False

    @classmethod
    def addScreenInfo(cls, content:str, timeout=1):
        """添加模拟屏幕文字块
        Args:
            content: 文字内容
            timeout: 超时处理参数
                - 正数: 等待指定秒数后自动清除
                - 负数: 文本被查找到指定次数后自动清除
                - 0: 不自动清除
        Returns:
            bool: 是否成功添加
        """
        g = _G._G_
        log = g.Log()
        try:
            # 只在非Android环境下(PC模拟模式)进行处理
            isPC = not cls.isAndroid()
            
            # 初始化屏幕缓存
            if cls._screenInfoCache is None:
                cls._screenInfoCache = []
            
            # 解析内容
            strs = content.split('(')
            text = strs[0].strip()
            
            # 检查文本是否已存在
            existing = next((item for item in cls._screenInfoCache if item['t'] == text), None)
            if existing:
                # 如果已存在，只更新findCount或添加定时清除任务
                if timeout < 0 and isPC:
                    existing[cls.FINDCOUNT_KEY] = abs(timeout)  # 负数timeout存为findCount
                elif timeout > 0 and isPC:
                    # 清除已有的定时任务(如果有)
                    existing.pop(cls.FINDCOUNT_KEY, None)
                    # 启动定时清除
                    import threading
                    def delayed_clear():
                        time.sleep(timeout)
                        cls.delScreenInfo(text)
                    threading.Thread(target=delayed_clear, daemon=True).start()
                return True
                
            # 处理边界信息
            bound = strs[1].strip(')').strip(' ') if len(strs) > 1 else None
            bounds = None
            if bound:
                bounds = [int(x) for x in bound.split(',')]
                bound_len = len(bounds)
                if bound_len < 2:
                    log.e(f"边界坐标格式错误: {bound}")
                    return False
                elif bound_len == 2:
                    bounds.append(bounds[0])
                    bounds.append(bounds[1])
                elif bound_len == 3:
                    bounds.append(bounds[2])

            # 创建屏幕信息对象
            screenInfo = {
                "t": text,
                "b": bounds
            }
            
            # 添加PC环境下的自动清除功能
            if isPC:
                # 处理负数timeout(查找次数限制)
                if timeout < 0:
                    screenInfo[cls.FINDCOUNT_KEY] = abs(timeout)
                # 处理正数timeout(定时清除)
                elif timeout > 0:
                    import threading
                    def delayed_clear():
                        time.sleep(timeout)
                        cls.delScreenInfo(text)
                    threading.Thread(target=delayed_clear, daemon=True).start()
            
            # 添加到缓存
            cls._screenInfoCache.append(screenInfo)
            log.i(f"屏幕信息已添加: {text}")
            return True
        except Exception as e:
            log.ex(e, "添加屏幕信息失败")
            return False

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

    
    @classmethod
    def _tryDelInfo(cls, item):
        """更新文本的findCount计数，当计数为0时自动删除
        
        Args:
            item: 要更新findCount的文本项
            
        Returns:
            bool: 是否成功更新计数
        """
        # 只在PC环境下处理计数
        if cls.isAndroid() or not item or cls.FINDCOUNT_KEY not in item:
            return False
            
        log = _G._G_.Log()
        # 减少计数
        item[cls.FINDCOUNT_KEY] -= 1
        # log.d(f"文本 '{item['t']}' 被查找，剩余次数: {item[cls.FINDCOUNT_KEY]}")
        
        # 当计数为0时自动删除
        if item[cls.FINDCOUNT_KEY] <= 0:
            # log.i(f"文本 '{item['t']}' 已达到查找次数限制，自动删除")
            cls.delScreenInfo(item['t'])
            return True
            
        return True
        
    @classmethod
    def _findTextPos(cls, text: str) -> Optional[Tuple[int, int]]:
        """在当前屏幕查找文本位置（内部方法）"""
        g = _G._G_
        log = g.Log()
        try:
            # 匹配文本
            matches = cls.matchText(text, None, True)
            if not matches:
                if cls.isAndroid():
                    return None
                else:
                    return (0, 0)
            
            # 获取第一个匹配项的中心坐标
            item = matches[0][0]
            bounds = item.get('b')
            if not bounds:
                return None
            
            centerX = (bounds[0] + bounds[2]) // 2
            centerY = (bounds[1] + bounds[3]) // 2

            # 应用坐标修正
            if cls._fixFactor > 0:
                offsetX = int(centerY * cls._fixFactor)
                centerX -= offsetX
                log.d(f"坐标修正: ({centerX+offsetX},{centerY}) -> ({centerX},{centerY})")
            
            return (centerX, centerY)
        except Exception as e:
            log.ex(e, f"查找文本位置失败: {text}")
            return None


    @classmethod
    def matchText(cls, text: str, this, refresh=False) -> List[Tuple[dict, re.Match]]:
        """匹配文本，返回所有匹配的(item, match)元组列表（改造后版本）"""
        def evalCondition(condition, region):
            items = cls.getScreenInfo(refresh)
            if not items:
                return None
            matches = cls.matchItems(condition, items)
            if region:
                matches = [(i, m) for i, m in matches if i.get('b') and region.isRectIn(*i['b'])]
                
            # 对匹配到的每个项目更新findCount
            for match in matches:
                cls._tryDelInfo(match[0])
                
            if matches and this:
                # 将匹配结果中argument添加到this中，属性名称为argument加_
                data = this.data
                if not data:
                    data = {}
                    this.data = data
                for m in matches:
                    if m[1]:
                        for k, v in m[1].groupdict().items():
                            data[k + '_'] = v
                            print(f"匹配结果: {k} = {v}")
                        # 设置data._item 为匹配到的内容
                        data['_matchItem'] = m[0]                
            return matches
        
        segments = cls._parseSegments(text, '&')
        if not segments:
            return None
        
        return cls._evalSegments(segments, evalCondition, True)

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
        g = _G._G_
        log = g.Log()
        try:
            # 获取文本位置
            pos = cls.findTextPos(text, direction)
            if not pos:
                log.w(f"未找到文本: {text}")
                return g.android is None
            
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
        g = _G._G_
        log = g.Log()
        try:
            x, y = pos
            x += offset[0]
            y += offset[1]
            
            if g.android:
                return g.android.click(x, y)
            else:
                return True
        except Exception as e:
            log.ex(e, f"点击位置失败: {pos}")
            return False

    @classmethod
    def findTextPos(cls, text: str, searchDir: str = None) -> Optional[Tuple[int, int]]:
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