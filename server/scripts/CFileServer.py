import os
import json
import requests
from typing import Callable
from threading import Thread
import _G

class CFileServer_:
    
    _serverIP = None
    @classmethod
    def server(cls):
        return _G._G_.Tools().getServerURL(cls._serverIP)
    
    @classmethod
    def Clone(cls, oldCls):
        cls._serverIP = oldCls.serverIp
    
    @classmethod
    def init(cls, serverIp):
        cls._serverIP = serverIp


    @classmethod
    def downAll(cls):
        # 定义一个内部函数run，用于执行更新脚本的操作
        log = _G._G_.Log()
        def run():
            success = True
            try:
                curVersions = cls.currentVersions()
                remoteVersions = cls.remoteVersions()
                # 遍历远程脚本的版本信息
                count = 0
                downloadTasks = []
                
                for filename, remoteVersion in remoteVersions.items():
                    currentVersion = curVersions.get(filename, "0")
                    if int(remoteVersion) > int(currentVersion):
                        # log.d(f"更新文件: {filename}")
                        downloadTask = Thread(target=cls.download, args=(filename,))
                        downloadTask.start()
                        downloadTasks.append(downloadTask)
                        count += 1
                
                # 等待所有下载任务完成
                for task in downloadTasks:
                    task.join()
                    
                if count > 0:
                    cls.setCurrentVersions(remoteVersions)
                log.d(f"更新了{count}个文件")
            except Exception as e:
                log.ex(e, "脚本更新失败")
                success = False
            return success
        
        # 创建并启动线程，但返回线程对象以便调用者可以等待完成
        downloadThread = Thread(target=run)
        downloadThread.start()
        return downloadThread
        

        
    @classmethod
    def download(cls, filename, callback: Callable[[bool], None] = None):
        """下载文件
        Args:
            filename: 文件名
            callback: 完成回调函数
        """
        g = _G._G_
        log = g.Log()
        ok = False
        try:
            url = f"{cls.server()}/file/{filename}"
            # log.d(f"下载文件...: {url}")
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            log.d(f"下载文件完成: {filename} (大小: {len(response.text)} bytes)")
            scriptFile = os.path.join(g.rootDir(), filename)
            # 确保目录存在
            os.makedirs(os.path.dirname(scriptFile), exist_ok=True)
            import CClient
            if CClient.CClient_.fromAndroid:
                with open(scriptFile, 'w', newline = '', encoding='utf-8') as f:
                    f.write(response.text)
                log.d(f"下载文件完成: {filename} => {scriptFile}")
                # 如果下载的是脚本文件，清除脚本名称缓存
                if filename.startswith('scripts/') and filename.endswith('.py'):
                    g.clearScriptNamesCache()
                    # log.d(f"脚本文件已更新，清除脚本名称缓存")
            ok = True
        except Exception as e:
            log.ex(e, f"下载文件失败: {filename}")
            ok = False
        if callback:
            callback(ok)
        return ok

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
        url = f"{cls.server()}/timestamps"
        # print('aaaaaaaaaaaaaaaaaaaaaaaaaa')
        try:
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            remote_versions = response.json()
            # print(f'22remote_versions={remote_versions}')
            return remote_versions
        except requests.RequestException as e:
            print(e)
            return {}
