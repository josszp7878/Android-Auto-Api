@echo off
echo 正在启动服务器...

:: 切换到项目根目录
cd ..

:: 检查虚拟环境
if exist venv (
    echo 使用虚拟环境...
    call venv\Scripts\activate
)

:: 启动服务器
echo 正在启动服务器...
cmd /c python server/run.py

pause 