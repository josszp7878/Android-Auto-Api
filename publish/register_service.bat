@echo off
chcp 65001 >nul
echo 正在注册Windows服务...

:: 切换到项目根目录
cd ..

:: 检查管理员权限
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 需要管理员权限来注册服务
    echo 请右键点击此脚本，选择"以管理员身份运行"
    pause
    exit /b
)

:: 检查NSSM是否存在
where nssm >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 未找到NSSM工具，正在下载...
    
    :: 创建工具目录
    if not exist publish\tools mkdir publish\tools
    
    :: 下载NSSM
    powershell -Command "Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile 'publish\tools\nssm.zip'"
    
    :: 解压NSSM
    powershell -Command "Expand-Archive -Path 'publish\tools\nssm.zip' -DestinationPath 'publish\tools' -Force"
    
    :: 复制NSSM到工具目录
    if exist publish\tools\nssm-2.24\win64\nssm.exe (
        copy publish\tools\nssm-2.24\win64\nssm.exe publish\tools\nssm.exe
    ) else (
        copy publish\tools\nssm-2.24\win32\nssm.exe publish\tools\nssm.exe
    )
    
    set NSSM_PATH=publish\tools\nssm.exe
) else (
    set NSSM_PATH=nssm
)

:: 获取当前目录
set PROJECT_DIR=%cd%
set PYTHON_PATH=%PROJECT_DIR%\venv\Scripts\python.exe
if not exist "%PYTHON_PATH%" (
    set PYTHON_PATH=python
)
set WEBHOOK_SCRIPT=%PROJECT_DIR%\publish\webhook_server.py

:: 注册服务
echo 正在注册Webhook服务...
%NSSM_PATH% install AutoDeployWebhook "%PYTHON_PATH%" "%WEBHOOK_SCRIPT%"
%NSSM_PATH% set AutoDeployWebhook DisplayName "自动部署Webhook服务"
%NSSM_PATH% set AutoDeployWebhook Description "监听Git更新并自动部署应用"

:: 创建日志目录
if not exist publish\logs mkdir publish\logs
%NSSM_PATH% set AutoDeployWebhook AppStdout "%PROJECT_DIR%\publish\logs\webhook_stdout.log"
%NSSM_PATH% set AutoDeployWebhook AppStderr "%PROJECT_DIR%\publish\logs\webhook_stderr.log"
%NSSM_PATH% set AutoDeployWebhook Start SERVICE_AUTO_START

:: 启动服务
echo 正在启动服务...
%NSSM_PATH% start AutoDeployWebhook

echo 服务注册完成！
pause 