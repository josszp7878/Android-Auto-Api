import json
from enum import Enum
import re
import time
import datetime
import random
import math
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

    @classmethod
    def eval(cls, code):
        """安全执行代码
        
        Args:
            code: 要执行的代码，可以是多行
            globals: 全局命名空间
            locals: 局部命名空间
            
        Returns:
            执行结果
        """
        g = _G._G_
        log = g.Log()
        # 检查代码是否为空
        if not code or code.strip() == '':
            return None
        
        # 处理引号不匹配的情况
        quote_chars = ['"', "'", '`']
        for char in quote_chars:
            if code.count(char) % 2 != 0:
                return f"Error: 引号 {char} 不匹配"
            
        # 创建安全的执行环境
        globals = {}
        # 添加基本模块
        import math, json, re, datetime, time
        globals.update({
            'math': math,
            'json': json,
            're': re,
            'datetime': datetime,
            'time': time,
        })

        locals = {
            'DoCmd': g.CmdMgr().do,
            'App': g.App(),
            'Tools': g.Tools(),
        }
        result = eval(code, globals, locals)
        return result

    @classmethod
    def _replaceVars(cls, s: str) -> str:
        """替换字符串中的$变量（安全增强版）"""
        # 添加空值防御
        if s is None:
            return s
        log = _G._G_.Log()
        # 正则处理 
        def replacer(match):
            code = match.group(1)
            try:
                val = cls.eval(code)
                return str(val)
            except Exception as e:
                log.ex(e, f"执行变量代码失败: {code}")
                return match.group(0)        
        return re.sub(r'\$\s*([\w\.\(\)]+)', replacer, s)

    @classmethod
    def evalStr(cls, str):
        """执行规则（内部方法）"""
        log = _G._G_.Log()
        str = cls._replaceVars(str)
        if re.match(r'^\s*\{.*\}\s*$', str):
            code = re.search(r'\{(.*)\}', str).group(1)
            try:
                return cls.eval(code)
            except Exception as e:
                return False
        return 'PASS'
    
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
