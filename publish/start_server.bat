@echo off
chcp 65001 >nul
echo 正在启动服务器...

cd ..

@REM echo 检查并激活虚拟环境
@REM if exist venv (
@REM     echo 使用虚拟环境...
@REM     call venv\Scripts\activate
@REM )

echo 检查并安装必要依赖...
pip install flask-sqlalchemy eventlet flask-socketio

echo 正在启动服务器...
cmd /c python server/run.py

pause 