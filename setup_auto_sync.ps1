# Automation Setup for SVSU Bot
# This script creates a Windows Scheduled Task to run the crawler automatically.

$TaskName = "SVSU_Bot_Daily_Sync"
$ScriptPath = "c:\Users\USER\Desktop\BOT-SVSU\sync_bot.ps1"
$WorkingDirectory = "c:\Users\USER\Desktop\BOT-SVSU"

Write-Host "--- Setting up Auto-Sync for SVSU Bot ---" -ForegroundColor Cyan

# 1. Check if task already exists
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "An automation task named '$TaskName' already exists. Removing it to update..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# 2. Define the action (Run PowerShell with the script path)
# -ExecutionPolicy Bypass ensures the script runs even if locally restricted
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$ScriptPath`"" -WorkingDirectory $WorkingDirectory

# 3. Define the trigger (Daily at 2:00 AM)
$Trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM

# 4. Define settings (Allow start if on battery, stop if it runs too long)
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# 5. Register the task
Register-ScheduledTask -Action $Action -Trigger $Trigger -TaskName $TaskName -Settings $Settings -Description "Automatically crawls SVSU.ac.in and updates the chatbot knowledge base daily."

Write-Host "--- SUCCESS! ---" -ForegroundColor Green
Write-Host "The chatbot will now automatically update itself every day at 2:00 AM." -ForegroundColor White
Write-Host "You can see this task in 'Windows Task Scheduler'." -ForegroundColor Gray
