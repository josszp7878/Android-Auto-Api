@echo off
chcp 65001 >nul
echo updating the code...

:: to the root directory
cd ..

:: check if git is installed
git --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Git not detected, please install Git first
    pause
    exit /b
)

:: save the current directory
set CURRENT_DIR=%cd%
:: set the fixed repository address
set REPO_URL=https://github.com/josszp7878/Android-Auto-Api.git
echo detected Git repository, pulling the latest code...
:: pull the latest code
git pull

:: check the result
if %ERRORLEVEL% NEQ 0 (
    echo update failed, please check the network connection or Git configuration
) else (
    echo update successfully!
)


echo update completed!
pause 