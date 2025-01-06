@echo off
:: 切换到脚本所在目录
@REM cd /d %~dp0

:: 如果有参数，将其作为设备ID传递
cmd /c python server/scripts/CMain.py %1 %2
pause