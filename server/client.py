import time
from logger import log
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
            self.device = None
            self.initialized = False


    
    def Begin(self, deviceID=None):
        # 测试
        deviceID = 'TEST2'
        ############################################################
        """客户端启动入口"""
        try:
             # 导入需要的模块（这些模块可能已经被重新加载）
            from CDevice import CDevice
            import Cmds
            import tasks
            from CmdMgr import cmdMgr
            from CFileServer import fileServer
            self.deviceID = deviceID or 'TEST1'
            self.device = CDevice(self.deviceID)

            if not self.device.connect(fileServer.serverUrl()):
                log.e("连接服务器失败")
                return  # 这里直接返回会触发 finally
            
            print("客户端运行中... 按Ctrl+C退出")    
            
            runFromApp = log.isAndroid()
            if not runFromApp: # 如果不是从App运行，则进入命令行模式
                while True:
                    try:
                        time.sleep(0.1)
                        cmd_input = input(f"{self.deviceID}> ").strip()
                        if cmd_input:
                            try:
                                result = cmdMgr.do(cmd_input)
                                if result:
                                    print(result)
                            except Exception as e:
                                log.ex(e, '执行命令出错')    
                    except KeyboardInterrupt:
                        # 捕获Ctrl+C
                        log.i('\n正在退出...') 
                        break       
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