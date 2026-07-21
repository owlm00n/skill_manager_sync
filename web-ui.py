#!/usr/bin/env python3
"""Skills Sync Manager - Web UI Server
Python HTTP server with static file serving + REST API.
Port: 8770 (default)
"""
import http.server
import socketserver
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

# ── Paths ──────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = SCRIPT_DIR / "skills"
CONFIG_FILE = SCRIPT_DIR / "config.yaml"
TRASH_FILE = SCRIPT_DIR / ".trash.json"
STATIC_DIR = SCRIPT_DIR / "static"
PS = "powershell.exe"
HOME = Path.home()

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


# ── Simple YAML parser (no deps) ──────────────────────
def parse_yaml(path):
    text = Path(path).read_text(encoding="utf-8")
    return _parse_yaml_text(text)

def _parse_yaml_text(text):
    root = {}
    stack = [(root, -1)]
    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(stripped)
        while len(stack) > 1 and indent <= stack[-1][1]:
            stack.pop()
        parent, _ = stack[-1]
        if stripped.startswith("- "):
            val = stripped[2:].strip()
            if isinstance(parent, list):
                parent.append(_yaml_val(val))
            continue
        if ":" not in stripped:
            continue
        key, _, val = stripped.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val.startswith("[") and val.endswith("]"):
            items = [x.strip().strip('"').strip("'") for x in val[1:-1].split(",") if x.strip()]
            parent[key] = items
        elif val == "":
            child = {}
            parent[key] = child
            stack.append((child, indent))
        else:
            parent[key] = _yaml_val(val)
    return root

def _yaml_val(s):
    if s.lower() == "true": return True
    if s.lower() == "false": return False
    return s

def write_yaml_value(path, key_path, value, agent_name=None):
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if key_path == "default_mode":
        for i, line in enumerate(lines):
            if line.strip().startswith("default_mode:"):
                indent = line[:len(line) - len(line.lstrip())]
                lines[i] = f'{indent}default_mode: {value}\n'
                break
    elif key_path == "active_presets":
        if agent_name:
            # Find the specific agent's active_presets
            in_agent = False
            for i, line in enumerate(lines):
                stripped = line.lstrip()
                # Agent config lines start with 2 spaces (under agents:)
                if stripped.startswith(f"{agent_name}:") and line.startswith("  "):
                    in_agent = True
                    continue
                if in_agent and "active_presets:" in line:
                    indent = line[:len(line) - len(line.lstrip())]
                    lines[i] = f'{indent}active_presets: {json.dumps(value)}\n'
                    break
                # Exit agent block when hitting another agent or top-level section
                if in_agent and line.strip() and not line.startswith("    ") and not line.startswith("\n"):
                    break
        else:
            for i, line in enumerate(lines):
                if "active_presets:" in line:
                    indent = line[:len(line) - len(line.lstrip())]
                    lines[i] = f'{indent}active_presets: {json.dumps(value)}\n'
                    break
    Path(path).write_text("".join(lines), encoding="utf-8")

def add_agent_config(path, config_name, tool, skills_path, presets=None):
    """Add a new agent config block to config.yaml."""
    text = Path(path).read_text(encoding="utf-8")
    presets_str = json.dumps(presets or [])
    new_block = f"\n  {config_name}:\n    tool: {tool}\n    path: \"{skills_path}\"\n    active_presets: {presets_str}\n    skills: [\"*\"]\n"
    # Insert after 'agents:' section
    if "\nagents:" in text:
        text = text.replace("\nagents:", "\nagents:" + new_block, 1)
    else:
        text += f"\nagents:{new_block}"
    Path(path).write_text(text, encoding="utf-8")


# ── Trash management ──────────────────────────────────
def load_trash():
    if TRASH_FILE.exists():
        return json.loads(TRASH_FILE.read_text(encoding="utf-8"))
    return []

def save_trash(items):
    TRASH_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Skill scanning ────────────────────────────────────
