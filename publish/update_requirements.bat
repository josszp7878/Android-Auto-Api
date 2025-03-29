@echo off
echo 正在生成项目依赖文件...

:: 切换到项目根目录
cd ..

:: 安装pipreqs工具
pip install pipreqs

:: 使用pipreqs自动生成依赖
pipreqs . --force

echo requirements.txt文件已生成完成！
pause 