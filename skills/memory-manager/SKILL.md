---
name: memory-manager
description: Manage Claude Code auto-memory files — list, preview, search, edit, delete, and Web UI across all projects.
---

# Memory Manager

Manages Claude Code's auto-memory files (`~/.claude/projects/*/memory/*.md`). Works through the CLI tool at `~/.claude/tools/memory-manager.py`.

## Tool path

```
python ~/.claude/tools/memory-manager.py <command> [args...]
```

On Windows under MobaXterm where `~` may resolve incorrectly, use the full path:
```
python C:/Users/<user>/.claude/tools/memory-manager.py <command> [args...]
```

## Available commands

| Command | Description |
|---------|-------------|
| `list` | List all memories across all projects |
| `list --project <name>` | Filter by project directory |
| `list --type <type>` | Filter by type (user/feedback/project/reference) |
| `preview <N>` | Show full content of memory #N |
| `search <text>` | Search memory names + descriptions + content |
| `edit <N> --name <new>` | Update `name:` field in frontmatter (writes `.bak`) |
| `edit <N> --desc "TEXT"` | Update `description:` field in frontmatter (writes `.bak`) |
| `delete <N>` | Move to trash (`~/.claude/memory-manager/trash/`) |
| `undelete [N]` | Restore trashed memories |
| `web [port]` | Start Web UI (default 8769), auto-opens browser |

## Behavior rules

1. **Always run via Bash tool.** Show the human-readable output to the user.
2. **Preview before delete.** Run `preview <N>` so the user can confirm before `delete <N>`.
3. **Edit always writes `.bak`.** A backup of the memory file is created before any frontmatter mutation.
4. **Delete is soft.** Memories are moved to `~/.claude/memory-manager/trash/` with a `.origin` sidecar file for restoration.
5. **MEMORY.md auto-maintained.** After edit/delete, the project's `MEMORY.md` index is regenerated.
6. **Indexes change after delete/undelete.** Re-run `list` to see updated indices.
7. **Web UI** runs on port 8769. Filter by project/type, search, and preview memories in a side drawer.