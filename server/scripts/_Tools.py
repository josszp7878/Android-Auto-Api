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
                _,val = cls.eval(this, code)
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
    def eval(cls, this, str:str):
        """执行规则"""
        log = _G._G_.Log()
        log.i(f"执行代码: {str}")
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
            str = cls._replaceVars(this, str)
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
                    result = True
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
    def toBool(cls, value, default=False):
        """将字符串转换为布尔值"""
        if value is None:
            return default
        return value.lower() in ['true', '1', 'yes', 'y', 'on']

    @classmethod
    def parsePos(cls, strPos: str) -> Tuple[str, tuple]:
        """解析位置字符串
        
        支持多种配置：
        1. 单轴坐标: text(axis100,-300) 其中axis是x或y, 坐标值分别对应x0,x1或y0,y1
        2. 双轴坐标: text(100,-200,300,400) 坐标值分别对应x0,y0,x1,y1
        3. 单值坐标: text(100) 单个值
        4. 纯坐标: 100,200 直接作为坐标处理
        
        Args:
            strPos: 位置字符串
            
        Returns:
            (text, (x0,y0,x1,y1)): 文本和坐标元组，坐标可能是None
        """
        try:
            if strPos is None:
                return None, None
            
            import re
            strPos = strPos.strip()
            
            # 检查是否是纯坐标形式 (如 "100,200,300,400")
            pure_coords_match = re.match(r'^([\s,xX\d]+)$', strPos)
            if pure_coords_match:
                values = [v.strip() for v in pure_coords_match.group(1).split(',')]
                values = [int(v) if v and re.match(r'[+-]?\d+', v) else None for v in values]
                return None, tuple(values)
            # 检查是否有括号
            bracket_match = re.match(r'(.*?)\s*[\(（](.*?)[\)）]', strPos)
            if not bracket_match:
                # 没有括号，返回None
                return None, None
            
            text = bracket_match.group(1).strip()
            content = bracket_match.group(2).strip()
            
            # 处理括号内容
            if not content:
                return text, (None, None, None, None)
            
            # 检查是否有轴标识
            axis_match = re.match(r'([xXyY])\s*(.*)', content)
            axis = None
            if axis_match:
                axis = axis_match.group(1).upper()
                content = axis_match.group(2)
            
            # 分割逗号分隔的值
            values = [v.strip() for v in content.split(',')]
            values = [int(v) if v and re.match(r'[+-]?\d+', v) else None for v in values]
            
            # 根据值的数量和轴标识处理不同情况
            if len(values) == 1:
                # 单个值
                val = values[0]
                if axis == 'X':
                    return text, (val, None, None, None)
                elif axis == 'Y':
                    return text, (None, val, None, None)
                else:
                    return text, (val, None, None, None)  # 默认为X轴
            
            elif len(values) == 2:
                # 两个值
                val1, val2 = values
                if axis == 'X':
                    return text, (val1, None, val2, None)
                elif axis == 'Y':
                    return text, (None, val1, None, val2)
                else:
                    return text, (val1, val2, None, None)  # 默认为X,Y坐标
            
            elif len(values) == 4:
                # 四个值 - 完整的矩形
                return text, tuple(values)
            
            # 其他情况，返回尽可能多的值，其余为None
            result = values + [None] * (4 - len(values))
            return text, tuple(result[:4])
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
        log = _G._G_.Log()
        log.i(f"regexMatch: {pattern}")
        for item in items:
            if isinstance(item, str):
                text = item
            else:
                text = item['t']
            if re.search(pattern, text):
                return item
        return None