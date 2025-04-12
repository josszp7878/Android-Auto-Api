from datetime import datetime
import threading
import time as time_module
import json
import _G
from _CmdMgr import regCmd

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
        _G._G_.Log().i("注册CCmds模块命令...")
        # 导入 regCmd
        from _CmdMgr import regCmd
        
        @regCmd(r"#信息|xx")
        def info():
            """
            功能：获取设备基本信息
            指令名: info-i
            中文名: 信息
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
                return f"e~获取设备信息失败: {str(e)}"
        
        # 注册时间命令
        @regCmd(r"#时间|sj")
        def date():
            """
            功能：获取当前时间
            指令名: date-d
            中文名: 时间
            参数: 无
            示例: 时间
            """ 
            return str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # 注册状态命令
        @regCmd(r"#状态|zt")
        def status():
            """
            功能：查看设备连接状态
            指令名: status-s
            中文名: 状态
            参数: 无
            示例: 状态
            """  
            g = _G._G_
            device = g.CDevice()
            status = "已连接" if device.connected else "未连接"
            return f"设备状态: {status}"
        


        @regCmd(r"(?P<text>.+?)#的位置|dwz")
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
            return "e~无效位置"

        @regCmd(r"#点击|dj(?P<text>\S+)?(?P<dir>[LlRrUuDd]+)?")
        def clIck(text, dir=None):
            """
            功能：点击指定位置或文本
            指令名: click-c
            中文名: 点[击]
            参数: text - 要点击的文本或坐标
            示例: 点[击] 确定
            """
            g = _G._G_
            tools = g.CTools()
            pos = tools.strToPos(text)
            if pos:
                return tools.clickPos(pos)
            return tools.click(text)

        @regCmd(r"#安装了|azl (?P<pkgName>\S+)")
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

        @regCmd(r"#安装|az (?P<pkgName>\S+)")
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

        @regCmd(r"#卸载|xs (?P<pkgName>\S+)")
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

        @regCmd(r"#打开|dk (?P<appName>\S+)")
        def openApp(appName):
            """
            功能：打开指定应用
            指令名: openApp-oA
            中文名: 打开-dk
            参数: appName - 应用名称
            示例: 打开 微信
            """
            App = _G._G_.CApp()
            ret = App.goApp(appName)
            if not ret:
                return f"打开应用 {appName} 失败"
            return f"成功打开应用 {appName}"

        @regCmd(r"#关闭|gb (?P<appName>\S+)?")
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
            
        @regCmd(r"#截屏|jp")
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
                if screen_data:
                    # 确保返回标准JSON
                    return json.dumps([
                        {
                            "t": item.get("t", ""),
                            "b": item.get("b", "")
                        } for item in screen_data
                    ],  ensure_ascii=False)
            
            except Exception as e:
                log.ex(e, "获取屏幕信息失败")
        

        @regCmd(r"#滑动|hd (?P<param>.+)")
        def swipe(param):
            """
            功能：在屏幕上滑动
            指令名: swipe
            中文名: 滑动
            参数: param - 滑动参数，格式为"起点x,起点y,终点x,终点y"或方向
            示例: 滑动 100,200,300,400
            """
            return _G._G_.CTools().swipe(param)

        @regCmd(r"#快照|kz")
        def takeScreenshot():
            """
            功能：截取当前屏幕并发送到服务器
            指令名: takeScreenshot-t
            中文名: 快照-kz
            参数: 无
            示例: 快照
            """
            _G._G_.CDevice().TakeScreenshot()

        @regCmd(r"#当前页面|dqym(?P<appName>\S+)?")
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
                if app and app._currentPage:
                    pageName = app._currentPage.name
                else:
                    return f"未找到应用 {appName} 或其页面信息"
            else:
                # 获取当前应用及其页面
                app = App.currentApp()
                if app and app._currentPage:
                    pageName = app._currentPage.name
            return f"{app.name if app else '':}:{pageName}"

        @regCmd(r"#跳转|tz (?P<target>.+)")
        def go(target):
            """
            功能：页面跳转
            指令名: go-g
            中文名: 跳转-tz
            参数: target - 目标页面路径
            示例: 跳转 首页
            """
            return _G._G_.App().currentApp().go(target)
        
        @regCmd(r"#路径|lj (?P<target>.+)")
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
        
        @regCmd(r"#桌面|zm|home")
        def home():
            """
            功能：返回手机桌面
            指令名: home-h
            中文名: 桌面-zm
            参数: 无
            示例: 桌面
            """
            return _G._G_.Tools().goHome()
        
        @regCmd(r"#返回|fh")
        def back():
            """
            功能：返回上一页
            指令名: back
            中文名: 返回
            参数: 无
            示例: 返回
            """           
            return _G._G_.Tools().goBack()



        @regCmd(r"#查找|cz (?P<text>\S+)(?:\s+(?P<dir>[LRUDNONE]+))?(?:\s+(?P<distance>\d+))?")
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
       

        @regCmd(r"#下载|xz (?P<fileName>.+)?")
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

        @regCmd(r"#获取文件(?P<fileName>.+)")
        def getFileName(fileName):
            """
            功能：检查文件是否存在
            指令名: getFileName
            中文名: 获取文件
            参数: fileName - 要检查的文件名
            示例: 获取文件 config.json
            """
            g = _G._G_
            log = g.Log()
            try:
                return g.findFileName(fileName)
            except Exception as e:
                log.ex(e, f'检查文件 {fileName} 是否存在时出错')
                return f"e~{str(e)}"

        @regCmd(r"#执行|zx (?P<code>.+)")
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
                result = g.Tools().doEval(g,code)
                return g.Tools().toNetStr(result)
            except Exception as e:
                log.ex(e, f"执行代码失败: {code}")
                return None

        @regCmd(r"#重载配置|zlpz")
        def loadConfig():
            """
            功能：加载环境配置
            指令名: loadConfig-l
            中文名: 加载配置-jzpz
            参数: 无
            示例: 加载配置
            """
            g = _G._G_
            g.CFileServer().download('config/pages.json', lambda result: g.App().loadConfig())

        @regCmd(r"#设置坐标修正范围|szzbxz (?P<scope>\d+)")
        def setPosFixScope(scope):
            """
            功能：设置坐标修正范围
            指令名: setPosFixScope-spfs
            中文名: 设置坐标修正范围-szzbxz
            参数: scope - 修正范围
            示例: 设置坐标修正范围 100
            """
            _G._G_.CTools().setPosFixScope(int(scope))


        @regCmd(r"#拓扑图|tpt (?P<appName>\S+)?")
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
        
        @regCmd(r"#显示坐标|xszb(?P<enable>\S+)?")
        def showClick(enable=None):
            """
            功能：启用/关闭显示坐标
            指令名: enableTouchMonitor
            中文名: 显示坐标
            参数: enable - 是否启用
            示例: 触摸监控 [true]
            """
            g = _G._G_
            log = g.Log()
            android = g.CTools().android
            
            # 默认为True
            enable_value = g.Tools().toBool(enable, True)
            log.i(f"设置触摸监控: {enable_value}")
            
            if android:
                try:
                    android.showClick(enable_value)
                    return f"触控监控{'开启' if enable_value else '关闭'}"
                except Exception as e:
                    log.ex(e, "设置触摸监控失败")
                    return f"设置触摸监控失败: {str(e)}"
            else:
                return f"触控监控{'开启' if enable_value else '关闭'}"

        @regCmd(r"#匹配|pp (?P<rule>\S+)")
        def match(rule):
            """
            功能：匹配当前屏幕上查找文字或者页面
            指令名: match-m
            中文名: 匹配-pp
            参数: rule - 文字规则或者页面名
            示例: 匹配 确定
            """
            g = _G._G_
            log = g.Log()
            try:
                if rule.startswith('@'):
                    rule = rule[1:].strip()
                    # 检查应用和页面，格式为app.page
                    page = g.App().getAppPage(rule)
                    if page:
                        return page.match()
                result = g.CTools().matchTexts(rule, True)
                return result
            except Exception as e:
                log.ex(e, "查找文字失败")
                return None


        @regCmd(r"#检查|jc (?P<checkerName>\S+)(?:\s+(?P<enabled>\S+))?")
        def chEck(checkerName, enabled=None):
            """
            功能：停止指定名称的检查器
            指令名: check-c
            中文名: 检查-jc
            参数: checkerName - 检查器名称
            示例: 检查 每日签到
            """ 
            g = _G._G_
            Checker = g.Checker()
            enabled = g.Tools().toBool(enabled, True)
            checkerName = checkerName.lower()
            if checkerName.startswith('@'):
                checkerName = checkerName[1:].strip()
                # 检查应用和页面，格式为app.page
                page = g.App().getAppPage(checkerName)
                if page:
                    page.check()
                    return f"已经开始检查页面 {page.name}"
            elif checkerName.startswith('!'):
                pageName = checkerName[1:].strip()
                g.App().currentApp().detectPage(pageName)
                return "已关闭当前应用"

            # 检查器
            checker = Checker.get(checkerName, create=True)
            log.i(f"checker.config = {checker._actions}")
            if checker:
                checker.enabled = enabled
                return f"检查器 {checkerName} 已设置为 {enabled}"
            else:
                return f"e~无效检查器: {checkerName}"

        @regCmd(r"#退出|tc")
        def exit():
            """退出应用
            指令名: exit
            中文名: 退出应用
            参数: 无
            示例: exit
            """
            try:
                # 获取Android对象
                android = _G._G_.Tools().android
                if android:
                    # 调用退出应用的方法
                    android.exitApp()
                    return "应用正在退出..."
                else:
                    return "无法获取Android对象，退出失败"
            except Exception as e:
                log.ex(e, "退出应用失败")
                return f"退出应用失败: {str(e)}"


       