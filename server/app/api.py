from flask import request, jsonify
from server.scripts._Log import LogHandler

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取日志API"""
    start_index = request.args.get('start', 0, type=int)
    logs = LogHandler.get_logs(start_index)
    return jsonify(logs)

@app.route('/api/logs/clear', methods=['POST'])
def clear_logs():
    """清空日志API"""
    LogHandler.clear_logs()
    return jsonify({"success": True}) 