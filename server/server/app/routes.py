# 面向控制器端的网页路由
from flask import render_template
from app import app
from app.websocket import device_manager  # 导入设备列表

@app.route('/')
def index():
    """首页路由，返回设备列表"""
    devices = device_manager.to_dict()
    return render_template('index.html', initial_devices=devices)

@app.route('/device/<device_id>')
def device(device_id):
    """设备控制页面"""
    device = device_manager.get_device(device_id)
    if not device:
        return "设备不存在", 404
    return render_template('device.html', device_id=device_id, device=device.to_dict())
