import sys
import time
import threading
from app import socketio, app
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import mimetypes
import json

class FileServerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        print(f"收到GET请求: {self.path}")  # 添加请求日志
        
        # 添加CORS头
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        
        # 处理时间戳API请求
        if self.path.rstrip('/') == '/timestamps':
            print("处理时间戳请求")
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # 获取所有脚本文件的时间戳
            timestamps = {}
            script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')
            print(f"$$$$$$脚本目录: {script_dir}")
            if os.path.exists(script_dir):
                for file in os.listdir(script_dir):
                    file_path = os.path.join(script_dir, file)
                    timestamps[file] = str(int(os.path.getmtime(file_path)))
            
            response = json.dumps(timestamps)
            print(f"返回时间戳信息: {response}")
            self.wfile.write(response.encode())
            return
        
        # 读取文件并发送
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts', os.path.basename(self.path))
        print(f"$$$$$$文件路径: {file_path}")
        if os.path.exists(file_path):
            # 根据文件类型设置Content-Type
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type:
                self.send_header('Content-Type', mime_type)
            else:
                self.send_header('Content-Type', 'application/octet-stream')
            self.end_headers()

            # 根据文件类型选择读取模式
            if mime_type and mime_type.startswith('text'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            else:
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
        else:
            self.send_error(404, "File not found")
        return

def run_file_server(port=8000, bind="0.0.0.0"):
    server_address = (bind, port)
    httpd = HTTPServer(server_address, FileServerHandler)
    print(f"启动文件服务器在 http://{bind}:{port}")
    httpd.serve_forever()

def start_socketio_server(port=5000, host="0.0.0.0"):
    """启动SocketIO服务器"""
    print(f"SocketIO服务器启动在: http://{host}:{port}")
    socketio.run(app, host=host, port=port)

def command_loop():
    """命令行循环"""
    print("服务器命令行模式")
    print("支持的命令:")
    print("- status: 查看服务器状态")
    print("- StartFS: 启动文件服务器")
    print("- StopFS: 停止文件服务器")
    print("- exit: 退出服务器")

    try:
        while True:
            cmd_input = input("server> ").strip()
            if not cmd_input:
                continue

            cmd = cmd_input.lower()

            if cmd == 'exit':
                break
            elif cmd == 'status':
                print("服务器正在运行")
            else:
                print(f"未知命令: {cmd}")

    except KeyboardInterrupt:
        print('\n正在退出...')
    except Exception as e:
        print(f'发生错误: {e}')
    finally:
        print("服务器已停止")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python MyServer.py [socketio|fileserver|console]")
        sys.exit(1)

    command = sys.argv[1].lower()
    
    if command == 'socketio':
        start_socketio_server()
    elif command == 'fileserver':
        run_file_server()
    elif command == 'console':
        command_loop()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python MyServer.py [socketio|fileserver|console]")
        sys.exit(1)
