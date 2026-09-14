import os
import json
from pathlib import Path
from skills import SkillManager
from utils import run_ps


def _is_reparse_point(path):
    """Detect if a path is a Windows junction/symlink (reparse point)."""
    try:
        if path.is_symlink():
            return True
        attrs = os.lstat(str(path))
        if hasattr(attrs, 'st_file_attributes'):
            return bool(attrs.st_file_attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
        return False
    except Exception:
        return False


class WorkspaceScanner:
    def __init__(self, script_dir: Path):
        self.script_dir = script_dir

    def scan_native(self, scan_path, max_depth=3):
        agent_dirs = {
            ".claude": {"tool": "claude_code", "label": "Claude Code", "skills_sub": "skills"},
            ".qoder": {"tool": "qoder", "label": "Qoder", "skills_sub": "skills"},
            ".cursor": {"tool": "cursor", "label": "Cursor", "skills_sub": "skills"},
            ".codex": {"tool": "codex", "label": "Codex", "skills_sub": "skills"},
            ".copilot": {"tool": "copilot", "label": "GitHub Copilot", "skills_sub": "skills"},
            ".gemini": {"tool": "gemini_cli", "label": "Gemini CLI", "skills_sub": "skills"},
            ".trae": {"tool": "trae", "label": "TRAE IDE", "skills_sub": "skills"},
            ".trae-cn": {"tool": "trae_cn", "label": "TRAE CN", "skills_sub": "skills"},
            ".grok": {"tool": "grok", "label": "Grok", "skills_sub": "skills"},
            ".continue": {"tool": "continue", "label": "Continue", "skills_sub": "skills"},
            ".cline": {"tool": "cline", "label": "Cline", "skills_sub": "skills"},
            ".hermes": {"tool": "hermes", "label": "Hermes", "skills_sub": "skills"},
        }
        results = []
        root = Path(scan_path)
        if not root.exists():
            return {"projects": [], "workspaces": []}
        for dirpath, dirnames, filenames in os.walk(str(root)):
            depth = len(Path(dirpath).relative_to(root).parts)
            if depth >= max_depth:
                dirnames.clear()
                continue
            dp = Path(dirpath)
            for agent_dir_name, agent_info in agent_dirs.items():
                agent_path = dp / agent_dir_name
                if agent_path.exists() and agent_path.is_dir():
                    skills_path = agent_path / agent_info["skills_sub"]
                    skills_list = []
                    if skills_path.exists():
                        for entry in sorted(skills_path.iterdir()):
                            if entry.name.startswith('.'):
                                continue
                            # Case 1: directory skill — <name>/SKILL.md
                            if entry.is_dir():
                                skill_md = entry / "SKILL.md"
                                disabled = entry / "SKILL.md.disabled"
                                # Detect if this skill dir is a junction/symlink (linked to central)
                                is_link = _is_reparse_point(entry)
                                if skill_md.exists():
                                    text = skill_md.read_text(encoding="utf-8", errors="replace")
                                    fm = SkillManager.parse_frontmatter(text)
                                    skills_list.append({
                                        "name": entry.name,
                                        "display_name": fm.get("name", entry.name),
                                        "description": fm.get("description", ""),
                                        "enabled": True,
                                        "type": "dir",
                                        "path": str(skill_md),
                                        "is_link": is_link,
                                    })
                                elif disabled.exists():
                                    text = disabled.read_text(encoding="utf-8", errors="replace")
                                    fm = SkillManager.parse_frontmatter(text)
                                    skills_list.append({
                                        "name": entry.name,
                                        "display_name": fm.get("name", entry.name),
                                        "description": fm.get("description", ""),
                                        "enabled": False,
                                        "type": "dir",
                                        "path": str(disabled),
                                        "is_link": is_link,
                                    })
                            # Case 2: single-file skill — <name>.md (with frontmatter)
                            elif entry.is_file() and entry.suffix.lower() == ".md":
                                text = entry.read_text(encoding="utf-8", errors="replace")
                                # Only treat as skill if it has frontmatter
                                if text.startswith("---"):
                                    fm = SkillManager.parse_frontmatter(text)
                                    if "name" in fm or "description" in fm:
                                        stem = entry.stem
                                        skills_list.append({
                                            "name": stem,
                                            "display_name": fm.get("name", stem),
                                            "description": fm.get("description", ""),
                                            "enabled": True,
                                            "type": "file",
                                            "path": str(entry),
                                        })
                    results.append({
                        "project_path": str(dp),
                        "project_name": dp.name,
                        "agent_dir": agent_dir_name,
                        "tool": agent_info["tool"],
                        "label": agent_info["label"],
                        "skills_path": str(skills_path) if skills_path.exists() else "",
                        "skills": skills_list,
                        "skill_count": len(skills_list),
                    })
        return {"projects": [], "workspaces": results}

    def scan_projects(self, scan_path, max_depth=3):
        r = run_ps("scan-agents.ps1", self.script_dir, ["-ScanPath", scan_path, "-MaxDepth", str(max_depth), "-Json"])
        if r["ok"]:
            try:
                text = r["stdout"]
                json_start = text.find("{")
                if json_start >= 0:
                    text = text[json_start:]
                return json.loads(text)
            except:
                return {"projects": [], "global_agents": []}
        return {"projects": [], "global_agents": [], "error": r["stderr"]}
