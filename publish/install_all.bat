@echo off
echo 开始一键部署过程...

:: 创建虚拟环境
echo 第1步: 创建虚拟环境...
call create_venv.bat

:: 更新代码
echo 第2步: 更新代码...
call update_code.bat

:: 启动服务器
echo 第3步: 启动服务器...
call start_server.bat

:: 启动webhook服务
echo 第4步: 启动Webhook服务...
call start_webhook.bat

:: 注册Windows服务
echo 第5步: 注册Windows服务...
call register_service.bat

echo 一键部署完成！
pause 