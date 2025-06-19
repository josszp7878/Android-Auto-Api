@echo off
chcp 65001 >nul
echo SSL递归错误修复工具

echo 1. 正在升级pip...
python -m pip install --upgrade pip

echo 2. 正在卸载可能冲突的库...
pip uninstall urllib3 requests certifi -y

echo 3. 正在安装固定版本的依赖...
pip install urllib3==1.26.18
pip install certifi==2021.10.8
pip install requests==2.28.2

echo 4. 正在更新项目依赖...
cd server
pip install -r requirements.txt

echo 5. 修复完成！请重新启动服务器
echo 如果问题仍然存在，请设置环境变量：
echo set DEBUG_MODE=1
echo 然后再次启动服务器

pause 