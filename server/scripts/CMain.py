import os
import time
import sys

android = None
# 全局变量声明
runFromAndroid = False  # 默认非Android环境

def getScriptDir():
    _scriptDir = None
    if android:
        # Android环境下使用应用私有目录
        _scriptDir = android.getFilesDir('scripts', True)
    else:
        # 开发环境使用当前目录
        _scriptDir = os.path.dirname(os.path.abspath(__file__))
    print(f"脚本目录: {_scriptDir}")
    return _scriptDir

# 更新脚本
def updateScripts():
    print(f'33333 runFromAndroid={runFromAndroid}')  # 调试输出
    if runFromAndroid:  # 使用全局变量判断
        # 更新脚本
        print('更新脚本ddd')
        waitting = True
        def onUpdated(ok):
            nonlocal waitting
            waitting = False
        from CFileServer import fileServer
        fileServer.updateScripts(onUpdated)
        # 等待脚本更新完成
        while waitting:
            try:
                time.sleep(1)
                print(".", end="", flush=True)
            except Exception:
                break

def Begin(deviceID=None, server=None, androidEnv=None):
    """初始化客户端"""
    global runFromAndroid  # 确保使用全局变量
    try:
        if androidEnv is not None:
            runFromAndroid = androidEnv  # 设置全局变量
            print(f'Begin中设置 runFromAndroid={runFromAndroid}')  # 调试输出
            if runFromAndroid:
                try:
                    from java import jclass            
                    android = jclass("cn.vove7.andro_accessibility_api.demo.script.PythonServices")
                except Exception as e:
                    print('加载java模块失败')

        # print(f'脚本更新前   &&&&&&&：runFromAndroid={runFromAndroid}')
        # 先更新脚本再初始化客户端
        updateScripts()
        from _Log import _Log
        _Log().init(is_server=False)
        from CClient import client
        print(f"初始化客户端: androidEnv={androidEnv} runFromAndroid={runFromAndroid}")
        client.Begin(deviceID, server)
    except Exception as e:
        _Log.ex(e, "初始化客户端失败")

def End():
    """清理函数"""
    from CClient import client
    client.End()

def main():
    # 命令行启动支持
    device_id = sys.argv[1] if len(sys.argv) > 1 else None
    server_url = sys.argv[2] if len(sys.argv) > 2 else None
    Begin(device_id, server_url, False)

if __name__ == '__main__':
    main() 