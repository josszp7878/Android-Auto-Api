from datetime import datetime
from logger import Log, requireAndroid
from CDevice import CDevice
from tools import Tools
from CmdMgr import regCmd
import re
import json

# 缓存 Android 实例
androidServices = Log().Android


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


@regCmd(r'点击', r'(?P<x>\d+)\D+(?P<y>\d+)')
@requireAndroid
def click(x, y):
    x, y = int(x), int(y)
    result = androidServices.clickPosition(x, y)
    return f"点击位置 ({x}, {y}) 结果: {result}"


@regCmd(r'返回')
@requireAndroid
def goBack():
    return androidServices.goBack()


@regCmd(r'获取屏幕文本')
@requireAndroid
def screenText():
    try:
        # 调用 Kotlin 方法获取屏幕文本和位置信息
        textInfos = PythonServices.getScreenTextWithInfo()
        
        # 将结果转换为 Python 格式，使用单字符键名
        result = []
        for info in textInfos:
            text = info['text']
            bounds = info['bounds']
            result.append({
                't': text,  # text -> t
                'b': {      # bounds -> b
                    'l': bounds['left'],   # left -> l
                    't': bounds['top'],    # top -> t
                    'r': bounds['right'],  # right -> r
                    'b': bounds['bottom']  # bottom -> b
                }
            })
        
        return result
    except Exception as e:
        Log.ex(e, "获取屏幕文本失败")
        return []


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


@regCmd(r'屏幕文本')
@requireAndroid
def getScreenText():
    try:
        text = PythonServices.getScreenText()
        if text:
            Log.i("识别到的文本: " + text)
            return text
        else:
            Log.i("未识别到文本")
            return "未识别到文本"
    except Exception as e:
        Log.ex(e, "获取屏幕文本失败")
        return "获取文本失败"


def _getScreenInfos():
    """获取并解析屏幕信息"""
    info = PythonServices.getScreenInfo()
    size = info.size()
    result = []
    
    for i in range(size):
        item = info.get(i)
        result.append({
            't': item.get('t'),
            'b': item.get('b')
        })
    return result


@regCmd(r'屏幕文本信息')
@requireAndroid
def getScreenInfo():
    try:
        # 使用封装的方法获取屏幕信息
        result = _getScreenInfos()
        
        # 直接使用返回的列表
        for item in result:
            bounds = item['b'].split(',')
            Log.i("Text:", item['t'])
            Log.i("Bounds:", f"left={bounds[0]}, top={bounds[1]}, right={bounds[2]}, bottom={bounds[3]}")
        
        return result
    except Exception as e:
        Log.ex(e, "获取屏幕文本信息失败")
        return "获取信息失败"


@regCmd(r'查找', r'(?P<pattern>.+)')
@requireAndroid
def findUI(pattern):
    try:
        # 编译正则表达式
        regex = re.compile(pattern)
        
        # 使用封装的方法获取屏幕信息
        screenInfo = _getScreenInfos()
        
        position = None
        # 遍历屏幕信息，查找匹配的文本
        for item in screenInfo:
            if regex.search(item['t']):
                bounds = item['b'].split(',')
                centerX = (int(bounds[0]) + int(bounds[2])) // 2
                centerY = (int(bounds[1]) + int(bounds[3])) // 2
                position = {'centerX': centerX, 'centerY': centerY}
                break
        
        Log.i(f"找到匹配的位置: {pattern}")
        
        # 将结果转换为 JSON 字符串
        return json.dumps(position) if position else None
    except Exception as e:
        Log.ex(e, "FindUI 指令执行失败")
        return "执行失败"


