from datetime import datetime
import _Log
import re
from typing import Pattern, List
import threading
import time as time_module
from CClient import client
from CDevice import CDevice
import CTools

# 添加缓存相关的变量
_screenInfoCache = None

# 添加一个全局变量来控制监控状态
_screenMonitorTask = None

class CCmds:

    _android = None
    @classmethod
    def android(cls):
        if cls._android is None:
            from CMain import android
            cls._android = android
        return cls._android
    
    @classmethod
    def OnReload(cls):
        """热更新后重新注册命令"""
        _Log.Log.i("CCmds模块热更新 重新注册命令")
        cls._android = None
        # 使用全局命令重新注册机制
        from _CmdMgr import _CmdMgr
        _CmdMgr.regAllCmds()

    @classmethod
    def registerCommands(cls):
        _Log.Log.i("注册CCmds模块命令...")
        # 导入 regCmd
        from _CmdMgr import regCmd
        
        @regCmd(r"信息")
        def info():
            """获取设备信息"""
            try:
                device = CDevice.instance()
                _Log.Log.i(f"获取设备信息: {device}")
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
            return str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # 注册状态命令
        @regCmd(r"状态")
        def status():
            """查看设备状态"""
            device = CDevice.instance()
            status = "已连接" if device.connected else "未连接"
            return f"设备状态: {status}"
        
        # ... 其他命令注册 ...
        
        # _Log.Log.d(f"CCmds模块命令注册完成")

        @regCmd(r"断开")
        def disconnect():
            """断开连接"""
            # 在函数内部导入 CDevice
            device = CDevice.instance()
            if device:
                device.disconnect()
                return "已断开连接"
            return "设备未连接"

        @regCmd(r"连接", r"(?P<server>\S+)")
        def connect(server):
            """连接到服务器
            用法: 连接 <服务器地址>
            """
            from CDevice import CDevice
            device = CDevice.instance()
            if device:
                return device.connect(server)
            return "设备未初始化"


        @regCmd(r"登录")
        def login():
            """登录设备"""
            device = CDevice.instance()
            if device.login():
                return "登录成功"
            return "登录失败"

        @regCmd(r"登出")
        def logout():
            """登出设备"""
            device = CDevice.instance()
            device.logout()
            return "已登出"

        @regCmd(r"连接状态")
        def isConnect():
            """检查连接状态"""
            device = CDevice.instance()
            if device.connected:
                return f"已连接到服务器，设备ID: {device.deviceID}"
            return "未连接到服务器"

        @regCmd(r"坐标|位置", r"(?P<pattern>.+)")
        def getPos(pattern):
            position = None
            try:
                # Log.i(f"@@@@点击指令: {pattern}")
                x, y = map(int, re.split(r"[,\s]+", pattern.strip()))
                position = (x, y)
            except Exception:
                CTools.CTools.refreshScreenInfos()
                regex = re.compile(pattern)
                position = findPos(regex)
                if not position:
                    _Log.Log.e(f"未找到坐标{pattern}")
            # Log.i(f"坐标:{position}")
            return position

        def inRect(pattern, region):
            position = getPos(pattern)
            if position:
                x, y = position
                left, top, right, bottom = region
                if left > 0 and not (left <= x <= right):
                    return False
                if top > 0 and not (top <= y <= bottom):
                    return False
                return True
                
            return False

        @regCmd(r"移到", r"(?P<param>.+)")
        def move(param):
            position = getPos(param)
            android = cls.android()
            if position and android:
                return android.move(position[0], position[1])
            return "未找到"

        @regCmd(r"点击", r"(?P<param>\S+)(?:\s+(?P<offset>\d+,\d+))?")
        def click(param, offset=None):
            """点击指定位置，支持偏移"""
            _Log.Log.i(f"点击指令: {param} {offset}")
            if not param:
                return False
            android = cls.android()
            if not android:
                _Log.Log.e("点击失败:未找到Android实例")
                return False
            position = getPos(param)   
            if position:
                # 应用偏移量
                x, y = 0, 0
                if offset:
                    offset = offset.split(',')
                    x, y = int(offset[0]), int(offset[1])
                x, y = position[0] + x, position[1] + y
                return android.click(x, y)
            return False

        @regCmd(r"返回")
        def goBack():
            android = cls.android()
            if android:
                return android.goBack()
            return False

        @regCmd(r"主屏幕")
        def goHome():
            android = cls.android()
            if android:
                return android.goHome()
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

        @regCmd(r"启动|打开", r"(?P<pkgName>\S+)")
        def openApp(pkgName):
            """打开应用"""
            try:
                # 使用 Tools 类的 openApp 方法
                return CTools.CTools.openApp(pkgName)
            except Exception as e:
                _Log.Log.ex(e, "打开应用失败")
                return False

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
            try:
                result = CTools.CTools.refreshScreenInfos()
                for item in result:
                    bounds = item["b"].split(",")
                    _Log.Log.i("Text:", item["t"])
                    _Log.Log.i("Bounds:", f"left={bounds[0]}, top={bounds[1]}, right={bounds[2]}, bottom={bounds[3]}")
                return result
            except Exception as e:
                _Log.Log.ex(e, "获取屏幕文本信息失败")
                return "获取信息失败"

        def findPos(regex: Pattern, region: List[int] = None):
            try:
                position = None
                match, item = CTools.CTools.matchScreenText(regex, region)
                if match:
                    position = CTools.CTools.toPos(item)
                    position = (position[0], position[1])
                    _Log.Log.i(f"找到坐标: {position}")
                return position
            except Exception as e:
                _Log.Log.ex(e, "FindUI 指令执行失败")
                return None

        @regCmd(r"查找应用", r"(?P<appName>[\w\s]+)")
        def _toApp(appName: str) -> bool:
            """查找应用"""
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
                _Log.Log.ex(e, "查找应用失败")
                return False

        def clearScreenCache():
            """清除屏幕信息缓存"""
            global _screenInfoCache
            _screenInfoCache = None

        def getScreenText(forceUpdate: bool = False) -> str:
            """获取屏幕文本"""
            try:
                screenInfo = refreshScreenInfos(forceUpdate)
                if not screenInfo:
                    return ""
                return "\n".join(item["t"] for item in screenInfo if item["t"])
            except Exception as e:
                _Log.Log.ex(e, "获取屏幕文本失败")
                return ""

        @regCmd(r"监控", r"(?P<interval>\d+)?")
        def startScreenMonitor(interval=None):
            """开始屏幕监控"""
            global _screenMonitorTask
            _Log.Log.i(f"开始监控@: {interval}")
            if _screenMonitorTask and _screenMonitorTask.is_alive():
                return "e->监控已在运行中"
            try:
                interval = int(interval) if interval else 5
                if interval < 1:
                    return "e->间隔时间不能小于1秒"
                def monitor_task():
                    while _screenMonitorTask:
                        try:
                            client.TakeScreenshot()
                            time_module.sleep(interval)
                        except Exception as e:
                            _Log.Log.ex(e, "监控任务异常")
                            break
                _screenMonitorTask = threading.Thread(target=monitor_task, daemon=True)
                _screenMonitorTask.start()
                return f"开始屏幕监控(间隔{interval}秒)"
            except Exception as e:
                _Log.Log.ex(e, "启动监控失败")
                return f"e->启动监控失败: {str(e)}"

        @regCmd(r"停止监控")
        def stopScreenMonitor():
            """停止屏幕监控"""
            global _screenMonitorTask
            _Log.Log.i(f"停止监控: {_screenMonitorTask}")
            if not _screenMonitorTask or not _screenMonitorTask.is_alive():
                return "监控未运行"
            try:
                _screenMonitorTask = None
                return "已停止屏幕监控"
            except Exception as e:
                _Log.Log.ex(e, "停止监控失败")
                return f"e->停止监控失败: {str(e)}"

        def saveScreenshotToLocal(base64_data, prefix="screenshot"):
            """保存截图到本地"""
            try:
                import base64
                from datetime import datetime
                import os
                image_data = base64.b64decode(base64_data)
                save_dir = "/storage/emulated/0/Download/AutoApi"
                os.makedirs(save_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{prefix}_{timestamp}.jpg"
                filepath = os.path.join(save_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(image_data)
                _Log.Log.i(f"截图已保存到: {filepath}")
                if os.path.exists(filepath):
                    filesize = os.path.getsize(filepath)
                    _Log.Log.i(f"文件大小: {filesize} 字节")
                    return filepath
            except Exception as e:
                _Log.Log.ex(e, "保存截图失败")
                return None

        @regCmd(r"截图")
        def captureScreen():
            """截图指令"""
            try:
                _Log.Log.i("截图指dddd令")
                android = cls.android()
                if android:
                    image = android.takeScreenshot()
                    if not image:
                        return "e->截图失败:未获取到图片数据"
                if not image.startswith("data:image"):
                    image = f"data:image/jpeg;base64,{image}"
                return image
            except Exception as e:
                _Log.Log.ex(e, "截图失败")
                return f"e->截图失败:{str(e)}"


        @regCmd(r"滑动", r"(?P<param>.+)")
        def swipe(param):
            """滑动屏幕"""
            """
            滑动指令支持两种格式:
            1. 坐标格式: "x1,y1 > x2,y2 [duration]"
            例如: "100,200 > 300,400 800"
            
            2. 方向枚举: "方向 [duration]"
            支持的方向:
            CR - 从中心向右滑动
            CL - 从中心向左滑动  
            CU - 从中心向上滑动
            CD - 从中心向下滑动
            ER - 从左边缘向右滑动
            EL - 从右边缘向左滑动
            EU - 从底部向上滑动
            ED - 从顶部向下滑动
            """
            try:
                android = cls.android()
                if not android:
                    return "e->滑动失败:未找到Android实例"
                # 默认持续时间为0.5秒
                default_duration = 500

                # 使用正则表达式解析参数
                match = re.match(r"(?P<start>\d+,\d+)\s*>\s*(?P<end>\d+,\d+)(?:\s+(?P<duration>\d+))?", param)
                if match:
                    # 解析为坐标
                    start = match.group("start")
                    end = match.group("end")
                    duration_str = match.group("duration")
                    
                    # 检查 duration 是否为数字
                    duration = int(duration_str) if duration_str and duration_str.isdigit() else default_duration
                    startX, startY = map(int, start.split(','))
                    endX, endY = map(int, end.split(','))
                    _Log.Log.i(f"滑动指令: 开始位置({startX}, {startY}), 结束位置({endX}, {endY}), 持续时间: {duration} ms")
                    if android.swipe(startX, startY, endX, endY, duration):
                        return "滑动成功"
                    else:
                        return "e->滑动失败"
                else:
                    # 解析为枚举
                    parts = param.split()
                    direction = parts[0]
                    duration = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else default_duration
                    _Log.Log.i(f"滑动指令: 方向({direction}), 持续时间: {duration} ms")
                    if android.sweep(direction, duration):
                        return "滑动成功"
                    else:
                        return "e->滑动失败"
            except Exception as e:
                _Log.Log.ex(e, "滑动失败")
                return f"e->滑动失败: {str(e)}"

        @regCmd('快照')
        def takeScreenshot():
            """截取当前屏幕并发送到服务器"""
            try:
                device = CDevice.instance()
                device.TakeScreenshot()
            except Exception as e:
                _Log.Log.ex(e, '截图失败')
                return f'e->截图异常: {str(e)}'

        @regCmd(r"当前应用")
        def curApp():
            """获取当前正在运行的应用信息"""
            try:
                return CTools.CTools.getCurrentApp()
            except Exception as e:
                _Log.Log.ex(e, "获取当前应用失败")
                return None
