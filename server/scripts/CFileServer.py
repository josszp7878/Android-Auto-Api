import os
import json
import requests
from typing import Callable
from threading import Thread
from logger import Log
from CTools import CTools

# 定义应用根目录

class CFileServer:
    TAG = "CFileServer"
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
            self._scriptDir = None  # 初始化私有变量

    @property
    def scriptDir(self):
        """懒加载脚本目录
        Returns:
            str: 脚本目录路径
        """
        if self._scriptDir is None:
            android = CTools.android()
            if android:
                # Android环境下使用应用私有目录
                # getFilesDir 直接返回字符串路径
                self._scriptDir = android.getFilesDir('scripts', True)
                Log.i(f"Android脚本目录: {self._scriptDir}")
            else:
                # 开发环境使用当前目录
                self._scriptDir = os.path.dirname(os.path.abspath(__file__))
                Log.i(f"开发环境脚本目录: {self._scriptDir}")
        return self._scriptDir

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
                    if int(remoteVersion) > int(currentVersion):
                        # Log.d(f"更新脚本: {filename}")
                        self.download(filename)
                        success = True
                if success:
                    self.saveVersions(remoteVersions)
                    Log.d("脚本已更新!!")
            except Exception as e:
                Log.ex(e, "更新脚本失败")                    
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
            Log.i(f"下载文件: {url}")
            response = requests.get(url, timeout=8)
            response.raise_for_status()

            scriptFile = os.path.join(self.scriptDir, filename)
            Log.i(f"保存文件到: {scriptFile}")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(scriptFile), exist_ok=True)
            
            with open(scriptFile, 'w', newline = '', encoding='utf-8') as f:
                f.write(response.text)

            Log.i(f"下载完成: {scriptFile} (大小: {os.path.getsize(scriptFile)} bytes)")
            if onComplete:
                onComplete(True)
            return True
        except Exception as e:
            Log.ex(e, f"下载失败: {filename}")
            if onComplete:
                onComplete(False)
            return False

    def currentVersions(self):
        version_file = os.path.join(self.scriptDir, "version.txt")
        if not os.path.exists(version_file):
            return {}

        with open(version_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def saveVersions(self, versions):
        version_file = os.path.join(self.scriptDir, "version.txt")
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(versions, f)
            
    def remoteVersions(self):
        # 测试阶段使用的方法
        url = f"{self.serverUrl}/timestamps"
        # Log.i(f"获取远程文件时间戳: {url}")
        try:
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            remote_versions = response.json()
            # Log.i(f"远程版本信息: {remote_versions}")

            # 过滤掉以 "_" 开头的文件
            remote_versions = {k: v for k, v in remote_versions.items() if not k.startswith("_")}
            return remote_versions
        except requests.RequestException as e:
            Log.ex(e, "获取时间戳失败")
            return {}
    ##############################
fileServer = CFileServer()