import time
from _Log import _Log
from CFileServer import fileServer
from CTools import CTools

class CClient:
    """客户端管理类"""
    _instance = None
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = super(CClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.deviceID = None
            self.server = None
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
                from _Log import _Log
                _Log.e("设备未连接，无法发送事件")
        except Exception as e:
            from _Log import _Log
            _Log.ex(e, "发送事件失败")

    def Begin(self, deviceID=None, server=None):  
        print(f"初始化客户端: deviceID={deviceID}, server={server}")      
        try:
            server = server or CTools.getLocalIP()
            print(f"获取本机IP: {server}")
            server_url = f"http://{server}:{CTools.port}"
            # 初始化设备连接
            # print(f"开始初始化设备: {deviceID}")
            from CDevice import CDevice
            self.deviceID = deviceID or 'TEST1'
            self.server = server
            self.device = CDevice(self.deviceID)       
            # 注册所有命令
            from _CmdMgr import _CmdMgr
            _CmdMgr.regAllCmds()     
            # 等待连接
            self.waitting = True
            def onConnected(ok):
                self.waitting = False
                if not ok:
                    CTools.toast("服务器连接失败，请检查服务器IP地址和相关的网络设置是否正确")
                else:
                    print("设备连接服务器成功")
            

            # print(f"开始连接设备到服务器: {server_url}")
            self.device.connect(server_url, onConnected)
            
            # 等待连接完成
            timeout = 30  # 30秒超时
            start_time = time.time()
            while self.waitting:
                try:
                    if time.time() - start_time > timeout:
                        print("连接超时")
                        break
                    time.sleep(1)
                    print(".", end="", flush=True)
                except Exception as e:
                    print(f"等待连接时发生错误: {str(e)}")
                    break
            
            if not self.device.connected:
                CTools.toast("无法连接到服务器，请检查网络和服务器地址")
                return
            fileServer.serverUrl = server_url                
            if CTools.runFromAndroid:
                # 更新脚本
                self.waitting = True
                def onUpdated(ok):
                    self.waitting = False
                # print("更新脚本...")   
                fileServer.updateScripts(onUpdated)
                # 等待脚本更新完成
                while self.waitting:
                    try:
                        time.sleep(1)
                        print(".", end="", flush=True)
                    except Exception:
                        break
                
            import CCmds as CCmds
            from _CmdMgr import _CmdMgr
            from CTaskMgr import taskMgr

            # print(f"runFrdddddddddddddomAndroid={CTools.runFromAndroid}")
            if not CTools.runFromAndroid:  # 如果不是从App运行，则进入命令行模式
                print("客户端运行中sss... 按Ctrl+C退出")    
                while True:
                    try:
                        time.sleep(0.1)
                        cmd_input = input(f"{self.deviceID}> ").strip()
                        if cmd_input:
                            try:
                                result,_ = _CmdMgr.do(cmd_input)
                                if result:
                                    print(result)
                            except Exception as e:
                                _Log.ex(e, '执行命令出错')    
                                break
                    except KeyboardInterrupt:
                        _Log.i('\n正在退出...') 
                        break  
                self.End()
            else:
                while True:
                    time.sleep(100)
        except Exception as e:
            _Log.ex(e, '初始化失败')


    
    def End(self):
        """清理函数"""
        print("End")
        if self.device :
            self.device.uninit()
        self.initialized = False

        try:
            from CTaskMgr import taskMgr
            # 停止所有任务
            taskMgr.uninit()
            _Log.i("所有任务已停止")

            # 其他结束逻辑...
            # 例如，断开连接，清理资源等
        except Exception as e:
            _Log.ex(e, "客户端结束失败")

# 创建全局单例实例
client = CClient()