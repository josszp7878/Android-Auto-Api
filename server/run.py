from app import app, socketio
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import mimetypes
import threading
import json

class ScriptServerHandler(SimpleHTTPRequestHandler):
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
            for file in os.listdir(script_dir):
                file_path = os.path.join(script_dir, file)
                timestamps[file] = str(int(os.path.getmtime(file_path)))
            
            response = json.dumps(timestamps)
            print(f"返回时间戳信息: {response}")
            self.wfile.write(response.encode())
            return
        
        # 读取文件并发送
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts', os.path.basename(self.path))
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
    httpd = HTTPServer(server_address, ScriptServerHandler)
    print(f"启动文件服务器在 http://{bind}:{port}")
    httpd.serve_forever()

if __name__ == '__main__':
    # 启动文件服务器
    file_server_thread = threading.Thread(target=run_file_server)
    file_server_thread.start()

    # 启动Flask应用
    socketio.run(
        app,
        debug=True,
        host='0.0.0.0',
        port=5000
    ) 