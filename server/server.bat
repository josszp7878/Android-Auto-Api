@echo off
echo Starting servers...

:: start socketio server
start "SocketIO Server" cmd /k python MyServer.py socketio

:: start file server
start "File Server" cmd /k python MyServer.py fileserver

:: start command console
start "Command Console" cmd /k python MyServer.py console

echo All servers started. 