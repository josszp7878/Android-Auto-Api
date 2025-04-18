import ast
import json
from enum import Enum
import re
from typing import Any, Tuple
import _G

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
    def doEval(cls, this, code:str) -> Any:
        """安全执行代码
        Args:
            code: 要执行的代码，可以是多行
            globals: 全局命名空间
            locals: 局部命名空间
            
        Returns:
            执行结果
        """
        g = _G._G_
        # 检查代码是否为空
        if not code or code.strip() == '':
            return None
        # 创建安全的执行环境
        locals = {
            'doCmd': g.CmdMgr().do,
            'app': g.App(),
            'T': g.Tools(),
            'ct': g.CTools(),
            'log': g.Log(),
            'this': this,
            'g': g,
            'click': g.CTools().click,
        }
        result = eval(code, cls.gl, locals)
        return result
    
    @classmethod
    def check(cls, this, str:str) -> bool:
        """检查规则"""
        return cls._eval(this, str, False)

    @classmethod
    def do(cls, this, str:str):
        """执行规则"""
        return cls._eval(this, str, True)
    
    @classmethod
    def _eval(cls, this, str:str, doAction:bool=True):
        """执行规则（内部方法）"""
        try:
            if str is None:
                return False
            str = str.strip()
            if str == '':
                return False
            g = _G._G_
            log = g.Log()
            # str = cls._replaceVars(this, str)
            evaled = re.match(r'^\s*\{(.*)\}\s*$', str)
            result = None
            if evaled:
                code = evaled.group(1)
                try:
                    result = cls.doEval(this, code)
                except Exception as e:
                    log.ex(e, f"执行规则失败: {str}")
            else:
                #非代码规则
                if doAction:
                    result = g.CTools().click(str)
                else:
                    #执行text检查
                    result = g.CTools().matchTexts(str)
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
                if '"' in str:
                    return dict(json.loads(str))
                else:
                    return ast.literal_eval(str)
            elif ',' in str:
                return tuple(str.split(','))
            else:
                return int(str)
        except (ValueError, SyntaxError):
            pass
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
    def regexMatch(cls, pattern, strs):
        if strs is None or len(strs) == 0:
            return None
        if pattern is None or pattern.strip() == '':
            return None
        # log.i(f"regexMatch: {pattern}")
        for str in strs:
            if re.search(pattern, str):
                return str
        return None
    
    @classmethod
    def regexMatchItems(cls, pattern, items):
        if items is None or len(items) == 0:
            return None
        pattern = pattern.strip() if pattern else ''
        if pattern == '':
            return None
        # log.i(f"regexMatch: {pattern}")
        retItems = []
        for item in items:
            text = item['t']
            if re.search(pattern, text):
                retItems.append(item)
        return retItems

    @classmethod
    def replaceSymbols(cls, text: str, symbol_map: dict = None) -> str:
        """高效替换字符串中的符号
        
        Args:
            text: 要处理的字符串
            symbol_map: 符号映射字典，如果不提供将使用默认映射
            
        Returns:
            str: 替换后的字符串
        """
        if text is None or text == '':
            return text
        
        # 默认符号映射表（中文符号 -> 英文符号）
        default_map = {
            '：': ':',
            '，': ',',
            '；': ';',
            '。': '.',
            '？': '?',
            '！': '!',
            '（': '(',
            '）': ')',
            '【': '[',
            '】': ']',
            '“': '"',
            '”': '"',
            '’': "'",
            '‘': "'",
            '`': "'",
            '《': '<',
            '》': '>',
            '—': '-',
            '。': '.',
            '　': ' '  # 全角空格转半角空格
        }
        
        # 使用传入的符号映射表或默认表
        map_to_use = symbol_map if symbol_map is not None else default_map
        
        # 如果没有需要替换的符号，直接返回原字符串
        if not map_to_use:
            return text
        
        # 使用列表构建结果字符串，比字符串拼接更高效
        result = []
        for char in text:
            # 如果字符在映射表中，则替换为对应的符号
            result.append(map_to_use.get(char, char))
        
        # 将结果列表连接为字符串
        return ''.join(result)