# Windows Task Scheduler Limitations in Domain Environments

## Problem: "Batch Logon Privilege" Error

When attempting to create an unattended scheduled task via `schtasks` with `LogonType=Password`, users may encounter:

```
WARNING: 任务已注册，但无法启动。该任务主体需要启用批登录特权。
```

**Root Cause**: The user account lacks the `SeBatchLogonRight` privilege, which is required for tasks to run in the background without an interactive login session. This is a common restriction in corporate domain environments where IT policies limit background task execution to prevent unauthorized services.

## Why `schtasks` Fails

Windows Task Scheduler has two primary logon types:
- **`InteractiveToken`**: Requires user to be logged in and unlocked. Task runs in user session.
- **`Password`**: Runs in background regardless of login state. **Requires `SeBatchLogonRight`**.

In domain environments:
- `SeBatchLogonRight` is typically granted only to administrators or specific service accounts.
- Regular users cannot create tasks that run when locked/unlogged.
- Even with correct credentials, the task will fail to execute at trigger time.

## Solution: Cron for Windows (`cron-win32`)

### Why Cron Works
- Runs as a **standard user process** (not a Windows service).
- No special privileges required.
- Works even when the screen is locked (as long as the user session is active).
- Portable: no installation, no admin rights.

### Architecture
```
cron.exe (background process)
  └─ Reads crontab
       └─ Executes: python -m scripts.playwright.scheduled_run fill
            └─ Writes to: logs/cron_fill.log
```

### Setup Steps
1. Run `scripts/setup_cron.ps1` in **Windows PowerShell** (not Git Bash).
2. Script downloads `cron.exe` and creates `crontab`.
3. Cron process starts automatically and runs until system shutdown.

### Crontab Format
```
# minute hour day month weekday command
0 8 * * 2-6 cd /d D:\06_Project\worklog && python -m scripts.playwright.scheduled_run fill >> logs/cron_fill.log 2>&1
```

**Weekday mapping**:
- 0 = Sunday
- 1 = Monday
- 2 = Tuesday
- 3 = Wednesday
- 4 = Thursday
- 5 = Friday
- 6 = Saturday

For **Tue-Sat at 8:00 AM**: `0 8 * * 2-6`

### Monitoring
- **Check process**: `Get-Process cron`
- **Check logs**: `logs/cron_fill.log`
- **Stop manually**: `Stop-Process -Name cron -Force`

### Persistence
- Cron runs as a user process. If the system reboots, the process stops.
- To auto-start on login, add `cron.exe` to Windows Startup folder or use a login script.
- Alternatively, re-run `setup_cron.ps1` after each reboot (quick, idempotent).

## Alternative: Request Domain Privilege (Not Recommended)

If you have access to domain IT support:
1. Request `SeBatchLogonRight` for your user account.
2. Wait for Group Policy propagation (can take hours).
3. Re-create the scheduled task.

**Drawbacks**:
- Requires IT approval (often denied for security).
- Policy changes are slow.
- Still relies on Windows Task Scheduler (complex, error-prone).

**Recommendation**: Use Cron for Windows. It's simpler, faster, and works out-of-the-box.
