---
name: worklog
description: "Automate daily worklog filling and weekly adjustment on uniworklog.unisoc.com via API-first architecture. Use when user asks to 'fill worklog', 'adjust worklog', '补填工时', '调整工时', or references uniworklog.unisoc.com."
---

# Worklog Skill

Automate worklog filling and adjustment on `uniworklog.unisoc.com`. API-first approach: Playwright only for SSO login, all read/write via HTTP API.

## Architecture

```
Task Scheduler (daily_fill.xml / monday_adjust.xml)
  └─ scheduled_run.py (main entry, token auto-refresh, retry)
       ├─ worklog_api.py (API client: CRUD, token management)
       ├─ worklog_fill_api.py (fill logic: auto-sync entries, copy from history)
       ├─ worklog_adjust_api.py (adjust logic: match clock-in hours)
       ├─ auth_helper.py (SSO silent login via NTLM)
       ├─ time_allocator.py (time distribution engine)
       └─ paths.py (centralized path constants)
```

## Two-Phase Workflow

### Phase 1: Daily Fill — `scheduled_run.py fill [date]`

Fill one day's worklog with 8H baseline. Runs Tuesday-Saturday 8:00 (fills previous day).

**Priority logic:**
1. **Auto-synced entries** (falg="new", 0h): Update in place. If `updateWorklog` returns 404 (no ID), fall back to insert.
2. **Copy from history**: If auto-synced entries < 2 or single entry > 7h, copy Bugzilla entries from recent 14 days.
3. **Already filled**: Skip if total >= 7.5h.

**Key constraints:**
- Single entry cannot exceed 7h (auto-split if needed)
- Max 2 Bugzilla entries copied from history
- Activity type: `客户支持~客户问题~客户问题` for customer project bugs
- Auto-synced entries (flag: 'new') cannot be deleted

### Phase 2: Monday Adjust — `scheduled_run.py adjust`

Adjust last week's entries to match actual clock-in hours. Runs Monday 1:07.

**Logic:**
1. Read clock-in hours (manHour) for each weekday
2. If manHour < 0 (unsettled), skip that day
3. Scale Bugzilla entry times proportionally to match clock-in
4. Update entries via API

## Usage

```bash
# Fill yesterday (default, for scheduled tasks)
python -m scripts.playwright.scheduled_run fill

# Fill specific date
python -m scripts.playwright.scheduled_run fill 2026-07-28

# Adjust last week (Monday-Friday)
python -m scripts.playwright.scheduled_run adjust

# Inspect a date (read-only, safe)
python -m scripts.playwright.worklog_api inspect 2026-07-28

# Force re-login (clear token cache)
python -c "from scripts.playwright.worklog_api import get_token_via_playwright; get_token_via_playwright(force_relogin=True)"
```

## Token Management

- **Cache duration**: 6 hours (not 72h — token expires faster)
- **Cache file**: `logs/.api_token.json`
- **Auth state**: `logs/.auth_state.json` (Playwright storage_state)
- **Re-login**: Clears auth_state before SSO to avoid stale session
- **Silent SSO**: NTLM/Negotiate flags, no password needed (uses Windows session credentials)

## Task Scheduler Configuration (Windows Native)

### Daily Fill (`config/daily_fill.xml`)
- **Trigger**: Tuesday-Saturday 8:00 AM
- **Command**: `python.exe -m scripts.playwright.scheduled_run fill`
- **Logon Mode**: Interactive/Background (runs when locked)
- **Battery**: No restrictions (runs on battery)

### Monday Adjust (`config/monday_adjust.xml`)
- **Trigger**: Monday 1:07 AM
- **Command**: `python.exe -m scripts.playwright.scheduled_run adjust`
- **Logon Mode**: Interactive/Background
- **Battery**: No restrictions

### Import tasks (requires Windows password)
```powershell
schtasks /create /tn "\WorklogDailyFill" /xml "config\daily_fill.xml" /ru "DOMAIN\username" /rp "password" /f
schtasks /create /tn "\WorklogMondayAdjust" /xml "config\monday_adjust.xml" /ru "DOMAIN\username" /rp "password" /f
```

> **⚠️ Domain Policy Warning**: If `schtasks` fails with "requires batch logon privilege" (`SeBatchLogonRight`), the user lacks domain permissions for unattended background tasks. **Use the Cron fallback instead** (see below).

## Unattended Execution Fallback (No Admin Privileges)

If Windows Task Scheduler fails due to domain restrictions (common in corporate environments), use **Cron for Windows** (`cron-win32`). It runs as a standard user process, requires **no admin rights**, and works even when locked.

