@echo off

echo Deploy Tool Launcher

:menu
cls
echo Please select an option:
echo 1. One-click Deploy
echo 2. Create Virtual Environment
echo 3. Update Code
echo 4. Update Dependencies
echo 5. Start Server
echo 6. Start Webhook Service
echo 7. Register Windows Service
echo 8. Exit

set /p choice=Enter option (1-7): 

if "%choice%"=="1" goto one_key
if "%choice%"=="2" goto create_venv
if "%choice%"=="3" goto update_code
if "%choice%"=="4" goto update_requirements
if "%choice%"=="5" goto start_server
if "%choice%"=="6" goto start_webhook
if "%choice%"=="7" goto register_service
if "%choice%"=="8" goto end

echo Invalid option, please try again
timeout /t 2 >nul
goto menu

:one_key
cd publish
call install_all.bat
cd ..
goto menu

:create_venv
cd publish
call create_venv.bat
cd ..
goto menu

:update_code
cd publish
call update_code.bat
cd ..
goto menu

:update_requirements
cd publish
call update_requirements.bat
cd ..
goto menu

:start_server
cd publish
call start_server.bat
cd ..
goto menu

:start_webhook
cd publish
call start_webhook.bat
cd ..
goto menu

:register_service
cd publish
call register_service.bat
cd ..
goto menu

:end
echo Operation completed 