@echo off
setlocal

:: 切换到脚本所在目录
@REM cd /d %~dp0

:: 如果有参数，将其作为设备ID传递
python scripts/main.py %1 %2

:: 如果Python脚本出错，暂停显示错误信息
if errorlevel 1 pause

endlocal 