import os
import json
import requests
from typing import Callable
from threading import Thread
import _Log

class CFileServer:
    _instance = None  # 用于存储单例实例

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(CFileServer, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.thread = Thread
            self.initialized = True
            self.serverUrl = None

   
    def updateScripts(self, callback: Callable[[bool], None]):
        # 定义一个内部函数run，用于执行更新脚本的操作
        def run():
            success = False
            try:
                curVersions = self.currentVersions()
                remoteVersions = self.remoteVersions()
                # 遍历远程脚本的版本信息
                for filename, remoteVersion in remoteVersions.items():
                    currentVersion = curVersions.get(filename, "0")
                    # print(f'更新脚本: filename={filename} currentVersion={currentVersion} remoteVersion={remoteVersion}')
                    if int(remoteVersion) > int(currentVersion):
                        self.download(filename)
                        success = True
                if success:
                    self.saveVersions(remoteVersions)
                    print("脚本更新成功!!")
            except Exception as e:
                print(e)                    
            callback(success)
        Thread(target=run).start()

    def download(self, filename, onComplete=None):
        """下载文件
        Args:
            filename: 文件名
            onComplete: 完成回调函数
        """
        try:
            url = f"{self.serverUrl}/scripts/{filename}"
            response = requests.get(url, timeout=8)
            response.raise_for_status()

            from CMain import getScriptDir
            scriptDir = getScriptDir()
            scriptFile = os.path.join(scriptDir, filename)
            # _Log.Log_.d(f"下载文件: {url} 到 {scriptFile}")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(scriptFile), exist_ok=True)
            
            with open(scriptFile, 'w', newline = '', encoding='utf-8') as f:
                f.write(response.text)
            _Log.Log_.d(f"下载文件完成: {filename} (大小: {os.path.getsize(scriptFile)} bytes)")
            if onComplete:
                onComplete(True)
            return True
        except Exception as e:
            print(e)
            if onComplete:
                onComplete(False)
            return False

    def currentVersions(self):
        from CMain import getScriptDir
        scriptDir = getScriptDir()
        version_file = os.path.join(scriptDir, "version.txt")
        if not os.path.exists(version_file):
            return {}

        with open(version_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def saveVersions(self, versions):
        from CMain import getScriptDir
        scriptDir = getScriptDir()
        version_file = os.path.join(scriptDir, "version.txt")
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(versions, f)
            
    def remoteVersions(self):
        # 测试阶段使用的方法
        url = f"{self.serverUrl}/timestamps"
        try:
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            remote_versions = response.json()
            print(f'22remote_versions={remote_versions}')
            return remote_versions
        except requests.RequestException as e:
            print(e)
            return {}
    ##############################
fileServer = CFileServer()