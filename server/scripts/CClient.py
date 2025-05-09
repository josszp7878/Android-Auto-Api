import time
import _G

class CClient_:
    """客户端管理类（静态方法）"""
    fromAndroid = False


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
    def Begin(cls, deviceID=None, server=None, fromAndroid=None):
        """初始化客户端"""
        g = _G._G_
        log = g.Log()
        # 如果fromAndroid为None，则用现成的。这个在reloadAll指令时会用到
        if fromAndroid is not None:
            cls.fromAndroid = fromAndroid
        log.d(f"初始化客户端: deviceID={deviceID}, server={server}, fromAndroid={fromAndroid}")
        try:
            CDevice = g.CDevice()
            CDevice.init(deviceID or 'TEST1', server)
            CDevice.connect()
            g.CFileServer().init(server)
            g.CmdMgr().regAllCmds()
            g.App().update()
            print("按Ctrl+C退出")
            while True:
                try:
                    cmd_input = input(f"{CDevice.deviceID()}> ").strip()
                    g.CmdMgr().do({'cmd': cmd_input})
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
        try:
            g.App().stopPage(None, True)
            CDevice = g.CDevice()
            if CDevice:
                CDevice.uninit()
        except Exception as e:
            log.ex(e, "客户端结束失败")

    @classmethod
    def onLoad(cls, clone):
        if clone is not None:
            cls.fromAndroid = clone.fromAndroid
        return True

CClient_.onLoad(None)