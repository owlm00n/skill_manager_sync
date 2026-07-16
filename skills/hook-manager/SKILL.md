---
name: hook-manager
description: Manage Claude Code hooks in settings.json — list, add, remove, and Web UI across all hook types.
---

# Hook Manager

Manages Claude Code hooks configured in `~/.claude/settings.json` under the `"hooks"` key. Works through the CLI tool at `~/.claude/tools/hook-manager.py`.

## Tool path

```
python ~/.claude/tools/hook-manager.py <command> [args...]
```

On Windows under MobaXterm where `~` may resolve incorrectly, use the full path:
```
python C:/Users/<user>/.claude/tools/hook-manager.py <command> [args...]
```

## Available commands

| Command | Description |
|---------|-------------|
| `list` | List all hooks grouped by hook type, with indices |
| `show <type>` | Show detailed JSON config for a specific hook type |
| `add <type> --command "CMD" [--matcher ""] [--timeout 10]` | Add a new command hook to a type |
| `remove <type> <index>` | Remove a hook by its 1-based index within type |
| `web [port]` | Start Web UI on port 8770 (default), auto-opens browser |

## Hook types

- `UserPromptSubmit` — Before user prompt is submitted
- `PreToolUse` — Before a tool is called
- `PostToolUse` — After a tool returns
- `Stop` — On conversation stop
- `Notification` — Background notifications

## Behavior rules

1. **Always run via Bash tool.** Show the human-readable output to the user.
2. **List before remove.** Run `list` first to see indices, then `remove <type> <index>`.
3. **Backups are automatic.** A `.bak-{timestamp}` is created in `~/.claude/` before any mutation.
4. **Web UI** runs on port 8770. Shows all hook types in a sidebar, with add/remove controls.