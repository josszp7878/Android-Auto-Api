import json
import os

# 获取脚本目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置文件路径
CONFIG_FILE_PATH = os.path.join(SCRIPT_DIR, 'config.json')


# 读取配置文件
with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
    config_data = json.load(f)

# 获取包名
def get_package_name(product_name):
    return config_data.get(product_name, {}).get('package_name')

# 获取APK文件路径
def get_apk_path(product_name):
    return config_data.get(product_name, {}).get('apk_path')