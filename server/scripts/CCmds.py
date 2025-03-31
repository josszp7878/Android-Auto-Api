from datetime import datetime
import threading
import time as time_module
import json
import _G

g = _G._G_
log = g.Log()
App = g.App()

# 添加缓存相关的变量
_screenInfoCache = None

# 添加一个全局变量来控制监控状态
_screenMonitorTask = None

class CCmds_:

    @classmethod
    def android(cls):
        return _G._G_.Tools().android
    

    
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
        
        @regCmd(r"信息-xx")
        def info():
            """
            功能：获取设备基本信息
            指令名: info-i
            中文名: 信息-xx
            参数: 无
            示例: 信息
            """
            try:
                g = _G._G_
                device = g.getClass('CDevice').instance()
                return {
                    "deviceID": device.deviceID if device else "未知",
                    "version": "1.0.0",
                    "timestamp": str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                }
            except Exception as e:
                return f"e->获取设备信息失败: {str(e)}"
        
        # 注册时间命令
        @regCmd(r"时间-sj")
        def date():
            """
            功能：获取当前时间
            指令名: date-d
            中文名: 时间-sj
            参数: 无
            示例: 时间
            """ 
            return str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # 注册状态命令
        @regCmd(r"状态-zt")
        def status():
            """
            功能：查看设备连接状态
            指令名: status-s
            中文名: 状态-zt
            参数: 无
            示例: 状态
            """  
            g = _G._G_
            device = g.getClass('CDevice').instance()
            status = "已连接" if device.connected else "未连接"
            return f"设备状态: {status}"
        
        # ... 其他命令注册 ...
        
        # _Log._Log_.d(f"CCmds模块命令注册完成")

        @regCmd(r"断开-dk")
        def disconnect():
            """
            功能：断开与服务器的连接
            指令名: disconnect-d
            中文名: 断开-dk
            参数: 无
            示例: 断开
            """
            g = _G._G_
            device = g.getClass('CDevice').instance()
            if device:
                device.disconnect()
                return "已断开连接"
            return "设备未连接"

        @regCmd(r"连接-lj", r"(?P<server>\S+)?")
        def connect(server):
            """
            功能：连接到指定的服务器地址
            指令名: connect-c
            中文名: 连接-lj
            参数: server - 服务器地址(可选)，如IP或域名
            示例: 连接 [192.168.1.100]
            """
            g = _G._G_
            device = g.Device()
            if device:
                return device.connect(server)
            return "设备未初始化"


        @regCmd(r"登录-dl")
        def login():
            """
            功能：登录设备
            指令名: login-l
            中文名: 登录-dl
            参数: 无
            示例: 登录
            """
            g = _G._G_
            device = g.getClass('CDevice').instance()
            if device.login():
                return "登录成功"
            return "登录失败"

        @regCmd(r"登出-dc")
        def logout():
            """
            功能：登出当前设备
            指令名: logout-l
            中文名: 登出-dc
            参数: 无
            示例: 登出
            """
            g = _G._G_
            device = g.getClass('CDevice').instance()
            device.logout()
            return "已登出"

        @regCmd(r"位置-wz", r"(?P<text>.+)")
        def pos(text):
            """
            功能：获取指定位置或文本的位置
            指令名: pos-w
            中文名: 位置-wz
            参数: text - 要获取位置的文本或坐标
            示例: 位置 确定
            """
            g = _G._G_
            tools = g.CTools()
            pos = tools.findTextPos(text)
            if pos:
                return f"{pos}"
            return "e->无效位置"

        @regCmd(r"点击-dj", r"(?P<text>.+)")
        def click(text):
            """
            功能：点击指定位置或文本
            指令名: click-c
            中文名: 点击-dj
            参数: text - 要点击的文本或坐标
            示例: 点击 确定
            """
            g = _G._G_
            tools = g.CTools()
            pos = tools.strToPos(text)
            if pos:
                return tools.clickPos(pos)
            return tools.click(text)

        @regCmd(r"安装了-azl", r"(?P<pkgName>\S+)")
        def isInstalled(pkgName):
            """
            功能：检查应用是否已安装
            指令名: isInstalled-iI
            中文名: 安装了-azl
            参数: pkgName - 应用包名
            示例: 安装了 com.example.app
            """
            android = cls.android()
            if android:
                return android.isAppInstalled(pkgName)
            return False

        @regCmd(r"安装-az", r"(?P<pkgName>\S+)")
        def install(pkgName):
            """
            功能：安装指定应用
            指令名: install-i
            中文名: 安装-az
            参数: pkgName - 应用包名或APK路径
            示例: 安装 com.example.app
            """
            android = cls.android()
            if android:
                return android.installApp(pkgName)
            return False

        @regCmd(r"卸载-xs", r"(?P<pkgName>\S+)")
        def uninstall(pkgName):
            """
            功能：卸载指定应用
            指令名: uninstall-u
            中文名: 卸载-xs
            参数: pkgName - 应用包名
            示例: 卸载 com.example.app
            """
            android = cls.android()
            if android:
                return android.uninstallApp(pkgName)
            return False

        @regCmd(r"打开-dk", r"(?P<appName>\S+)")
        def openApp(appName):
            """
            功能：打开指定应用
            指令名: openApp-oA
            中文名: 打开-dk
            参数: appName - 应用名称
            示例: 打开 微信
            """
            App = _G._G_.CApp()
            ret, app = App.goApp(appName)
            if not ret:
                return f"打开应用 {appName} 失败"
            return f"成功打开应用 {appName}, 当前页面: {app.currentPage.name}"

        @regCmd(r"关闭-gb", r"(?P<appName>\S+)?")
        def closeApp(appName=None):
            """
            功能：关闭应用
            指令名: closeApp-cA
            中文名: 关闭-gb
            参数: appName - 应用名称(可选)，不提供则关闭当前应用
            示例: 关闭 [微信]
            """
            App = _G._G_.App()
            # 如果未指定应用名，使用当前应用
            if not appName:
                appName = App.getCurAppName()
                if not appName:
                    return "未指定要关闭的应用"            
            return App.closeApp(appName)
            
        @regCmd(r"截屏-jp")
        def getScreen():
            """
            功能：获取屏幕结构化数据
            指令名: getScreen-g
            中文名: 截屏-jp
            参数: 无
            示例: 截屏
            """
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
                ],  ensure_ascii=False)
            
            except Exception as e:
                log.ex(e, "获取屏幕信息失败")
                return '[]'
        
        @regCmd(r"监控-jk", r"(?P<interval>\d+)?")
        def startScreenMonitor(interval=None):
            """
            功能：开始屏幕监控
            指令名: startScreenMonitor-s
            中文名: 监控-jk
            参数: interval - 监控间隔秒数(可选)
            示例: 监控 [5]
            """
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

        @regCmd(r"停止监控-tzjk")
        def stopScreenMonitor():
            """
            功能：停止屏幕监控
            指令名: stopScreenMonitor-s
            中文名: 停止监控-tzjk
            参数: 无
            示例: 停止监控
            """
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

        @regCmd(r"滑动-hd", r"(?P<param>.+)")
        def swipe(param):
            """
            功能：在屏幕上滑动
            指令名: swipe-s
            中文名: 滑动-hd
            参数: param - 滑动参数，格式为"起点x,起点y,终点x,终点y"或方向
            示例: 滑动 100,200,300,400
            """
            return _G._G_.Tools().swipe(param)

        @regCmd('快照-kz')
        def takeScreenshot():
            """
            功能：截取当前屏幕并发送到服务器
            指令名: takeScreenshot-t
            中文名: 快照-kz
            参数: 无
            示例: 快照
            """
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
            """
            功能：获取当前页面信息
            指令名: curPage-c
            中文名: 当前页面-dqym
            参数: appName - 应用名称(可选)
            示例: 当前页面 [微信]
            """
            pageName = ''
            App = _G._G_.App()
            if appName:
                # 获取指定应用的当前页面
                app = App.getApp(appName, True)
                if app and app.currentPage:
                    pageName = app.currentPage.name
                else:
                    return f"未找到应用 {appName} 或其页面信息"
            else:
                # 获取当前应用及其页面
                app = App.getCurApp()
                if app and app.currentPage:
                    pageName = app.currentPage.name
            return f"{app.name}:{pageName}"

        @regCmd(r"跳转-tz", r"(?P<target>.+)")
        def go(target):
            """
            功能：页面跳转
            指令名: go-g
            中文名: 跳转-tz
            参数: target - 目标页面路径
            示例: 跳转 首页
            """
            import CApp
            return CApp.CApp_.go(target)
        
        @regCmd(r"路径-lj", r"(?P<target>.+)")
        def pathTo(target):
            """
            功能：获取到目标页面的路径
            指令名: pathTo-p
            中文名: 路径-lj
            参数: target - 目标页面
            示例: 路径 设置
            """
            import _Page
            return _Page._Page_.currentPathTo(target)
        
        @regCmd(r"桌面-zm")
        def home():
            """
            功能：返回手机桌面
            指令名: home-h
            中文名: 桌面-zm
            参数: 无
            示例: 桌面
            """
            return _G._G_.Tools().goHome()
        
        @regCmd(r"返回-fh")
        def goBack():
            """
            功能：返回上一页
            指令名: goBack-g
            中文名: 返回-fh
            参数: 无
            示例: 返回
            """           
            return _G._G_.Tools().goBack()



        @regCmd(r"查找-cz", r"(?P<text>\S+)(?:\s+(?P<dir>[LRUDNONE]+))?(?:\s+(?P<distance>\d+))?")
        def findText(text, dir=None, distance=None):
            """
            功能：查找屏幕上的文字
            指令名: findText-f
            中文名: 查找-cz
            参数: 
              text - 要查找的文字
              dir - 查找方向(可选)，如LR(左右)、UD(上下)等
              distance - 查找距离(可选)
            示例: 查找 下一步 [LR] [500]
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
            """
            功能：下载指定文件
            指令名: download-d
            中文名: 下载-xz
            参数: fileName - 文件名(可选)，不提供则下载所有文件
            示例: 下载 [config.json]
            """
            g = _G._G_
            log = g.Log()
            try:
                FS = g.CFileServer()
                if fileName:
                    existFileName = g.findFileName(fileName)
                    if existFileName:
                        fileName = existFileName
                    FS.download(fileName)    
                else:
                    FS.downAll()
                return True
            except Exception as e:
                log.ex(e, '下载操作异常')
                return False

        @regCmd('获取文件-hqwj', r"(?P<fileName>.+)")
        def getFileName(fileName):
            """
            功能：检查文件是否存在
            指令名: getFileName-g
            中文名: 获取文件-hqwj
            参数: fileName - 要检查的文件名
            示例: 获取文件 config.json
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
            """
            功能：执行代码并返回结果
            指令名: eval-e
            中文名: 执行-zx
            参数: code - 要执行的代码
            示例: 执行 print("Hello")
            """
            g = _G._G_
            log = g.Log()
            try:
                result = g.Tools().eval(g,code)
                return g.Tools().toNetStr(result)
            except Exception as e:
                log.ex(e, f"执行代码失败: {code}")
                return None

        @regCmd('匹配文字-ppwz', r"(?P<rule>\S+)")
        def matchText(rule):
            """
            功能：在当前屏幕上查找文字
            指令名: matchText-m
            中文名: 匹配文字-ppwz
            参数: rule - 文字规则
            示例: 匹配文字 确定
            """
            g = _G._G_
            log = g.Log()
            try:
                if rule.startswith('@'):
                    import _Page
                    page = _Page._Page_.getCurrent().findPagesByPath(rule[1:])[-1]
                    return page.match(page.matches)
                result = g.CTools().matchText(rule, False)
                return result
            except Exception as e:
                log.ex(e, "查找文字失败")
                return None


        @regCmd(r"返回桌面-fhzm")
        def goHome():
            """
            功能：返回手机桌面
            指令名: goHome-g
            中文名: 返回桌面-fhzm
            参数: 无
            示例: 返回桌面
            """
            App = _G._G_.App()
            result = App.goHome()
            if result:
                return "已返回主屏幕"
            else:
                return "返回主屏幕失败"


        @regCmd(r"加载配置-jzpz")
        def loadConfig():
            """
            功能：加载环境配置
            指令名: loadConfig-l
            中文名: 加载配置-jzpz
            参数: 无
            示例: 加载配置
            """
            _G._G_.load()

        @regCmd(r"设置坐标修正范围-szzbxz", r"(?P<scope>\d+)")
        def setPosFixScope(scope):
            """
            功能：设置坐标修正范围
            指令名: setPosFixScope-spfs
            中文名: 设置坐标修正范围-szzbxz
            参数: scope - 修正范围
            示例: 设置坐标修正范围 100
            """
            _G._G_.CTools().setPosFixScope(int(scope))

        @regCmd(r"显示点击-xsdj", r"(?P<enable>\S+)?")
        def showClicker(enable=None):
            """
            功能：显示点击
            指令名: showClicker-s
            中文名: 显示点击-xsdj
            参数: enable - 是否显示
            示例: 显示点击 true
            """
            g = _G._G_
            android = g.CTools().android
            if android:
                android .showClicker(g.Tools().toBool(enable))

        @regCmd(r"拓扑图-tpt", r"(?P<appName>\S+)?")
        def appTopology(appName=None):
            """
            功能：打印应用页面拓扑结构图
            指令名: appTopology-aT
            中文名: 拓扑图-tpt
            参数: appName - 应用名称(可选)，不提供则使用当前应用
            示例: 拓扑图 [微信]
            """
            from _App import _App_
            return _App_.printTopology(appName)

        @regCmd(r"跳转页面-tzym", r"(?P<pageName>[^ ]+)(\s+(?P<appName>[^ ]+))?")
        def gotoPage(pageName, appName=None):
            """
            功能：跳转到指定应用的指定页面
            指令名: gotoPage-gp
            中文名: 跳转页面-tzym
            参数: 
                pageName - 目标页面名称
                appName - 应用名称(可选)，不提供则使用当前应用
            示例: 跳转页面 设置 [微信]
            """
            g = _G._G_
            log = g.Log()
            
            try:
                # 获取应用对象
                app = None
                if appName:
                    app = g.CApp().getApp(appName)
                    if not app:
                        return f"e->找不到应用: {appName}"
                else:
                    app = g.CApp().getCurrentApp()
                    if not app:
                        return "e->当前没有活跃的应用"
                
                # 执行页面跳转
                result = app._gotoPage(pageName)
                if result:
                    return f"成功跳转到页面: {pageName}"
                else:
                    return f"e->跳转到页面 {pageName} 失败"
            except Exception as e:
                log.ex(e, "执行页面跳转命令失败")
                return f"e->执行页面跳转命令失败: {str(e)}"


        @regCmd(r"应用为-yyw", r"(?P<appName>\S+)?")
        def checkApp(appName=None):
            """
            功能：启动全局应用检测器
            指令名: checkApp
            中文名: 应用为-yyw
            参数: appName - 应用名称(可选)，默认为当前应用
            示例: 应用为 [微信]
            """
            ret = g.Checker().checkApp(appName)
            return ret
       
        @regCmd(r"检查-jcq", r"(?P<checkerName>\S+)")
        def check(checkerName):
            """
            功能：测试指定名称的检查器，使用当前页面作为参数
            指令名: check
            中文名: 检查-jcq
            参数: 
                checkerName - 检查器名称
            示例: 检查 每日签到
            """
            Checker = g.Checker()
            # 获取当前应用和页面
            curApp = App.getCurApp()
            if not curApp:
                return "当前没有检测到应用，无法测试检查器"
            curPage = curApp.curPage
            if not curPage:
                return "当前没有检测到页面，无法测试检查器"
            # 创建检查器
            checker = Checker.add(checkerName, curPage, None)
            if not checker:
                return None
            # 设置回调函数
            def onCheckResult(result):
                log.i(f"检查器 {checkerName} 结果: {result}")
            
            checker.onResult = onCheckResult
            checker.enabled = True
            
            # 执行检查
            result = checker.check()
            if result:
                checker.do()
                return f"检查器 {checkerName} 匹配成功，已执行操作"
            else:
                return f"检查器 {checkerName} 匹配失败"
       