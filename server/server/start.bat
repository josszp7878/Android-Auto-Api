@echo off
echo start server...
@REM pip install -r requirements.txt
python run.py
if errorlevel 1 (
    echo Server failed to start
    pause
) 