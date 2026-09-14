# Windows Task Scheduler Domain Environment Failure

## Symptom

Windows Task Scheduler tasks (e.g., `WorklogDailyFill`, `WorklogMondayAdjust`) appear to be configured correctly but **never execute**.

### Diagnostic Evidence

```powershell
Get-ScheduledTaskInfo -TaskName 'WorklogDailyFill'

LastRunTime        : 1999.11.30 0:00:00  ← Never executed (default value)
LastTaskResult     : 267011              ← Error code (failure)
NextRunTime        : 2026.8.5 8:00:00    ← Scheduled for future
State              : Ready               ← Misleading: looks OK
```

- **LastRunTime = 1999.11.30**: The task has **never successfully run**. This is the default "never run" timestamp.
- **LastTaskResult = 267011**: Generic error code indicating the task failed to start (often permission-related).
- **State = Ready**: Misleading; the task is configured but cannot execute due to domain restrictions.

## Root Cause

### Domain Policy Restriction: `SeBatchLogonRight`

Corporate domain environments often restrict the **Batch Logon Right** (`SeBatchLogonRight`) for standard users. This privilege is required for tasks to run in the background (even when the user is logged in).

**Why it fails**:
- Task Scheduler attempts to launch the task as a background process.
- Domain policy blocks this due to missing `SeBatchLogonRight`.
- The task silently fails or returns error `267011`.
- No log file is generated (e.g., `logs/scheduled_run_YYYY-MM-DD.log` is missing).

### Common Misconfigurations That Exacerbate the Issue

1. **LogonType = InteractiveToken**: Intended to run when user is logged in, but still requires batch logon privilege in some domain policies.
2. **LogonType = Password**: Requires storing credentials, which may be blocked by Group Policy.
3. **Run whether user is logged on or not**: Requires higher privileges and often fails in domain environments.
4. **Hidden = true**: Makes debugging harder; task errors are not visible.

## Impact

- **Daily Fill**: Missing worklog entries for previous day (e.g., Monday's log not filled on Tuesday).
- **Monday Adjust**: Last week's hours not adjusted to match actual clock-in.
- **Silent Failure**: No error notification; user must manually check logs or notice missing entries.

## Solution: Use Cron for Windows (Recommended)

Cron for Windows (`cron-win32`) runs as a **standard user process**, bypassing domain restrictions on Task Scheduler.

### Setup

1. **Run the setup script in PowerShell** (not Git Bash):
   ```powershell
   cd D:\06_Project\worklog
   powershell -ExecutionPolicy Bypass -File scripts/setup_cron.ps1
   ```

2. **Verify the cron process is running**:
   ```powershell
   Get-Process cron
   ```

3. **Check logs**:
   ```powershell
   cat logs/cron_fill.log
   ```

4. **Stop manually if needed**:
   ```powershell
   Stop-Process -Name cron -Force
   ```

### Configuration

Edit `tools/cron/crontab` to adjust timing:
```cron
# minute hour day month weekday command
0 8 * * 2-6 cd /d D:\06_Project\worklog && python -m scripts.playwright.scheduled_run fill >> logs/cron_fill.log 2>&1
```
- Weekdays: `2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat`
- Adjust as needed (e.g., add Monday if required).

## Fallback: Manual Execution

If automation fails, always have a manual fallback:

```bash
# Fill a specific date (e.g., Monday's log on Tuesday)
cd D:\06_Project\worklog
python -m scripts.playwright.scheduled_run fill 2026-08-03

# Adjust last week's hours
python -m scripts.playwright.scheduled_run adjust
```

## Verification Checklist

Before assuming automation works:

- [ ] Check `logs/scheduled_run_YYYY-MM-DD.log` exists and is recent.
- [ ] Verify `Get-ScheduledTaskInfo` shows `LastRunTime` is **not** `1999.11.30`.
- [ ] Confirm `LastTaskResult` is `0` (success).
- [ ] Manually inspect worklog on `uniworklog.unisoc.com` to confirm entries exist.

## Prevention

1. **Never assume Task Scheduler works** in domain environments without verification.
2. **Prefer Cron for Windows** for unattended tasks.
3. **Set up log monitoring**: If `logs/scheduled_run_*.log` is missing for today, alert the user.
4. **Document the workaround**: Ensure team members know to run commands manually if automation fails.

## Error Code Reference

- **267011 (0x67B11)**: Task failed to start. Common causes:
  - Permission denied (`SeBatchLogonRight` missing).
  - Path or working directory incorrect.
  - Dependency service not running.
  - Domain policy blocking background tasks.

## Related Files

- `config/daily_fill.xml` — Task Scheduler XML (may not work in domain).
- `config/monday_adjust.xml` — Task Scheduler XML (may not work in domain).
- `scripts/setup_cron.ps1` — Cron setup script.
- `tools/cron/crontab` — Cron schedule configuration.
- `logs/cron_fill.log` — Cron execution log.

---
**Last Updated**: 2026-08-04  
**Status**: Active workaround for domain environment restrictions.
