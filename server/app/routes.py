from flask import Blueprint, send_file, render_template, jsonify, request, current_app, send_from_directory
from app import app
from _Log import _Log
from SDeviceMgr import deviceMgr
import os
import json
from datetime import datetime

# 创建蓝图
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """首页路由，返回设备列表"""
    _Log.i('Server', '访问首页')
    devices = deviceMgr.to_dict()
    return render_template('index.html', initial_devices=devices)


@bp.route('/device/<device_id>')
def device(device_id):
    """设备控制页面"""
    device = deviceMgr.get_device(device_id)
    if not device:
        return "设备不存在", 404
    return render_template('device.html', device_id=device_id, device=device.to_dict())


@bp.route('/scripts/<path:filename>')
def serve_script(filename):
    """处理脚本文件请求"""
    _Log.i('Server', f'处理脚本文件请求: {filename}')
    script_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        'scripts'
    )
    return send_file(os.path.join(script_dir, filename))


@bp.route('/timestamps')
def get_timestamps():
    """处理时间戳请求"""
    _Log.i('Server', "处理时间戳请求")
    timestamps = {}
    script_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        'scripts'
    )
    if os.path.exists(script_dir):
        for file in os.listdir(script_dir):
            file_path = os.path.join(script_dir, file)
            if os.path.isfile(file_path):
                timestamps[file] = str(int(os.path.getmtime(file_path)))
    return json.dumps(timestamps)


@bp.route('/logs')
def get_logs():
    # 修改为返回空列表或其他替代方案
    return jsonify([])
