@echo off
echo 正在更新代码...

:: 切换到项目根目录
cd ..

:: 检查git是否安装
git --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 未检测到Git，请先安装Git
    pause
    exit /b
)

:: 保存当前目录
set CURRENT_DIR=%cd%
:: 设置固定的仓库地址
set REPO_URL=https://github.com/josszp7878/Android-Auto-Api.git

:: 如果存在.git目录，直接拉取；否则初始化并添加远程仓库
if exist .git (
    echo 检测到Git仓库，正在拉取最新代码...
    :: 拉取最新代码
    git pull
) else (
    echo 当前目录不是Git仓库，正在初始化...
    
    :: 初始化Git仓库
    git init
    
    :: 添加远程仓库
    git remote add origin %REPO_URL%
    
    :: 拉取代码
    echo 正在拉取代码...
    git pull origin main
    
    :: 如果main分支拉取失败，尝试master分支
    if %ERRORLEVEL% NEQ 0 (
        echo main分支拉取失败，尝试master分支...
        git pull origin master
    )
)

:: 检查结果
if %ERRORLEVEL% NEQ 0 (
    echo 代码更新失败，请检查网络连接或Git配置
) else (
    echo 代码更新成功！
)

:: 更新依赖
echo 正在更新依赖...
pip install -r requirements.txt

echo 更新完成！
pause 