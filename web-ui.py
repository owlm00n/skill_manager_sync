#!/usr/bin/env python3
"""Skills Sync Manager - Web UI Server
Python HTTP server with static file serving + REST API.
Port: 8780 (default, was 8770 — moved to avoid conflict with cc-hub Hook Manager)
"""
import http.server
import socketserver
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

from config import ConfigManager
from skills import SkillManager
from agents import AgentManager
from workspace import WorkspaceScanner
from trash import TrashManager
from git_ops import GitManager
from utils import run_ps, open_folder

# ── Paths ──────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = SCRIPT_DIR / "skills"
CONFIG_FILE = SCRIPT_DIR / "config.yaml"
TRASH_FILE = SCRIPT_DIR / ".trash.json"
TRASH_DIR = SCRIPT_DIR / ".trash"
STATIC_DIR = SCRIPT_DIR / "static"
HOME = Path.home()

# ── Module instances ──────────────────────────────────
config_mgr = ConfigManager(CONFIG_FILE)
skill_mgr = SkillManager(SKILLS_DIR, config_mgr)
agent_mgr = AgentManager(HOME, SKILLS_DIR, config_mgr)
workspace_mgr = WorkspaceScanner(SCRIPT_DIR)
trash_mgr = TrashManager(TRASH_FILE, TRASH_DIR)
git_mgr = GitManager(SCRIPT_DIR)

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


def create_link(src, target, mode="junction"):
    """Create a junction (Windows, no admin) or symlink. Returns True on success."""
    src, target = str(src), str(target)
    if mode == "junction":
        # Windows junction via mklink /J (no admin required)
        try:
            r = subprocess.run(["cmd", "/c", "mklink", "/J", target, src],
                               capture_output=True, text=True, timeout=10)
            return r.returncode == 0
        except Exception:
            return False
    else:
        # Symlink (may require admin on Windows)
        try:
            os.symlink(src, target)
            return True
        except (OSError, NotImplementedError):
            return False


