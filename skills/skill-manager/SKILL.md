---
name: skill-manager
description: Manage Claude Code skills — list, preview, enable/disable, edit metadata, and soft-delete. Triggers on /skill-manager or when user asks about CC skills.
---

# Skill Manager

Manages Claude Code skills across user-level (`~/.claude/skills/`), project-level (`<cwd>/.claude/skills/`), and plugin marketplace (`~/.claude/plugins/marketplaces/*/`) locations. Works through the CLI tool bundled with this skill.

## Tool path

The tool is bundled in this skill's `assets/` directory. Use the path relative to this SKILL.md:
```
python <this-skill-dir>/assets/skill-manager.py <command> [args...]
```

For Claude Code global skills, the default path is:
```
python ~/.claude/skills/skill-manager/assets/skill-manager.py <command> [args...]
```

On Windows, use the full path:
```
python C:/Users/<user>/.claude/skills/skill-manager/assets/skill-manager.py <command> [args...]
```

## Available commands

| Command | Description |
|---------|-------------|
| `list` | List all skills (user / project / plugin) sorted by source then name |
| `list --verbose` / `-v` | Include full file path + extra frontmatter fields |
| `list --trash` | List soft-deleted skills in trash |
| `list --source=user\|project\|plugin` | Filter by source |
| `preview <N>` | Print full SKILL.md content of skill #N |
| `enable <N>` | Rename `SKILL.md.disabled` → `SKILL.md` |
| `disable <N>` | Rename `SKILL.md` → `SKILL.md.disabled` |
| `edit <N> --name NAME` | Update `name:` field in frontmatter (writes `.bak`) |
| `edit <N> --desc "TEXT"` | Update `description:` field in frontmatter (writes `.bak`) |
| `delete <N>` | Move skill folder to `~/.claude/skill-manager/trash/` |
| `undelete` | Restore ALL trashed skills |
| `undelete <N>` | Restore specific trashed skill |
| `web [port]` | Start Web UI (default 8766), auto-opens browser |

## Behavior rules

1. **Always run via Bash tool.** Show the human-readable output to the user.
2. **Preview before delete.** Run `preview <N>` so the user can confirm before `delete <N>`.
3. **Disable is non-destructive.** It only renames `SKILL.md` ↔ `SKILL.md.disabled`. CC won't load disabled skills, but the folder is preserved.
4. **Edit always writes `.bak`.** A backup of `SKILL.md` is created before any frontmatter mutation. Only top-level scalar keys (`name`, `description`, etc.) are touched.
5. **Indices change.** After any enable/disable/delete/undelete, the index numbering shifts. Re-run `list` to see updated indices.
6. **Restart CC after enable/disable** for changes to take effect in the running session.
7. **Web UI** runs on port 8766 (session-manager uses 8765). Toggle, edit, delete, and restore all work from the UI.
