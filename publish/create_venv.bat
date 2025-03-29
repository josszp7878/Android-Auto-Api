@echo off
echo 正在创建虚拟环境...

:: 切换到项目根目录
cd ..

:: 检查venv模块
python -m venv --help >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 未找到venv模块，请确保使用Python 3.3+
    pause
    exit /b
)

:: 创建虚拟环境
python -m venv venv

:: 激活虚拟环境并安装依赖
echo 正在激活虚拟环境...
call venv\Scripts\activate

echo 正在安装依赖...
pip install -r requirements.txt

:: 检查安装结果
if %ERRORLEVEL% NEQ 0 (
    echo 依赖安装失败，请检查网络连接或requirements.txt文件
) else (
    echo 依赖安装成功！
)

echo.
echo 虚拟环境设置完成！
echo 使用方法:
echo - 激活环境: call venv\Scripts\activate
echo - 退出环境: deactivate

pause 