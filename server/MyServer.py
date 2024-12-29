from app import socketio, app

def start_server():
    """启动集成服务器"""
    print("正在启动集成服务器...")
    print("Web 服务器启动中...")
    socketio.run(
        app, 
        host="0.0.0.0", 
        port=5000,
        debug=False,
        use_reloader=False
    )

if __name__ == '__main__':
    start_server()
