@echo off
chcp 936
setlocal enabledelayedexpansion

:: 设置源目录和目标目录
set "SOURCE_DIR=%~dp0server\scripts"
set "TARGET_DIR=%~dp0app\src\main\assets\scripts"

:: 创建目标目录(如果不存在)
if not exist "%TARGET_DIR%" (
    echo create target dir: %TARGET_DIR%
    mkdir "%TARGET_DIR%"
)

:: 要复制的核心脚本文件列表
set "CORE_SCRIPTS=CMain.py client.py logger.py tools.py CFileServer.py"

echo.
echo start publish scripts...
echo source dir: %SOURCE_DIR%
echo target dir: %TARGET_DIR%
echo.

:: 清理目标目录中的旧文件
echo clean target dir...
if exist "%TARGET_DIR%\*.py" del /Q "%TARGET_DIR%\*.py"

:: 复制核心脚本文件
for %%f in (%CORE_SCRIPTS%) do (
    if exist "%SOURCE_DIR%\%%f" (
        echo copy: %%f
        copy /Y "%SOURCE_DIR%\%%f" "%TARGET_DIR%\" > nul
        if errorlevel 1 (
            echo error: copy %%f failed
        )
    ) else (
        echo warning: not found file %%f
    )
)

echo.
echo publish scripts done!
echo copied files:
dir /B "%TARGET_DIR%\*.py" 2>nul
