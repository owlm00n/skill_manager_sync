# Worklog Cron Scheduler - Troubleshooting Guide

## Problem: Scheduler Won't Start

### Symptom
```
FileNotFoundError: [Errno 2] No such file or directory: 'D:\\06_Project\\logs\\cron_scheduler.log'
```

### Root Cause
The `logs/` directory doesn't exist.

### Solution
```bash
mkdir logs
python -m scripts.cron_scheduler
```

**Prevention**: The scheduler now auto-creates the `logs/` directory.

---

## Problem: Crontab Not Found

### Symptom
```
错误：crontab 文件不存在：D:\06_Project\tools\cron\crontab
```

### Root Cause
- File path resolution error
- Working directory is wrong
- File was moved or deleted

### Solution
```bash
# Verify file exists
dir tools\cron\crontab

# If missing, restore from template
copy templates\crontab.example tools\cron\crontab

# Check current directory
cd
# Should show: D:\06_Project\worklog
```

### Prevention
Always run from the worklog root directory:
```bash
cd D:\06_Project\worklog
python -m scripts.cron_scheduler
```

---

## Problem: Task Not Triggering

### Symptom
Scheduler runs but never executes the fill command.

### Diagnosis
```bash
# Check scheduler log
tail -100 logs/cron_scheduler.log

# Look for:
# - "加载 1 个任务" (loaded tasks)
# - "触发任务" (triggered task) - if missing, check time/weekday
```

### Common Causes

#### 1. Time mismatch
- Crontab: `0 8 * * 2-6` means 8:00 AM on Tue-Sat
- If it's Monday or 8:01 AM, it won't trigger

#### 2. Weekday conversion error
- Crontab: 0=Sun, 1=Mon, 2=Tue, ...
- Python: 0=Mon, 1=Tue, 2=Wed, ...
- Conversion: `cron_weekday = (py_weekday + 2) % 7`

**Debug**:
```python
from datetime import date
d = date.today()
py_wd = d.weekday()  # 0=Mon
cron_wd = (py_wd + 2) % 7  # Convert to Crontab
print(f"Today: {d}, Python weekday: {py_wd}, Crontab weekday: {cron_wd}")
```

#### 3. Command syntax error
- Crontab command must be valid shell command
- Use `cd /d` for Windows path change
- Escape special characters

**Test manually**:
```bash
cd /d D:\06_Project\worklog && python -m scripts.playwright.scheduled_run fill
```

---

## Problem: Command Executes but Fails

### Symptom
Scheduler triggers, but `logs/cron_fill.log` shows errors.

### Diagnosis
```bash
tail -100 logs/cron_fill.log
```

### Common Causes

#### 1. Token expired
```
HTTP 403: Unauthorized
```
**Fix**: The scheduler auto-retries with re-login. Check `logs/scheduled_run_*.log` for details.

#### 2. No source bugs
```
DataError: No Bugzilla entries found in last 14 days
```
**Fix**: Ensure there are Bugzilla entries to copy. Run `inspect` first.

#### 3. Network timeout
```
ConnectionError: Max retries exceeded
```
**Fix**: Check network. The scheduler has exponential backoff retry.

---

## Problem: Scheduler Stops After Reboot

### Symptom
Scheduler works but stops after system restart.

### Root Cause
The scheduler is a **user process**, not a Windows service. It stops when the user logs out or the system reboots.

### Solution

#### Option A: Startup Folder (Recommended)
1. Create `start_cron.vbs`:
   ```vbs
   Set objShell = CreateObject("WScript.Shell")
   objShell.Run "cmd /c cd /d D:\06_Project\worklog && python -m scripts.cron_scheduler", 0
   ```
2. Copy to:
   ```powershell
   Copy-Item start_cron.vbs "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\"
   ```

#### Option B: Task Scheduler (Logon Trigger)
1. Open `taskschd.msc`
2. Create Basic Task
3. Trigger: **When I log on**
4. Action: Start `python.exe`, Argument: `-m scripts.cron_scheduler`
5. **Important**: Do NOT use "At Startup" (requires admin) or "Run whether logged on" (requires `SeBatchLogonRight`)

---

## Problem: Encoding Issues (Chinese Characters)

### Symptom
```
UnicodeDecodeError: 'utf-8' codec can't decode byte...
```

### Root Cause
Crontab file or command contains non-UTF-8 characters.

### Solution
1. Save `tools/cron/crontab` as UTF-8 (no BOM)
2. Avoid Chinese in the **command** part (comments are OK)
3. Use English variable names

**Check encoding**:
```powershell
Get-Content tools\cron\crontab | Format-List *
```

---

## Problem: Multiple Instances Running

### Symptom
Multiple `cron_scheduler` processes in `tasklist`.

### Root Cause
Scheduler was started multiple times.

### Solution
```bash
# Stop all
taskkill /F /IM python.exe /FI "WINDOWTITLE eq python*"

# Or use the stop script
.\stop_cron.bat

# Restart cleanly
.\start_cron.bat
```

### Prevention
The `start_cron.bat` script checks for existing instances and stops them before starting a new one.

---

## Problem: Logs Not Growing

### Symptom
`logs/cron_scheduler.log` is empty or not updating.

### Diagnosis
```bash
# Check if scheduler is running
tasklist | findstr "python.*cron_scheduler"

# Check permissions
icacls logs
```

### Solutions

#### 1. Scheduler not running
Start it: `python -m scripts.cron_scheduler`

#### 2. Permission denied
```bash
# Take ownership
takeown /F logs /R
icacls logs /grant Users:F /T
```

#### 3. File locked
Close any text editors viewing the log file.

---

## Quick Diagnostic Commands

```bash
# 1. Check process
tasklist | findstr "python.*cron_scheduler"

# 2. Check crontab
type tools\cron\crontab

# 3. Check logs
tail -50 logs\cron_scheduler.log
tail -50 logs\cron_fill.log

# 4. Test command manually
cd D:\06_Project\worklog && python -m scripts.playwright.scheduled_run fill 2026-08-03

# 5. Verify Python environment
python --version
where python

# 6. Check working directory
cd
```

---

## Contact/Support

If issues persist:
1. Check `logs/cron_scheduler.log` for full error trace
2. Run diagnostic commands above
3. Review `references/python-cron-scheduler.md` for architecture details
4. Temporarily run in foreground to see real-time output:
   ```bash
   python -m scripts.cron_scheduler
   ```
