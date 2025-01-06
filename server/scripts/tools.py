import time
import builtins
import sys
import importlib
from logger import Log
import threading


class Tools:
    _instance = None
    TAG = "Tools"
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Tools, cls).__new__(cls)
        return cls._instance

    def _handle_module_reload(self, module_name: str, log: Log) -> bool:
        """处理模块重新加载
        Args:
            module_name: 模块名称
            log: 日志实例
        Returns:
            bool: 是否重载成功
        """
        try:
            if module_name in sys.modules:
                module = sys.modules[module_name]
                # 执行预加载
                if not self._execute_preload(module, module_name, log):
                    return False
                
                # 重新加载模块
                del sys.modules[module_name]
                module = importlib.import_module(module_name)
                
                # 执行重载后回调
                if not self._execute_reload(module, module_name, log):
                    return False
                    
                log.i(f"重新加载模块成功: {module_name}")
            else:
                module = importlib.import_module(module_name)
                log.i(f"首次加载模块成功: {module_name}")
            return True
        except Exception as e:
            log.ex(e, f"加载模块失败: {module_name}")
            return False

    def _execute_preload(self, module, module_name: str, log: Log) -> bool:
        """执行模块的预加载函数
        Args:
            module: 模块实例
            module_name: 模块名称
            log: 日志实例
        Returns:
            bool: 是否执行成功
        """
        if hasattr(module, 'OnPreload'):
            try:
                module.OnPreload()
                return True
            except Exception as e:
                log.ex(e, f"执行预重载函数失败: {module_name}")
                return False
        return True

    def _execute_reload(self, module, module_name: str, log: Log) -> bool:
        """执行模块的重载后函数
        Args:
            module: 模块实例
            module_name: 模块名称
            log: 日志实例
        Returns:
            bool: 是否执行成功
        """
        if hasattr(module, 'OnReload'):
            try:
                module.OnReload()
                return True
            except Exception as e:
                log.ex(e, f"执行热更新函数失败: {module_name}")
                return False
        return True

    def reloadModule(self, module_name: str) -> bool:
        """重新加载指定模块
        Args:
            module_name: 模块名称（不含.py后缀）
        Returns:
            bool: 是否重载成功
        """
        log = Log()
        try:
            if log.isAndroid():
                def onComplete(success: bool, error: str = None):
                    if not success:
                        log.e(f"下载模块文件失败: {module_name} - {error}")
                        return False
                    return self._handle_module_reload(module_name, log)

                # 启动下载
                return log.Android.download(f"{module_name}.py", onComplete)
            
            return True
        except Exception as e:
            log.ex(e, f"重载模块失败: {module_name}")
            return False

    def printCallStack(self):
        """打印调用栈"""
        import traceback
        print('\n保存日志调用栈:')
        for line in traceback.format_stack()[:-1]:
            print(line.strip())