---
name: cc-hub
description: Unified CC Tools Hub dashboard — session manager, skill manager, prompt manager, API switcher, and more. Triggers on /cc-hub.
---

# CC Tools Hub

Unified dashboard for all Claude Code tools. Embeds Session Manager (port 8765), Skill Manager (port 8766), Skills Sync (port 8780), and more via iframe, with planned slots for Prompt Manager and API Switcher.

## Tool path

```
python ~/.claude/tools/cc-hub.py <command> [args...]
```

On Windows under MobaXterm where `~` may resolve incorrectly, use the full path:
```
python C:/Users/<user>/.claude/tools/cc-hub.py <command> [args...]
```

## Available commands

| Command | Description |
|---------|-------------|
| `start [port]` | Start the Hub web server (default 8767), auto-launches ready modules |
| `stop` | Stop the Hub and all child processes |
| `restart [port]` | Stop all processes then start fresh (stop + start in one command) |
| `status` | Print module status table with online/offline indicators |

## Web UI

The Hub dashboard is a dark tech-themed single-page app at `http://127.0.0.1:8767/`.

- **Welcome grid**: Cards for all modules (Session Manager, Skill Manager, Prompt Manager, API Switcher) with status badges
- **Sidebar mode**: After clicking a module, left sidebar nav with iframe embed for ready modules, placeholder pages for planned modules
- **Health polling**: Every 5 seconds, the UI polls `/api/modules` to update live connection indicators
- **Auto-start**: On startup, the Hub checks each ready module's port and auto-launches any that aren't already running

## Modules

| Module | Port | Status |
|--------|------|--------|
| Session Manager | 8765 | Ready |
| Skill Manager | 8766 | Ready |
| Permission Manager | 8768 | Ready |
| Memory Manager | 8769 | Ready |
| Hook Manager | 8770 | Ready |
| Agent Manager | 8771 | Ready |
| Skills Sync | 8780 | Ready |
| Prompt Manager | -- | Planned |
| API Switcher | -- | Planned |
