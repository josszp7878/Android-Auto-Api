from flask import Flask, request, jsonify
import subprocess
import hmac
import hashlib
import os
import logging
from datetime import datetime

# 获取项目根目录路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLISH_DIR = os.path.dirname(os.path.abspath(__file__))

# 创建logs目录
logs_dir = os.path.join(PUBLISH_DIR, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# 配置日志
log_file = os.path.join(logs_dir, f'webhook_{datetime.now().strftime("%Y%m%d")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('webhook')

app = Flask(__name__)

# 配置
SECRET_TOKEN = "your_secret_token"  # 设置为你的密钥
UPDATE_SCRIPT = os.path.join(PUBLISH_DIR, "update_code.bat")

@app.route('/webhook', methods=['POST'])
def webhook():
    # 验证签名
    signature = request.headers.get('X-Hub-Signature')
    if not signature:
        logger.warning("未提供签名")
        return jsonify({"status": "error", "message": "未提供签名"}), 400
    
    payload = request.data
    computed_signature = 'sha1=' + hmac.new(
        SECRET_TOKEN.encode(), payload, hashlib.sha1).hexdigest()
    
    if not hmac.compare_digest(signature, computed_signature):
        logger.warning("签名验证失败")
        return jsonify({"status": "error", "message": "签名验证失败"}), 401
    
    # 执行更新脚本
    try:
        logger.info("开始执行更新脚本")
        subprocess.Popen([UPDATE_SCRIPT], shell=True)
        logger.info("更新脚本执行成功")
        return jsonify({"status": "success", "message": "部署已启动"}), 200
    except Exception as e:
        logger.error(f"执行更新脚本时出错: {str(e)}")
        return jsonify({"status": "error", "message": f"执行更新脚本时出错: {str(e)}"}), 500

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "online", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}), 200

if __name__ == '__main__':
    logger.info("Webhook服务器启动")
    app.run(host='0.0.0.0', port=5000) 