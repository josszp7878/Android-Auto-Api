import sys
import time
import importlib
from logger import Log
from tools import Tools

class Client:
    """客户端管理类"""
    _instance = None
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = super(Client, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.deviceID = None
            self.server = None
            self.device = None
            self.initialized = False
            
    
    def Begin(self, deviceID=None, server=None):
        """客户端启动入口"""
        log = Log()
        log.init(is_server=False)
        try:
             # 导入需要的模块（这些模块可能已经被重新加载）
            from CDevice import CDevice
            from CmdMgr import CmdMgr
            import Cmds
            try:
                self.deviceID = deviceID or 'TEST1'
                self.server = server or "localhost"
                self.device = CDevice(self.deviceID)
                
                log.i(f"设备 {self.deviceID} 正在连接到服务器 {self.server}")
                if not self.device.connect(f"http://{self.server}:5000"):
                    log.e("连接服务器失败")
                    return  # 这里直接返回会触发 finally
                
                print("客户端运行中... 按Ctrl+C退出")    
                
                runFromApp = log.isAndroid()
                while True:
                    if not runFromApp:
                        cmd_input = input(f"{self.deviceID}> ").strip()
                        if cmd_input:
                            try:
                                result = CmdMgr().do(cmd_input)
                                if result:
                                    print(result)
                            except Exception as e:
                                log.ex(e, '执行命令出错')
                    time.sleep(0.1)
                
            except KeyboardInterrupt:
                log.i('\n正在退出...')
            except Exception as e:
                log.ex(e, '发生错误')
        except Exception as e:
            log.ex(e, '初始化失败')
        finally:
            self.End()
    
    
    def End(self):
        """清理函数"""
        # Tools().printCallStack()
        print("End")
        if self.device and self.device.connected:
            self.device.logout()
            self.device.disconnect()
            print("已断开服务器连接")
        self.initialized = False

# 创建全局单例实例
client = Client()