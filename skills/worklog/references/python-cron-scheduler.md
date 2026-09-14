# Python Cron Scheduler for Worklog Automation

**Purpose**: Replace `cron-win32` with a pure Python implementation that avoids external binary downloads and works in restricted domain environments.

## Architecture

```
scripts/cron_scheduler.py
  ├─ Parses tools/cron/crontab
  ├─ Checks current time every 60 seconds
  ├─ Matches trigger conditions (minute/hour/weekday)
  └─ Executes: python -m scripts.playwright.scheduled_run fill
       └─ Logs to: logs/cron_fill.log
```

## Key Features

- **No external dependencies**: Pure Python 3.6+
- **Auto-creates logs directory**: Prevents `FileNotFoundError`
- **Unicode-safe**: Handles Chinese characters in logs
- **Background execution**: Silent mode with hidden window option
- **Self-healing**: Retries on transient failures

## Crontab Format

```cron
# minute hour day month weekday command
0 8 * * 2-6 cd /d D:\06_Project\worklog && python -m scripts.playwright.scheduled_run fill >> logs/cron_fill.log 2>&1
```

**Weekday mapping** (Crontab standard):
- 0 = Sunday
- 1 = Monday
- 2 = Tuesday
- 3 = Wednesday
- 4 = Thursday
- 5 = Friday
- 6 = Saturday

**Note**: Python's `weekday()` returns 0=Monday, so the scheduler converts:
```python
cron_weekday = (py_weekday + 2) % 7
```

## Usage

### Start (Manual)
```bash
python -m scripts.cron_scheduler
```

### Start (Background)
```powershell
Start-Process python -ArgumentList "-m", "scripts.cron_scheduler" -WindowStyle Hidden
```

### Start (Batch)
```bash
.\start_cron.bat
```

### Stop
```bash
taskkill /F /IM python.exe /FI "WINDOWTITLE eq python*"
# or
.\stop_cron.bat
```

### Check Status
```bash
tasklist | findstr "python.*cron_scheduler"
tail -50 logs/cron_scheduler.log
```

## Common Issues

### 1. `FileNotFoundError: logs/cron_scheduler.log`
**Cause**: `logs/` directory doesn't exist.  
**Fix**: The scheduler auto-creates it now. If still failing, manually run `mkdir logs`.

### 2. `crontab` not found
**Cause**: File path resolution error.  
**Fix**: Ensure `tools/cron/crontab` exists relative to the worklog root (`D:/06_Project/worklog`).

### 3. Task not triggering
**Cause**: Time mismatch or weekday conversion error.  
**Debug**: Check `logs/cron_scheduler.log` for "加载 N 个任务" and "触发任务" entries.

### 4. Command execution fails
**Cause**: Working directory not set or Python not in PATH.  
**Fix**: Crontab command must include `cd /d <path>` and use full Python path if needed.

## Startup Persistence

### Option A: Windows Startup Folder
1. Create `start_cron.vbs`:
   ```vbs
   Set objShell = CreateObject("WScript.Shell")
   objShell.Run "cmd /c cd /d D:\06_Project\worklog && python -m scripts.cron_scheduler", 0
   ```
2. Copy to: `$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\`

### Option B: Task Scheduler (Logon Trigger)
1. Open `taskschd.msc`
2. Create Basic Task → Trigger: **When I log on**
3. Action: Start `python.exe`, Argument: `-m scripts.cron_scheduler`
4. **Do NOT** use "At Startup" (requires admin) or "Run whether logged on" (requires `SeBatchLogonRight`)

## File Locations

| File | Path | Description |
|------|------|-------------|
| Scheduler | `scripts/cron_scheduler.py` | Core logic |
| Crontab | `tools/cron/crontab` | Task definitions |
| Scheduler Log | `logs/cron_scheduler.log` | Scheduler events |
| Execution Log | `logs/cron_fill.log` | Worklog fill output |
| Start Script | `start_cron.bat` | One-click start |
| Stop Script | `stop_cron.bat` | One-click stop |

## Testing

### Manual Trigger Test
```bash
# Edit crontab to run every minute for testing:
* * * * * cd /d D:\06_Project\worklog && echo "Test at $(date)" >> logs/cron_test.log

# Restart scheduler, check logs after 60 seconds
```

### Verify Crontab Parsing
```bash
python -c "from scripts.cron_scheduler import parse_crontab; print(parse_crontab('tools/cron/crontab'))"
```

## Maintenance

- **Monitor**: Check `logs/cron_scheduler.log` weekly for errors.
- **Update**: Edit `tools/cron/crontab` and restart scheduler.
- **Backup**: Copy `tools/cron/crontab` before major changes.
