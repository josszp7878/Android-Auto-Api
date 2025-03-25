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
        return _G._G_.Tools().android
    
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
            # log = _G._G_.Log()
            # log.i("获取当前时dffdd")
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
            position = _G._G_.Tools().findText(text)
            android = cls.android()
            if position and android:
                return android.move(position[0], position[1])
            return "未找到"

        @regCmd(r"点击", r"(?P<text>.+)")
        def click(text):
            """点击指定位置，支持偏移"""
            g = _G._G_
            tools = g.CTools()
            pos = tools.strToPos(text)
            if pos:
                return tools.clickPos(pos)
            return tools.click(text)

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
            return _G._G_.Tools().openApp(appName)

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

        @regCmd(r"截屏-jp")
        def getScreen():
            """获取屏幕结构化数据"""
            try:
                g = _G._G_
                log = g.Log()
                screen_data = g.CTools().refreshScreenInfos()
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
            return _G._G_.Tools().swipe(param)

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

        @regCmd(r"当前页面-dqym", r"(?P<appName>\S+)?")
        def curPage(appName=None):
            """获取当前页面信息
            用法: 当前页面 [应用名]
            如果提供应用名，返回该应用的当前页面
            如果不提供应用名，返回当前应用及其页面
            """
            pageName = ''
            from CApp import CApp_
            if appName:
                # 获取指定应用的当前页面
                app = CApp_.getApp(appName, True)
                if app and app.currentPage:
                    pageName = app.currentPage.name
                else:
                    return f"未找到应用 {appName} 或其页面信息"
            else:
                # 获取当前应用及其页面
                appName = CApp_.getCurAppName(True)
                app = CApp_.getApp(appName)
                if app and app.currentPage:
                    pageName = app.currentPage.name
            return f"{appName}:{pageName}"

        @regCmd(r"跳转-tz", r"(?P<target>.+)")
        def go(target):
            """页面跳转测试命令"""
            import CApp
            return CApp.CApp_.go(target)
        
        @regCmd(r"路径-lj", r"(?P<target>.+)")
        def pathTo(target):
            """页面路径测试命令"""
            import _Page
            return _Page._Page_.currentPathTo(target)
        
        @regCmd(r"桌面-zm")
        def home():
            """返回手机桌面"""
            return _G._G_.Tools().goHome()
        
        @regCmd(r"返回-fh")
        def goBack():
            """返回上一页"""           
            return _G._G_.Tools().goBack()



        @regCmd(r"查找-cz", r"(?P<text>\S+)(?:\s+(?P<dir>[LRUDNONE]+))?(?:\s+(?P<distance>\d+))?")
        def findText(text, dir=None, distance=None):
            """测试文字查找功能
            格式：测试查找 文字 [方向] [距离]
            示例：测试查找 下一步 LR 500
            """
            distance = int(distance) if distance else None
            g = _G._G_
            log = g.Log()
            pos = g.Tools().findText(text, dir, distance)
            log.i(f"找到文字位置: {pos}")
            
            if pos:
                # 安全地访问坐标
                if isinstance(pos, tuple) and len(pos) >= 2:
                    return f"找到文字位置: {pos[0]},{pos[1]}"
                else:
                    # 处理非元组返回值
                    return f"找到文字，但返回格式异常: {pos}"
            return "未找到匹配文字"
       

        @regCmd('下载-xz', r"(?P<fileName>.+)?")
        def download(fileName):
            """下载指定文件"""
            g = _G._G_
            log = g.Log()
            try:
                FS = g.CFileServer()
                if fileName:
                    existFileName = g.findFileName(fileName)
                    if existFileName:
                        fileName = existFileName
                    # log.i(f"下载文件: {fileName}")
                    FS.download(fileName)    
                else:
                    FS.downAll()
                return True
            except Exception as e:
                log.ex(e, '下载操作异常')
                return False

        @regCmd('获取文件-hqwj', r"(?P<fileName>.+)")
        def getFileName(fileName):
            """检查文件是否存在
            Args:
                fileName: 要检查的文件名
            Returns:
                str: 文件是否存在的结果
            """
            g = _G._G_
            log = g.Log()
            try:
                return g.findFileName(fileName)
            except Exception as e:
                log.ex(e, f'检查文件 {fileName} 是否存在时出错')
                return f"e->{str(e)}"

        @regCmd(r"执行-zx", r"(?P<code>.+)")
        def eval(code):
            """执行代码并返回结果
            用法: eval <代码>
            """
            g = _G._G_
            log = g.Log()
            try:
                result = g.Tools().eval(code)
                return g.Tools().toNetStr(result)
            except Exception as e:
                log.ex(e, f"执行代码失败: {code}")
                return None

        @regCmd('匹配文字-ppwz', r"(?P<rule>\S+)")
        def matchText(rule):
            """在当前屏幕上查找文字
            用法: 匹配文字 <文字规则>
            
            文字规则支持以下格式:
            - 普通文字: 直接查找包含该文字的元素
            - 区域限制: [x1,y1,x2,y2]文字 - 在指定区域内查找文字
            - Y轴限制: [y100,200]文字 - 在指定Y轴范围内查找文字
            - X轴限制: [x100,200]文字 - 在指定X轴范围内查找文字
            
            返回找到的元素信息，包括文字内容和位置
            """
            g = _G._G_
            log = g.Log()
            try:
                if rule.startswith('@'):
                    import _Page
                    pages = _Page._Page_.getCurrent().findPageByPath(rule[1:])
                    page = pages.last()
                    return page.checkRules(page.rules)
                result = g.CTools().matchText(rule, False)
                return result
            except Exception as e:
                log.ex(e, "查找文字失败")
                return None


        @regCmd(r"打开-dk", r"(?P<appName>\S+)")
        def openApp(appName):
            """打开指定应用
            用法: 打开应用 <应用名>
            """
            from CApp import CApp_
            result = CApp_.gotoApp(appName)
            if result:
                # 检查应用是否在配置中注册
                app = CApp_.getApp(appName)
                if app and app.currentPage:
                    return f"成功打开应用 {appName}，当前页面: {app.currentPage.name}"
                return f"成功打开应用 {appName}"
            else:
                return f"打开应用 {appName} 失败"

        @regCmd(r"返回桌面-fhzm")
        def goHome():
            """返回主屏幕"""
            from CApp import CApp_
            result = CApp_.goHome()
            if result:
                return "已返回主屏幕"
            else:
                return "返回主屏幕失败"


        @regCmd(r"关闭-gb", r"(?P<appName>\S+)?")
        def closeApp(appName=None):
            """关闭应用
            用法: 关闭应用 [应用名]
            如果不提供应用名，则关闭当前应用
            """
            from CApp import CApp_
            
            # 如果未指定应用名，使用当前应用
            if not appName:
                appName = CApp_.getCurAppName()
                if not appName:
                    return "未指定要关闭的应用"
            
            result = CApp_.closeApp(appName)
            if result:
                return f"已关闭应用 {appName}"
            else:
                return f"关闭应用 {appName} 失败"
        

        @regCmd(r"加载配置-jzpz")
        def loadConfig():
            """加载环境配置
            """
            _G._G_.load()


