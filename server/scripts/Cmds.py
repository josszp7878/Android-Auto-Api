from datetime import datetime
from logger import Log, requireAndroid
from CDevice import CDevice
from tools import Tools, tools
from CmdMgr import regCmd
import re
from typing import Pattern, List
from task import Task
from checkers import Check
from CFileServer import fileServer
import threading
import time
from client import client

# 缓存 Android 实例
androidServices = Log.android

# 添加缓存相关的变量
_screenInfoCache = None

# 添加一个全局变量来控制监控状态
_screenMonitorTask = None

@regCmd(r"信息")
def info():
    """获取设备信息"""
    return {
        "device": "Android Device",
        "version": "1.0.0",
        "timestamp": str(datetime.now()),
    }

@regCmd(r"时间")
def time():
    """获取当前时间"""
    return str(datetime.now())

@regCmd(r"状态")
def status():
    """查看设备状态"""
    device = CDevice.instance()
    status = "已连接" if device.connected else "未连接"
    return f"设备状态: {status}"

@regCmd(r"断开")
def disconnect():
    """断开连接"""
    device = CDevice.instance()
    device.disconnect()
    return "已断开连接"

@regCmd(r"连接(?:\s+(?P<server_url>\S+))?")
def connect(server_url=None):
    """连接服务器"""
    device = CDevice.instance()
    if device.connect(server_url):
        return "连接成功"
    return "连接失败"

@regCmd(r"日志", r"(?P<level>[iwe])\s+(?P<content>.+)")
def log(level, content):
    if level not in ["i", "w", "e"]:
        return "日志级别必须是 i/w/e 之一"
    if level == "i":
        Log.i(content)
    elif level == "w":
        Log.w(content)
    else:
        Log.e(content)

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

@regCmd(r"坐标", r"(?P<pattern>.+)")
@requireAndroid
def getPos(pattern):
    position = None
    try:
        Log.i(f"@@@@点击指令: {pattern}")
        x, y = map(int, re.split(r"[,\s]+", pattern.strip()))
        position = (x, y)
    except Exception as e:
        tools.refreshScreenInfos()
        regex = re.compile(pattern)
        position = tools.findPos(regex)
    Log.i(f"坐标:{position}")
    return position

@regCmd(r"移到", r"(?P<param>.+)")
@requireAndroid
def move(param):
    position = getPos(param)
    if position:
        return androidServices.move(position[0], position[1])
    return "未找到"

@regCmd(r"点击", r"(?P<param>.+)")
@requireAndroid
def click(param):
    position = getPos(param)
    if position:
        return androidServices.click(position[0], position[1])
    return "未找到"

@regCmd(r"返回")
@requireAndroid
def goBack():
    return androidServices.goBack()

@regCmd(r"主屏幕")
@requireAndroid
def goHome():
    return androidServices.goHome()

@regCmd(r"检查安装\s+(?P<pkgName>\S+)")
@requireAndroid
def isInstalled(pkgName):
    return androidServices.isAppInstalled(pkgName)

@regCmd(r"安装\s+(?P<pkgName>\S+)")
@requireAndroid
def install(pkgName):
    return androidServices.installApp(pkgName)

@regCmd(r"卸载\s+(?P<pkgName>\S+)")
@requireAndroid
def uninstall(pkgName):
    return androidServices.uninstallApp(pkgName)

@regCmd(r"启动|打开", r"(?P<pkgName>\S+)")
@requireAndroid
def startApp(pkgName):
    return androidServices.openApp(pkgName)

@regCmd(r"停止", r"(?P<pkgName>\S+)")
@requireAndroid
def stopApp(pkgName):
    return androidServices.closeApp(pkgName)

@regCmd(r"切换应用|任务列表|最近任务")
@requireAndroid
def switchApp():
    """显示最近任务列表"""
    return androidServices.showRecentApps()

@regCmd(r"截屏")
@requireAndroid
def getScreen():
    try:
        result = Tools().refreshScreenInfos()
        for item in result:
            bounds = item["b"].split(",")
            Log.i("Text:", item["t"])
            Log.i("Bounds:", f"left={bounds[0]}, top={bounds[1]}, right={bounds[2]}, bottom={bounds[3]}")
        return result
    except Exception as e:
        Log.ex(e, "获取屏幕文本信息失败")
        return "获取信息失败"

