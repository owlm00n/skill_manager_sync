---
name: permission-manager
description: Manage Claude Code permissions — query, add/remove allow/deny/ask rules, apply presets, detect conflicts across user/project/local settings layers.
---

# Permission Manager

Manages Claude Code permission rules across three settings layers: user (`~/.claude/settings.json`), project (`<cwd>/.claude/settings.json`), and local (`<cwd>/.claude/settings.local.json`). Works through the CLI tool at `~/.claude/tools/permission-manager.py`.

## Tool path

```
python ~/.claude/tools/permission-manager.py <command> [args...]
```

On Windows under MobaXterm where `~` may resolve incorrectly, use the full path:
```
python C:/Users/<user>/.claude/tools/permission-manager.py <command> [args...]
```

## Available commands

| Command | Description |
|---------|-------------|
| `list [--scope=user\|project\|local\|all]` | List all permission rules across scopes |
| `show <scope>` | Show full settings.json for a scope |
| `add <bucket> "<rule>" [--scope=user]` | Add a rule to allow/deny/ask |
| `remove <bucket> "<rule>" [--scope=user]` | Remove a rule from allow/deny/ask |
| `move <bucket> "<rule>" --from=user --to=project` | Move a rule between scopes |
| `set-mode <mode> [--scope=user]` | Set defaultMode (bypassPermissions/askPermissions/restricted) |
| `preset list` | List built-in presets |
| `preset apply <name> [--scope=user]` | Apply a preset to a scope |
| `preset save-from-scope <name> [--scope=all]` | Save current scope rules as a new preset |
| `preset export <name>` | Export a preset as JSON for pasting into settings.json |
| `check` | Run conflict detection across all scopes |
| `web [port]` | Start Web UI (default 8768), auto-opens browser |

## Built-in presets

| Preset | Description |
|--------|-------------|
| `safe-readonly` | Read-only tools (Read/Glob/Grep), safe Bash, deny destructive commands |
| `dev-nodejs` | Allow npm/npx/pnpm/yarn/node/tsc |
| `dev-python` | Allow python/pip/pytest/uv/ruff |
| `git-full` | Allow all git commands, deny force-push and reset --hard |
| `mcp-open` | Allow all MCP tools |
| `danger-bypass` | Full Bash/Read/Write/Edit access (use with caution!) |

## Behavior rules

1. **Always run via Bash tool.** Show the human-readable output to the user.
2. **Every write creates `.bak`.** A timestamped backup is created before any mutation, keeping max 5.
3. **Presets are additive.** Applying a preset adds new rules; it never removes existing ones.
4. **Conflict detection.** Use `check` before/after changes to catch duplicates and allow-deny overlaps.
5. **Scope priority.** local > project > user. Rules in higher-priority scopes override lower ones.
