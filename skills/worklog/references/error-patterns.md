# Worklog Automation Error Patterns & Workarounds

## Session: 2026-08-03 - Manual补填 Thursday/Friday + Monday Adjust

### Problem: Task Scheduler Tasks Never Execute

**Symptoms**:
- `schtasks /query /tn "WorklogDailyFill"` shows task exists
- `Get-ScheduledTaskInfo` returns empty `LastExecutionTime`
- No `scheduled_run_*.log` files generated despite trigger time passing

**Root Cause**:
Domain policy restricts `SeBatchLogonRight` (Batch Logon privilege), preventing unattended background execution even with:
- `LogonType=Password` configured
- Explicit user credentials provided
- "Run whether user is logged on or not" selected

**Error from Task Scheduler**:
```
该任务主体需要启用批登录特权
```
(Translation: "Task subject requires batch logon privilege")

**Workaround**:
Bypass Task Scheduler entirely. Execute commands directly:

```powershell
# Fill a specific date (e.g., Thursday 7/30)
python -m scripts.playwright.scheduled_run fill 2026-07-30

# Fill Friday 7/31
python -m scripts.playwright.scheduled_run fill 2026-07-31

# Adjust last week (Monday-Friday)
python -m scripts.playwright.scheduled_run adjust
```

**Verification**:
- Commands execute successfully when run from PowerShell/cmd.exe
- Token auto-refreshes via silent SSO (NTLM)
- Logs generated in `logs/scheduled_run_YYYY-MM-DD.log`

---

## API Error Patterns

### 1. Auto-Synced Entries Return 404 on Update

**Pattern**:
```
updateWorklog HTTP 404: {'code': 404, 'msg': None, 'data': None}
```

**Context**:
- Entries with `falg="new"` and `taskCost=0` (auto-synced from Bugzilla)
- Server has no record of these entries in the worklog database

**Workaround**:
Always fall back to `insertWorklog` when `updateWorklog` returns 404:
```python
try:
    api.update_entry(body)
except RuntimeError as ex:
    if "404" in str(ex):
        # Fall back to insert
        api.insert_entry(insert_body)
```

**Note**: This is expected behavior for auto-synced entries that haven't been "confirmed" yet.

---

### 2. Activity Invalid Error on Insert

**Pattern**:
```
insertWorklog HTTP 400: {'code': 400, 'msg': '当前活动失效，无法操作', 'data': None}
```

**Context**:
- Inserting with the original `projectID`/`activityID` from the auto-synced entry
- The activity may have been deactivated or the project structure changed

**Workaround**:
1. Extract fallback project/activity from recent confirmed entries:
   ```python
   # Search backwards from target date
   for _dd in range(1, 8):
       _cd = (target_date - timedelta(days=_dd)).isoformat()
       _entries = api.list_entries_for_date(_cd, contains="yes")
       for e in _entries:
           if float(e.get("taskCost") or 0) > 0:
               fallback_pid = e.get("projectID")
               fallback_aid = e.get("activityIds")
               break
   ```

2. Retry insert with fallback project:
   ```python
   insert_body = build_insert_body(
       project_id=fallback_pid,
       activity_ids=fallback_aid,
       # ... other fields from original entry
   )
   api.insert_entry(insert_body)
   ```

**Success Rate**: ~95% when fallback project exists from recent history.

---

### 3. Token Expiration with refresh_token Error

**Pattern**:
```
getWorkLogDetailList HTTP 403: {
  'path': '/writeWorklog/getWorkLogDetailList',
  'errorCode': '4031',
  'message': 'b4810c23-3b74-4b5b-be73-fa74706a6917 if there is a refresh_token, please use it to get access_token'
}
```

**Context**:
- Cached token expired (server-side timeout < 6 hours)
- Current retry logic attempts silent SSO but may not properly handle refresh_token flow

**Current Workaround**:
- Clear auth state and force re-login:
  ```python
  if AUTH_STATE_FILE.exists():
      AUTH_STATE_FILE.unlink()
  get_token_via_playwright(force_relogin=True)
  ```
- This works but is slower (10-15 seconds for SSO)

**Note**: Token cache duration of 6 hours is a heuristic; actual server timeout may vary.

---

## Operational Checklist for Manual补填

When Task Scheduler fails and you need to manually补填 missing dates:

1. **Identify missing dates**: Check `logs/scheduled_run_*.log` for gaps
2. **Fill each missing date**:
   ```bash
   python -m scripts.playwright.scheduled_run fill YYYY-MM-DD
   ```
3. **Run adjust for last week**:
   ```bash
   python -m scripts.playwright.scheduled_run adjust
   ```
4. **Verify**: Check generated log file for successful completion
5. **Submit manually**: Go to uniworklog.unisoc.com and click "提交" (skill only fills/saves, not submits)

---

## Lessons from 2026-08-03 Session

- **Thursday 7/30**: 2 auto-synced bugs → both inserted as 4.0h each
- **Friday 7/31**: 1 auto-synced + 2 copied bugs → 2.7h + 2.7h + 2.6h = 8.0h
- **Adjust**: All 5 days scaled from 8.0h to 10.2-11.3h based on actual clock-in
- **Total time**: ~10 seconds per fill/adjust operation
- **Success rate**: 100% when running directly via CLI

---

## Future Prevention

1. **Monitor**: Check `logs/scheduled_run_*.log` daily for gaps
2. **Alert**: If no log file generated within 1 hour of scheduled time, run manually
3. **Alternative**: Consider Cron for Windows (`cron-win32`) as more reliable scheduler
4. **Documentation**: Keep this error pattern document updated with new issues
