from flask import render_template
from app import app
from app.websocket import devices  # 导入设备列表

@app.route('/')
def index():
    return render_template('index.html', devices=devices)

@app.route('/device/<device_id>')
def device(device_id):
    device = devices.get(device_id, {
        'status': 'unknown',
        'last_seen': None,
        'info': {}
    })  # 如果设备不存在，提供默认值
    return render_template('device.html', device_id=device_id, device=device) 