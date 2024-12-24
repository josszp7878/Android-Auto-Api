from flask import Blueprint, render_template
from .device_manager import DeviceManager

# 创建蓝图
bp = Blueprint('main', __name__)

# 获取设备管理器实例
device_manager = DeviceManager()

@bp.route('/')
def index():
    """首页路由，返回设备列表"""
    devices = device_manager.to_dict()
    return render_template('index.html', initial_devices=devices)

@bp.route('/device/<device_id>')
def device(device_id):
    """设备控制页面"""
    device = device_manager.get_device(device_id)
    if not device:
        return "设备不存在", 404
    return render_template('device.html', device_id=device_id, device=device.to_dict())
