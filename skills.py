import os
import re
from pathlib import Path


def _is_reparse_point(path):
    """Detect if a path is a Windows junction/symlink (reparse point)."""
    try:
        p = Path(path)
        if p.is_symlink():
            return True
        attrs = os.lstat(str(p))
        if hasattr(attrs, 'st_file_attributes'):
            return bool(attrs.st_file_attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
        return False
    except Exception:
        return False


class SkillManager:
    def __init__(self, skills_dir: Path, config_mgr):
        self.skills_dir = skills_dir
        self.config_mgr = config_mgr

    @staticmethod
    def parse_frontmatter(text):
        m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
        fm = {}
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip().strip('"').strip("'")
        return fm

    def scan_all(self):
        skills = []
        if not self.skills_dir.exists():
            return skills
        cfg = self.config_mgr.load()
        tags_map = cfg.get("tags", {})
        for d in sorted(self.skills_dir.iterdir()):
            if not d.is_dir():
                continue
            skill_md = d / "SKILL.md"
            disabled = d / "SKILL.md.disabled"
            if skill_md.exists():
                enabled = True
                md_path = skill_md
            elif disabled.exists():
                enabled = False
                md_path = disabled
            else:
                continue
            text = md_path.read_text(encoding="utf-8", errors="replace")
            fm = self.parse_frontmatter(text)
            skill_tags = []
            if isinstance(tags_map, dict):
                skill_tags = tags_map.get(d.name, [])
                if isinstance(skill_tags, str):
                    skill_tags = [skill_tags]
            skills.append({
                "name": fm.get("name", d.name),
                "dir": d.name,
                "description": fm.get("description", ""),
                "enabled": enabled,
                "size": md_path.stat().st_size,
                "path": str(md_path),
                "folder": str(d),
                "frontmatter": fm,
                "tags": skill_tags,
            })
        return skills

    def scan_agent_skills_dir(self, skills_dir_path):
        results = []
        p = Path(skills_dir_path)
        if not p.exists():
            return results
        for d in sorted(p.iterdir()):
            if d.name.startswith('.'):
                continue
            # Case 1: directory skill — <name>/SKILL.md
            if d.is_dir():
                skill_md = d / "SKILL.md"
                disabled = d / "SKILL.md.disabled"
                is_link = _is_reparse_point(d)
                if skill_md.exists():
                    text = skill_md.read_text(encoding="utf-8", errors="replace")
                    fm = self.parse_frontmatter(text)
                    results.append({
                        "name": fm.get("name", d.name), "dir": d.name,
                        "description": fm.get("description", ""), "enabled": True,
                        "path": str(skill_md), "folder": str(d),
                        "type": "dir", "is_link": is_link,
                    })
                elif disabled.exists():
                    text = disabled.read_text(encoding="utf-8", errors="replace")
                    fm = self.parse_frontmatter(text)
                    results.append({
                        "name": fm.get("name", d.name), "dir": d.name,
                        "description": fm.get("description", ""), "enabled": False,
                        "path": str(disabled), "folder": str(d),
                        "type": "dir", "is_link": is_link,
                    })
            # Case 2: single-file skill — <name>.md (with frontmatter)
            elif d.is_file() and d.suffix.lower() == ".md":
                text = d.read_text(encoding="utf-8", errors="replace")
                if text.startswith("---"):
                    fm = self.parse_frontmatter(text)
                    if "name" in fm or "description" in fm:
                        stem = d.stem
                        results.append({
                            "name": fm.get("name", stem), "dir": stem,
                            "description": fm.get("description", ""), "enabled": True,
                            "path": str(d), "folder": str(d.parent),
                            "type": "file",
                        })
        return results