### CRITICAL: Task Scheduler May Appear Created But Never Execute
**Symptom**: `schtasks /query` shows task exists, but `LastExecutionTime` is empty and no logs are generated.
**Cause**: Domain policy restricts `SeBatchLogonRight` privilege, preventing background execution even with `LogonType=Password`.
**Immediate workaround**: Bypass Task Scheduler entirely and run commands directly:
```bash
# Fill specific date
python -m scripts.playwright.scheduled_run fill 2026-07-30

# Adjust last week
## Unattended Execution Fallback (No Admin Privileges)

If Windows Task Scheduler fails due to domain restrictions (common in corporate environments), use **Python Cron Scheduler** instead of `cron-win32`. It runs as a standard Python process, requires **no admin rights**, works even when locked, and avoids downloading external binaries (which may fail in restricted networks).

### Why Python Cron?
- **No external dependencies**: Pure Python, no `cron.exe` download needed.
- **Domain-safe**: Runs as a user process, bypasses `SeBatchLogonRight` restrictions.
- **Self-healing**: Auto-creates logs directory, handles encoding issues.
- **Easy debugging**: Full Python stack traces in logs.

### Setup (One-time)
1. **Ensure crontab exists**: `tools/cron/crontab`
   ```cron
   # minute hour day month weekday command
   0 8 * * 2-6 cd /d D:\06_Project\worklog && python -m scripts.playwright.scheduled_run fill >> logs/cron_fill.log 2>&1
   ```
   (Weekdays: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat)

2. **Start the scheduler**:
   ```bash
   # Method A: Manual (test)
   python -m scripts.cron_scheduler

   # Method B: Background (production)
   Start-Process python -ArgumentList "-m", "scripts.cron_scheduler" -WindowStyle Hidden

   # Method C: Startup script
   .\start_cron.bat
   ```

### ⚠️ Critical Limitation: No "Catch-Up" Logic
The Python Cron Scheduler **only triggers at the exact configured time** (e.g., 08:00). If the computer is off, the user is logged out, or the scheduler process is not running at that exact minute:
- **The task will NOT execute automatically**.
- **It does NOT "catch up" missed runs** (unlike Windows Task Scheduler which can be configured to "run missed tasks").
- **Solution**: Manually run `python -m scripts.playwright.scheduled_run fill [date]` for any missed dates.

### ⚠️ Do NOT Fill Future Dates
- **Never** run `fill` for a date that hasn't happened yet (e.g., filling Thursday on Wednesday).
- The system assumes logs are filled for **past dates only**.
- Filling future dates creates invalid data that may conflict with actual work entries.
- **Correct workflow**: Wait until the next day (e.g., fill Tuesday on Wednesday morning).

### Verification
- **Check process**: `tasklist | findstr "python.*cron_scheduler"`
- **Check logs**: `tail -50 logs/cron_scheduler.log` (scheduler) or `logs/cron_fill.log` (execution)
- **Stop manually**: `taskkill /F /IM python.exe /FI "WINDOWTITLE eq python*"` or `.\stop_cron.bat`

### Configuration
Edit `tools/cron/crontab` to adjust timing. The scheduler checks every 60 seconds.

### ⚠️ Critical Pitfalls
- **Path resolution**: `scripts/cron_scheduler.py` uses `Path(__file__).resolve().parent.parent` to find the worklog root. Do not move the script without updating this logic.
- **Encoding**: Crontab must be ASCII or UTF-8. Avoid Chinese characters in the command line part.
- **Logs directory**: The scheduler auto-creates `logs/` if missing, but ensure it exists before first run.
- **Startup**: The scheduler is a **user process**. If the PC reboots, it stops. Use `start_cron.vbs` in the Startup folder or a "Logon" Task Scheduler entry (not "At Startup") to auto-restart.

## API Key Parameters (reverse-engineered from archive/worklog_app.js)

- `weekId` = ISO week number (e.g. 27), NOT the weekId from getWorkLogTotalWorkDayWeekCost (407)
- `yearMonth` = month of the week's **Monday** (e.g. 2026-07-02's week Monday is in June → yearMonth=2026-06)
- `contains` = `'yes'` (unsubmitted week, includes all) or `'no'` (submitted week)
- `activityIds` format: `"roleID_actID1_actID2_actID3"`, split by `_` into 4 int fields
- Bug ID extracted from `taskDesc` prefix when `refBugId` is null

## Key Files

| File | Purpose |
|------|---------|
| `scripts/playwright/scheduled_run.py` | **Main entry** — fill/adjust with retry, token refresh |
| `scripts/playwright/worklog_api.py` | API client — token, CRUD, inspect |
| `scripts/playwright/worklog_fill_api.py` | Fill logic — find entries to copy, auto-sync handling |
| `scripts/playwright/worklog_adjust_api.py` | Adjust logic — match clock-in hours |
| `scripts/playwright/auth_helper.py` | SSO silent login via NTLM |
| `scripts/utils/time_allocator.py` | Time distribution engine (fill + adjust modes) |
| `scripts/utils/paths.py` | Centralized path constants (single source of truth) |
| `scripts/utils/config_loader.py` | Config/endpoints loader |
| `scripts/cron_scheduler.py` | **Python Cron** — unattended execution fallback (no admin rights) |
| `tools/cron/crontab` | Cron scheduler configuration |
| `scripts/start_cron.bat` | One-click start for Python Cron |
| `scripts/stop_cron.bat` | One-click stop for Python Cron |
| `config/daily_fill.xml` | Task Scheduler config for daily fill (if domain permits) |
| `config/monday_adjust.xml` | Task Scheduler config for Monday adjust (if domain permits) |
| `config/endpoints.json` | API endpoint definitions |
| `references/error-patterns.md` | **Error patterns & workarounds** — Task Scheduler failures, API errors, operational checklist |
| `references/scheduler-troubleshooting.md` | **Scheduler troubleshooting** — step-by-step diagnosis for missed runs, token issues, future date prevention |

## Error Handling
## Error Handling

- **Token expired (403)**: Auto re-login via silent SSO, retry up to 3 times
- **Update 404**: Auto-synced entries have no ID → fall back to insert
- **Activity invalid (400)**: Use fallback project/activity from recent confirmed entries
- **Network error**: Exponential backoff retry (2^n seconds)
- **Cron scheduler not running**: Check `logs/cron_scheduler.log`, restart with `.\start_cron.bat`
- **Crontab parse error**: Ensure file is UTF-8, valid cron syntax (see `templates/crontab.example`)
- **Logs directory missing**: Auto-created by scheduler, or manually `mkdir logs`

## Lessons Learned

- Token cache 72h is too long — server expires tokens faster, use 6h
- `silent_login` must clear `auth_state` before re-login to avoid stale session reuse
- Element-UI form interaction fails (Vue reactivity not triggered by JS `.value` set) — use API instead
- `agent_run.py` (AI proxy) has 1800s timeout — use `scheduled_run.py` directly for reliability
- Task Scheduler `DisallowStartIfOnBatteries=true` blocks execution on laptops — set to false
- `LogonType` must be `Password` (not `InteractiveToken`) for locked-screen execution
- Auto-synced 0h entries (falg="new") return 404 on updateWorklog — always fall back to insert
- **Critical**: Task must be explicitly created with `schtasks /create` — XML alone does not register the task. Common pitfall: assuming task exists after XML creation. Always verify with `schtasks /query /tn <name>` before relying on automation.
- **Critical**: Python Cron Scheduler does NOT catch up missed runs. If the scheduler is not running at the exact trigger time (e.g., 08:00), the task is skipped permanently. Always manually fill missed dates.
- **Critical**: Never fill future dates. Only fill dates that have already passed. Filling future dates (e.g., filling Thursday on Wednesday) creates invalid data.
- **Critical**: If task is missing, use `scripts/create_task.bat` or `scripts/create_task.ps1` to register it with proper credentials. Manual Task Scheduler GUI setup requires: "Run whether user is logged on or not" + "Run with highest privileges" + explicit user credential.
- **Critical (Domain Environments)**: Windows Task Scheduler often fails with `SeBatchLogonRight` errors. Use **Python Cron Scheduler** (`scripts/cron_scheduler.py`) instead — it requires no admin rights, works when locked, and avoids external binary downloads. See "Unattended Execution Fallback" section.
- **Critical (Cron Startup)**: Python Cron is a **user process**, not a service. It stops on reboot. Configure auto-start via Startup folder (`start_cron.vbs`) or "Logon" Task Scheduler trigger (not "At Startup").
- **Critical (Domain Environment)**: Windows Task Scheduler tasks may fail with error code `267011` (or `LastRunTime` stuck at `1999-11-30`) due to domain policy restrictions on `SeBatchLogonRight` (Batch Logon privilege). Even if the task shows `Ready` state, it may never actually execute.
  - **Symptom**: `Get-ScheduledTaskInfo` shows `LastRunTime` as `1999.11.30` or `LastTaskResult` as non-zero (e.g., `267011`).
  - **Impact**: Automated daily fill/adjust tasks will silently fail in corporate domain environments.
  - **Workaround**: Do not rely on Task Scheduler. Use **Cron for Windows** (`cron-win32`) instead, which runs as a standard user process and bypasses domain restrictions.
  - **Fallback Command**: Always have a manual fallback: `python -m scripts.playwright.scheduled_run fill <date>` or `adjust`.
  - **Verification**: Before assuming automation works, check `logs/scheduled_run_YYYY-MM-DD.log` exists and contains recent entries. If missing, assume automation failed and run manually.
