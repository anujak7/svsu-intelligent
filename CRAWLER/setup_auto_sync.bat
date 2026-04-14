@echo off
set SCRIPT_PATH=C:\Users\USER\Desktop\BOT-SVSU\CRAWLER\intelligent_sync.py
set LOG_PATH=C:\Users\USER\Desktop\BOT-SVSU\CRAWLER\sync_log.txt

echo [INFO] Scheduling SVSU Intelligent Sync Task... 🚀
echo.

:: 1. Delete Existing Task if any
schtasks /delete /tn "SVSU_Auto_Sync" /f >nul 2>&1

:: 2. Create New Scheduled Task (Every 1 hour)
:: /SC = Schedule Type (HOURLY)
:: /MO = Modifier (1 hour)
:: /TN = Task Name
:: /TR = Task Run (the command to execute)
schtasks /create /sc hourly /mo 1 /tn "SVSU_Auto_Sync" /tr "python %SCRIPT_PATH%" /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✅ SUCCESS: SVSU Intelligent Auto-Sync has been scheduled!
    echo ==============================================
    echo [RUNS]: Every 1 hour background (Multi-Agent)
    echo [TASK]: SVSU_Auto_Sync
    echo [LOGS]: Check c:\Users\USER\Desktop\BOT-SVSU\CRAWLER\sync_log.txt for results.
    echo ==============================================
    echo.
    echo Running first sync now to verify... 🔄
    python %SCRIPT_PATH% >> %LOG_PATH% 2>&1
    echo ✨ Done! You can close this window now.
) else (
    echo.
    echo ❌ FAILED: Please run this as Administrator!
    pause
)
