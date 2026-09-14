@echo off
chcp 65001 >nul
title Worklog Cron Scheduler

echo ========================================
echo Worklog Cron Scheduler
echo ========================================
echo.

REM 1. Check if already running
tasklist | findstr /I "python" | findstr /I "cron_scheduler" >nul
if %errorlevel% equ 0 (
    echo [WARNING] Cron Scheduler already running
    for /f "tokens=2" %%a in ('tasklist ^| findstr /I "python" ^| findstr /I "cron_scheduler"') do echo   PID: %%a
    echo.
    echo Press any key to stop and restart, or Ctrl+C to exit
    pause >nul
    
    taskkill /F /IM python.exe /FI "WINDOWTITLE eq python*" 2>nul
    echo Stopped old process
    timeout /t 2 /nobreak >nul
)

REM 2. Ensure logs directory exists
if not exist "logs" mkdir logs

REM 3. Start the scheduler
echo Starting Cron Scheduler...
start "python" cmd /c "cd /d D:\06_Project\worklog && python -m scripts.cron_scheduler"

timeout /t 2 /nobreak >nul

REM 4. Verify startup
tasklist | findstr /I "python" | findstr /I "cron_scheduler" >nul
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo SUCCESS! Scheduler is running
    echo ========================================
    echo.
    echo Process:
    for /f "tokens=1,2" %%a in ('tasklist ^| findstr /I "python" ^| findstr /I "cron_scheduler"') do (
        echo   %%a: %%b
    )
    echo.
    echo Logs:
    echo   - Scheduler: logs\cron_scheduler.log
    echo   - Execution: logs\cron_fill.log
    echo.
    echo Next execution: Tue-Sat 8:00 AM
    echo.
    echo Press any key to exit (scheduler continues in background)
    pause >nul
) else (
    echo.
    echo [ERROR] Failed to start scheduler
    echo Check logs\cron_scheduler.log for details
    pause
    exit /b 1
)
