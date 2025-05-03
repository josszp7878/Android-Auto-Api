import json
import time
import _G
from typing import List, Optional

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
        return _G._G_.android
    
    _editTarget = None

    @classmethod
    def registerCommands(cls):
        # 导入 regCmd
        from _CmdMgr import regCmd

        @regCmd(r"#位置|wz(?P<text>.+?)")
        def pos(text):
            """
            功能：获取指定位置或文本的位置
            参数: text - 要获取位置的文本或坐标
            示例: 位置 确定
            """
            g = _G._G_
            tools = g.Tools()
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
            tools = g.Tools()
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
            ret = App.open(appName)
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
                appName = App.curName()
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
                screen_data = g.Tools().refreshScreenInfos()
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
            return _G._G_.Tools().swipe(param)

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

        @regCmd(r"#当前|dq(?P<what>\S*)")
        def cuRrenT(what):
            """
            功能：获取当前信息，支持包括当前应用、页面、坐标，任务等
            参数: what，按如下规则解析
                  pos|位置:  坐标
                  task|任务: 任务
                  其它: 应用名称-页面名称：如果应用名—为空，表示当前应用，返回应用名称-页面名称
                  空：  则返回当前应用和页面
            示例: 
                 当前 
                 当前 pos|位置
                 当前 task|任务
                 当前 微信-首页
            """
            g = _G._G_
            log = g.Log()
            tools = g.Tools()
            App = g.App()
            app = App.cur()
            if what:
                if what == 'pos|位置':
                    return log.i('todo: 获取坐标')
                if what == 'task|任务':
                    return log.i('todo: 获取任务')
                # 解析应用名称-页面名称
                appName, pageName = tools.parseAppPage(what)
                if appName:
                    app = App.getApp(appName, True)
                    if not app:
                        log.e(f"未找到应用 {appName}")
            return f"{app.name}-{app.curPage.name}"


        @regCmd(r"#跳转|tz (?P<target>.+)")
        def go(target):
            """
            功能：页面跳转
            指令名: go-g
            中文名: 跳转-tz
            参数: target - 目标页面路径
            示例: 跳转 首页
            """
            return _G._G_.App().go(target)
        
        @regCmd(r"#路径|lj(?P<to>.+) (?P<From>.+)?")
        def PATH(to, From=None):
            """
            功能：获取到目标页面的路径
            参数: to - 目标页面
            示例: 路径 设置
            """
            curApp = _G._G_.App().cur()
            toPage = curApp.getPage(to)
            if not toPage:
                return f"未找到目标页面 {to}"
            fromPage = curApp.getPage(From) if From else curApp.curPage
            pages = curApp.findPath(fromPage, toPage)
            if pages:
                return "\n".join(f"{p.name}" for p in pages)
            return f"e~未找到从{From}到{to}的路径"
        
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
       

        @regCmd(r"#设置坐标修正范围|szzbxz (?P<scope>\d+)")
        def setPosFixScope(scope):
            """
            功能：设置坐标修正范围
            指令名: setPosFixScope-spfs
            中文名: 设置坐标修正范围-szzbxz
            参数: scope - 修正范围
            示例: 设置坐标修正范围 100
            """
            _G._G_.Tools().setPosFixScope(int(scope))


        @regCmd(r"#拓扑图|tpt (?P<appName>\S+)?")
        def appTopology(appName=None):
            """
            功能：打印应用页面拓扑结构图
            """
            from  _App import _App_
            return _App_.printTopology(appName)
        
        @regCmd(r"#显示|xs(?P<uiName>\S+)(?P<enable>\S+)?")
        def sHow(uiName: str, enable=None):
            """
            功能：启用/关闭显示UI组件
            示例: 
            xs 坐标 1
            xs 工具栏 1
            xs 日志 1
            """
            g = _G._G_
            log = g.Log()
            android = g.android
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
                # 首先停止所有打开的应用
                g.App().stopAllApps()
                
                # 获取Android对象
                android = _G._G_.android
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
        @regCmd(r"#编辑|ksbj(?P<name>\S+)")
        def startEdit(name):  
            """
            功能：开始编辑
            检测器有以下参数可以设置：
                match: 匹配规则
                event: 匹配 + 操作 对
                timeout: 超时时间
                interval: 检测间隔
                示例:
                "name": "每日打.+好礼",
                "event": {"点我.取": "click"}
            示例：
            @编辑 每日打.+好礼
            """
            if not name.strip():
                return "e~检查器名称不能为空"
            g = _G._G_
            log = g.Log()
            pos = g.Tools().findTextPos(name.strip('_'))
            if pos is None:
                log.w(f"未找到{name}的位置")
            App = g.App()
            page = App.getPage(name, True, True)
            if not page:
                return f"e~未找到{name}的页面"
            cls._editTarget = page
            if page:
                return f"开始编辑... {name}"

        @regCmd(r"#结束编辑|jsbc(?P<save>[01]*)?")
        def endEdit(save='1'):
            target = cls._editTarget
            if not target:
                return "e~当前没有编辑的对象"
            bSave = g.Tools().toBool(save, True)
            if bSave:
                target.save()
            else:
                if target.type == 'temp':
                    g.App().cur().delPage(target.name)
            cls._editTarget = None
            return f"保存{target.name} 成功"      

        @regCmd(r"#设置属性|szsx (?P<param>\w+)(?P<value>.+)?")
        def setProp(param, value=None):
            """
            设置检查器参数，如interval、timeout,match,event等
            其中event的格式为：{匹配, 操作}
            示例：
            set event {'.*签到', 'click'}
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
            添加数组类型参数里面的某个ITEM，match, event,等
            示例：
            add match 发现 100
            add event 发现 点我.取
            """
            target = cls._editTarget
            if not target:
                return "e~请先开始编辑检查器"
            value = g.Tools().fromStr(value)
            target.addProp(param, value, postfix)

        @regCmd(r"#\-|移除属性|ycsx(?P<param>\S+)(?P<value>\S+)?")
        def removeProp(param, value=None):
            """
            删除数组类型参数里面的某个ITEM，match, event,等
            示例：
            remove match 发现
            remove event 发现
            """ 
            target = cls._editTarget
            if not target:
                return "e~请先开始编辑检查器"
            value = g.Tools().fromStr(value)
            target.removeProp(param, value)

        @regCmd(r"#删除(?P<pageName>\S+)?")
        def dELete(pageName=None):
            if not pageName:                
                if cls._editTarget:
                    pageName = cls._editTarget.name
            if g.Page().delTemplate(pageName):
                return f"删除检查器 {pageName} 成功"

        @regCmd(r"#显示页面|xsym (?P<pageName>\S+)")
        def showPage(pageName):
            """
            功能：显示页面
            示例：
            xsym 发现
            """
            appName, pageName = g.App().parsePageName(pageName)
            pages = g.Page().getTemplates(pageName)
            if not pages:
                return f"{pageName} 不存在"
            return "\n".join(f"{json.dumps(c.config, indent=2, ensure_ascii=False)}" for c in pages)

        @regCmd(r"#匹配|pp(?P<name>\S+)?")
        def maTch(name, enabled=None):
            """
            功能：匹配指定页面
            示例: 
                匹配 每日签到
                匹配 河马剧场.剧场
            """ 
            g = _G._G_
            App = g.App()
            if not name:
                page = App.cur().curPage
            else:
                appName, name = App.parsePageName(name)
                if not name:
                    return f"e~无效页面名: {name}"
                app = App.getApp(appName)
                if not app:
                    return f"e~无效应用: {appName}"
                page = app.getPage(name, False, False)
            if page:
                m = page.Match()
                if m:
                    return f"匹配成功: {name}"
                else:
                    return f"e~匹配失败: {name}"
            else:
                return f"e~无效页面: {name}"
            
            
        @regCmd(r"#执行|zx(?P<content>\S+)")
        def run(content, cmd):
            """
            执行检查器或代码
                @开头：则认为是纯代码
                否则：认为是检查器名称
            示例：
                执行@print("Hello")
                执行看广告
                执行微信.看广告 (跨应用执行)
            """
            if content.startswith('@'):
                # 执行纯代码
                return g.Tools().do(content)
            else:
                # 检查是否含有应用名.检查器名的格式
                App = g.App()
                appName, pageName = App.parsePageName(content)
                if appName:
                    app = App.getApp(appName, True)
                    if not app:
                        return f"e~找不到应用: {appName}"
                    app.start(pageName)
                    return f"执行检查器 {appName}.{pageName} 成功"

        @regCmd(r"#停止|tz(?:(?P<pageName>[^\s]+|_))?(?:\s+(?P<cancel>[01]))?")
        def stop(pageName=None, cancel=None):
            """
            功能：停止检查器
            指令名: stop
            中文名: 停止
            参数: pageName - 要停止的检查器名称，不指定则停止当前应用所有检查器
                   格式可以是 "应用名.检查器名" 表示停止指定应用的检查器
                   如果为 "all" 则停止所有已打开应用的所有检查器
                   使用 _ 表示占位符
                  cancel - 可选，1表示强制取消不执行退出逻辑，0表示正常退出
            示例: 停止 page1 - 停止当前应用的page1检查器
            示例: 停止 微信.page1 - 停止微信应用的page1检查器
            示例: 停止 微信._ - 停止微信应用的所有检查器
            示例: 停止 all - 停止所有已打开应用的所有检查器
            示例: 停止 page1 1 - 强制取消page1检查器，不执行退出逻辑
            示例: 停止 _ 1 - 强制取消当前应用所有检查器，不执行退出逻辑
            示例: 停止 - 停止当前应用所有检查器
            """
            g = _G._G_
            log = g.Log()
            pageName = pageName.strip() if pageName else ''
            cancel = g.Tools().toBool(cancel, False)

            App = g.App()
            # 处理特殊情况: 停止所有应用
            if pageName == '':
                return App.stopAllApps()
            appName, pageName = App.parsePageName(pageName)
            # 获取目标应用
            if appName:
                app = App.getApp(appName, True)
                if not app:
                    log.e(f"未找到应用: {appName}")
                    return False
            # 执行停止操作
            result = app.stop(pageName, cancel)
            if not result:
                log.e(f"停止检查器 {pageName} 失败")
                return False
            return True
        
        @regCmd(r"#检测")
        def deTecT():
            """
            功能：检测当前应用和当前页面
            示例：
            jc
            """
            g = _G._G_
            App = g.App()
            App.detect()
            curApp = App.cur()
            if curApp:
                return f"当前应用: {curApp.name} 当前页面: {curApp.curPage.name}"
            else:
                return "e~检测不到当前应用"

        
        # 新增批量执行相关命令
        @regCmd(r"#批量执行|plzx (?P<pageName>\S+)(?P<data>.+)?")
        def batchRun(pageName: str, data: str):
            """批量执行检查器
            参数: data
            [次数] [间隔秒数]
            次数默认为1，间隔默认为5秒
            """
            g = _G._G_
            log = g.Log()
            try:
                Page = g.Page()
                page = Page.getInst(pageName, create=True)
                if not page:
                    return f'找不到页面：{pageName}'
                policy = {}
                if data:
                    # 将DATA转换成字典
                    data = data.replace(' ', '')
                    datas = data.split(',')
                    for d in datas:
                        if d.isdigit():
                            times = int(d)
                            policy["t"] = times
                        else:
                            interval = int(d)
                            policy["i"] = interval
                from CSchedule import CSchedule_
                CSchedule_.run(page, policy)
                return f'批量执行: {pageName} 成功'
            except Exception as e:
                log.ex(e, '批量执行页面失败')
                return f"批量执行失败: {str(e)}"
        
        @regCmd(r"执行所有")
        def runAll():
            """根据策略文件批量执行检查器
            策略执行 [策略文件路径]
            默认使用config/Policy.json
            """
            from CSchedule import CSchedule_
            CSchedule_.runAll()
            return '执行所有策略完成'

        @regCmd(r"#屏幕信息|pmxx(?P<text>\D+)?(?P<timeout>\d+)?")
        def screenInfo(text=None, timeout=0):
            """功能：添加模拟屏幕文字块用于识别
            参数：
               text - 内容
                    ？ - 显示当前屏幕信息
                    空 - 清除当前屏幕信息
                    其它 - 添加屏幕信息
            示例：
                屏幕信息 登录
                屏幕信息 ?
                屏幕信息 
            """
            g = _G._G_
            tools = g.Tools()
            text = text.strip() if text else ''
            if text == '?':
                # 显示当前屏幕信息
                pass
            elif text == '':
                # 清除当前屏幕信息
                tools.clearScreenInfo()
            else:
                # 添加屏幕信息
                ret = tools.addScreenInfo(text)
                if not ret:
                    return "添加屏幕信息失败"
                timeout = int(timeout)
                if timeout > 0:
                    time.sleep(timeout)
                    tools.delScreenInfo(text)
            return f"当前屏幕信息：{tools.getScreenInfo()}"
            
        @regCmd(r"#删除页面|dp(?P<pageName>\S+)")
        def delPage(pageName: str) -> bool:
            """删除页面"""
            return g.Page().delPage(pageName)

        @regCmd(r"#获取所有页面|gp")
        def pages(self) -> List[str]:
            """获取所有页面名称"""
            return g.Page().getPages()

        @regCmd(r"#获取页面|gp(?P<pageName>\S+)")
        def getPages(self) -> List[str]:
            """获取所有页面名称"""
            return g.Page().getPages()

        @regCmd(r"#获取页面|gp(?P<pageName>\S+)")
        def getPage(self, pageName: str) -> Optional["_Page_"]:
            """获取页面"""
            return g.Page().getPage(pageName)
            