@echo off
echo 正在启动Webhook服务...

:: 切换到项目根目录
cd ..

:: 检查虚拟环境
if exist venv (
    echo 使用虚拟环境...
    call venv\Scripts\activate
)

:: 安装依赖
pip install flask

:: 创建日志目录
if not exist publish\logs mkdir publish\logs

:: 获取当前日期时间
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /format:list') do set datetime=%%I
set logdate=%datetime:~0,8%
set logtime=%datetime:~8,6%

:: 启动Webhook服务器
echo 正在启动Webhook服务器，日志将保存到publish\logs目录...
start /B python publish\webhook_server.py > publish\logs\webhook_%logdate%_%logtime%.log 2>&1

echo Webhook服务器已在后台启动
echo 服务器监听在: http://localhost:5000/webhook
echo 你可以在publish\logs目录查看日志

pause 