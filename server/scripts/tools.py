import time
import builtins  # 导入 builtins 模块


class Tools:
    _instance = None
    TAG = "Tools"
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Tools, cls).__new__(cls)
        return cls._instance
    
    @property
    def Android(self):
        return self._android
    
    def isAndroid(self):
        """判断是否为 Android 平台"""
        return self._android is not None
    
    def initPlatform(self):
        """初始化平台判定"""
        try:
            from java import jclass            
            self._android = jclass("cn.vove7.andro_accessibility_api.demo.script.PythonServices")
        except Exception as e:
            self._android = None
    


    def printCallStack(self):
        # 打印调用栈
        import traceback
        print('\n保存日志调用栈:')
        for line in traceback.format_stack()[:-1]:  # 去掉最后一行(当前函数)
                print(line.strip())        