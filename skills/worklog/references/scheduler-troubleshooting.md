# Worklog Scheduler Troubleshooting Checklist

## Symptom: Logs Not Filled Automatically

### Step 1: Check Current Date & Time
```bash
python -c "import datetime; print('Now:', datetime.datetime.now().strftime('%Y-%m-%d %A %H:%M'))"
```
- If it's **before 08:00**, the task hasn't triggered yet.
- If it's **after 08:00**, the scheduler may have missed the window.

### Step 2: Verify Scheduler is Running
```bash
# Check if cron_scheduler process is running
ps aux | grep cron_scheduler
```
- **No process found?** → Scheduler is not running. Start it:
  ```bash
  python -m scripts.cron_scheduler
  ```
- **Process found?** → Check logs for errors.

### Step 3: Check Scheduler Logs
```bash
tail -n 50 logs/cron_scheduler.log
```
Look for:
- `"触发任务：..."` → Task was triggered
- `"执行成功"` → Command executed successfully
- `"执行失败"` or `"错误"` → Something went wrong

### Step 4: Manually Fill Missed Dates
If the scheduler missed a run, **it will NOT auto-catch-up**. Fill manually:
```bash
# Fill a specific missed date
python -m scripts.playwright.scheduled_run fill 2026-08-04

# Verify
python -m scripts.playwright.worklog_api inspect 2026-08-04
```

### Step 5: Verify Token is Valid
```bash
python -c "from scripts.playwright.worklog_api import get_cached_token; print(get_cached_token())"
```
- If token is expired (>6h), force re-login:
  ```bash
  python -c "from scripts.playwright.worklog_api import get_token_via_playwright; get_token_via_playwright(force_relogin=True)"
  ```

---

## Symptom: Filled Wrong Dates (Future Dates)

### Problem
Accidentally filled a future date (e.g., filled Thursday on Wednesday).

### Solution
1. **Do NOT delete entries manually** via the web UI (may cause API conflicts).
2. **Contact system admin** to remove invalid future entries if necessary.
3. **Prevention**: Always verify `datetime.now()` before running `fill [date]`.

---

## Symptom: Token Expired (HTTP 403)

### Error
```
RuntimeError: getWorkLogDetailList HTTP 403: ... if there is a refresh_token, please use it to get access_token
```

### Solution
```bash
# Force re-login
python -c "from scripts.playwright.worklog_api import get_token_via_playwright; get_token_via_playwright(force_relogin=True)"

# Retry the operation
python -m scripts.playwright.scheduled_run fill 2026-08-04
```

---

## Symptom: Auto-Synced Entries Return 404

### Error
```
[3503860] update failed (updateWorklog HTTP 404), falling back to insert
```

### Explanation
This is **expected behavior** for `flag="new"` entries with 0h. The script automatically falls back to `insert`. No action needed.

---

## Prevention: Best Practices

1. **Keep scheduler running**: Start `cron_scheduler` at login and keep it running.
2. **Check logs daily**: Review `logs/cron_scheduler.log` each morning.
3. **Manual fallback**: If scheduler is down, manually fill the previous day before 10:00 AM.
4. **Never fill future dates**: Only fill dates that have already passed.
5. **Token refresh**: If you see HTTP 403, refresh token immediately.

---

## Quick Commands Reference

| Action | Command |
|--------|---------|
| Start scheduler | `python -m scripts.cron_scheduler` |
| Stop scheduler | `Ctrl+C` (in terminal) or `taskkill /F /PID <pid>` |
| Fill specific date | `python -m scripts.playwright.scheduled_run fill 2026-08-04` |
| Adjust last week | `python -m scripts.playwright.scheduled_run adjust` |
| Inspect a date | `python -m scripts.playwright.worklog_api inspect 2026-08-04` |
| Refresh token | `python -c "from scripts.playwright.worklog_api import get_token_via_playwright; get_token_via_playwright(force_relogin=True)"` |
| Check scheduler logs | `tail -n 50 logs/cron_scheduler.log` |
| Check fill logs | `tail -n 50 logs/scheduled_run_*.log` |
