import time
import _G

class CClient_:
    """客户端管理类（静态方法）"""
    _init = False
    deviceID = None
    server = None
    device = None
    fromAndroid = False


    @classmethod
    def Clone(cls, clone):
        try:
            """克隆实例"""
            g = _G._G_
            cls.fromAndroid = clone.fromAndroid
            cls.deviceID = clone.deviceID
            cls.server = clone.server
            cls.device = clone.device
            # g.Log().d("CClient克隆完成")
            return True
        except Exception as e:
            g.Log().ex(e, "克隆失败")
            return False

    @classmethod
    def emit(cls, event, data=None):
        """发送事件到服务器
        Args:
            event: 事件名称
            data: 事件数据
        """
        g = _G._G_
        log = g.Log()
        try:
            if cls.device and cls.device.connected:
                cls.device.emit(event, data)
            else:
                log.e("设备未连接，无法发送事件")
        except Exception as e:
            log.ex(e, "发送事件失败")

    @classmethod
    def updateFiles(cls):
        """更新脚本文件"""
        g = _G._G_
        # log = _G._G_.Log()
        if cls.fromAndroid:  # 使用全局变量判断
            # 更新脚本
            waitting = True

            def onUpdated(ok):
                nonlocal waitting
                waitting = False
            g.getClass('CFileServer').downAll(onUpdated)
            # 等待脚本更新完成
            while waitting:
                try:
                    time.sleep(1)
                    print(".", end="", flush=True)
                except Exception:
                    break

    @classmethod
    def _connectServer(cls, server, tools):
        """连接服务器核心逻辑"""
        waitting = True
        def onConnected(ok):
            nonlocal waitting
            waitting = False
            if not ok:
                tools.toast("服务器连接失败")
        cls.device.connect(server, onConnected)
        timeout = 30
        start_time = time.time()
        while waitting:
            if time.time() - start_time > timeout:
                print("连接超时")
                break
            time.sleep(1)
            print(".", end="", flush=True)

        if not cls.device.connected:
            tools.toast("无法连接到服务器")                

    @classmethod
    def Begin(cls, deviceID=None, server=None, fromAndroid=None):  
        """初始化客户端"""
        g = _G._G_
        log = g.Log()
        # 如果fromAndroid为None，则用现成的。这个在reloadAll指令时会用到
        if fromAndroid is not None:
            cls.fromAndroid = fromAndroid
        log.d(f"初始化客户端: deviceID={deviceID}, server={server}, fromAndroid={fromAndroid}")      
        try:
            tools = g.CTools()
            
            from CDevice import CDevice_
            cls.deviceID = deviceID or 'TEST1'
            cls.server = server
            cls.device = CDevice_(cls.deviceID)
            g.CmdMgr().regAllCmds()
            cls._connectServer(server, tools)
            g.CFileServer().serverIp = server
            g.Checker().start()
            print("按Ctrl+C退出")    
            while True:
                try:
                    cmd_input = input(f"{cls.deviceID}> ").strip()
                    if cmd_input:
                        result,_ = g.getClass('_CmdMgr').do(cmd_input)
                        if result:
                            print(result)
                except EOFError:
                    cls.fromAndroid = True
                    break
                except KeyboardInterrupt:
                    log.i('\n正在退出...') 
                    cls.End()
                    break
                except Exception as e:
                    log.ex(e, '执行命令出错')
        except Exception as e:
            log.ex(e, '初始化失败')

   
    @classmethod
    def End(cls):
        """清理函数"""
        g = _G._G_
        log = g.Log()
        g.Checker().stop()
        if cls.device:
            cls.device.uninit()
        try:
            from CTaskMgr import taskMgr
            taskMgr.uninit()
            log.i("所有任务已停止")
        except Exception as e:
            log.ex(e, "客户端结束失败")
