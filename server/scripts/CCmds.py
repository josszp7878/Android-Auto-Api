from ctypes import cast
from datetime import datetime
import json
import _G
# import typing
# if typing.TYPE_CHECKING:

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
    
    _editTarget = None

    @classmethod
    def registerCommands(cls):
        # 导入 regCmd
        from _CmdMgr import regCmd

        @regCmd(r"(?P<text>.+?)#的位置|dwz")
        def pos(text):
            """
            功能：获取指定位置或文本的位置
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
        def inStall(pkgName):
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

        @regCmd(r"#卸载|xz(?P<pkgName>\S+)")
        def unInstall(pkgName):
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
            App = _G._G_.App()
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
        def sWipe(param):
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
        def hoMe():
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
       

        @regCmd(r"#下载 (?P<fileName>.+)?")
        def downLoad(fileName):
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

        @regCmd(r"#执行代码|zxdm (?P<code>.+)")
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
            """
            from _App import _App_
            return _App_.printTopology(appName)
        
        @regCmd(r"#显示|xs(?P<uiName>\S+)(?P<enable>\S+)?")
        def sHow(uiName:str, enable=None):
            """
            功能：启用/关闭显示UI组件
            示例: 
            xs 坐标 1
            xs 工具栏 1
            xs 日志 1
            """
            g = _G._G_
            log = g.Log()
            enable = g.Tools().toBool(enable, True)
            android = g.CTools().android
            log.i(f"显示{uiName}: {enable}")
            
            if not android:
                return
            
            # UI组件配置：[别名1, 别名2, ..., 方法名]
            showConfig = [
                ['坐标', 'zb', 'pos', 'showClick'],
                ['工具栏', 'gjl', 'toolbar', 'showToolbar'],
                ['日志', 'rz', 'log', 'showLog'],
                ['界面', 'ui', 'showUI'],
                ['光标', 'gb', 'cursor', 'showCursor']
            ]
            # 在配置中查找匹配的UI组件
            for component in showConfig:
                # 最后一个元素是方法名，其余都是别名
                method_name = component[-1]
                aliases = component[:-1]
                if uiName in aliases:
                    # 动态调用对应的方法
                    if hasattr(android, method_name):
                        method = getattr(android, method_name)
                        method(enable)
                        return
            
            # 未找到匹配的组件
            log.e(f"显示{uiName} {'开启' if enable else '关闭'}失败")

        @regCmd(r"#退出|tc")
        def eXit():
            """退出应用
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

        # === 检查器相关命令 ===
        @regCmd(r"#编辑|bj(?P<name>\S+)")
        def eDit(name):  
            """
            功能：开始编辑
            检测器有以下参数可以设置：
                match: 匹配规则
                do: 匹配 + 操作 对
                timeout: 超时时间
                interval: 检测间隔
                示例:
                "name": "每日打.+好礼",
                "do": {"点我.取": "click"}
            示例：
            @编辑 每日打.+好礼
            """
            if not name.strip():
                return "e~检查器名称不能为空"
            g = _G._G_
            name = g.App().getCheckName(name)
            checker = g.Checker().getTemplate(name, True)
            cls._editTarget = checker
            if checker:
                return f"开始编辑... {name}"
            

        @regCmd(r"#设置属性|szsx (?P<param>\w+)(?P<value>.+)?")
        def setProp(param, value=None):
            """
            设置检查器参数，如interval、timeout,match,do等
            其中do的格式为：{匹配, 操作}
            示例：
            set do {'.*签到', 'click'}
            set match {'.*签到'}
            set timeout {10}
            """
            target = cls._editTarget
            if not target:
                return "e~请先开始编辑检查器"
            value = g.Tools().fromStr(value)
            # 使用setattr设置普通属性
            try:
                setattr(target, param, value)
            except AttributeError:
                return f"e~设置属性: {param} 失败"
            return f"设置参数 {param}={value}"

        @regCmd(r"#\+|添加属性|tjsx(?P<param>\w+)(?P<value>\S+)?(?P<postfix>\S+)?")
        def addProp(param, value=None, postfix=None):
            """
            添加数组类型参数里面的某个ITEM，match, checks等
            示例：
            add match 发现 100
            add checks 签到
            """
            target = cls._editTarget
            if not target:
                return "e~请先开始编辑检查器"
            value = g.Tools().fromStr(value)
            target.addProp(param, value, postfix)

        @regCmd(r"#\-|移除属性|ycsx(?P<param>\S+)(?P<value>\S+)?")
        def removeProp(param, value=None):
            """
            删除数组类型参数里面的某个ITEM，match, checks等
            示例：
            remove match 签到
            remove checks 签到
            """ 
            target = cls._editTarget
            if not target:
                return "e~请先开始编辑检查器"
            value = g.Tools().fromStr(value)
            target.removeProp(param, value)

        @regCmd(r"#保存|bc(?P<save>[01]*)?")
        def sAve(save='1'):
            target = cls._editTarget
            if not target:
                return "e~当前没有编辑的对象"
            if not target.save(save=g.Tools().toBool(save, True)):
                return f"e~保存{target.name} 失败"
            cls._editTarget = None
            return f"保存{target.name} 成功"

        @regCmd(r"#删除|sc(?P<checkName>\S+)?")
        def dElete(checkName=None):
            if not checkName:                
                if cls._editTarget:
                    checkName = cls._editTarget.name
            if g.Checker().delete(checkName):
                return f"删除检查器 {checkName} 成功"

        @regCmd(r"#检查列表|jclb")
        def listChecK():
            checker = g.Checker()
            return "当前检查器列表：\n" + "\n".join(f'{t.name}' for t in checker.templates())
        
        @regCmd(r"#显示检查|xsjc (?P<checkName>\S+)")
        def sHowCheck(checkName):
            """
            功能：显示检查器
            示例：
            xsjc -发现
            """
            checkName = g.App().getCheckName(checkName)
            checkers = g.Checker().getTemplates(checkName)
            if not checkers:
                return f"{checkName} 不存在"
            return "\n".join(f"{json.dumps(t.to_dict(), indent=2, ensure_ascii=False)}" for t in checkers)

        @regCmd(r"#匹配|pp(?P<name>\S+)")
        def maTch(name, enabled=None):
            """
            功能：匹配指定名称的检查器
            示例: 匹配 每日签到
            """ 
            g = _G._G_
            name = g.App().getCheckName(name)
            checker = g.Checker().getTemplate(name, False)
            if checker:
                checker.Match()
            else:
                return f"e~无效检查器: {name}"
            
        @regCmd(r"#检查|jc(?P<name>\S+)")
        def checK(name):
            """
            功能：检查指定名称的检查器
            示例: 检查 每日签到
            """
            g = _G._G_
            name = g.App().getCheckName(name)
            g.Checker().check(name, g.App().currentApp())
            return f"检查器 {name} 已检查"

        @regCmd(r"#执行|zx(?P<name>\S+)")
        def do(name):
            """
            功能：执行指定名称的检查器
            示例: 执行 每日签到
            """
            g = _G._G_
            name = g.App().getCheckName(name)
            checker = g.Checker().getTemplate(name, False)
            if checker:
                checker.Do()
            else:
                return f"e~无效检查器: {name}"