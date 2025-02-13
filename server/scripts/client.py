import time
from logger import log
from CFileServer import fileServer
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

    def emit(self, event, data=None):
        """发送事件到服务器
        Args:
            event: 事件名称
            data: 事件数据
        """
        try:
            if self.device and self.device.connected:
                self.device.emit(event, data)
            else:
                from logger import Log
                Log.e("设备未连接，无法发送事件")
        except Exception as e:
            from logger import Log
            Log.ex(e, "发送事件失败")

    def Begin(self, deviceID=None, server=None):  
        log.i(f"开始初始化客户端: deviceID={deviceID}, server={server}")      
        try:
            server = server or Tools.getLocalIP()
            log.i(f"获取本机IP: {server}")
            server_url = f"http://{server}:{Tools.port}"
            # 初始化设备连接
            log.i(f"开始初始化设备: {deviceID}")
            from CDevice import CDevice
            self.deviceID = deviceID or 'TEST1'
            self.device = CDevice(self.deviceID)            
            # 等待连接
            self.waitting = True
            def onConnected(ok):
                self.waitting = False
                if not ok:
                    log.e("设备连接服务器失败")
                    # 在APP中显示Toast提示
                    if log.isAndroid():
                        log.toast("服务器连接失败，请检查服务器IP地址和相关的网络设置是否正确")
                else:
                    log.i("设备连接服务器成功")
            

            log.i(f"开始连接设备到服务器: {server_url}")
            self.device.connect(server_url, onConnected)
            
            # 等待连接完成
            timeout = 30  # 30秒超时
            start_time = time.time()
            while self.waitting:
                try:
                    if time.time() - start_time > timeout:
                        log.e("连接超时")
                        break
                    time.sleep(1)
                    print(".", end="", flush=True)
                except Exception as e:
                    log.e(f"等待连接时发生错误: {str(e)}")
                    break
            
            if not self.device.connected:
                log.e("设备连接失败")
                if log.isAndroid():
                    log.toast("无法连接到服务器，请检查网络和服务器地址")
                return
            fileServer.serverUrl = server_url                
            runFromApp = log.isAndroid()
            if runFromApp:
                # 更新脚本
                self.waitting = True
                def onUpdated(ok):
                    self.waitting = False
                print("更新脚本...")   
                fileServer.updateScripts(onUpdated)
                # 等待脚本更新完成
                while self.waitting:
                    try:
                        time.sleep(1)
                        print(".", end="", flush=True)
                    except Exception:
                        break
                
            import Cmds
            import tasks
            from CmdMgr import cmdMgr


            if not runFromApp:  # 如果不是从App运行，则进入命令行模式
                print("客户端运行中... 按Ctrl+C退出")    
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
                                break
                    except KeyboardInterrupt:
                        log.i('\n正在退出...') 
                        break  
                self.End()
            else:
                while True:
                    time.sleep(100)
        except Exception as e:
            log.ex(e, '初始化失败')


    
    def End(self):
        """清理函数"""
        print("End")
        if self.device and self.device.connected:
            self.device.logout()
            self.device.disconnect()
            print("已断开服务器连接")
        self.initialized = False

# 创建全局单例实例
client = Client()