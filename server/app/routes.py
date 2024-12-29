from flask import Blueprint, send_file, render_template
from .device_manager import DeviceManager
import os
import json
from .logger import Logger

# 创建蓝图
bp = Blueprint('main', __name__)

# 获取设备管理器实例
device_manager = DeviceManager()


@bp.route('/')
def index():
    """首页路由，返回设备列表"""
    print("处理首页请求@@@@")
    # 添加测试日志
    Logger.i('Server', '访问首页')
    devices = device_manager.to_dict()
    return render_template('index.html', initial_devices=devices)


@bp.route('/device/<device_id>')
def device(device_id):
    """设备控制页面"""
    device = device_manager.get_device(device_id)
    if not device:
        return "设备不存在", 404
    return render_template('device.html', device_id=device_id, device=device.to_dict())


@bp.route('/scripts/<path:filename>')
def serve_script(filename):
    """处理脚本文件请求"""
    print("处理脚本文件请求@@@@")
    script_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        'scripts'
    )
    return send_file(os.path.join(script_dir, filename))


@bp.route('/timestamps')
def get_timestamps():
    """处理时间戳请求"""
    print("处理时间戳请求@@@@")
    timestamps = {}
    script_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        'scripts'
    )
    if os.path.exists(script_dir):
        for file in os.listdir(script_dir):
            file_path = os.path.join(script_dir, file)
            timestamps[file] = str(int(os.path.getmtime(file_path)))
    return json.dumps(timestamps)
