import os
import json
import requests
from typing import Callable
from threading import Thread
import _G

class CFileServer_:
    serverUrl = None

    @classmethod
    def Clone(cls, oldCls):
        cls.serverUrl = oldCls.serverUrl

    @classmethod
    def update(cls, callback: Callable[[bool], None]):
        # 定义一个内部函数run，用于执行更新脚本的操作
        log = _G._G_.Log()
        def run():
            success = False
            try:
                curVersions = cls.currentVersions()
                remoteVersions = cls.remoteVersions()
                # 遍历远程脚本的版本信息
                for filename, remoteVersion in remoteVersions.items():
                    currentVersion = curVersions.get(filename, "0")
                    if int(remoteVersion) > int(currentVersion):
                        log.d(f"更新文件: {filename}")
                        cls.download(filename)
                        success = True
                if success:
                    cls.setCurrentVersions(remoteVersions)
                    log.d("脚本更新成功!!")
            except Exception as e:
                log.ex(e, "脚本更新失败")                    
            callback(success)
        Thread(target=run).start()

    @classmethod
    def toRelativePath(cls, filename):
        """查找文件
        如果filename不带后缀且不包含路径，则在根目录及子目录下查找匹配的文件
        Args:
            filename: 文件名
        Returns:
            找到的文件相对路径，未找到则返回None
        """
        g = _G._G_
        log = g.Log()
        dir = g.scriptDir()
        # 检查文件名是否包含路径或后缀
        if os.path.basename(filename) == filename and '.' not in filename:
            log.d(f"查找文件: {filename}")
            # 在根目录及子目录下查找匹配的文件
            for root, dirs, files in os.walk(dir):
                for file in files:
                    # 忽略大小写比较文件名前缀
                    name, ext = os.path.splitext(file)
                    if name.lower() == filename.lower():
                        # 返回相对于根目录的路径
                        relPath = os.path.relpath(os.path.join(root, file), dir)
                        log.d(f"找到匹配文件: {relPath}")
                        return relPath
            log.d(f"未找到匹配文件: {filename}")
            return None
        else:
            # 如果包含路径或后缀，直接返回
            return filename
        
    @classmethod
    def download(cls, filename, onComplete=None):
        """下载文件
        Args:
            filename: 文件名
            onComplete: 完成回调函数
        """
        g = _G._G_
        log = g.Log()
        try:
            url = f"{cls.serverUrl}/file/{filename}"
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            scriptFile = os.path.join(g.rootDir(), filename)
            # 确保目录存在
            os.makedirs(os.path.dirname(scriptFile), exist_ok=True)
            
            with open(scriptFile, 'w', newline = '', encoding='utf-8') as f:
                f.write(response.text)
            log.d(f"下载文件完成d: {scriptFile} (大小: {os.path.getsize(scriptFile)} bytes)")
            if onComplete:
                onComplete(True)
            return True
        except Exception as e:
            log.ex(e, f"下载文件失败: {filename}")
            if onComplete:
                onComplete(False)
            return False

    @classmethod
    def currentVersions(cls):
        dir = _G._G_.rootDir()
        version_file = os.path.join(dir, "version.txt")
        if not os.path.exists(version_file):
            return {}

        with open(version_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @classmethod
    def setCurrentVersions(cls, versions):
        dir = _G._G_.rootDir()
        version_file = os.path.join(dir, "version.txt")
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(versions, f)
            
    @classmethod
    def remoteVersions(cls):
        # 测试阶段使用的方法
        url = f"{cls.serverUrl}/timestamps"
        try:
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            remote_versions = response.json()
            print(f'22remote_versions={remote_versions}')
            return remote_versions
        except requests.RequestException as e:
            print(e)
            return {}
