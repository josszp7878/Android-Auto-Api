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
            'DoCmd': g.CmdMgr().do,
            'App': g.App(),
            'T': g.Tools(),
            'CT': g.CTools(),
            'Log': g.Log(),
            'this': this,
        }
        result = eval(code, cls.gl, locals)
        return result
    
    #return (是否执行成功, 执行结果)
    @classmethod
    def eval(cls, this, str:str) -> Tuple[bool, Any]:
        """执行规则（内部方法）"""
        try:
            if str is None:
                return False
            str = str.strip()
            if str == '':
                return False
            log = _G._G_.Log()
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
                result = cls._doAction(log, this, str)
            return evaled, result
        except Exception as e:
            log.ex(e, f"执行规则失败: {str}")
            return False, None
        
    @classmethod
    def _doAction(cls, log, this, str:str) -> Any:
        """执行动作"""
        # 判断动作类型   
        cTools = _G._G_.CTools()       
        m = re.search(r'(?P<action>[^-\s]+)\s*[:：]\s*(?P<target>.*)', str)
        if m:
            action = m.group('action')
            target = m.group('target')
            # 根据动作类型执行相应操作
            if action == 'C':
                return cTools.click(target)
            elif action == 'O':
                # 打开应用
                is_home = cTools.isHome()
                if not is_home:
                    log.e("不在主屏幕，无法打开应用")
                    return False                
                return cTools.click(target, waitTime=2)
            elif action == 'S':
                return cTools.swipe(target)
            elif action == 'B':
                return cTools.goBack()
        else:
            return cTools.click(str)
    
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
