@echo off
echo Starting SVSU Intelligent Bot Local Server...
echo.
cd BOT_BACKEND
IF EXIST "..\.venv\Scripts\activate" (
    echo Activating Virtual Environment...
    call "..\.venv\Scripts\activate"
) ELSE (
    echo WARNING: Virtual Environment (.venv) not found. Scanning for python dependencies...
)
echo Server is launching on: http://localhost:8000
echo Admin Panel: http://localhost:8000/admin_panel/admin_login.html
echo Chatbot UI: http://localhost:8000/admin_panel/chatbot.html
echo.
IF EXIST "..\.venv\Scripts\python.exe" (
    echo Launching with Virtual Environment Python...
    ..\.venv\Scripts\python api_server.py
) ELSE (
    echo Launching with Global Python...
    python api_server.py
)
pause
