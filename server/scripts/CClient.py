import signal
import atexit
import _G

class CClient_:
    """客户端管理类（静态方法）"""
    fromAndroid = False
    _cleanup_registered = False
    running = False  # 运行标志，支持退出命令

    @classmethod
    def _registerCleanup(cls):
        """注册清理函数，确保退出时调用"""
        if cls._cleanup_registered:
            return
        cls._cleanup_registered = True
        
        def cleanup():
            """清理函数"""
            print("atexit清理程序执行...")
            cls.End()
        
        # 注册atexit处理器
        atexit.register(cleanup)
        
        # 注册信号处理器
        def signal_handler(signum, frame):
            print(f"收到信号 {signum}，设置退出标志...")
            cls.running = False  # 设置退出标志，让主循环退出
        
        # 注册常见的终止信号
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
        if hasattr(signal, 'SIGBREAK'):  # Windows
            signal.signal(signal.SIGBREAK, signal_handler)

    @classmethod
    def updateFiles(cls):
        """更新脚本文件"""
        g = _G._G_
        # log = _G._G_.Log()
        if cls.fromAndroid:  # 使用全局变量判断
            log = g.Log()
            log.i("开始更新脚本...")
            downAll = g.CFileServer().downAll()
            downAll.join()
            log.i("脚本更新完成")

    @classmethod
    def init(cls, deviceID=None, server=None)->bool:
        """初始化客户端"""
        g = _G._G_
        log = g.Log()
        try:
            log.i("初始化客户端")
            CDevice = g.CDevice()
            CDevice.init(deviceID or 'TEST1', server)
            CDevice.connect()
            g.App().onLoad()
            g.CFileServer().init(server)
            g.CmdMgr().regAllCmds()
            from RPC import initRPC
            initRPC()
        except Exception as e:
            log.ex(e, '初始化失败')
            return False
        return True

    @classmethod
    def Begin(cls, deviceID=None, server=None, fromAndroid=None)->bool:
        """初始化客户端"""
        g = _G._G_
        log = g.Log()
        # 如果fromAndroid为None，则用现成的。这个在reloadAll指令时会用到
        if fromAndroid is not None:
            cls.fromAndroid = fromAndroid
        log.d(f"初始化客户端: deviceID={deviceID}, server={server}, fromAndroid={fromAndroid}")
        
        # 注册清理函数（仅PC端）
        if not cls.fromAndroid:
            cls._registerCleanup()
        
        try:
            if not cls.init(deviceID, server):
                return False
            #起一个线程去更新app
            g.App().update()
            print("按Ctrl+C退出")
            device = g.CDevice()
            if device is None:
                log.e("设备初始化失败")
                return False
            cls.running = True  # 设置运行标志
            while cls.running:
                try:
                    cmd_input = input(f"{device.name}> ").strip()
                    g.CmdMgr().do({'cmd': cmd_input})
                except EOFError:
                    cls.fromAndroid = True
                    break
                except KeyboardInterrupt:
                    log.i('\n正在退出...')
                    break
                except Exception as e:
                    log.ex(e, '执行命令出错')
                    return False
        except Exception as e:
            log.ex(e, '初始化失败')
        finally:
            # 最后的安全网
            log.uninit()
        return True

    @classmethod
    def End(cls):
        """清理函数"""
        g = _G._G_
        log = g.Log()
        try:
            CDevice = g.CDevice()
            if CDevice:
                CDevice.uninit()
            # 清理日志系统，保存日志到文件
            if not cls.fromAndroid:
                log.uninit()
        except Exception as e:
            log.ex(e, "客户端结束失败")

    @classmethod
    def onLoad(cls, clone):
        if clone is not None:
            cls.fromAndroid = clone.fromAndroid
        return True

CClient_.onLoad(None)