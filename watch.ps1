<#
.SYNOPSIS
    Skills Sync Manager - File watcher for auto-sync
.DESCRIPTION
    Monitors the skills/ directory for changes and automatically triggers sync.ps1.
    Uses FileSystemWatcher with debounce to avoid excessive syncs.
.PARAMETER WatchPath
    Custom path to watch. Defaults to ./skills/
.PARAMETER DebounceSeconds
    Seconds to wait after last change before triggering sync. Default: 2
.PARAMETER Mode
    Sync mode override: symlink | copy
.EXAMPLE
    .\watch.ps1
    .\watch.ps1 -DebounceSeconds 5
    .\watch.ps1 -Mode copy
#>

param(
    [string]$WatchPath,
    [int]$DebounceSeconds = 2,
    [ValidateSet("symlink", "copy")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SyncScript = Join-Path $ScriptDir "sync.ps1"

if (-not $WatchPath) {
    $WatchPath = Join-Path $ScriptDir "skills"
}

if (-not (Test-Path $WatchPath)) {
    Write-Host "ERROR: Watch path not found: $WatchPath" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Skills Sync Watcher" -ForegroundColor Cyan
Write-Host "  Watching: $WatchPath" -ForegroundColor Cyan
Write-Host "  Debounce: ${DebounceSeconds}s" -ForegroundColor Cyan
if ($Mode) {
    Write-Host "  Mode: $Mode" -ForegroundColor Cyan
}
Write-Host "  Press Ctrl+C to stop" -ForegroundColor DarkGray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $WatchPath
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $false
$watcher.NotifyFilter = [System.IO.NotifyFilters]::FileName -bor
                         [System.IO.NotifyFilters]::DirectoryName -bor
                         [System.IO.NotifyFilters]::LastWrite -bor
                         [System.IO.NotifyFilters]::Size

# Debounce state
$script:lastSync = [datetime]::MinValue
$script:pendingSync = $false
$script:syncLock = $false

function Invoke-DebouncedSync {
    $now = Get-Date
    $elapsed = ($now - $script:lastSync).TotalSeconds

    if ($elapsed -ge $DebounceSeconds -and -not $script:syncLock) {
        $script:syncLock = $true
        $timestamp = Get-Date -Format "HH:mm:ss"
        Write-Host "  [$timestamp] Change detected, syncing..." -ForegroundColor Yellow

        try {
            $syncArgs = @()
            if ($Mode) { $syncArgs += @("-Mode", $Mode) }

            if ($syncArgs.Count -gt 0) {
                & $SyncScript @syncArgs
            } else {
                & $SyncScript
            }
            $script:lastSync = Get-Date
            Write-Host "  [$timestamp] Sync complete" -ForegroundColor Green
        } catch {
            Write-Host "  [$timestamp] Sync error: $_" -ForegroundColor Red
        }

        $script:syncLock = $false
    } else {
        $script:pendingSync = $true
    }
}

try {
    # Main loop using WaitForChanged with timeout
    while ($true) {
        $result = $watcher.WaitForChanged(
            [System.IO.WatcherChangeTypes]::All,
            1000  # 1 second timeout for responsiveness
        )

        if (-not $result.TimedOut) {
            $changeType = $result.ChangeType
            $name = $result.Name

            # Skip __pycache__ and .git
            if ($name -match '__pycache__|\.git' -or $name -match '\.pyc$') {
                continue
            }

            $timestamp = Get-Date -Format "HH:mm:ss"
            Write-Host "  [$timestamp] $changeType : $name" -ForegroundColor DarkGray

            # Trigger debounced sync
            Invoke-DebouncedSync
        }

        # Check if there's a pending sync after debounce period
        if ($script:pendingSync) {
            $elapsed = ((Get-Date) - $script:lastSync).TotalSeconds
            if ($elapsed -ge $DebounceSeconds -and -not $script:syncLock) {
                $script:pendingSync = $false
                Invoke-DebouncedSync
            }
        }
    }
} finally {
    $watcher.EnableRaisingEvents = $false
    $watcher.Dispose()
    Write-Host ""
    Write-Host "Watcher stopped." -ForegroundColor Yellow
}
