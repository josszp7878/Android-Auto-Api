@echo off
setlocal

:: 切换到脚本所在目录
@REM cd /d %~dp0

:: 检查是否有命令行参数
if "%~1"=="" (
    :: 如果没有参数，使用默认设备ID
    python scripts/main.py
) else (
    :: 如果有参数，将其作为设备ID传递
    python scripts/main.py %1
)

:: 如果Python脚本出错，暂停显示错误信息
if errorlevel 1 pause

endlocal 