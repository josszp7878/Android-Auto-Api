@echo off
chcp 65001 >nul
echo 正在生成项目依赖文件...

:: 切换到项目根目录
cd ..
@REM :: 安装pipreqs工具
@REM pip install pipreqs

@REM :: 使用pipreqs自动生成依赖
@REM pipreqs . --force

echo requirements.txt文件已生成完成！
:: update the dependencies
echo installing dependencies...
pip install -r requirements.txt
pause 