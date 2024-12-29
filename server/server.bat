@echo off
echo Starting servers...

:: start file server
start "File Server" python MyServer.py fileserver
:: start socketio server
start "SocketIO Server" python MyServer.py socketio
:: start command console in new window
cmd /c python MyServer.py console

echo All servers started.