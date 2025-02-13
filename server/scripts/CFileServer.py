import os
import json
import requests
import sys
import importlib
from typing import Callable
from threading import Thread
from logger import Log
from tools import Tools

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
            android = Log.android
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
            
            with open(scriptFile, 'w', encoding='utf-8') as f:
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

    def _onPreload(self, module, module_name: str, log: Log) -> bool:
        """执行模块的预加载函数"""
        if hasattr(module, 'OnPreload'):
            try:
                module.OnPreload()
                return True
            except Exception as e:
                log.ex(e, f"执行预重载函数失败: {module_name}")
                return False
        return True
    

    #热加载
    ##########    
    def _reload(self, module_name: str, log: Log) -> bool:
        """处理模块重新加载
        Args:
            module_name: 模块名称
            log: 日志实例
        Returns:
            bool: 是否重载成功
        """
        try:
            if module_name in sys.modules:
                module = sys.modules[module_name]
                # 执行预加载
                if hasattr(module, 'OnPreload'):
                    module.OnPreload()
                
                # 获取所有引用了该模块的模块
                referrers = [m for m in sys.modules.values() 
                            if m and hasattr(m, '__dict__') and module_name in m.__dict__]
                
                # 重新加载模块
                del sys.modules[module_name]
                # 强制重新从文件加载模块
                spec = importlib.util.find_spec(module_name)
                if not spec:
                    log.e(f"找不到模块: {module_name}")
                    return False
                    
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # 更新引用
                for referrer in referrers:
                    if hasattr(referrer, '__dict__'):
                        referrer.__dict__[module_name] = module
                
                # 执行重载后回调
                if not self._onReload(module, module_name, log):
                    return False
                    
                log.i(f"重新加载模块成功: {module_name}")
            else:
                # 首次加载直接使用import_module
                module = importlib.import_module(module_name)
                log.i(f"首次加载模块成功: {module_name}")
            
            return True
        except Exception as e:
            log.ex(e, f"加载模块失败: {module_name}")
            return False

    def _onReload(self, module, module_name: str, log: Log) -> bool:
        """执行模块的重载后函数"""
        if hasattr(module, 'OnReload'):
            try:
                module.OnReload()
                return True
            except Exception as e:
                log.ex(e, f"执行热更新函数失败: {module_name}")
                return False
        return True

    def reloadModule(self, module_name):
        """重新加载模块
        Args:
            module_name: 模块名
            onComplete: 完成回调函数
        """
        try:
            def onComplete(success):
                if success:
                    self._reload(module_name, Log)
                else:
                    Log.e(f"下载失败: {module_name}")
            return self.download(f"{module_name}.py", onComplete)
        except Exception as e:
            Log.ex(e, '重载模块失败')
            return False
    ##############################
fileServer = CFileServer()