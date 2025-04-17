import os
import json
import requests
from typing import Callable
from threading import Thread
import _G
import time
import fnmatch

class CFileServer_:
    
    _serverIP = None
    @classmethod
    def server(cls):
        return _G._G_.Tools().getServerURL(cls._serverIP)
    
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
        
    @classmethod
    def onLoad(cls, oldCls):
        if oldCls:
            cls._serverIP = oldCls._serverIP

 
    @classmethod
    def _uploadFile(cls, local_path):
        """上传文件到服务器
        
        Args:
            local_path: 本地文件的完整路径
        Returns:
            str: 上传结果信息
        """
        import os
        
        g = _G._G_
        log = g.Log()
        client = g.CClient()
        
        try:
            # 读取文件内容
            with open(local_path, 'rb') as f:
                file_content = f.read()
            
            file_size = len(file_content)
            file_name = os.path.basename(local_path)      
            rel_path = os.path.relpath(local_path, g.rootDir())
            # 使用现有的上传文件方法
            success = cls.uploadFileContent(rel_path, file_content)
            
            if success:
                return f"文件上传成功: {file_name}，大小: {file_size} 字节，保存到: {rel_path}"
            else:
                return f"e~文件上传失败: {file_name}"
        except Exception as e:
            log.ex(e, f"上传文件失败: {local_path}")
            return f"e~上传文件出错: {str(e)}"

    @classmethod
    def uploadFile(cls, fileName, rootDir='config'):
        """将本地文件上传到服务器
        
        Args:
            fileName: 要上传的文件名，支持模式匹配
            rootDir: 搜索的根目录，默认为'config'
            
        Returns:
            str: 上传结果信息
        """
        try:
            import os
            import fnmatch
            g = _G._G_
            log = g.Log()
            
            base_dir = os.path.join(g.rootDir(), rootDir)
            if not os.path.isdir(base_dir):
                log.e(f"目录不存在: {base_dir}")
                return f"e~目录不存在: {rootDir}"
            
            # 缓存目录下所有文件的相对路径
            all_files = []
            for root, _, files in os.walk(base_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    all_files.append(full_path)
            
            # 匹配文件名
            pattern = f"*{fileName}*" if '.' not in fileName else fileName
            matched_files = []
            for full_path in all_files:
                if fnmatch.fnmatch(full_path.lower(), pattern.lower()):
                    matched_files.append(full_path)
            
            if not matched_files:
                log.e(f"找不到匹配的文件: {fileName}")
            
            # 选择第一个匹配的文件上传
            for full_path in matched_files:   
                cls._uploadFile(full_path)
        except Exception as e:
            log.ex(e, f"上传文件失败: {fileName}")


    @classmethod
    def registerCommands(cls):
        """注册文件服务器相关命令"""
        g = _G._G_
        regCmd = g.CmdMgr().reg
        
        @regCmd(r"#上传(?P<fileName>.+)")
        def upLoad(fileName):
            """功能：将本地data目录下的文件上传到服务器
            示例：上传 Checks
                  sc pages
                  上传 images/logo.png
            """
            return cls.uploadFile(fileName)
        
    @classmethod
    def uploadFileContent(cls, server_path, file_content):
        """将文件内容上传到服务器
        
        Args:
            server_path: 服务器端的文件路径
            file_content: 要上传的文件内容
            
        Returns:
            bool: 上传是否成功
        """
        g = _G._G_
        log = g.Log()
        
        try:
            # 构建上传请求URL
            url = f"{cls.server()}/api/upload"
            
            # 准备请求参数
            params = {'path': server_path}
            headers = {'Content-Type': 'application/octet-stream'}
            
            # 发送POST请求上传文件
            response = requests.post(
                url,
                params=params,
                data=file_content,
                headers=headers,
                timeout=30
            )
            
            # 检查上传结果
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    log.i(f"文件上传成功: {server_path}, 大小: {len(file_content)} 字节")
                    return True
                else:
                    log.e(f"服务器返回错误: {result.get('message')}")
                    return False
            else:
                log.e(f"上传文件失败，HTTP状态码: {response.status_code}")
                return False
            
        except Exception as e:
            log.ex(e, f"上传文件出错: {server_path}")
            return False

CFileServer_.onLoad(None)