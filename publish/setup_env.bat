@echo off
echo 正在设置项目环境...

:: 切换到项目根目录
cd ..

:: 检查Python版本
python --version 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 未检测到Python，请先安装Python 3.x
    pause
    exit /b
)

:: 安装依赖
echo 正在安装项目依赖...
pip install -r requirements.txt

:: 检查安装结果
if %ERRORLEVEL% NEQ 0 (
    echo 依赖安装失败，请检查网络连接或requirements.txt文件
) else (
    echo 依赖安装成功！
)

:: 显示Python环境信息
echo.
echo 环境信息:
python -c "import sys; print('Python版本:', sys.version)"
echo.
echo 设置完成，现在可以运行项目了

pause 