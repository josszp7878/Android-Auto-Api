import re
from _G import TaskState
import _G
import json
from datetime import datetime

class CCmds_:

    @classmethod
    def android(cls):
        return _G._G_.android
    
    _editTarget = None

    @classmethod
    def registerCommands(cls):
        # 导入 regCmd
        from _CmdMgr import regCmd

        @regCmd(r"#>>|log (?P<content>.+)?")
        def log(content):
            _G._G_.Log().log(content)

        @regCmd('#保存日志|bcrz')
        def saveLog():
            """功能：强制保存当前客户端日志缓存到文件
            指令名：saveLog
            中文名：保存日志
            参数：无
            示例：保存日志
            """
            try:
                import _Log
                log = _G._G_.Log()
                # 强制保存日志缓存
                log._save(True)
                return '客户端日志已保存到文件'
            except Exception as e:
                _Log._Log_.ex(e, '保存日志失败')
                return f'e~保存日志失败: {str(e)}'

        @regCmd(r"#位置|wz(?P<text>.+)?")
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
                g.android.move(pos[0], pos[1])
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
            ret = _G._G_.CDevice().open(appName)
            if not ret:
                return f"打开应用 {appName} 失败"
            return f"成功打开应用 {appName}, ret:{ret}"

        @regCmd(r"#关闭|gb (?P<appName>\S+)?")
        def closeApp(appName=None):
            """
            功能：关闭应用
            指令名: closeApp-cA
            中文名: 关闭-gb
            参数: appName - 应用名称(可选)，不提供则关闭当前应用
            示例: 关闭 [微信]
            """
            return _G._G_.CDevice().closeApp(appName)
            
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

        @regCmd(r"#当前|dq(?P<what>\S*)?")
        def current(what=None):
            """
            功能：获取当前信息，
            参数: 
                what: 
                    pos|位置:  坐标
                    空： 支持包括当前应用、页面、坐标，任务等
            """
            g = _G._G_
            log = g.Log()
            if what and re.match(r'^(pos|位置)$', what, re.IGNORECASE):
                return log.i('todo: 获取坐标')
            else:
                return g.CDevice().currentInfo()


        @regCmd(r"#跳转|tz(?P<target>.+)")
        def go(target):
            """
            功能：页面跳转
            指令名: go-g
            中文名: 跳转-tz
            参数: target - 目标页面路径
            示例: 跳转 首页
            """
            CApp = _G._G_.CApp()
            return CApp.go(target)
        
        @regCmd(r"#路径|lj(?P<to>.+) (?P<From>.+)?")
        def PATH(to, From=None):
            """
            功能：获取到目标页面的路径
            参数: to - 目标页面
            示例: 路径 设置
            """
            curApp = _G._G_.CDevice().currentApp
            toPage = curApp.getPage(to)
            if not toPage:
                return f"未找到目标页面 {to}"
            fromPage = curApp.getPage(From) if From else curApp.curPage
            path = curApp.findPath(fromPage, toPage)
            if path:
                return "\n".join(f"{pageName}" for pageName in path)
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

        

        @regCmd(r"#查找|cz (?P<text>\S+)(?P<dir>[LlRrUuDd]+)?")
        def findText(text, dir=None):
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
            g = _G._G_
            pos = g.Tools().findTextPos(text, dir)            
            if pos:
                # 安全地访问坐标
                if isinstance(pos, tuple) and len(pos) >= 2:
                    return f"找到文字位置: {pos[0]},{pos[1]}"
                else:
                    # 处理非元组返回值
                    return f"e~找到文字，但返回格式异常: {pos}"
            return "e~未找到匹配文字"
       

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
            
        @regCmd(r"#连接|lj")
        def connect():
            """
            功能：连接设备
            指令名: connect
            中文名: 连接-连接
            """
            g = _G._G_  
            log = g.Log()
            log.i("连接设备")
            # 获取当前设备
            CDevice = g.CDevice()
            ret = CDevice.connect()
            if ret:
                return "连接成功"
            else:
                return "连接失败"
        
        @regCmd(r"#断开|dk")
        def disconnect():
            """
            功能：断开设备
            指令名: disconnect
            中文名: 断开-断开
            """ 
            g = _G._G_  
            log = g.Log()
            log.i("断开设备")
            # 获取当前设备
            CDevice = g.CDevice()
            ret = CDevice.disconnect()
            if ret:
                return "断开成功"
            else:
                return "断开失败"
            
        @regCmd(r"#登录|dl")
        def login():
            """
            功能：登录
            指令名: login
            中文名: 登录
            参数: 无
            """
            g = _G._G_
            log = g.Log()
            log.i("登录")
            # 获取当前设备
            CDevice = g.CDevice()
            ret = CDevice.login()
            if ret:
                return "登录成功"
            else:
                return "登录失败"
            
        @regCmd(r"#退出登录|tc")
        def logout():
            """
            功能：退出登录
            指令名: logout
            中文名: 退出登录
            """
            g = _G._G_
            log = g.Log()
            log.i("退出登录")
            # 获取当前设备
            CDevice = g.CDevice()
            ret = CDevice.logout()
            if ret:
                return "退出登录成功"
            else:
                return "退出登录失败"

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
            _G._G_.Tools().setUIHeadHeight(int(scope))


        @regCmd(r"#拓扑图|tpt (?P<appName>\S+)?")
        def appTopology(appName=None):
            """
            功能：打印应用页面拓扑结构图
            """
            from  _App import _App_
            return _App_.printTopology(appName)
        
        @regCmd(r"#显示|xs(?P<uiName>\S+)(?P<enable>\S+)?")
        def show(uiName: str, enable=None):
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
            # log.i(f"显示{uiName}: {enable}")
            showConfig = [
                ['坐标', 'zb', 'pos', 'showClick'],
                ['工具栏', 'gjl', 'toolbar', 'showToolbar'],
                ['日志', 'rz', 'log', 'showLog'],
                ['界面', 'ui', 'showUI'],
                ['光标', 'gb', 'cursor', 'showCursor']
            ]
            # 在配置中查找匹配的UI组件
            findConfig = next((component for component in showConfig if uiName in component[:-1]), None)    
            if findConfig:
                method_name = findConfig[-1]
                if android:
                    if hasattr(android, method_name):
                        method = getattr(android, method_name)
                        method(enable)
                        return
                else:
                    log.i(f"set {uiName} {enable}")

        @regCmd(r"#退出|tc")
        def eXit():
            """退出应用
            """
            g = _G._G_
            log = g.Log()
            try:
                # 首先停止所有打开的应用
                # g.App().stopAllApps()
                
                # 获取Android对象
                android = _G._G_.android
                if android:
                    # 调用退出应用的方法
                    android.exitApp()
                    return "应用正在退出..."
                else:
                    g.CClient().running = False
                    return "无法获取Android对象，退出失败"
            except Exception as e:
                log.ex(e, "退出应用失败")
                return f"退出应用失败: {str(e)}"

        # === 页面相关命令 ===
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
                return "e~页面名称不能为空"
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
                if target.hasAttr(_G.TEMP):
                    g.App().last().delPage(target.name)
            cls._editTarget = None
            return f"保存{target.name} 成功"      

        @regCmd(r"#设置属性|szsx (?P<param>\w+)(?P<value>.+)?")
        def setProp(param, value=None):
            """
            设置页面参数，如interval、timeout,match,event等
            其中event的格式为：{匹配, 操作}
            示例：
            set event {'.*签到', 'click'}
            set match {'.*签到'}
            set timeout {10}
            """
            target = cls._editTarget
            if not target:
                return "e~请先开始编辑页面"
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
                return "e~请先开始编辑页面"
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
                return "e~请先开始编辑页面"
            value = g.Tools().fromStr(value)
            target.removeProp(param, value)

        @regCmd(r"#删除(?P<pageName>\S+)?")
        def dELete(pageName=None):
            g = _G._G_
            if not pageName:                
                if cls._editTarget:
                    pageName = cls._editTarget.name
            if g.CApp().delPage(pageName):
                return f"删除页面 {pageName} 成功"

        @regCmd(r"#显示页面|xsym (?P<pageName>\S+)")
        def showPage(pageName):
            """
            功能：显示页面
            示例：
            xsym 发现
            """
            g = _G._G_
            appName, pageName = g.CApp().parseName(pageName)
            pages = g.CApp().getTemplates(pageName)
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
            App = g.CApp()
            if not name:
                page = g.CDevice().currentApp.curPage
            else:
                appName, name = App.parseName(name)
                if not name:
                    return f"e~无效页面名: {name}"
                app = App.getTemplate(appName)
                if not app:
                    return f"e~无效应用: {appName}"
                page = app.getPage(name, False, False)
            if page:
                m = page.match()
                if m:
                    return f"匹配成功: {name}"
                else:
                    return f"e~匹配失败: {name}"
            else:
                return f"e~无效页面: {name}"
            
        @regCmd(r"#启动任务|qd(?P<key>\S+)")
        def startTask(key:str)->TaskState:
            """
            功能：启动任务
            参数：
                taskName - 任务名称
            示例：
            启动任务 看广告
            """
            g = _G._G_
            log = g.Log()
            if not key:
                log.e_("任务名称不能为空")
                return None
            task = g.CDevice().getTask(key)
            if not task:
                log.e_(f"任务不存在: {key}")
                return None
            return task.begin()
        
        @regCmd(r"#更新任务|gx(?P<taskID>\d+)")
        def updateTask(taskID):
            """
            功能：更新任务
            示例：
            更新任务 看广告 10
            """
            g = _G._G_
            log = g.Log()
            task = g.CDevice().getTask(taskID)
            if not task:
                log.e_(f"任务{taskID}不存在: ")
                return None
            return task._updateProgress()

        @regCmd(r"#停止任务|tz(?P<task>\S+)")
        def stopTask(task:str)->TaskState:
            """
            功能：停止任务
            参数：
                task - 任务名称
            示例：
            停止任务 看广告
            """
            g = _G._G_
            log = g.Log()
            task = g.CDevice().getTask(task)
            if not task:
                log.e_(f"任务不存在: {task}")
                return None
            return task.stop()  
            
        @regCmd(r"#执行|zx(?P<content>\S+)")
        def run(content:str):
            """
            执行页面或代码
                @代码：则认为是纯代码
                !任务名：则认为是任务名称
                否则：认为是页面名称
            示例：
                执行@print("Hello")
                执行看广告
                执行微信.看广告 (跨应用执行)
                执行!看广告 (执行任务)
            """
            if content.startswith('@'):
                # 执行纯代码
                return g.Tools().do(content)
            elif content.startswith('!'):
                task = g.App().getTask(content[1:])
                if not task:
                    return f"e~任务不存在: {content[1:]}"
                return task.begin()
            else:
                return g.App().go(content)
               

        @regCmd(r"#停止|tz(?:(?P<content>[^\s]+))?")
        def stop(content=None):
            """
            功能：停止页面
            指令名: stop
            中文名: 停止
            参数:
                !任务名: 停止任务
                pageName - 要停止的页面名称，不指定则停止当前应用所有页面
                   格式可以是 "应用名.页面名" 表示停止指定应用的页面
                    空：停止当前所有应用的页面
                    app-:停止应用app的所有页面
                    -page:停止当前应用的page页面
                    app-page:停止应用app的page页面
            示例：
                停止 河马剧场.剧场
                停止 河马剧场
                停止 app-河马剧场
                停止 -河马剧场
                停止 app-page-河马剧场
                停止 -page-河马剧场
                停止 !看广告
            """
            g = _G._G_
            # log = g.Log()
            content = content.strip() if content else ''
            if content.startswith('!'):
                taskName = content[1:]
                task = g.App().getTask(taskName)
                if not task:
                    return f"e~任务不存在: {taskName}"
                task.stop()
            else:
                g.App().stopAllTasks()
                return f"停止所有任务成功"
                

        @regCmd(r"#屏幕信息|pmxx|si(?P<text>.+)")
        def screenInfo(text=None):
            """功能：添加模拟屏幕文字块用于识别
            参数：
               text - 内容
                    ？ - 显示当前屏幕信息
                    空 - 清除当前屏幕信息
                    其它 - 添加屏幕信息（可包含超时参数，如：签到得1200金币 10）
                    负数超时：添加的文本在被查找到N次后自动清除（如：签到得1200金币 -3 表示被查找到3次后自动清除）
            示例：
                屏幕信息 登录
                屏幕信息 ?
                屏幕信息 
                屏幕信息 签到得1200金币 10
                屏幕信息 签到得1200金币 -3
            """
            g = _G._G_
            tools = g.Tools()
            text = text.strip() if text else ''
            
            # 解析参数
            timeout = -1  # 默认使用负数表示无限次查找
            if text and text.split()[-1].replace('-', '').isdigit():
                # 提取文本和超时值
                parts = text.rsplit(maxsplit=1)
                text = parts[0] if len(parts) > 1 else ''
                timeout = int(parts[-1])
            
            # 处理特殊命令
            if text == '?':
                # 显示当前屏幕信息
                return f"当前屏幕信息：{tools.getScreenInfo()}"
            elif text == '':
                # 清除当前屏幕信息
                tools.clearScreenInfo()
                return "屏幕信息已清除"
            else:
                # 添加屏幕信息，timeout参数直接传递给addScreenInfo处理
                ret = tools.addScreenInfo(text, timeout)
                if not ret:
                    return "添加屏幕信息失败"
                return f"当前屏幕信息：{tools.getScreenInfo()}"
            
        
        @regCmd(r"#状态|zt (?P<taskName>\S+)?")
        def state(taskName=None):
            """
            功能：获取任务状态
            参数: taskName - 应用名-任务名格式
            示例: 状态 抖音-广告观看
            """
            g = _G._G_
            # 显示客户端的连接状态
            device = g.CDevice()
            state_value = device.state()
            # 确保返回字符串
            return str(state_value)

        @regCmd(r"#获取日志|getLogs(?P<date>\S+)?")
        def getLogs(date=None):
            """获取客户端本地日志
            
            Args:
                date: 日期，支持格式: YYYYMMDD, YYYY-MM-DD 等，可选，默认为今天
                
            Returns:
                dict: 包含日志数据的响应
            """
            try:
                from _Log import _Log_
                
                # 获取客户端本地日志
                logs = _Log_.gets(date)
                logData = [logItem.toSheetData() for logItem in logs]
                
                return {
                    'success': True,
                    'data': logData,
                    'date': date,
                    'count': len(logData)
                }
                
            except Exception as e:
                _G._G_.Log().ex(e, f'获取客户端日志失败: {date}')
                return {
                    'success': False,
                    'message': str(e)
                }

        @regCmd(r"#命名|mm (?P<newName>.+)")
        def name(newName):
            """
            功能：命名设备（通过服务端统一处理）
            指令名：name
            中文名：命名
            参数：
                newName - 新的设备名称
            示例：命名 测试设备
            示例：name 我的手机
            """
            g = _G._G_
            log = g.Log()
            
            if not newName:
                log.e_("新名称不能为空")
                return "e~新名称不能为空"
            
            newName = newName.strip()
            if not newName:
                log.e_("新名称不能为空")
                return "e~新名称不能为空"
            
            try:
                # 获取当前设备信息
                device = g.CDevice()
                if not device:
                    log.e_("设备连接未建立")
                    return "e~设备连接未建立"
                
                deviceId = device.name
                if not deviceId:
                    log.e_("设备ID无效")
                    return "e~设备ID无效"
                
                # 通过服务端统一处理属性更新
                try:
                    result = g.emitRet('C2S_SetProp', {
                        'type': 'devices',
                        'target': deviceId,
                        'params': {'name': newName}
                    })
                    
                    if result and result.get('success'):
                        log.i_(f"设备名称已修改为: {newName}")
                        return f"c~设备名称已修改为: {newName}"
                    else:
                        error_msg = result.get('message', '未知错误') if result else '服务器无响应'
                        log.e_(f"修改设备名称失败: {error_msg}")
                        return f"e~修改设备名称失败: {error_msg}"
                        
                except Exception as e:
                    log.ex(e, f"与服务器通信失败: {newName}")
                    return f"e~与服务器通信失败: {str(e)}"
                
            except Exception as e:
                log.ex(e, f"修改设备名称失败: {newName}")
                return f"e~修改设备名称失败: {str(e)}"   