# ── HTTP Handler ──────────────────────────────────────
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def _serve_static(self, rel_path):
        fpath = STATIC_DIR / rel_path
        if not fpath.exists() or not fpath.is_file():
            self._json({"error": "not found"}, 404)
            return
        ext = fpath.suffix.lower()
        ctype = MIME_TYPES.get(ext, "application/octet-stream")
        data = fpath.read_bytes()
        mtime = int(fpath.stat().st_mtime)
        etag = f'"{mtime}-{len(data)}"'
        # Conditional request: return 304 if unchanged
        if self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("ETag", etag)
        # Allow caching but always revalidate (so bug fixes propagate)
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(data)

    def _route(self, method):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        parts = path.split("/")

        # ── Static files ──
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            self._serve_static(rel)
            return

        # ── Index ──
        if path == "" or path == "/":
            self._serve_static("index.html")
            return

        # ── API routes ──

        # Settings: get/set sync mode
        if path == "/api/settings" and method == "GET":
            cfg = config_mgr.load()
            self._json({"default_mode": cfg.get("default_mode", "junction")})
            return

        if path == "/api/settings/mode" and method == "POST":
            body = self._read_body()
            mode = body.get("mode", "")
            if mode not in ("symlink", "junction", "copy"):
                self._json({"error": "invalid mode"}, 400)
                return
            config_mgr.update_value("default_mode", mode)
            self._json({"ok": True, "mode": mode})
            return

        # Skills list
        if path == "/api/skills" and method == "GET":
            self._json({"skills": skill_mgr.scan_all(), "skills_dir": str(SKILLS_DIR)})
            return

        # Agents list
        if path == "/api/agents" and method == "GET":
            self._json({"agents": agent_mgr.detect_installed(), "sync_status": agent_mgr.get_sync_status()})
            return

        # Scan for new agents (auto-discover unknown agents)
        if path == "/api/agents/scan" and method == "POST":
            agents = agent_mgr.detect_installed()
            # Auto-discover unknown agents by scanning home directory
            discovered = agent_mgr.discover_unknown(agents)
            if discovered:
                agents.extend(discovered)
            self._json({"agents": agents, "sync_status": agent_mgr.get_sync_status(), "new_count": len(discovered)})
            return

        # Presets list
        if path == "/api/presets" and method == "GET":
            cfg = config_mgr.load()
            presets_cfg = cfg.get("presets", {})
            presets = []
            all_skill_names = [s["dir"] for s in skill_mgr.scan_all()]
            for name, pcfg in presets_cfg.items():
                if not isinstance(pcfg, dict):
                    continue
                skills = pcfg.get("skills", [])
                if skills == ["*"]:
                    skills = all_skill_names
                presets.append({"name": name, "description": pcfg.get("description", ""), "skills": skills})
            self._json({"presets": presets})
            return

        # Tags list
        if path == "/api/tags" and method == "GET":
            cfg = config_mgr.load()
            tags_map = cfg.get("tags", {})
            all_tags = set()
            if isinstance(tags_map, dict):
                for sk, st in tags_map.items():
                    if isinstance(st, list):
                        all_tags.update(st)
                    elif isinstance(st, str):
                        all_tags.add(st)
            self._json({"tags": sorted(all_tags)})
            return

        # Status
        if path == "/api/status" and method == "GET":
            self._json({"skills": skill_mgr.scan_all(), "agents": agent_mgr.detect_installed(), "sync_status": agent_mgr.get_sync_status()})
            return

        # Trash
        if path == "/api/trash" and method == "GET":
            self._json({"items": trash_mgr.load()})
            return

        # ── POST routes ──

        # Sync
        if path == "/api/sync" and method == "POST":
            body = self._read_body()
            args = []
            if body.get("agent"):
                args.extend(["-Agent", body["agent"]])
            if body.get("mode"):
                args.extend(["-Mode", body["mode"]])
            r = run_ps("sync.ps1", SCRIPT_DIR, args if args else None)
            self._json({"ok": r["ok"], "output": r["stdout"], "error": r["stderr"]})
            return

        # Scan
        if path == "/api/scan" and method == "POST":
            body = self._read_body()
            result = workspace_mgr.scan_projects(body.get("path", "."), body.get("max_depth", 3))
            self._json(result)
            return

        # Scan & Import
        if path == "/api/scan/import" and method == "POST":
            body = self._read_body()
            r = run_ps("scan-agents.ps1", SCRIPT_DIR, ["-ScanPath", body.get("path", "."), "-MaxDepth", str(body.get("max_depth", 3)), "-Import"])
            self._json({"ok": r["ok"], "output": r["stdout"], "error": r["stderr"]})
            return

        # Create preset
        if path == "/api/presets" and method == "POST":
            body = self._read_body()
            name = body.get("name", "")
            desc = body.get("description", "")
            skills = body.get("skills", [])
            if not name:
                self._json({"ok": False, "error": "name required"}, 400)
                return
            text = Path(CONFIG_FILE).read_text(encoding="utf-8")
            skills_yaml = "[" + ", ".join(f'"{s}"' for s in skills) + "]"
            new_block = f'  {name}:\n    description: "{desc}"\n    skills: {skills_yaml}\n'
            if "\nagents:" in text:
                text = text.replace("\nagents:", new_block + "\nagents:")
            else:
                text += "\n" + new_block
            Path(CONFIG_FILE).write_text(text, encoding="utf-8")
            self._json({"ok": True})
            return

        # Open folder
        if path == "/api/open-folder" and method == "POST":
            body = self._read_body()
            folder = body.get("path", "")
            if not folder:
                self._json({"ok": False, "error": "path required"}, 400)
                return
            ok = open_folder(folder)
            self._json({"ok": ok})
            return

        # ── /api/skills/create (central repo unified creation) ──
        if path == "/api/skills/create" and method == "POST":
            body = self._read_body()
            name = (body.get("name") or "").strip()
            desc = (body.get("description") or "").strip()
            if not name:
                self._json({"ok": False, "error": "name required"}, 400)
                return
            # Validate directory name (no path separators, no spaces)
            if not re.match(r'^[A-Za-z0-9_\-]+$', name):
                self._json({"ok": False, "error": "name must be alphanumeric/hyphen/underscore only"}, 400)
                return
            target = SKILLS_DIR / name
            if target.exists():
                self._json({"ok": False, "error": "skill already exists", "path": str(target)}, 409)
                return
            target.mkdir(parents=True, exist_ok=True)
            if not desc:
                desc = "TODO: Add description"
            skill_md = (
                "---\n"
                f"name: {name}\n"
                f'description: {desc}\n'
                "---\n\n"
                f"# {name}\n\n"
                "TODO: Add skill instructions here.\n\n"
                "## When to Use\n\n"
                "- 触发场景\n\n"
                "## Steps\n\n"
                "1. ...\n"
            )
            (target / "SKILL.md").write_text(skill_md, encoding="utf-8")
            # Optional: auto-sync after create
            if body.get("auto_sync"):
                sync_r = run_ps("sync.ps1", SCRIPT_DIR)
                self._json({"ok": True, "name": name, "path": str(target),
                            "synced": sync_r["ok"], "sync_output": sync_r["stdout"][-500:] if sync_r["stdout"] else ""})
            else:
                self._json({"ok": True, "name": name, "path": str(target)})
            return

        # ── /api/skills/install/* and batch/* (must be before <name>/... routes) ──
        if path == "/api/skills/install/local" and method == "POST":
            body = self._read_body()
            src_path = body.get("path", "")
            if not src_path or not Path(src_path).exists():
                self._json({"ok": False, "error": "path not found"}, 400)
                return
            src = Path(src_path)
            name = src.name if src.is_dir() else src.stem
            target = SKILLS_DIR / name
            if target.exists():
                self._json({"ok": False, "error": "already exists"}, 400)
                return
            if src.is_dir():
                # Validate SKILL.md presence
                if not (src / "SKILL.md").exists() and not (src / "SKILL.md.disabled").exists():
                    self._json({"ok": False, "error": "source directory must contain SKILL.md"}, 400)
                    return
                shutil.copytree(str(src), str(target))
            else:
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(target / src.name))
            self._json({"ok": True, "name": name})
            return

        if path == "/api/skills/install/git" and method == "POST":
            body = self._read_body()
            git_url = body.get("url", "")
            if not git_url:
                self._json({"ok": False, "error": "url required"}, 400)
                return
            with tempfile.TemporaryDirectory() as tmp:
                r = subprocess.run(["git", "clone", "--depth=1", git_url, tmp],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace")
                if r.returncode != 0:
                    self._json({"ok": False, "error": r.stderr})
                    return
                for skill_dir in Path(tmp).rglob("SKILL.md"):
                    src = skill_dir.parent
                    name = src.name
                    target = SKILLS_DIR / name
                    if not target.exists():
                        shutil.copytree(str(src), str(target))
            self._json({"ok": True})
            return

        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "skills" and parts[3].startswith("batch"):
            batch_action = f"{parts[3]}-{parts[4]}" if len(parts) > 4 and parts[3] == "batch" else parts[3]
            body = self._read_body()
            skill_names = body.get("names", [])
            results = []
            for sn in skill_names:
                skill_dir = SKILLS_DIR / sn
                if not skill_dir.exists():
                    results.append({"name": sn, "ok": False, "error": "not found"})
                    continue
                if batch_action == "batch-enable":
                    disabled = skill_dir / "SKILL.md.disabled"
                    if disabled.exists():
                        disabled.rename(skill_dir / "SKILL.md")
                    results.append({"name": sn, "ok": True})
                elif batch_action == "batch-disable":
                    enabled = skill_dir / "SKILL.md"
                    if enabled.exists():
                        enabled.rename(skill_dir / "SKILL.md.disabled")
                    results.append({"name": sn, "ok": True})
                elif batch_action == "batch-delete":
                    trash_mgr.add(sn, skill_dir)
                    results.append({"name": sn, "ok": True})
                elif batch_action == "batch-export":
                    results.append({"name": sn, "ok": True, "path": str(skill_dir)})
            self._json({"ok": True, "results": results})
            return

        # ── /api/skills/<name>/... routes ──
        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "skills":
            skill_name = parts[3]
            action = parts[4] if len(parts) > 4 else None

            # Get content
            if action == "content" and method == "GET":
                skill_dir = SKILLS_DIR / skill_name
                for fname in ["SKILL.md", "SKILL.md.disabled"]:
                    fp = skill_dir / fname
                    if fp.exists():
                        text = fp.read_text(encoding="utf-8", errors="replace")
                        fm = SkillManager.parse_frontmatter(text)
                        self._json({
                            "skill": {"name": fm.get("name", skill_name), "description": fm.get("description", ""),
                                      "enabled": fname == "SKILL.md", "size": fp.stat().st_size, "path": str(fp),
                                      "folder": str(fp.parent), "tags": []},
                            "content": text,
                        })
                        return
                self._json({"error": "not found"}, 404)
                return

            # Edit
            if action == "edit" and method == "POST":
                body = self._read_body()
                skill_dir = SKILLS_DIR / skill_name
                for fname in ["SKILL.md", "SKILL.md.disabled"]:
                    fp = skill_dir / fname
                    if fp.exists():
                        text = fp.read_text(encoding="utf-8")
                        for key in ["name", "description"]:
                            if key in body:
                                pattern = rf'^({key}:\s*)(.*)$'
                                replacement = rf'\g<1>"{body[key]}"'
                                text = re.sub(pattern, replacement, text, count=1, flags=re.MULTILINE)
                        fp.write_text(text, encoding="utf-8")
                        self._json({"ok": True})
                        return
                self._json({"error": "not found"}, 404)
                return

            # Delete
            if action == "delete" and method == "POST":
                skill_dir = SKILLS_DIR / skill_name
                if not skill_dir.exists():
                    self._json({"error": "not found"}, 404)
                    return
                trash_mgr.add(skill_name, skill_dir)
                self._json({"ok": True})
                return

            # Enable/Disable
            if action == "enable" and method == "POST":
                skill_dir = SKILLS_DIR / skill_name
                disabled = skill_dir / "SKILL.md.disabled"
                enabled = skill_dir / "SKILL.md"
                if disabled.exists():
                    disabled.rename(enabled)
                self._json({"ok": True})
                return

            if action == "disable" and method == "POST":
                skill_dir = SKILLS_DIR / skill_name
                enabled = skill_dir / "SKILL.md"
                disabled = skill_dir / "SKILL.md.disabled"
                if enabled.exists():
                    enabled.rename(disabled)
                self._json({"ok": True})
                return

            # Toggle agent (install/remove skill from agent)
            if action == "toggle-agent" and method == "POST":
                body = self._read_body()
                agent_key = body.get("agent_key", "")
                agent = agent_mgr.find_by_key(agent_key)
                if not agent:
                    self._json({"ok": False, "error": "agent not found"}, 404)
                    return
                skills_dir = HOME / agent["skills"]
                skills_dir.mkdir(parents=True, exist_ok=True)
                target = skills_dir / skill_name
                src = SKILLS_DIR / skill_name
                if target.exists() or target.is_symlink():
                    # Remove
                    if target.is_symlink() or target.is_dir():
                        shutil.rmtree(str(target), ignore_errors=True)
                    self._json({"ok": True, "action": "removed"})
                else:
                    # Install - try symlink, fallback to copy
                    if not src.exists():
                        self._json({"ok": False, "error": "skill not in central repo"}, 404)
                        return
                    try:
                        os.symlink(str(src), str(target))
                    except (OSError, NotImplementedError):
                        shutil.copytree(str(src), str(target))
                    self._json({"ok": True, "action": "installed"})
                return

            # Tags management
            if action == "tags" and method == "POST":
                body = self._read_body()
                tag_action = body.get("action", "")
                tag = body.get("tag", "")
                cfg = config_mgr.load()
                tags_map = cfg.get("tags", {})
                if not isinstance(tags_map, dict):
                    tags_map = {}
                skill_tags = tags_map.get(skill_name, [])
                if isinstance(skill_tags, str):
                    skill_tags = [skill_tags]
                if tag_action == "add" and tag:
                    if tag not in skill_tags:
                        skill_tags.append(tag)
                elif tag_action == "remove" and tag:
                    skill_tags = [t for t in skill_tags if t != tag]
                tags_map[skill_name] = skill_tags
                # Write back tags section
                text = Path(CONFIG_FILE).read_text(encoding="utf-8")
                # Simple approach: rebuild tags section
                tags_lines = ["tags:"]
                for sk, st in sorted(tags_map.items()):
                    if isinstance(st, list) and st:
                        quoted = ", ".join('"' + t + '"' for t in st)
                        tags_lines.append(f'  {sk}: [{quoted}]')
                # Replace existing tags section
                if re.search(r'^tags:', text, re.MULTILINE):
                    text = re.sub(r'^tags:.*?(?=^\S|\Z)', '', text, flags=re.MULTILINE | re.DOTALL)
                text = text.rstrip() + "\n\n" + "\n".join(tags_lines) + "\n"
                Path(CONFIG_FILE).write_text(text, encoding="utf-8")
                self._json({"ok": True, "tags": skill_tags})
                return

        # ── /api/trash/<name>/restore ──
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "trash" and parts[4] == "restore":
            skill_name = parts[3]
            target_dir = SKILLS_DIR / skill_name
            if not trash_mgr.restore(skill_name, target_dir):
                self._json({"error": "not in trash"}, 404)
                return
            self._json({"ok": True})
            return

        # ── /api/presets/<name>/... routes ──
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "presets":
            preset_name = parts[3]
            action = parts[4]

            if action == "activate" and method == "POST":
                body = self._read_body()
                agent = body.get("agent", "")
                cfg = config_mgr.load()
                agents_cfg = cfg.get("agents", {})
                config_name = agent_mgr.find_config_by_key(agent, agents_cfg)
                if not config_name:
                    # Auto-create agent config
                    detected = agent_mgr.detect_installed()
                    agent_info = next((a for a in detected if a["key"] == agent), None)
                    if agent_info:
                        config_name = f"{agent}_auto"
                        config_mgr.add_agent_config(config_name, agent, agent_info["skills_dir"].replace("\\", "/"))
                    else:
                        self._json({"error": "agent not found"}, 404)
                        return
                # Update active_presets for this specific agent
                cfg = config_mgr.load()  # Re-read after potential add
                agents_cfg = cfg.get("agents", {})
                current = agents_cfg.get(config_name, {}).get("active_presets", [])
                if preset_name not in current:
                    current.append(preset_name)
                config_mgr.update_value("active_presets", current, agent_name=config_name)
                sync_result = run_ps("sync.ps1", SCRIPT_DIR, ["-Agent", config_name])
                print(f"[Preset activate] {preset_name} for {config_name}: sync_ok={sync_result.get('ok')}")
                self._json({"ok": True, "agent_config": config_name})
                return

            if action == "deactivate" and method == "POST":
                body = self._read_body()
                agent = body.get("agent", "")
                cfg = config_mgr.load()
                agents_cfg = cfg.get("agents", {})
                config_name = agent_mgr.find_config_by_key(agent, agents_cfg)
                if config_name:
                    current = agents_cfg[config_name].get("active_presets", [])
                    if preset_name in current:
                        current.remove(preset_name)
                    config_mgr.update_value("active_presets", current, agent_name=config_name)
                    sync_result = run_ps("sync.ps1", SCRIPT_DIR, ["-Agent", config_name])
                    print(f"[Preset deactivate] {preset_name} for {config_name}: sync_ok={sync_result.get('ok')}")
                    self._json({"ok": True})

            if action == "edit" and method == "POST":
                body = self._read_body()
                desc = body.get("description", "")
                skills = body.get("skills", [])
                text = Path(CONFIG_FILE).read_text(encoding="utf-8")
                skills_yaml = "[" + ", ".join(f'"{s}"' for s in skills) + "]"
                # Replace the preset block
                pattern = rf'(  {re.escape(preset_name)}:\n)(.*?)(?=\n  \S|\n\S|\Z)'
                new_block = f'  {preset_name}:\n    description: "{desc}"\n    skills: {skills_yaml}'
                text = re.sub(pattern, new_block, text, flags=re.DOTALL)
                Path(CONFIG_FILE).write_text(text, encoding="utf-8")
                self._json({"ok": True})
                return

            if action == "add-skill" and method == "POST":
                body = self._read_body()
                skill = body.get("skill", "")
                text = Path(CONFIG_FILE).read_text(encoding="utf-8")
                pattern = rf'({preset_name}:[\s\S]*?skills:\s*\[)(.*?)(\])'
                m = re.search(pattern, text)
                if m:
                    existing = m.group(2).strip()
                    new_skill = f', "{skill}"' if existing else f'"{skill}"'
                    text = text[:m.start(2)] + existing + new_skill + text[m.end(2):]
                    Path(CONFIG_FILE).write_text(text, encoding="utf-8")
                    self._json({"ok": True})
                else:
                    self._json({"error": "preset not found"}, 404)
                return

            if action == "remove-skill" and method == "POST":
                body = self._read_body()
                skill = body.get("skill", "")
                text = Path(CONFIG_FILE).read_text(encoding="utf-8")
                pattern = rf'({preset_name}:[\s\S]*?skills:\s*\[)(.*?)(\])'
                m = re.search(pattern, text)
                if m:
                    skills_str = m.group(2)
                    skills_str = re.sub(rf'[",\s]*"{re.escape(skill)}"[",\s]*', '', skills_str)
                    skills_str = re.sub(r',\s*,', ',', skills_str).strip().strip(',')
                    text = text[:m.start(2)] + skills_str + text[m.end(2):]
                    Path(CONFIG_FILE).write_text(text, encoding="utf-8")
                    self._json({"ok": True})
                else:
                    self._json({"error": "preset not found"}, 404)
                return

        # ── /api/workspace/global/<agent_key> ──
        if len(parts) == 5 and parts[1] == "api" and parts[2] == "workspace" and parts[3] == "global":
            agent_key = parts[4]
            agent = agent_mgr.find_by_key(agent_key)
            if not agent:
                self._json({"error": "agent not found"}, 404)
                return
            skills_dir = HOME / agent["skills"]
            skills = skill_mgr.scan_agent_skills_dir(skills_dir)
            # Mark which are from central repo
            central_names = {s["dir"] for s in skill_mgr.scan_all()}
            for s in skills:
                s["in_central"] = s["dir"] in central_names
            self._json({"agent": agent, "skills": skills})
            return

        # ── /api/workspace/global/<agent_key>/add ──
        if len(parts) >= 6 and parts[1] == "api" and parts[2] == "workspace" and parts[3] == "global" and parts[5] == "add":
            agent_key = parts[4]
            body = self._read_body()
            skill_names = body.get("skill_names", [])
            if not skill_names:
                single = body.get("skill", "")
                if single:
                    skill_names = [single]
            agent = agent_mgr.find_by_key(agent_key)
            if not agent:
                self._json({"error": "agent not found", "results": []}, 404)
                return
            cfg = config_mgr.load()
            sync_mode = cfg.get("default_mode", "junction")
            skills_dir = HOME / agent["skills"]
            skills_dir.mkdir(parents=True, exist_ok=True)
            results = []
            for sn in skill_names:
                target = skills_dir / sn
                src = SKILLS_DIR / sn
                if not src.exists():
                    results.append({"name": sn, "ok": False, "error": "skill not found"})
                    continue
                if target.exists() or target.is_symlink():
                    results.append({"name": sn, "ok": False, "error": "already exists"})
                    continue
                try:
                    if sync_mode in ("symlink", "junction"):
                        if create_link(src, target, sync_mode):
                            results.append({"name": sn, "ok": True, "mode": sync_mode, "linked": True})
                        else:
                            # Fallback to copy if link fails
                            shutil.copytree(str(src), str(target))
                            results.append({"name": sn, "ok": True, "mode": "copy", "linked": False, "note": f"{sync_mode} failed, copied instead"})
                    else:
                        shutil.copytree(str(src), str(target))
                        results.append({"name": sn, "ok": True, "mode": "copy", "linked": False})
                except Exception as e:
                    results.append({"name": sn, "ok": False, "error": str(e)})
            self._json({"ok": True, "results": results, "mode": sync_mode})
            return

        # ── /api/workspace/global/<agent_key>/remove ──
        if len(parts) >= 6 and parts[1] == "api" and parts[2] == "workspace" and parts[3] == "global" and parts[5] == "remove":
            agent_key = parts[4]
            body = self._read_body()
            skill_names = body.get("skill_names", [])
            if not skill_names:
                single = body.get("skill", "")
                if single:
                    skill_names = [single]
            agent = agent_mgr.find_by_key(agent_key)
            if not agent:
                self._json({"error": "agent not found", "results": []}, 404)
                return
            results = []
            for sn in skill_names:
                target = HOME / agent["skills"] / sn
                if target.exists() or target.is_symlink():
                    # Check if it's a junction (Windows reparse point)
                    try:
                        attrs = os.lstat(str(target))
                        is_junction = bool(attrs.st_file_attributes & 0x400) if hasattr(attrs, 'st_file_attributes') else False
                        if is_junction:
                            os.rmdir(str(target))  # os.rmdir works on junctions
                        else:
                            shutil.rmtree(str(target), ignore_errors=True)
                    except Exception:
                        shutil.rmtree(str(target), ignore_errors=True)
                results.append({"name": sn, "ok": True})
            self._json({"ok": True, "results": results})
            return

        # ── /api/workspace/project/import ──
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "workspace" and parts[3] == "project" and parts[4] == "import":
            body = self._read_body()
            project_path = body.get("path", "")
            skill_names = body.get("skill_names", [])
            if not skill_names:
                single = body.get("skill", "")
                if single:
                    skill_names = [single]
            if not project_path or not skill_names:
                self._json({"ok": False, "error": "path and skill required"}, 400)
                return
            results = []
            for sn in skill_names:
                src = None
                src_type = None  # "dir" or "file"
                for agent_dir in [".claude", ".qoder", ".cursor", ".codex", ".copilot", ".gemini", ".trae", ".trae-cn", ".grok", ".continue", ".cline"]:
                    # Try directory form first: <path>/.claude/skills/<name>/
                    candidate_dir = Path(project_path) / agent_dir / "skills" / sn
                    if candidate_dir.exists() and candidate_dir.is_dir():
                        if (candidate_dir / "SKILL.md").exists() or (candidate_dir / "SKILL.md.disabled").exists():
                            src = candidate_dir
                            src_type = "dir"
                            break
                    # Try single-file form: <path>/.claude/skills/<name>.md
                    candidate_file = Path(project_path) / agent_dir / "skills" / f"{sn}.md"
                    if candidate_file.exists() and candidate_file.is_file():
                        src = candidate_file
                        src_type = "file"
                        break
                if not src:
                    results.append({"name": sn, "ok": False, "error": "not found in project"})
                    continue
                target = SKILLS_DIR / sn
                if target.exists() or (src_type == "file" and (SKILLS_DIR / f"{sn}.md").exists()):
                    results.append({"name": sn, "ok": False, "error": "already in central repo"})
                    continue
                try:
                    if src_type == "dir":
                        # Import as directory skill: <central>/skills/<name>/SKILL.md
                        shutil.copytree(str(src), str(target))
                    else:
                        # Single-file skill: copy as <central>/skills/<name>/SKILL.md (normalize to dir form)
                        target.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(str(src), str(target / "SKILL.md"))
                    results.append({"name": sn, "ok": True, "type": src_type})
                except Exception as e:
                    results.append({"name": sn, "ok": False, "error": str(e)})
            self._json({"ok": True, "results": results})
            return

        # ── /api/workspace/project/remove ──
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "workspace" and parts[3] == "project" and parts[4] == "remove":
            body = self._read_body()
            project_path = body.get("path", "")
            agent_dir = body.get("agent_dir", "")
            skill_names = body.get("skill_names", [])
            if not project_path or not agent_dir or not skill_names:
                self._json({"ok": False, "error": "path, agent_dir and skill_names required"}, 400)
                return
            results = []
            for sn in skill_names:
                target_dir = Path(project_path) / agent_dir / "skills" / sn
                target_file = Path(project_path) / agent_dir / "skills" / f"{sn}.md"
                try:
                    if target_dir.exists() or target_dir.is_symlink():
                        # Check if it's a junction (Windows reparse point)
                        try:
                            attrs = os.lstat(str(target_dir))
                            is_junction = bool(attrs.st_file_attributes & 0x400) if hasattr(attrs, 'st_file_attributes') else False
                            if is_junction:
                                os.rmdir(str(target_dir))  # os.rmdir works on junctions
                            else:
                                shutil.rmtree(str(target_dir), ignore_errors=True)
                        except Exception:
                            shutil.rmtree(str(target_dir), ignore_errors=True)
                        results.append({"name": sn, "ok": True, "type": "dir"})
                    elif target_file.exists():
                        target_file.unlink()
                        results.append({"name": sn, "ok": True, "type": "file"})
                    else:
                        results.append({"name": sn, "ok": False, "error": "not found"})
                except Exception as e:
                    results.append({"name": sn, "ok": False, "error": str(e)})
            self._json({"ok": True, "results": results})
            return

        # ── /api/workspace/project/toggle ──
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "workspace" and parts[3] == "project" and parts[4] == "toggle":
            body = self._read_body()
            project_path = body.get("path", "")
            agent_dir = body.get("agent_dir", "")
            skill_names = body.get("skill_names", [])
            enabled = body.get("enabled", True)
            if not project_path or not agent_dir or not skill_names:
                self._json({"ok": False, "error": "path, agent_dir and skill_names required"}, 400)
                return
            results = []
            for sn in skill_names:
                skill_dir = Path(project_path) / agent_dir / "skills" / sn
                skill_md = skill_dir / "SKILL.md"
                skill_md_disabled = skill_dir / "SKILL.md.disabled"
                try:
                    if enabled:
                        # Enable: SKILL.md.disabled -> SKILL.md
                        if skill_md_disabled.exists():
                            skill_md_disabled.rename(skill_md)
                            results.append({"name": sn, "ok": True, "enabled": True})
                        elif skill_md.exists():
                            results.append({"name": sn, "ok": True, "enabled": True, "note": "already enabled"})
                        else:
                            results.append({"name": sn, "ok": False, "error": "skill not found"})
                    else:
                        # Disable: SKILL.md -> SKILL.md.disabled
                        if skill_md.exists():
                            skill_md.rename(skill_md_disabled)
                            results.append({"name": sn, "ok": True, "enabled": False})
                        elif skill_md_disabled.exists():
                            results.append({"name": sn, "ok": True, "enabled": False, "note": "already disabled"})
                        else:
                            results.append({"name": sn, "ok": False, "error": "skill not found"})
                except Exception as e:
                    results.append({"name": sn, "ok": False, "error": str(e)})
            self._json({"ok": True, "results": results})
            return

        # ── /api/workspace/project/add ──
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "workspace" and parts[3] == "project" and parts[4] == "add":
            body = self._read_body()
            project_path = body.get("path", "")
            agent_dir = body.get("agent_dir", "")
            skill_names = body.get("skill_names", [])
            if not project_path or not agent_dir or not skill_names:
                self._json({"ok": False, "error": "path, agent_dir and skill_names required"}, 400)
                return
            cfg = config_mgr.load()
            sync_mode = cfg.get("default_mode", "junction")
            skills_target_dir = Path(project_path) / agent_dir / "skills"
            skills_target_dir.mkdir(parents=True, exist_ok=True)
            results = []
            for sn in skill_names:
                src = SKILLS_DIR / sn
                target = skills_target_dir / sn
                if not src.exists():
                    results.append({"name": sn, "ok": False, "error": "skill not found in library"})
                    continue
                if target.exists() or target.is_symlink():
                    results.append({"name": sn, "ok": False, "error": "already exists in project"})
                    continue
                try:
                    if sync_mode in ("symlink", "junction"):
                        if create_link(src, target, sync_mode):
                            results.append({"name": sn, "ok": True, "mode": sync_mode, "linked": True})
                        else:
                            # Fallback to copy if link fails
                            shutil.copytree(str(src), str(target))
                            results.append({"name": sn, "ok": True, "mode": "copy", "linked": False, "note": f"{sync_mode} failed, copied instead"})
                    else:
                        shutil.copytree(str(src), str(target))
                        results.append({"name": sn, "ok": True, "mode": "copy", "linked": False})
                except Exception as e:
                    results.append({"name": sn, "ok": False, "error": str(e)})
            self._json({"ok": True, "results": results, "mode": sync_mode})
            return

        # ── /api/workspace/project/add-to-preset ──
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "workspace" and parts[3] == "project" and parts[4] == "add-to-preset":
            body = self._read_body()
            project_path = body.get("path", "")
            agent_dir = body.get("agent_dir", "")
            skill_names = body.get("skill_names", [])
            preset_name = body.get("preset", "")
            if not project_path or not agent_dir or not skill_names or not preset_name:
                self._json({"ok": False, "error": "path, agent_dir, skill_names and preset required"}, 400)
                return
            cfg = config_mgr.load()
            sync_mode = cfg.get("default_mode", "junction")
            presets_cfg = cfg.get("presets", {})
            if preset_name not in presets_cfg:
                self._json({"ok": False, "error": f"preset '{preset_name}' not found"}, 404)
                return
            results = []
            for sn in skill_names:
                result = {"name": sn, "ok": True, "imported": False, "added_to_preset": False, "replaced_with_link": False}
                src = Path(project_path) / agent_dir / "skills" / sn
                central_target = SKILLS_DIR / sn
                # Step 1: Import to central if not exists
                if not central_target.exists():
                    if src.exists() and src.is_dir():
                        try:
                            shutil.copytree(str(src), str(central_target))
                            result["imported"] = True
                        except Exception as e:
                            result["ok"] = False
                            result["error"] = f"import failed: {str(e)}"
                            results.append(result)
                            continue
                    else:
                        result["ok"] = False
                        result["error"] = "skill not found in project"
                        results.append(result)
                        continue
                # Step 2: Add to preset skills list
                text = Path(CONFIG_FILE).read_text(encoding="utf-8")
                pattern = rf'({re.escape(preset_name)}:[\s\S]*?skills:\s*\[)(.*?)(\])'
                m = re.search(pattern, text)
                if m:
                    existing = m.group(2).strip()
                    if f'"{sn}"' not in existing and f"'{sn}'" not in existing:
                        new_skill = f', "{sn}"' if existing else f'"{sn}"'
                        text = text[:m.start(2)] + existing + new_skill + text[m.end(2):]
                        Path(CONFIG_FILE).write_text(text, encoding="utf-8")
                        result["added_to_preset"] = True
                    else:
                        result["added_to_preset"] = True
                        result["note"] = "already in preset"
                # Step 3: Replace with link if in symlink/junction mode
                if sync_mode in ("symlink", "junction") and src.exists() and src.is_dir():
                    # Check if already a link
                    try:
                        attrs = os.lstat(str(src))
                        is_reparse = bool(attrs.st_file_attributes & 0x400) if hasattr(attrs, 'st_file_attributes') else src.is_symlink()
                    except Exception:
                        is_reparse = src.is_symlink()
                    if not is_reparse:
                        try:
                            shutil.rmtree(str(src))
                            if create_link(central_target, src, sync_mode):
                                result["replaced_with_link"] = True
                            else:
                                # Fallback: copy back from central
                                shutil.copytree(str(central_target), str(src))
                                result["link_error"] = f"{sync_mode} creation failed, restored copy"
                        except Exception as e:
                            result["link_error"] = str(e)
                results.append(result)
            # Step 4: Trigger sync for agents with this preset active
            cfg = config_mgr.load()
            agents_cfg = cfg.get("agents", {})
            synced_agents = []
            for agent_name, acfg in agents_cfg.items():
                if isinstance(acfg, dict) and preset_name in (acfg.get("active_presets") or []):
                    run_ps("sync.ps1", SCRIPT_DIR, ["-Agent", agent_name])
                    synced_agents.append(agent_name)
            self._json({"ok": True, "results": results, "mode": sync_mode, "synced_agents": synced_agents})
            return

        # ── /api/skills/reverse-sync (recover orphan skills from agent dirs + project dirs) ──
        if path == "/api/skills/reverse-sync" and method == "POST":
            body = self._read_body() if self.command == "POST" else {}
            dry_run = bool(body.get("dry_run", False))
            cfg = config_mgr.load()
            agents_cfg = cfg.get("agents", {})
            central_names = {s["dir"] for s in skill_mgr.scan_all()}
            imported, skipped, errors = [], [], []

            def _is_reparse(path):
                try:
                    attrs = os.lstat(str(path))
                    return bool(attrs.st_file_attributes & 0x400) if hasattr(attrs, 'st_file_attributes') else False
                except Exception:
                    return False

            def _try_import(src_path, src_type, agent_label, project_label=""):
                """Import a single skill source into central repo.

                For dir type, src_path may point to either the skill directory
                or the SKILL.md file inside it — normalize to the directory.
                """
                if src_type == "dir":
                    # If src_path is a file (e.g. SKILL.md), use its parent dir
                    if src_path.is_file():
                        src_path = src_path.parent
                    name = src_path.name
                else:  # file
                    name = src_path.stem
                label = agent_label + (f" @ {project_label}" if project_label else "")
                if name in central_names or (src_type == "file" and (SKILLS_DIR / name).exists()):
                    skipped.append({"name": name, "source": label, "reason": "already in central"})
                    return
                if src_type == "dir" and _is_reparse(src_path):
                    skipped.append({"name": name, "source": label, "reason": "managed junction/symlink"})
                    return
                target = SKILLS_DIR / name
                if target.exists():
                    skipped.append({"name": name, "source": label, "reason": "name conflict"})
                    return
                if dry_run:
                    imported.append({"name": name, "source": label, "type": src_type, "dry_run": True})
                    return
                try:
                    if src_type == "dir":
                        shutil.copytree(str(src_path), str(target))
                    else:
                        # Normalize single-file skill to <central>/skills/<name>/SKILL.md
                        target.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(str(src_path), str(target / "SKILL.md"))
                    imported.append({"name": name, "source": label, "type": src_type})
                    central_names.add(name)
                except Exception as e:
                    errors.append({"name": name, "source": label, "error": str(e)})

            # 1) Scan global agent dirs (from config.yaml)
            for name, acfg in agents_cfg.items():
                if not isinstance(acfg, dict):
                    continue
                agent_path = acfg.get("path", "")
                if not agent_path:
                    continue
                p = Path(agent_path.replace("~", str(HOME)))
                if not p.exists():
                    continue
                for entry in sorted(p.iterdir()):
                    if entry.name.startswith('.'):
                        continue
                    if entry.is_dir():
                        if (entry / "SKILL.md").exists() or (entry / "SKILL.md.disabled").exists():
                            _try_import(entry, "dir", name)
                    elif entry.is_file() and entry.suffix.lower() == ".md":
                        text = entry.read_text(encoding="utf-8", errors="replace")
                        if text.startswith("---"):
                            fm = SkillManager.parse_frontmatter(text)
                            if "name" in fm or "description" in fm:
                                _try_import(entry, "file", name)

            # 2) Scan project-level dirs (from request body or default D:\06_Project)
            project_scan_path = body.get("project_path", "D:\\06_Project")
            project_max_depth = int(body.get("project_depth", 3))
            scan_result = workspace_mgr.scan_native(project_scan_path, project_max_depth)
            for w in scan_result.get("workspaces", []):
                project_name = w.get("project_name", "")
                for s in w.get("skills", []):
                    src_path = Path(s.get("path", ""))
                    if not src_path.exists():
                        continue
                    _try_import(src_path, s.get("type", "dir"), w.get("label", ""), project_name)

            self._json({
                "ok": True,
                "dry_run": dry_run,
                "imported": imported,
                "skipped": skipped,
                "errors": errors,
                "imported_count": len(imported),
                "skipped_count": len(skipped),
            })
            return

        # ── /api/workspace/scan (native Python scanner) ──
        if path == "/api/workspace/scan" and method == "POST":
            body = self._read_body()
            result = workspace_mgr.scan_native(body.get("path", "."), body.get("max_depth", 3))
            self._json(result)
            return

        # ── /api/backup/* ──
        if len(parts) >= 3 and parts[1] == "api" and parts[2] == "backup":
            action = parts[3] if len(parts) > 3 else "status"

            if action == "status" and method == "GET":
                r = git_mgr.run(["status", "--porcelain"])
                r2 = git_mgr.run(["remote", "-v"])
                remote_url = ""
                for line in r2["stdout"].splitlines():
                    if line.startswith("origin") and "(fetch)" in line:
                        remote_url = line.split("\t")[-1].split(" ")[0] if "\t" in line else ""
                        break
                # Fetch last commit info
                last_commit = ""
                last_commit_date = ""
                lr = git_mgr.run(["log", "-1", "--format=%s|%ai"])
                if lr["ok"] and lr["stdout"].strip():
                    p = lr["stdout"].strip().split("|", 1)
                    if len(p) == 2:
                        last_commit, last_commit_date = p[0], p[1][:16]
                # Ahead/behind remote
                ahead = 0
                behind = 0
                if remote_url:
                    abr = git_mgr.run(["rev-list", "--left-right", "--count", "HEAD...origin/HEAD"])
                    if abr["ok"] and abr["stdout"].strip():
                        try:
                            l, r_side = abr["stdout"].split()
                            ahead, behind = int(l), int(r_side)
                        except Exception:
                            pass
                self._json({
                    "ok": True,
                    "clean": r["stdout"] == "",
                    "has_remote": bool(remote_url),
                    "remote": remote_url,
                    "last_commit": last_commit,
                    "last_commit_date": last_commit_date,
                    "ahead": ahead,
                    "behind": behind,
                })
                return

            if action == "now" and method == "POST":
                body = self._read_body() if self.command == "POST" else {}
                msg = body.get("message") or f"Backup {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                git_mgr.run(["add", "-A"])
                commit_r = git_mgr.run(["commit", "-m", msg])
                # commit returns non-zero when there's nothing to commit; treat as success
                nothing_to_commit = (not commit_r["ok"]) and ("nothing to commit" in commit_r["stdout"] or "nothing to commit" in commit_r["stderr"] or "no changes" in commit_r["stdout"] or "no changes" in commit_r["stderr"])
                push_ok = True
                push_output = ""
                push_err = ""
                # Push only if a remote exists
                remote_r = git_mgr.run(["remote", "-v"])
                has_remote = bool(remote_r["stdout"].strip())
                if has_remote:
                    # Try with rebase to avoid merge commits; fall back to plain push
                    push_r = git_mgr.run(["push", "origin", "HEAD"])
                    if not push_r["ok"]:
                        push_r2 = git_mgr.run(["push"])
                        if not push_r2["ok"]:
                            push_ok = False
                            push_err = push_r2["stderr"] or push_r["stderr"] or "push failed"
                            push_output = push_r2["stdout"] + push_r["stdout"]
                        else:
                            push_output = push_r2["stdout"]
                    else:
                        push_output = push_r["stdout"]
                ok = (commit_r["ok"] or nothing_to_commit) and push_ok
                self._json({
                    "ok": ok,
                    "message": msg,
                    "commit_ok": commit_r["ok"] or nothing_to_commit,
                    "nothing_to_commit": nothing_to_commit,
                    "commit_output": commit_r["stdout"],
                    "commit_error": commit_r["stderr"],
                    "pushed": has_remote and push_ok,
                    "push_output": push_output,
                    "push_error": push_err,
                })
                return

            if action == "pull" and method == "POST":
                r = git_mgr.run(["pull", "--rebase"])
                self._json({"ok": r["ok"], "output": r["stdout"], "error": r["stderr"]})
                return

            if action == "configure" and method == "POST":
                body = self._read_body()
                remote_url = body.get("remote_url", "")
                if remote_url:
                    git_mgr.run(["remote", "remove", "origin"])
                    r = git_mgr.run(["remote", "add", "origin", remote_url])
                    self._json({"ok": r["ok"]})
                else:
                    self._json({"ok": False, "error": "remote_url required"}, 400)
                return

            if action == "history" and method == "GET":
                r = git_mgr.run(["log", "--format=%H|%ai|%s", "-20"])
                commits = []
                for line in r["stdout"].splitlines():
                    if not line.strip():
                        continue
                    p = line.split("|", 2)
                    if len(p) == 3:
                        commits.append({"hash": p[0], "date": p[1][:16], "message": p[2]})
                    else:
                        commits.append({"hash": "", "date": "", "message": line})
                self._json({"ok": r["ok"], "commits": commits})
                return

        self._json({"error": "not found"}, 404)

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8780
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Skills Sync Manager Web UI")
    print(f"  http://127.0.0.1:{port}")
    print(f"  Skills dir: {SKILLS_DIR}")
    print(f"  Config: {CONFIG_FILE}")
    print(f"  Static: {STATIC_DIR}")
    print(f"Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
