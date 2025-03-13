from datetime import datetime
import threading
import time as time_module
import json
import _G

# 添加缓存相关的变量
_screenInfoCache = None

# 添加一个全局变量来控制监控状态
_screenMonitorTask = None

class CCmds_:

    @classmethod
    def android(cls):
        return _G._G_.CTools().android
    
    @classmethod
    def Clone(cls, oldCls):
        log = _G._G_.Log()
        log.i("CCmds模块克隆 ddddddd注册命令")

    
    @classmethod
    def OnReload(cls):
        g = _G._G_
        log = g.Log()
        """热更新后重新注册命令"""
        log.i("CCmds模块热更新 重新注册命令")
        cls.registerCommands()


    @classmethod
    def registerCommands(cls):
        log = _G._G_.Log()
        log.i("注册CCmds模块命令...")
        # 导入 regCmd
        from _CmdMgr import regCmd
        
        @regCmd(r"信息")
        def info():
            """获取设备信息"""
            try:
                g = _G._G_
                log = g.Log()
                device = g.getClass('CDevice').instance()
                # log.i(f"获取设备信息: {device}")
                return {
                    "deviceID": device.deviceID if device else "未知",
                    "version": "1.0.0",
                    "timestamp": str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                }
            except Exception as e:
                return f"e->获取设备信息失败: {str(e)}"
        
        # 注册时间命令
        @regCmd(r"时间")
        def date():
            """获取当前时间""" 
            log = _G._G_.Log()
            log.i("获取当前时间ddd")
            return str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # 注册状态命令
        @regCmd(r"状态")
        def status():
            """查看设备状态"""
            g = _G._G_
            device = g.getClass('CDevice').instance()
            status = "已连接" if device.connected else "未连接"
            return f"设备状态: {status}"
        
        # ... 其他命令注册 ...
        
        # _Log._Log_.d(f"CCmds模块命令注册完成")

        @regCmd(r"断开")
        def disconnect():
            """断开连接"""
            # 在函数内部导入 CDevice
            g = _G._G_
            device = g.getClass('CDevice').instance()
            if device:
                device.disconnect()
                return "已断开连接"
            return "设备未连接"

        @regCmd(r"连接", r"(?P<server>\S+)")
        def connect(server):
            """连接到服务器
            用法: 连接 <服务器地址>
            """
            g = _G._G_
            device = g.getClass('CDevice').instance()
            if device:
                return device.connect(server)
            return "设备未初始化"


        @regCmd(r"登录")
        def login():
            """登录设备"""
            g = _G._G_
            device = g.getClass('CDevice').instance()
            if device.login():
                return "登录成功"
            return "登录失败"

        @regCmd(r"登出")
        def logout():
            """登出设备"""
            g = _G._G_
            device = g.getClass('CDevice').instance()
            device.logout()
            return "已登出"

        @regCmd(r"连接状态")
        def isConnect():
            """检查连接状态"""
            g = _G._G_
            device = g.getClass('CDevice').instance()
            if device.connected:
                return f"已连接到服务器，设备ID: {device.deviceID}"
            return "未连接到服务器"

        
        @regCmd(r"移到", r"(?P<text>.+)")
        def move(text):
            position = _G._G_.CTools().findText(text)
            android = cls.android()
            if position and android:
                return android.move(position[0], position[1])
            return "未找到"

        @regCmd(r"点击", r"(?P<param>\S+)(?:\s+(?P<offset>\d+,\d+))?")
        def click(param, offset=None):
            """点击指定位置，支持偏移"""
            g = _G._G_
            log = g.Log()
            log.i(f"点击指令: {param} {offset}")
            if not param:
                return False
            android = cls.android()
            if not android:
                log.e("点击失败:未找到Android实例")
                return False
            position = _G._G_.CTools().findText(param)   
            if position:
                # 应用偏移量
                x, y = 0, 0
                if offset:
                    offset = offset.split(',')
                    x, y = int(offset[0]), int(offset[1])
                x, y = position[0] + x, position[1] + y
                return android.click(x, y)
            return False

        @regCmd(r"检查安装\s+(?P<pkgName>\S+)")
        def isInstalled(pkgName):
            android = cls.android()
            if android:
                return android.isAppInstalled(pkgName)
            return False

        @regCmd(r"安装\s+(?P<pkgName>\S+)")
        def install(pkgName):
            android = cls.android()
            if android:
                return android.installApp(pkgName)
            return False

        @regCmd(r"卸载\s+(?P<pkgName>\S+)")
        def uninstall(pkgName):
            android = cls.android()
            if android:
                return android.uninstallApp(pkgName)
            return False

        @regCmd(r"启动|打开", r"(?P<appName>\S+)")
        def openApp(appName):
            """打开应用"""
            return _G._G_.CTools().openApp(appName)

        @regCmd(r"停止|关闭", r"(?P<pkgName>\S+)")
        def stopApp(pkgName):
            android = cls.android()
            if android:
                return android.closeApp(pkgName)
            return False

        @regCmd(r"切换应用|任务列表|最近任务")
        def switchApp():
            """显示最近任务列表"""
            android = cls.android()
            if android:
                return android.showRecentApps()
            return False

        @regCmd(r"截屏")
        def getScreen():
            """获取屏幕结构化数据"""
            try:
                g = _G._G_
                log = g.Log()
                screen_data = g.getClass('CTools').refreshScreenInfos()
                # 确保返回标准JSON
                return json.dumps([
                    {
                        "t": item.get("t", ""),
                        "b": item.get("b", "")
                    } for item in screen_data
                ], ensure_ascii=False)
            except Exception as e:
                log.ex(e, "获取屏幕信息失败")
                return '[]'


        @regCmd(r"查找应用", r"(?P<appName>[\w\s]+)")
        def _toApp(appName: str) -> bool:
            """查找应用"""
            log = _G._G_.Log()
            try:
                android = cls.android()
                if android:
                    texts = android.getScreenText()
                    if not texts:
                        return False
                    for text in texts:
                        if appName in text:
                            return True
                return False
            except Exception as e:
                log.ex(e, "查找应用失败")
                return False

        def clearScreenCache():
            """清除屏幕信息缓存"""
            global _screenInfoCache
            _screenInfoCache = None
        
        @regCmd(r"监控", r"(?P<interval>\d+)?")
        def startScreenMonitor(interval=None):
            """开始屏幕监控"""
            global _screenMonitorTask
            g = _G._G_
            log = g.Log()
            log.i(f"开始监控@: {interval}")
            if _screenMonitorTask and _screenMonitorTask.is_alive():
                return "e->监控已在运行中"
            try:
                interval = int(interval) if interval else 5
                if interval < 1:
                    return "e->间隔时间不能小于1秒"
                def monitor_task():
                    while _screenMonitorTask:
                        try:
                            g.CClient().TakeScreenshot()
                            time_module.sleep(interval)
                        except Exception as e:
                            log.ex(e, "监控任务异常")
                            break
                _screenMonitorTask = threading.Thread(target=monitor_task, daemon=True)
                _screenMonitorTask.start()
                return f"开始屏幕监控(间隔{interval}秒)"
            except Exception as e:
                log.ex(e, "启动监控失败")
                return f"e->启动监控失败: {str(e)}"

        @regCmd(r"停止监控")
        def stopScreenMonitor():
            """停止屏幕监控"""
            global _screenMonitorTask
            g = _G._G_
            log = g.Log()
            log.i(f"停止监控: {_screenMonitorTask}")
            if not _screenMonitorTask or not _screenMonitorTask.is_alive():
                return "监控未运行"
            try:
                _screenMonitorTask = None
                return "已停止屏幕监控"
            except Exception as e:
                log.ex(e, "停止监控失败")
                return f"e->停止监控失败: {str(e)}"


        @regCmd(r"截图")
        def captureScreen():
            """截图指令"""
            try:
                g = _G._G_
                log = g.Log()
                log.i("截图指令")
                android = cls.android()
                if android:
                    image = android.takeScreenshot()
                    if not image:
                        return "e->截图失败:未获取到图片数据"
                if not image.startswith("data:image"):
                    image = f"data:image/jpeg;base64,{image}"
                return image
            except Exception as e:
                log.ex(e, "截图失败")
                return f"e->截图失败:{str(e)}"


        @regCmd(r"滑动", r"(?P<param>.+)")
        def swipe(param):
            ret = _G._G_.CTools().swipe(param)
            return "i->滑动成功" if ret else "e->滑动失败"

        @regCmd('快照')
        def takeScreenshot():
            """截取当前屏幕并发送到服务器"""
            g = _G._G_
            log = g.Log()
            try:
                device = g.getClass('CDevice').instance()
                device.TakeScreenshot()
            except Exception as e:
                log.ex(e, '截图失败')
                return f'e->截图异常: {str(e)}'

        @regCmd(r"当前应用")
        def curApp():
            """获取当前正在运行的应用信息"""
            g = _G._G_
            log = g.Log()
            try:
                log.i("获取当前应用111")
                return _G._G_.CTools().getCurrentApp()
            except Exception as e:
                log.ex(e, "获取当前应用失败")
                return None

        @regCmd(r"当前页面")
        def currentPage():
            return _G._G_.PageMgr().findCurPage() or None

        @regCmd(r"跳转", r"(?P<target>.+)")
        def go(target):
            """页面跳转测试命令"""
            return _G._G_.PageMgr().go(target)

        @regCmd(r"桌面")
        def home():
            """返回手机桌面"""
            return _G._G_.CTools().goHome()
        
        @regCmd(r"返回")
        def back():
            """返回上一页"""
            return _G._G_.CTools().goBack()

        @regCmd(r"查找路径", r"(?P<fromPage>\S+)\s*->\s*(?P<toPage>\S+)")
        def findPath(fromPage, toPage):
            """测试路径查找功能"""
            path = _G._G_.PageMgr().findPath(fromPage, toPage)
            if path:
                return f"找到路径: {' → '.join(path)}"
            else:
                return f"未找到 {fromPage} 到 {toPage} 的路径"

        @regCmd(r"查找", r"(?P<text>\S+)(?:\s+(?P<dir>[LRUDNONE]+))?(?:\s+(?P<distance>\d+))?")
        def findText(text, dir=None, distance=None):
            """测试文字查找功能
            格式：测试查找 文字 [方向] [距离]
            示例：测试查找 下一步 LR 500
            """
            distance = int(distance) if distance else None
            g = _G._G_
            log = g.Log()
            pos = g.CTools().findText(text, dir, distance)
            log.i(f"找到文字位置: {pos}")
            
            if pos:
                # 安全地访问坐标
                if isinstance(pos, tuple) and len(pos) >= 2:
                    return f"找到文字位置: {pos[0]},{pos[1]}"
                else:
                    # 处理非元组返回值
                    return f"找到文字，但返回格式异常: {pos}"
            return "未找到匹配文字"
       
        # 新增文件更新相关命令
        @regCmd('更新')
        def updateFiles():
            """触发文件更新"""
            g = _G._G_
            log = g.Log()
            try:
                def callback(success):
                    if success:
                        log.i("文件更新成功")
                    else:
                        log.w("文件更新失败或无需更新")
                g.getClass('CFileServer').update(callback)
                return "i->开始检查文件更新..."
            except Exception as e:
                log.ex(e, '文件更新失败')
                return f"e->{str(e)}"

        @regCmd('下载', r"(?P<fileName>.+)")
        def download(fileName):
            """下载指定文件"""
            g = _G._G_
            log = g.Log()
            try:
                def callback(success):
                    if success:
                        log.i(f"文件[{fileName}]下载成功")
                    else:
                        log.w(f"文件[{fileName}]下载失败")
                fileName = g.CFileServer().toRelativePath(fileName)
                g.CFileServer().download(fileName, callback)
                return f"i->开始下载文件:{fileName}"
            except Exception as e:
                log.ex(e, '下载操作异常')
                return f"e->{str(e)}"


