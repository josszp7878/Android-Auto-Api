from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import json
import time

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
            script_dir = os.path.dirname(os.path.abspath(__file__))
            for file in os.listdir(script_dir):
                if file.endswith('.py') and file != 'file_server.py':
                    file_path = os.path.join(script_dir, file)
                    timestamps[file] = str(int(os.path.getmtime(file_path)))
            
            response = json.dumps(timestamps)
            print(f"返回时间戳信息: {response}")
            self.wfile.write(response.encode())
            return
        
        if self.path.endswith('.py'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            
            # 读取文件并发送
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                   os.path.basename(self.path))
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.wfile.write(content.encode('utf-8'))
            return
        
        # 其他请求使用默认的文件服务处理
        print("处理文件请求")
        self.send_header('Content-type', 'application/octet-stream')
        self.end_headers()
        super().do_GET()

    def log_message(self, format, *args):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format%args}")

def run_server(port=8000, bind="0.0.0.0"):
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    server_address = (bind, port)
    httpd = HTTPServer(server_address, ScriptServerHandler)
    print(f"启动服务器在 http://{bind}:{port}")
    print(f"当前工作目录: {os.getcwd()}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server() 