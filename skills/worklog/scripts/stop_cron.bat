@echo off
chcp 65001 >nul
echo ========================================
echo Stopping Worklog Cron Scheduler
echo ========================================
echo.

taskkill /F /IM python.exe /FI "WINDOWTITLE eq python*" 2>nul

if %errorlevel% equ 0 (
    echo Scheduler stopped successfully
) else (
    echo No running scheduler process found
)

echo.
pause