def parse_frontmatter(text):
    m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm

def scan_skills():
    skills = []
    if not SKILLS_DIR.exists():
        return skills
    cfg = parse_yaml(CONFIG_FILE) if CONFIG_FILE.exists() else {}
    tags_map = cfg.get("tags", {})
    for d in sorted(SKILLS_DIR.iterdir()):
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
        fm = parse_frontmatter(text)
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


# ── Agent detection ───────────────────────────────────
AGENT_REGISTRY = [
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

def detect_agents():
    found = []
    for a in AGENT_REGISTRY:
        detect_dir = HOME / a["detect"]
        if detect_dir.exists():
            skills_dir = HOME / a["skills"]
            count = 0
            synced = []
            if skills_dir.exists():
                for sd in skills_dir.iterdir():
                    if sd.name.startswith('.'):  # Skip hidden/system directories
                        continue
                    if sd.is_dir() and ((sd / "SKILL.md").exists() or (sd / "SKILL.md.disabled").exists()):
                        count += 1
                        synced.append(sd.name)
            found.append({
                "key": a["key"], "label": a["label"], "installed": True,
                "skills_dir": str(skills_dir), "skill_count": count, "synced": synced,
            })
    return found

def discover_unknown_agents(detected_agents):
    """Scan home directory for dot-directories with skills subdirectory not in registry."""
    detected_dirs = set()
    for a in AGENT_REGISTRY:
        detected_dirs.add(str(HOME / a["detect"]))
    detected_skills_dirs = set(a["skills_dir"] for a in detected_agents)
    
    discovered = []
    try:
        for item in HOME.iterdir():
            if not item.is_dir() or not item.name.startswith('.'):
                continue
            # Skip already registered agents
            if str(item) in detected_dirs:
                continue
            # Check for skills subdirectory
            skills_dir = item / "skills"
            if not skills_dir.exists() or not skills_dir.is_dir():
                continue
            # Count skills
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

def get_sync_status():
    cfg = parse_yaml(CONFIG_FILE) if CONFIG_FILE.exists() else {}
    agents_cfg = cfg.get("agents", {})
    results = []
    for name, acfg in agents_cfg.items():
        if not isinstance(acfg, dict):
            continue
        agent_path = acfg.get("path", "")
        tool = acfg.get("tool", "")
        presets = acfg.get("active_presets", [])
        skills_list = acfg.get("skills", [])
        p = Path(agent_path.replace("~", str(HOME)))
        synced, missing = [], []
        if p.exists():
            for sd in sorted(SKILLS_DIR.iterdir()):
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


def find_agent_config_by_key(agent_key, agents_cfg):
    """Find agent config name by agent key (tool field or config name match)."""
    if agent_key in agents_cfg:
        return agent_key
    for name, acfg in agents_cfg.items():
        if isinstance(acfg, dict) and acfg.get("tool", "") == agent_key:
            return name
    return None


def scan_workspaces_native(scan_path, max_depth=3):
    """Scan for agent workspace directories (.claude, .qoder, etc.) under scan_path."""
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
    # Walk directory tree up to max_depth
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
                    for sd in sorted(skills_path.iterdir()):
                        if sd.is_dir() and ((sd / "SKILL.md").exists() or (sd / "SKILL.md.disabled").exists()):
                            fm = parse_frontmatter((sd / "SKILL.md").read_text(encoding="utf-8", errors="replace") if (sd / "SKILL.md").exists() else (sd / "SKILL.md.disabled").read_text(encoding="utf-8", errors="replace"))
                            skills_list.append({
                                "name": sd.name,
                                "display_name": fm.get("name", sd.name),
                                "description": fm.get("description", ""),
                                "enabled": (sd / "SKILL.md").exists(),
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


# ── PowerShell helpers ────────────────────────────────
def run_ps(script, args=None, timeout=15):
    cmd = [PS, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT_DIR / script)]
    if args:
        cmd.extend(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return {"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr, "code": r.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "timeout", "code": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}

def scan_projects(scan_path, max_depth=3):
    r = run_ps("scan-agents.ps1", ["-ScanPath", scan_path, "-MaxDepth", str(max_depth), "-Json"])
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


# ── Workspace helpers ─────────────────────────────────
def find_agent_by_key(key):
    for a in AGENT_REGISTRY:
        if a["key"] == key:
            return a
    return None

def scan_agent_skills_dir(skills_dir_path):
    """Scan a directory for skills, return list of skill records."""
    results = []
    p = Path(skills_dir_path)
    if not p.exists():
        return results
    for d in sorted(p.iterdir()):
        if not d.is_dir() or d.name.startswith('.'):
            continue
        skill_md = d / "SKILL.md"
        disabled = d / "SKILL.md.disabled"
        if skill_md.exists():
            text = skill_md.read_text(encoding="utf-8", errors="replace")
            fm = parse_frontmatter(text)
            results.append({
                "name": fm.get("name", d.name), "dir": d.name,
                "description": fm.get("description", ""), "enabled": True,
                "path": str(skill_md), "folder": str(d),
            })
        elif disabled.exists():
            text = disabled.read_text(encoding="utf-8", errors="replace")
            fm = parse_frontmatter(text)
            results.append({
                "name": fm.get("name", d.name), "dir": d.name,
                "description": fm.get("description", ""), "enabled": False,
                "path": str(disabled), "folder": str(d),
            })
    return results


# ── Git helpers ───────────────────────────────────────
def run_git(args):
    try:
        r = subprocess.run(["git"] + args, capture_output=True, text=True,
                           cwd=str(SCRIPT_DIR), encoding="utf-8", errors="replace")
        return {"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e)}


# ── Open folder helper ────────────────────────────────
def open_folder(path_str):
    """Open a folder in Windows Explorer."""
    p = Path(path_str)
    if not p.exists():
        return False
    try:
        if sys.platform == "win32":
            os.startfile(str(p))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(p)])
        else:
            subprocess.run(["xdg-open", str(p)])
        return True
    except Exception:
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
            cfg = parse_yaml(CONFIG_FILE)
            self._json({"default_mode": cfg.get("default_mode", "junction")})
            return

        if path == "/api/settings/mode" and method == "POST":
            body = self._read_body()
            mode = body.get("mode", "")
            if mode not in ("symlink", "junction", "copy"):
                self._json({"error": "invalid mode"}, 400)
                return
            write_yaml_value(CONFIG_FILE, "default_mode", mode)
            self._json({"ok": True, "mode": mode})
            return

        # Skills list
        if path == "/api/skills" and method == "GET":
            self._json({"skills": scan_skills(), "skills_dir": str(SKILLS_DIR)})
            return

        # Agents list
        if path == "/api/agents" and method == "GET":
            self._json({"agents": detect_agents(), "sync_status": get_sync_status()})
            return

        # Scan for new agents (auto-discover unknown agents)
        if path == "/api/agents/scan" and method == "POST":
            agents = detect_agents()
            # Auto-discover unknown agents by scanning home directory
            discovered = discover_unknown_agents(agents)
            if discovered:
                agents.extend(discovered)
            self._json({"agents": agents, "sync_status": get_sync_status(), "new_count": len(discovered)})
            return

        # Presets list
        if path == "/api/presets" and method == "GET":
            cfg = parse_yaml(CONFIG_FILE)
            presets_cfg = cfg.get("presets", {})
            presets = []
            all_skill_names = [s["dir"] for s in scan_skills()]
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
            cfg = parse_yaml(CONFIG_FILE)
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
            self._json({"skills": scan_skills(), "agents": detect_agents(), "sync_status": get_sync_status()})
            return

        # Trash
        if path == "/api/trash" and method == "GET":
            self._json({"items": load_trash()})
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
            r = run_ps("sync.ps1", args if args else None)
            self._json({"ok": r["ok"], "output": r["stdout"], "error": r["stderr"]})
            return

        # Scan
        if path == "/api/scan" and method == "POST":
            body = self._read_body()
            result = scan_projects(body.get("path", "."), body.get("max_depth", 3))
            self._json(result)
            return

        # Scan & Import
        if path == "/api/scan/import" and method == "POST":
            body = self._read_body()
            r = run_ps("scan-agents.ps1", ["-ScanPath", body.get("path", "."), "-MaxDepth", str(body.get("max_depth", 3)), "-Import"])
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
            import tempfile
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
                    trash = load_trash()
                    trash.append({"name": sn, "deleted_at": datetime.now().isoformat(), "dir": str(skill_dir)})
                    save_trash(trash)
                    trash_dir = SCRIPT_DIR / ".trash" / sn
                    trash_dir.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(skill_dir), str(trash_dir))
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
                        fm = parse_frontmatter(text)
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
                trash = load_trash()
                trash.append({"name": skill_name, "deleted_at": datetime.now().isoformat(), "dir": str(skill_dir)})
                save_trash(trash)
                trash_dir = SCRIPT_DIR / ".trash" / skill_name
                trash_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(skill_dir), str(trash_dir))
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
                agent = find_agent_by_key(agent_key)
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
                cfg = parse_yaml(CONFIG_FILE)
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
            trash_dir = SCRIPT_DIR / ".trash" / skill_name
            target_dir = SKILLS_DIR / skill_name
            if not trash_dir.exists():
                self._json({"error": "not in trash"}, 404)
                return
            shutil.move(str(trash_dir), str(target_dir))
            trash = load_trash()
            trash = [t for t in trash if t["name"] != skill_name]
            save_trash(trash)
            self._json({"ok": True})
            return

        # ── /api/presets/<name>/... routes ──
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "presets":
            preset_name = parts[3]
            action = parts[4]

            if action == "activate" and method == "POST":
                body = self._read_body()
                agent = body.get("agent", "")
                cfg = parse_yaml(CONFIG_FILE)
                agents_cfg = cfg.get("agents", {})
                config_name = find_agent_config_by_key(agent, agents_cfg)
                if not config_name:
                    # Auto-create agent config
                    detected = detect_agents()
                    agent_info = next((a for a in detected if a["key"] == agent), None)
                    if agent_info:
                        config_name = f"{agent}_auto"
                        add_agent_config(CONFIG_FILE, config_name, agent, agent_info["skills_dir"].replace("\\", "/"))
                    else:
                        self._json({"error": "agent not found"}, 404)
                        return
                # Update active_presets for this specific agent
                cfg = parse_yaml(CONFIG_FILE)  # Re-read after potential add
                agents_cfg = cfg.get("agents", {})
                current = agents_cfg.get(config_name, {}).get("active_presets", [])
                if preset_name not in current:
                    current.append(preset_name)
                write_yaml_value(CONFIG_FILE, "active_presets", current, agent_name=config_name)
                sync_result = run_ps("sync.ps1", ["-Agent", config_name])
                print(f"[Preset activate] {preset_name} for {config_name}: sync_ok={sync_result.get('ok')}")
                self._json({"ok": True, "agent_config": config_name})
                return

            if action == "deactivate" and method == "POST":
                body = self._read_body()
                agent = body.get("agent", "")
                cfg = parse_yaml(CONFIG_FILE)
                agents_cfg = cfg.get("agents", {})
                config_name = find_agent_config_by_key(agent, agents_cfg)
                if config_name:
                    current = agents_cfg[config_name].get("active_presets", [])
                    if preset_name in current:
                        current.remove(preset_name)
                    write_yaml_value(CONFIG_FILE, "active_presets", current, agent_name=config_name)
                    sync_result = run_ps("sync.ps1", ["-Agent", config_name])
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
            agent = find_agent_by_key(agent_key)
            if not agent:
                self._json({"error": "agent not found"}, 404)
                return
            skills_dir = HOME / agent["skills"]
            skills = scan_agent_skills_dir(skills_dir)
            # Mark which are from central repo
            central_names = {s["dir"] for s in scan_skills()}
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
            agent = find_agent_by_key(agent_key)
            if not agent:
                self._json({"error": "agent not found", "results": []}, 404)
                return
            skills_dir = HOME / agent["skills"]
            skills_dir.mkdir(parents=True, exist_ok=True)
            results = []
            for sn in skill_names:
                target = skills_dir / sn
                src = SKILLS_DIR / sn
                if not src.exists():
                    results.append({"name": sn, "ok": False, "error": "skill not found"})
                    continue
                if target.exists():
                    results.append({"name": sn, "ok": False, "error": "already exists"})
                    continue
                try:
                    os.symlink(str(src), str(target))
                except (OSError, NotImplementedError):
                    shutil.copytree(str(src), str(target))
                results.append({"name": sn, "ok": True})
            self._json({"ok": True, "results": results})
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
            agent = find_agent_by_key(agent_key)
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
                for agent_dir in [".claude", ".qoder", ".cursor", ".codex", ".copilot", ".gemini", ".trae", ".trae-cn", ".grok", ".continue", ".cline"]:
                    candidate = Path(project_path) / agent_dir / "skills" / sn
                    if candidate.exists():
                        src = candidate
                        break
                if not src:
                    results.append({"name": sn, "ok": False, "error": "not found in project"})
                    continue
                target = SKILLS_DIR / sn
                if target.exists():
                    results.append({"name": sn, "ok": False, "error": "already in central repo"})
                    continue
                shutil.copytree(str(src), str(target))
                results.append({"name": sn, "ok": True})
            self._json({"ok": True, "results": results})
            return

        # ── /api/workspace/scan (native Python scanner) ──
        if path == "/api/workspace/scan" and method == "POST":
            body = self._read_body()
            result = scan_workspaces_native(body.get("path", "."), body.get("max_depth", 3))
            self._json(result)
            return

        # ── /api/backup/* ──
        if len(parts) >= 3 and parts[1] == "api" and parts[2] == "backup":
            action = parts[3] if len(parts) > 3 else "status"

            if action == "status" and method == "GET":
                r = run_git(["status", "--porcelain"])
                r2 = run_git(["remote", "-v"])
                remote_url = ""
                for line in r2["stdout"].splitlines():
                    if line.startswith("origin") and "(fetch)" in line:
                        remote_url = line.split("\t")[-1].split(" ")[0] if "\t" in line else ""
                        break
                self._json({"ok": True, "clean": r["stdout"] == "", "has_remote": bool(remote_url), "remote": remote_url})
                return

            if action == "now" and method == "POST":
                msg = f"Backup {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                run_git(["add", "-A"])
                r = run_git(["commit", "-m", msg])
                if has_remote := bool(run_git(["remote", "-v"])["stdout"].strip()):
                    run_git(["push"])
                self._json({"ok": r["ok"], "message": msg})
                return

            if action == "pull" and method == "POST":
                r = run_git(["pull", "--rebase"])
                self._json({"ok": r["ok"], "output": r["stdout"], "error": r["stderr"]})
                return

            if action == "configure" and method == "POST":
                body = self._read_body()
                remote_url = body.get("remote_url", "")
                if remote_url:
                    run_git(["remote", "remove", "origin"])
                    r = run_git(["remote", "add", "origin", remote_url])
                    self._json({"ok": r["ok"]})
                else:
                    self._json({"ok": False, "error": "remote_url required"}, 400)
                return

            if action == "history" and method == "GET":
                r = run_git(["log", "--format=%H|%ai|%s", "-20"])
                commits = []
                for line in r["stdout"].splitlines():
                    if not line.strip():
                        continue
                    parts = line.split("|", 2)
                    if len(parts) == 3:
                        commits.append({"hash": parts[0], "date": parts[1][:16], "message": parts[2]})
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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
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
