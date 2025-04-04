from flask import Blueprint, send_file, render_template, jsonify, request, current_app, send_from_directory
import _G
from SDeviceMgr import deviceMgr
import os
import json
from datetime import datetime

# 创建蓝图
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """首页路由，返回设备列表"""
    log = _G._G_.Log()
    log.i('Server', '访问首页')
    devices = deviceMgr.toDict()
    curDeviceID = deviceMgr.curDeviceID
    return render_template('index.html', initial_devices=devices, curDeviceID=curDeviceID)


@bp.route('/device/<device_id>')
def device(device_id):
    """设备控制页面"""
    device = deviceMgr.get(device_id)
    if not device:
        return "设备不存在", 404
    return render_template('device.html', device_id=device_id, device=device.to_dict())


@bp.route('/file/<path:filename>')
def serve_file(filename):
    """处理文件请求"""
    g = _G._G_
    log = g.Log()
    file_path = os.path.join(g.rootDir(), filename)
    log.i('Server', f'处理文件请求: {file_path}')
    return send_file(file_path)


@bp.route('/timestamps')
def get_timestamps():
    """处理时间戳请求"""
    g = _G._G_
    log = g.Log()
    log.i('Server', "处理时间戳请求")
    timestamps = {}
    dir = g.rootDir()
    log.i(f'获取目录文件版本:{dir}')
    def getVersion(rootDir, relativeDir, timestamps):
        """获取目录下所有文件的时间戳"""
        dir = os.path.join(rootDir, relativeDir)
        if os.path.exists(dir):
            for file in os.listdir(dir):
                # 忽略大写S开头的服务器本地文件
                if file.startswith('S'):
                    continue
                file_path = os.path.join(dir, file)  
                if os.path.isfile(file_path):
                    timestamps[f"{relativeDir}/{file}"] = str(int(os.path.getmtime(file_path)))
    getVersion(dir, 'scripts', timestamps)
    getVersion(dir, 'config', timestamps)
    return json.dumps(timestamps)


@bp.route('/logs')
def get_logs():
    # 修改为返回空列表或其他替代方案
    return jsonify([])

@bp.route('/api/device/<device_id>/screenshot', methods=['POST'])
def take_screenshot(device_id):
    """设备截图API"""
    device = deviceMgr.get(device_id)
    if not device:
        return jsonify({'success': False, 'message': '设备不存在'}), 404
    
    success = device.takeScreenshot()
    return jsonify({
        'success': success,
        'message': '截图指令已发送' if success else '截图失败'
    })

@bp.route('/api/device/<device_id>/refresh', methods=['POST'])
def refresh_device(device_id):
    """刷新设备API"""
    device = deviceMgr.get(device_id)
    if not device:
        return jsonify({'success': False, 'message': '设备不存在'}), 404
    
    device.refresh()
    return jsonify({'success': True, 'message': '设备已刷新'})

@bp.route('/api/devices/batch', methods=['POST'])
def batch_operation():
    """批量设备操作API"""
    data = request.json
    device_ids = data.get('device_ids', [])
    operation = data.get('operation')
    
    results = []
    for device_id in device_ids:
        device = deviceMgr.get(device_id)
        if not device:
            results.append({'device_id': device_id, 'success': False, 'message': '设备不存在'})
            continue
            
        if operation == 'screenshot':
            success = device.takeScreenshot()
            results.append({
                'device_id': device_id,
                'success': success,
                'message': '截图指令已发送' if success else '截图失败'
            })
        elif operation == 'refresh':
            device.refresh()
            results.append({
                'device_id': device_id,
                'success': True,
                'message': '设备已刷新'
            })
    
    return jsonify({'results': results})
