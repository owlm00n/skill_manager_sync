from pathlib import Path


class AgentManager:
    REGISTRY = [
        {"key": "claude_code", "label": "Claude Code", "detect": ".claude", "skills": ".claude/skills"},
        {"key": "qoder", "label": "Qoder", "detect": ".qoder", "skills": ".qoder/skills"},
        {"key": "cursor", "label": "Cursor", "detect": ".cursor", "skills": ".cursor/skills"},
        {"key": "codex", "label": "Codex", "detect": ".codex", "skills": ".codex/skills"},
        {"key": "copilot", "label": "GitHub Copilot", "detect": ".copilot", "skills": ".copilot/skills"},
        {"key": "gemini_cli", "label": "Gemini CLI", "detect": ".gemini", "skills": ".gemini/skills"},
        {"key": "windsurf", "label": "Windsurf", "detect": ".codeium\\windsurf", "skills": ".codeium\\windsurf\\skills"},
        {"key": "trae", "label": "TRAE IDE", "detect": ".trae", "skills": ".trae/skills"},
        {"key": "trae_cn", "label": "TRAE CN", "detect": ".trae-cn", "skills": ".trae-cn/skills"},
        {"key": "grok", "label": "Grok", "detect": ".grok", "skills": ".grok/skills"},
        {"key": "opencode", "label": "OpenCode", "detect": ".config\\opencode", "skills": ".config\\opencode\\skills"},
        {"key": "continue", "label": "Continue", "detect": ".continue", "skills": ".continue/skills"},
        {"key": "deepseek", "label": "DeepSeek", "detect": ".deepseek", "skills": ".deepseek/skills"},
        {"key": "qwen", "label": "Qwen", "detect": ".qwen", "skills": ".qwen/skills"},
        {"key": "amp", "label": "Amp", "detect": ".agents", "skills": ".agents/skills"},
        {"key": "kilo_code", "label": "Kilo Code", "detect": ".kilocode", "skills": ".kilocode/skills"},
        {"key": "roo_code", "label": "Roo Code", "detect": ".roo", "skills": ".roo/skills"},
        {"key": "goose", "label": "Goose", "detect": ".config\\goose", "skills": ".config\\goose\\skills"},
        {"key": "cline", "label": "Cline", "detect": ".cline", "skills": ".cline/skills"},
        {"key": "cc_switch", "label": "CC Switch", "detect": ".cc-switch", "skills": ".cc-switch/skills"},
        {"key": "skills_mgr", "label": "Skills Manager", "detect": ".skills-manager", "skills": ".skills-manager/skills"},
        {"key": "hermes", "label": "Hermes", "detect": ".hermes", "skills": ".hermes/skills"},
        {"key": "droid", "label": "Droid", "detect": ".factory", "skills": ".factory/skills"},
    ]

    def __init__(self, home_dir: Path, skills_dir: Path, config_mgr):
        self.home_dir = home_dir
        self.skills_dir = skills_dir
        self.config_mgr = config_mgr

    def detect_installed(self):
        found = []
        for a in self.REGISTRY:
            detect_dir = self.home_dir / a["detect"]
            if detect_dir.exists():
                skills_dir = self.home_dir / a["skills"]
                count = 0
                synced = []
                if skills_dir.exists():
                    for sd in skills_dir.iterdir():
                        if sd.name.startswith('.'):
                            continue
                        if sd.is_dir() and ((sd / "SKILL.md").exists() or (sd / "SKILL.md.disabled").exists()):
                            count += 1
                            synced.append(sd.name)
                found.append({
                    "key": a["key"], "label": a["label"], "installed": True,
                    "skills_dir": str(skills_dir), "skill_count": count, "synced": synced,
                })
        return found

    def discover_unknown(self, detected_agents):
        detected_dirs = set()
        for a in self.REGISTRY:
            detected_dirs.add(str(self.home_dir / a["detect"]))
        detected_skills_dirs = set(a["skills_dir"] for a in detected_agents)

        discovered = []
        try:
            for item in self.home_dir.iterdir():
                if not item.is_dir() or not item.name.startswith('.'):
                    continue
                if str(item) in detected_dirs:
                    continue
                skills_dir = item / "skills"
                if not skills_dir.exists() or not skills_dir.is_dir():
                    continue
                count = 0
                synced = []
                for sd in skills_dir.iterdir():
                    if sd.name.startswith('.'):
                        continue
                    if sd.is_dir() and ((sd / "SKILL.md").exists() or (sd / "SKILL.md.disabled").exists()):
                        count += 1
                        synced.append(sd.name)
                if count > 0 or skills_dir.exists():
                    key = item.name.lstrip('.')
                    label = key.replace('-', ' ').replace('_', ' ').title()
                    discovered.append({
                        "key": key, "label": label, "installed": True,
                        "skills_dir": str(skills_dir), "skill_count": count, "synced": synced,
                        "auto_discovered": True,
                    })
        except Exception:
            pass
        return discovered

    def get_sync_status(self):
        cfg = self.config_mgr.load()
        agents_cfg = cfg.get("agents", {})
        results = []
        for name, acfg in agents_cfg.items():
            if not isinstance(acfg, dict):
                continue
            agent_path = acfg.get("path", "")
            tool = acfg.get("tool", "")
            presets = acfg.get("active_presets", [])
            skills_list = acfg.get("skills", [])
            p = Path(agent_path.replace("~", str(self.home_dir)))
            synced, missing = [], []
            if p.exists():
                for sd in sorted(self.skills_dir.iterdir()):
                    if not sd.is_dir(): continue
                    target = p / sd.name
                    if target.exists() or target.is_symlink():
                        synced.append(sd.name)
                    else:
                        missing.append(sd.name)
            results.append({
                "name": name, "tool": tool, "path": agent_path,
                "active_presets": presets, "skills": skills_list,
                "synced": synced, "missing": missing,
                "synced_count": len(synced), "total_count": len(synced) + len(missing),
            })
        return results

    def find_by_key(self, key):
        for a in self.REGISTRY:
            if a["key"] == key:
                return a
        return None

    @staticmethod
    def find_config_by_key(agent_key, agents_cfg):
        if agent_key in agents_cfg:
            return agent_key
        for name, acfg in agents_cfg.items():
            if isinstance(acfg, dict) and acfg.get("tool", "") == agent_key:
                return name
        return None
