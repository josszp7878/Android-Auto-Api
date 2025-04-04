@echo off

echo Deploy Tool Launcher

:menu
cls
echo Please select an option:
echo 1. One-click Deploy
echo 2. Update Code
echo 3. Update Dependencies
echo 4. Exit

set /p choice=Enter option (1, 3-4): 

if "%choice%"=="1" goto oneKey
if "%choice%"=="2" goto updateCode
if "%choice%"=="3" goto updateRequirements
if "%choice%"=="4" goto end

echo Invalid option, please try again
timeout /t 2 >nul
goto menu

:oneKey
cd publish
call update_code.bat
call update_requirements.bat
cd ..
echo 你可以执行./server 启动服务器
goto menu

:updateCode
cd publish
call update_code.bat
cd ..
goto menu

:updateRequirements
cd publish
call update_requirements.bat
cd ..
goto menu

:end
echo Operation completed 