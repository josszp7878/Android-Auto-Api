from datetime import datetime
from logger import Log, requireAndroid
from CDevice import CDevice
from tools import Tools
from CmdMgr import regCmd
import re
from typing import Pattern
# 缓存 Android 实例
androidServices = Log().Android

# 添加缓存相关的变量
_screenInfoCache = None


@regCmd(r'信息')
def info():
    """获取设备信息"""
    return {
        'device': 'Android Device',
        'version': '1.0.0',
        'timestamp': str(datetime.now())
    }


@regCmd(r'时间')
def time():
    """获取当前时间"""
    return str(datetime.now())


@regCmd(r'状态')
def status():
    """查看设备状态"""
    device = CDevice.instance()
    status = "已连接" if device.connected else "未连接"
    return f'设备状态: {status}'


@regCmd(r'断开')
def disconnect():
    """断开连接"""
    device = CDevice.instance()
    device.disconnect()
    return "已断开连接"


@regCmd(r'连接(?:\s+(?P<server_url>\S+))?')
def connect(server_url=None):
    """连接服务器"""
    device = CDevice.instance()
    if device.connect(server_url):
        return "连接成功"
    return "连接失败"


@regCmd(r'日志', r'(?P<level>[iwe])\s+(?P<content>.+)')
def log(level, content):
    if level not in ['i', 'w', 'e']:
        return "日志级别必须是 i/w/e 之一"
    if level == 'i':
        Log.i(content)
    elif level == 'w':
        Log.w(content)
    else:
        Log.e(content)


@regCmd(r'登录')
def login():
    """登录设备"""
    device = CDevice.instance()
    if device.login():
        return "登录成功"
    return "登录失败"


@regCmd(r'登出')
def logout():
    """登出设备"""
    device = CDevice.instance()
    device.logout()
    return "已登出"


@regCmd(r'连接状态')
def isConnect():
    """检查连接状态"""
    device = CDevice.instance()
    if device.connected:
        return f"已连接到服务器，设备ID: {device.deviceID}"
    return "未连接到服务器"

@regCmd(r'坐标', r'(?P<pattern>.+)')
@requireAndroid
def getPos(pattern):
    position = None
    # 尝试解析参数为坐标
    try:
        # 假设坐标格式为 "x, y" 或 "x y"
        Log.i(f"@@@@点击指令: {pattern}")
        x, y = map(int, re.split(r'[,\s]+', pattern.strip()))
        position = (x, y)
    except Exception as e:
        refreshScreenInfos()
        regex = re.compile(pattern)        
        position = findPos(regex)
    Log.i(f"坐标:{position}")
    return position

@regCmd(r'移到', r'(?P<param>.+)')
@requireAndroid
def move(param):
    position = getPos(param)
    if position:
        return androidServices.move(position[0], position[1])
    return "未找到"


@regCmd(r'点击', r'(?P<param>.+)')
@requireAndroid
def click(param):
    position = getPos(param)
    if position:
        return androidServices.click(position[0], position[1])
    return "未找到"


@regCmd(r'返回')
@requireAndroid
def goBack():
    return androidServices.goBack()

@regCmd(r'主屏幕')
@requireAndroid
def goHome():
    return androidServices.goHome()


@regCmd(r'检查安装\s+(?P<pkgName>\S+)')
@requireAndroid
def isInstalled(pkgName):
    return androidServices.isAppInstalled(pkgName)


@regCmd(r'安装\s+(?P<pkgName>\S+)')
@requireAndroid
def install(pkgName):
    return androidServices.installApp(pkgName)


@regCmd(r'卸载\s+(?P<pkgName>\S+)')
@requireAndroid
def uninstall(pkgName):
    return androidServices.uninstallApp(pkgName)


@regCmd(r'启动', r'(?P<pkgName>\S+)')
@requireAndroid
def startApp(pkgName):
    return androidServices.openApp(pkgName)


@regCmd(r'停止', r'(?P<pkgName>\S+)')
@requireAndroid
def stopApp(pkgName):
    return androidServices.closeApp(pkgName)


