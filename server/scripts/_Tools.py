import _Log
from enum import Enum

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
    

class _Tools:
    @classmethod
    def toTaskId(cls, appName: str, templateId: str) -> str:
        """生成任务唯一标识"""
        return f"{appName}_{templateId}"

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
    def GetClassMethod(cls, module, method_name):
        """查找模块中包含指定方法的类，并返回该方法
        
        Args:
            module: 模块对象
            method_name: 方法名称
            
        Returns:
            tuple: (类对象, 方法对象) 如果找到，否则返回 (None, None)
        """
        try:
            # 遍历模块中的所有属性
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                # 检查是否是类，并且是否有指定的方法
                if isinstance(attr, type) and hasattr(attr, method_name) and callable(getattr(attr, method_name)):
                    return attr, getattr(attr, method_name)
            return None, None
        except Exception as e:
            _Log.Log_.ex(e, f"查找类方法失败: {method_name}")
            return None, None