def findPos(regex: Pattern, region: List[int] = None):
    try:
        position = None
        match, item = Tools().matchScreenText(regex, region)
        if match:
            position = Tools().toPos(item)
            Log.i(f"找到坐标: {position}")
        return position
    except Exception as e:
        Log.ex(e, "FindUI 指令执行失败")
        return None

@regCmd(r"查找应用", r"(?P<appName>[\w\s]+)")
@requireAndroid
def _toApp(appName: str) -> bool:
    """查找应用"""
    try:
        texts = androidServices.getScreenText()
        if not texts:
            return False
        for text in texts:
            if appName in text:
                return True
        return False
    except Exception as e:
        Log.ex(e, "查找应用失败")
        return False

@regCmd(r"打开应用", r"(?P<appName>[\w\s]+)")
@requireAndroid
def openApp(appName: str) -> bool:
    """打开指定应用"""
    try:
        CDevice.currentAppName = appName
        if CDevice.currentAppName == appName:
            return True
        result = click(appName)
        if result is None:
            if _toApp(appName):
                click(appName)
            else:
                return False
        return True
    except Exception as e:
        Log.ex(e, "打开应用失败")
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
        Log.ex(e, "获取屏幕文本失败")
        return ""

@regCmd(r"开始监控", r"(?P<interval>\d+)?")
@requireAndroid
def startScreenMonitor(interval=None):
    """开始屏幕监控"""
    global _screenMonitorTask
    Log.i(f"开始监控@: {interval}")
    if _screenMonitorTask and _screenMonitorTask.is_alive():
        return "e##监控已在运行中"
    try:
        interval = int(interval) if interval else 5
        if interval < 1:
            return "e##间隔时间不能小于1秒"
        def monitor_task():
            while _screenMonitorTask:
                try:
                    image = androidServices.takeScreenshot()
                    Log.i("获取截图:")
                    if image:
                        client.emit("C2S_UpdateScreenshot", {"device_id": client.deviceID, "screenshot": image})
                    time.sleep(interval)
                except Exception as e:
                    Log.ex(e, "监控任务异常")
                    break
        _screenMonitorTask = threading.Thread(target=monitor_task, daemon=True)
        _screenMonitorTask.start()
        return f"开始屏幕监控(间隔{interval}秒)"
    except Exception as e:
        Log.ex(e, "启动监控失败")
        return f"e##启动监控失败: {str(e)}"

@regCmd(r"停止监控")
def stopScreenMonitor():
    """停止屏幕监控"""
    global _screenMonitorTask
    Log.i(f"停止监控: {_screenMonitorTask}")
    if not _screenMonitorTask or not _screenMonitorTask.is_alive():
        return "监控未运行"
    try:
        _screenMonitorTask = None
        return "已停止屏幕监控"
    except Exception as e:
        Log.ex(e, "停止监控失败")
        return f"e##停止监控失败: {str(e)}"

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
        Log.i(f"截图已保存到: {filepath}")
        if os.path.exists(filepath):
            filesize = os.path.getsize(filepath)
            Log.i(f"文件大小: {filesize} 字节")
            return filepath
    except Exception as e:
        Log.ex(e, "保存截图失败")
        return None

@regCmd(r"截图")
@requireAndroid
def captureScreen():
    """截图指令"""
    try:
        Log.i("截图指dddd令")
        image = androidServices.takeScreenshot()
        if not image:
            return "e##截图失败:未获取到图片数据"
        if not image.startswith("data:image"):
            image = f"data:image/jpeg;base64,{image}"
        return image
    except Exception as e:
        Log.ex(e, "截图失败")
        return f"e##截图失败:{str(e)}"

@regCmd(r"加载", r"(?P<module_name>\w+)")
def reload(module_name):
    print(f"热加载模块: {module_name}")
    try:
        if fileServer.reloadModule(module_name):
            return f"模块 {module_name} 重新加载成功ee"
        return f"模块 {module_name} 重新加载失败"
    except Exception as e:
        Log.ex(e, f"重新加载模块失败: {module_name}")
        return f"重新加载失败: {str(e)}"

def OnReload():
    Log.w("Cmds模块热更新 OnReload")
    from client import client

def OnPreload():
    Log.w("Cmds模块热更新 onPreload")

@regCmd(r"aa")
@requireAndroid
def aa():
    Log.i("dddaa")