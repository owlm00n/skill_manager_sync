---
name: session-manager
description: Manage Claude Code session history — list, preview, rename, delete, backup, and clean test sessions. Triggers on /session-manager or when user asks about CC sessions/resume.
---

# Session Manager

Manages Claude Code session files in `~/.claude/projects/`. Works through the CLI tool at `~/.claude/tools/session-manager.py`.

## Quick Install

Copy the two files into place:

```bash
cp session-manager.py ~/.claude/tools/session-manager.py
mkdir -p ~/.claude/skills/session-manager
cp SKILL.md ~/.claude/skills/session-manager/SKILL.md
```

Then restart Claude Code or type `/session-manager`.

## Tool path

```
python ~/.claude/tools/session-manager.py <command> [args...]
```

## Available commands

| Command | Description |
|---------|-------------|
| `list` | List all sessions across all projects (sorted by date, newest first) |
| `list --verbose` / `list -v` | List sessions with full UUID and file path |
| `list --trash` | List soft-deleted sessions in trash |
| `list --project=<PROJ>` | List sessions for a specific project only |
| `preview <N>` | Show detailed preview of session #N (user messages, tools, stats) |
| `preview <N> --all` | Show ALL user messages |
| `preview <N> --msgs N` | Show N user messages (default: 5) |
| `rename <N> <"new title">` | Rename session #N — appends `custom-title` entry to JSONL + updates metadata |
| `delete <N>` | Soft-delete session #N → moves to `~/.claude/session-manager/trash/` |
| `undelete` | Restore ALL trashed sessions |
| `undelete <N>` | Restore specific trashed session |
| `clean-test` | Detect "who are you" / test sessions (dry-run, no deletion) |
| `clean-test --force` | Delete all detected test sessions → trash |
| `backup <path>` | Full backup (projects + metadata + trash) to target directory |
| `restore <path>` | Restore from backup directory |
| `tag <N> <tag1,tag2>` | Add tags to session #N |
| `note <N> <"text">` | Add note to session #N |
| `split <N> --at-msg <N>` | Split session at user message #N into two sessions |
| `split <N> --at-uuid <uuid>` | Split session at message with given UUID |
| `web [port]` | Start web-based visual UI (default port 8765), auto-opens browser |
| `resume <N>` | Print `claude --resume <uuid>` command for session #N |
| `resume <N> --copy` | Print and copy the resume command to clipboard |
| `parent` | Print `claude --resume` for the newest session's parent (auto-detects /branch parent) |
| `parent --copy` | Print and copy the parent resume command to clipboard |
| `parent <N>` | Find parent of specific session #N |
| `export <N>` | Export session as Markdown file (`session-<title>.md`) |
| `export <N> --clip` | Export session to clipboard as Markdown |
| `export <N> <file>` | Export session to specified file |
| `running` | List all running Claude sessions (from running.json) |
| `snapshot` | Scan all claude processes, update running.json |
| `launch <path> [uuid]` | Launch claude in new WT tab, optionally with --resume |
| `restore-script` | Generate .bat restore script for all running sessions |
| `resume <N> --force` | Print claude --resume command even if parent lookup fails |
| `kill <PID>` | Force kill a claude session by PID |

## Behavior rules

1. **Always run via Bash tool.** The tool prints human-readable output — show it to the user.
2. **Preview before delete.** When the user asks to delete, run `preview` first so they can confirm.
3. **clean-test is dry-run by default.** Always run without `--force` first. Ask for confirmation before re-running with `--force`.
4. **rename appends `custom-title` to JSONL.** CC natively reads `type: custom-title` entries as session display name. The original `last-prompt` title is preserved and shown as `resume: ...` in the list. A backup (`.jsonl.bak`) is always created.
5. **restore asks first.** Before full restore, tell the user what will be overwritten.
6. **Indices change.** After any delete/undelete, the index numbering shifts. Re-run `list` to show updated indices.
7. **Web UI.** The `web` command starts an HTTP server on 127.0.0.1:8765 and auto-opens the browser. The UI provides sortable table, search/project filters, side-drawer preview, and modal dialogs for rename/backup/clean-test.
8. **Branch parent lookup.** When a session was created with `/branch`, the first JSONL line contains a `forkedFrom.sessionId` field pointing to the parent session UUID. The `parent` command reads this field, locates the parent across all projects, and prints the resume command. When the user says "这个是branch，打开之前的session", "回到上一个session", "open previous session", or similar phrases meaning "this is a branch, resume the parent", the AI should automatically run `python ~/.claude/tools/session-manager.py parent --copy` and execute the printed command.
9. **Running sessions.** The `running` command and Web UI Running tab show live Claude sessions tracked in `~/.claude/session-manager/running.json`. Sessions are auto-registered by SessionStart hook (`session-hook.py`). Dead sessions (PID gone) show with red status dot and "Remove" button instead of "Kill".
10. **Crash recovery.** After a computer restart or crash: (a) start the web UI: `python ~/.claude/tools/session-manager.py web`, (b) open Running tab — all pre-reboot sessions show as Dead, (c) click "New Win" to relaunch each, or use "Restore All" / download .bat script. The `--force` flag on `resume` bypasses parent-lookup for recovery scenarios.
11. **Web UI Running tab.** Provides: Snapshot (process scan), Restore All (batch WT launch), Download Script (.bat file), per-session actions (Resume/New Win/Kill/Remove/Rename). Sessions are grouped by WT window, orphans shown separately.
