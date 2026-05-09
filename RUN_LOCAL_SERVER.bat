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
echo Main Chatbot: http://localhost:8000/chatbot
echo Admin Dashboard: http://localhost:8000/admin
echo Login Page: http://localhost:8000/login
echo.
IF EXIST "..\.venv\Scripts\python.exe" (
    echo Launching with Virtual Environment Python...
    ..\.venv\Scripts\python api_server.py
) ELSE (
    echo Launching with Global Python...
    python api_server.py
)
pause
