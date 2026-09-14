# 一键配置 Cron for Windows (无需管理员权限)
# 下载、安装、配置 Worklog 自动任务
#
# Usage (in Windows PowerShell, NOT Git Bash):
#   powershell -ExecutionPolicy Bypass -File scripts/setup_cron.ps1
#
# This script:
#   1. Downloads cron-win32 (portable, no admin needed)
#   2. Creates crontab with 8:00 AM trigger (Tue-Sat)
#   3. Starts cron process in background
#   4. Logs output to logs/cron_fill.log

$CronUrl = "https://github.com/mtrebi/cron-win32/releases/download/v1.0/cron-win32.zip"
$CronDir = "D:\06_Project\worklog\tools\cron"
$CronExe = "$CronDir\cron.exe"
$CrontabFile = "$CronDir\crontab"
$LogDir = "D:\06_Project\worklog\logs"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuring Cron for Windows (Unattended)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Create directory
Write-Host "[1/4] Creating directory..." -ForegroundColor Yellow
if (-not (Test-Path $CronDir)) {
    New-Item -ItemType Directory -Path $CronDir -Force | Out-Null
    Write-Host "  Created: $CronDir" -ForegroundColor Green
} else {
    Write-Host "  Directory exists" -ForegroundColor Gray
}

# 2. Download cron.exe (if missing)
if (-not (Test-Path $CronExe)) {
    Write-Host "[2/4] Downloading cron.exe..." -ForegroundColor Yellow
    $ZipFile = "$CronDir\cron.zip"
    
    try {
        Invoke-WebRequest -Uri $CronUrl -OutFile $ZipFile -UseBasicParsing
        Write-Host "  Downloaded, extracting..." -ForegroundColor Gray
        Expand-Archive -Path $ZipFile -DestinationPath $CronDir -Force
        Remove-Item $ZipFile -Force
        Write-Host "  cron.exe ready" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Download failed: $_" -ForegroundColor Red
        Write-Host "Manual download: https://github.com/mtrebi/cron-win32/releases" -ForegroundColor Yellow
        Write-Host "Extract to: $CronDir" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "[2/4] cron.exe exists" -ForegroundColor Green
}

# 3. Create Crontab config
Write-Host "[3/4] Configuring Crontab..." -ForegroundColor Yellow

# Worklog Auto Fill: Tue-Sat 8:00 AM (fill previous day)
# Format: minute hour day month weekday command
# Weekday: 0=Sun, 1=Mon, 2=Tue, ..., 6=Sat
$CrontabContent = @"
# Worklog Auto Fill
# Format: minute hour day month weekday command
# Run at 8:00 AM on Tue, Wed, Thu, Fri, Sat (fill previous day)
0 8 * * 2-6 cd /d D:\06_Project\worklog && python -m scripts.playwright.scheduled_run fill >> $LogDir\cron_fill.log 2>&1
"@

Set-Content -Path $CrontabFile -Value $CrontabContent -Encoding ASCII
Write-Host "  Crontab saved: $CrontabFile" -ForegroundColor Green
Write-Host "  Schedule: Tue-Sat 8:00 AM (auto-fill previous day)" -ForegroundColor Gray

# 4. Start Cron process (user-level, hidden)
Write-Host "[4/4] Starting Cron process..." -ForegroundColor Yellow

# Stop old process
Get-Process -Name cron -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$CronDir*" } | Stop-Process -Force -ErrorAction SilentlyContinue

# Start new process (hidden window)
Start-Process -FilePath $CronExe -ArgumentList "-f $CrontabFile" -WindowStyle Hidden -WorkingDirectory $CronDir

Start-Sleep -Seconds 2

# Verify
$CronProc = Get-Process -Name cron -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$CronDir*" }
if ($CronProc) {
    Write-Host "  Cron started (PID: $($CronProc.Id))" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Setup Complete! Cron running in background" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Monitoring:" -ForegroundColor Yellow
    Write-Host "  - Log file: $LogDir\cron_fill.log"
    Write-Host "  - Next run: Tue-Sat 8:00 AM"
    Write-Host "  - Manual test: $CronExe -t $CrontabFile"
    Write-Host ""
    Write-Host "Stop Cron: Stop-Process -Name cron -Force" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "[ERROR] Failed to start Cron process" -ForegroundColor Red
    exit 1
}
