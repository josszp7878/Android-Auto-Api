from Command import command, do
from client.scripts.tools import Tools
from config import get_package_name, get_apk_path
from java import jclass

# 导入Java类
PythonServices = jclass("cn.vove7.andro_accessibility_api.demo.script.PythonServices")

@command(r"点击\s+(?P<x>\d+)\s+(?P<y>\d+)")
def click(x, y):
    try:
        x, y = int(x), int(y)
        result = PythonServices.clickPosition(x, y)
        return f"点击位置 ({x}, {y}) 结果: {result}"
    except Exception as e:
        return f"Error calling clickPosition: {e}"

@command(r"屏幕内容")
def getScreenText():
    try:
        screen_text = PythonServices.getScreenText()
        return f"屏幕文本: {screen_text}"
    except Exception as e:
        return f"Error calling getScreenText: {e}"


@command(r"返回")
def go_back():
    return PythonServices.goBack()

@command(r"主屏幕")
def go_home():
    return PythonServices.goHome()

@command(r"检查安装\s+(?P<productName>\S+)")
def is_app_installed(productName):
    packageName = get_package_name(productName)
    if packageName:
        return PythonServices.isAppInstalled(packageName)
    return f"未找到产品名对应的包名: {productName}"

@command(r"打开\s+(?P<productName>\S+)")
def open_app(productName):
    return Tools.openApp(productName)

@command(r"关闭\s+(?P<productName>\S+)")
def close_app(productName):
    packageName = get_package_name(productName)
    if packageName:
        return PythonServices.closeApp(packageName)
    return f"未找到产品名对应的包名: {productName}"

@command(r"安装\s+(?P<productName>\S+)")
def install_app(productName):
    apkPath = get_apk_path(productName)
    if apkPath:
        return PythonServices.installApp(apkPath)
    return f"未找到产品名对应的APK路径: {productName}"
@command(r"卸载\s+(?P<productName>\S+)")
def uninstall_app(productName):
    packageName = get_package_name(productName)
    if packageName:
        return PythonServices.uninstallApp(packageName)
    return f"未找到产品名对应的包名: {productName}"

@command(r"截屏")
def take_screenshot():
    try:
        result = PythonServices.takeScreenshot()
        return f"截屏结果: {result}"
    except Exception as e:
        return f"Error calling takeScreenshot: {e}"