def saveScreenshotToLocal(base64_data, prefix="screenshot"):
    """保存截图到本地
    Args:
        base64_data: base64格式的图片数据
        prefix: 文件名前缀
    Returns:
        str: 保存的文件路径，失败返回 None
    """
    try:
        import base64
        from datetime import datetime
        import os

        image_data = base64.b64decode(base64_data)
        
        # 使用下载目录
        save_dir = '/storage/emulated/0/Download/AutoApi'
        os.makedirs(save_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{prefix}_{timestamp}.jpg'
        filepath = os.path.join(save_dir, filename)
        
        # 保存文件
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        Log.i(f"截图已保存到: {filepath}")
        
        # 检查文件大小
        if os.path.exists(filepath):
            filesize = os.path.getsize(filepath)
            Log.i(f"文件大小: {filesize} 字节")
            return filepath
            
    except Exception as e:
        Log.ex(e, "保存截图失败")
        return None


@regCmd(r'截图')
@requireAndroid
def captureScreen():
    """截图指令"""
    try:
        image = androidServices.takeScreenshot()
        if not image:
            return "e##截图失败:未获取到图片数据"
        # 可选：同时保存到本地
        # saveScreenshotToLocal(image)
        if not image.startswith('data:image'):
            image = f"data:image/jpeg;base64,{image}"
        return image
    except Exception as e:
        Log.ex(e, "截图失败")
        return f"e##截图失败:{str(e)}"


@regCmd(r'加载', r'(?P<module_name>\w+)')
def reload(module_name):
    """热加载指定模块
    用法: reload <module_name>
    示例: 
        reload Cmds  # 重新加载命令模块
        reload CmdMgr  # 重新加载命令管理器
    """
    print(f"热加载模块: {module_name}")
    try:
        if Tools().reloadModule(module_name):
            return f"模块 {module_name} 重新加载成功ee"
        return f"模块 {module_name} 重新加载失败"
    except Exception as e:
        Log.ex(e, f"重新加载模块失败: {module_name}")
        return f"重新加载失败: {str(e)}"


def OnReload():
    Log.w("Cmds模块热更新 OnReload")

def OnPreload():
    Log.w("Cmds模块热更新 onPreload")


@regCmd(r'切换应用|任务列表|最近任务')
@requireAndroid
def switchApp():
    """显示最近任务列表
    用法: 切换应用/任务列表/最近任务
    """
    return androidServices.showRecentApps()

def screenInfos():
    return _screenInfoCache

def refreshScreenInfos() -> list:
    """获取并解析屏幕信息,支持缓存
    Args:
        forceUpdate: 是否强制更新缓存
    Returns:
        list: 屏幕文本信息列表
    """
    global _screenInfoCache
    
    try:
        info = androidServices.getScreenInfo()
        size = info.size()
        result = []
        
        for i in range(size):
            item = info.get(i)
            result.append({
                't': item.get('t'),
                'b': item.get('b')
            })
            
        # 更新缓存
        _screenInfoCache = result
        return result
        
    except Exception as e:
        Log.ex(e, "获取屏幕信息失败")
        return []


@regCmd(r'屏幕文本信息')
@requireAndroid
def getScreen():
    try:
        # 使用封装的方法获取屏幕信息
        result = refreshScreenInfos()
        
        # 直接使用返回的列表
        for item in result:
            bounds = item['b'].split(',')
            Log.i("Text:", item['t'])
            Log.i("Bounds:", f"left={bounds[0]}, top={bounds[1]}, right={bounds[2]}, bottom={bounds[3]}")
        
        return result
    except Exception as e:
        Log.ex(e, "获取屏幕文本信息失败")
        return "获取信息失败"
def matchScreenText(regex: Pattern, region: list[int] = None):
    """查找匹配文本的位置
    Args:
        pattern: 匹配模式(正则表达式)
        region: 搜索区域[left, top, right, bottom], None表示全屏搜索
        forceUpdate: 是否强制更新缓存
    Returns:
        tuple: (x, y) 匹配文本的中心坐标,未找到返回None
    """
    try:
        # 使用缓存的屏幕信息
        screenInfo = screenInfos()        
        # 遍历屏幕信息，查找匹配的文本
        for item in screenInfo:
            # 解析当前文本的边界
            bounds = [int(x) for x in item['b'].split(',')]
            
            # 如果指定了区域,检查文本是否在区域内
            if region is not None:
                # 检查是否有重叠
                if (bounds[2] < region[0] or  # 文本在区域左边
                    bounds[0] > region[2] or  # 文本在区域右边
                    bounds[3] < region[1] or  # 文本在区域上边
                    bounds[1] > region[3]):   # 文本在区域下边
                    continue

            match = regex.search(item['t'])
            if match:
                return match, item
        return None, None
        
    except Exception as e:
        Log.ex(e, "FindUI 指令执行失败")
        return None, None    
           
def findPos(regex: Pattern, region: list[int] = None):
    try:
        position = None
        # 使用缓存的屏幕信息
        match, item = matchScreenText(regex, region)
        if match:
            Log.i(f"找到坐标: {item['b']}")
            bounds = [int(x) for x in item['b'].split(',')]
            centerX = (bounds[0] + bounds[2]) // 2
            centerY = (bounds[1] + bounds[3]) // 2
            position = (centerX, centerY)
        return position
    except Exception as e:
        Log.ex(e, "FindUI 指令执行失败")
        return None


@regCmd(r'查找应用', r'(?P<appName>[\w\s]+)')
@requireAndroid
def _toApp(appName: str) -> bool:
    """查找应用
    用法: findApp <应用名>
    示例: findApp 微信
    """
    try:
        # 获取屏幕文本
        texts = androidServices.getScreenText()
        if not texts:
            return False
            
        # 检查应用名是否在屏幕文本中
        for text in texts:
            if appName in text:
                return True
                
        return False
    except Exception as e:
        Log.ex(e, "查找应用失败")
        return False

@regCmd(r'打开应用', r'(?P<appName>[\w\s]+)')
@requireAndroid
def openApp(appName: str) -> bool:
    """打开指定应用
    用法: openApp <应用名>
    示例: openApp 微信
    """
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
    """获取屏幕文本
    Args:
        forceUpdate: 是否强制更新缓存
    Returns:
        str: 所有文本内容
    """
    try:
        # 使用缓存的屏幕信息
        screenInfo = refreshScreenInfos(forceUpdate)
        if not screenInfo:
            return ""
            
        # 提取所有文本
        return "\n".join(item['t'] for item in screenInfo if item['t'])
        
    except Exception as e:
        Log.ex(e, "获取屏幕文本失败")
        return ""
