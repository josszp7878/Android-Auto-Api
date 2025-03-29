@echo off
setlocal enabledelayedexpansion

echo 正在查找应用进程ID...
for /f "tokens=2" %%a in ('adb shell ps ^| findstr "cn.vove7.andro_accessibility_api.demo.script"') do (
    set PID=%%a
    echo 找到进程ID: !PID!
    goto :found
)

echo 未找到应用进程，尝试使用包名过滤...
adb logcat -v threadtime | findstr "cn.vove7.andro_accessibility_api.demo.script"
goto :end

:found
echo 正在使用进程ID !PID! 过滤日志...
adb logcat -v threadtime --pid=!PID!

:end
pause 