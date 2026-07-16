#!/usr/bin/env python3
"""Skills Sync Manager - Web UI Server
A single-file Python HTTP server providing a web management interface.
Port: 8770 (default)
"""
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# ── Paths ──────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = SCRIPT_DIR / "skills"
CONFIG_FILE = SCRIPT_DIR / "config.yaml"
TRASH_FILE = SCRIPT_DIR / ".trash.json"
PS = "powershell.exe"


# ── Simple YAML parser (no deps) ──────────────────────
def parse_yaml(path):
    """Minimal YAML parser for our config format."""
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


def write_yaml_value(path, key_path, value):
    """Update a single value in config.yaml using regex."""
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    # For active_presets, find the line and replace
    if key_path == "active_presets":
        for i, line in enumerate(lines):
            if "active_presets:" in line:
                indent = line[:len(line) - len(line.lstrip())]
                lines[i] = f'{indent}active_presets: {json.dumps(value)}\n'
                break
    Path(path).write_text("".join(lines), encoding="utf-8")


def save_config(data):
    """Write full config back - not used, we do targeted edits."""
    pass


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
    """Scan central skills directory."""
    skills = []
    if not SKILLS_DIR.exists():
        return skills
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
        size = md_path.stat().st_size
        skills.append({
            "name": fm.get("name", d.name),
            "dir": d.name,
            "description": fm.get("description", ""),
            "enabled": enabled,
            "size": size,
            "path": str(md_path),
            "frontmatter": fm,
        })
    return skills


# ── Agent detection ───────────────────────────────────
AGENT_REGISTRY = [
    {"key": "claude_code", "label": "Claude Code", "detect": ".claude", "skills": ".claude/skills"},
    {"key": "cursor", "label": "Cursor", "detect": ".cursor", "skills": ".cursor/skills"},
    {"key": "codex", "label": "Codex", "detect": ".codex", "skills": ".codex/skills"},
    {"key": "copilot", "label": "GitHub Copilot", "detect": ".copilot", "skills": ".copilot/skills"},
    {"key": "gemini_cli", "label": "Gemini CLI", "detect": ".gemini", "skills": ".gemini/skills"},
    {"key": "windsurf", "label": "Windsurf", "detect": ".codeium/windsurf", "skills": ".codeium/windsurf/skills"},
    {"key": "trae", "label": "Trae", "detect": ".trae", "skills": ".trae/skills"},
    {"key": "grok", "label": "Grok", "detect": ".grok", "skills": ".grok/skills"},
    {"key": "opencode", "label": "OpenCode", "detect": ".opencode", "skills": ".opencode/skills"},
    {"key": "amp", "label": "Amp", "detect": ".amp", "skills": ".amp/skills"},
    {"key": "kilo_code", "label": "Kilo Code", "detect": ".kilocode", "skills": ".kilocode/skills"},
    {"key": "roo_code", "label": "Roo Code", "detect": ".roo", "skills": ".roo/skills"},
    {"key": "goose", "label": "Goose", "detect": ".goose", "skills": ".goose/skills"},
    {"key": "cline", "label": "Cline", "detect": ".cline", "skills": ".cline/skills"},
    {"key": "droid", "label": "Droid", "detect": ".droid", "skills": ".droid/skills"},
]


def detect_agents():
    home = Path.home()
    found = []
    for a in AGENT_REGISTRY:
        detect_dir = home / a["detect"]
        if detect_dir.exists():
            skills_dir = home / a["skills"]
            count = 0
            if skills_dir.exists():
                count = sum(1 for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists() or (d / "SKILL.md.disabled").exists())
            found.append({
                "key": a["key"],
                "label": a["label"],
                "installed": True,
                "skills_dir": str(skills_dir),
                "skill_count": count,
            })
    return found


def get_sync_status():
    """Check sync status for each configured agent."""
    cfg = parse_yaml(CONFIG_FILE)
    agents_cfg = cfg.get("agents", {})
    results = []
    for name, acfg in agents_cfg.items():
        if not isinstance(acfg, dict):
            continue
        agent_path = acfg.get("path", "")
        tool = acfg.get("tool", "")
        presets = acfg.get("active_presets", [])
        skills_list = acfg.get("skills", [])
        p = Path(agent_path.replace("~", str(Path.home())))
        synced = []
        missing = []
        if p.exists():
            for sd in sorted(SKILLS_DIR.iterdir()):
                if not sd.is_dir():
                    continue
                target = p / sd.name
                if target.exists() or target.is_symlink():
                    synced.append(sd.name)
                else:
                    missing.append(sd.name)
        results.append({
            "name": name,
            "tool": tool,
            "path": agent_path,
            "active_presets": presets,
            "skills": skills_list,
            "synced": synced,
            "missing": missing,
            "synced_count": len(synced),
            "total_count": len(synced) + len(missing),
        })
    return results


# ── PowerShell helpers ────────────────────────────────
def run_ps(script, args=None, timeout=30):
    cmd = [PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT_DIR / script)]
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
            return json.loads(r["stdout"])
        except:
            return {"projects": [], "global_agents": []}
    return {"projects": [], "global_agents": [], "error": r["stderr"]}


# ── HTML SPA ──────────────────────────────────────────
HTML = r'''<!DOCTYPE html>
<html lang="en" class="antialiased">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Skills Sync Manager</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<script>
tailwind.config={darkMode:"class",theme:{extend:{fontFamily:{sans:['Outfit','sans-serif']},colors:{primary:{50:'#eef2ff',100:'#e0e7ff',200:'#c3dafe',300:'#a3bffa',400:'#7f9cf5',500:'#667eea',600:'#5a67d8',700:'#4c51bf',800:'#434190',900:'#3c366b'}},animation:{'blob':'blob 7s infinite','fade-in-up':'fadeInUp 0.6s cubic-bezier(0.16,1,0.3,1) forwards'},keyframes:{blob:{'0%':{transform:'translate(0px,0px) scale(1)'},'33%':{transform:'translate(30px,-50px) scale(1.1)'},'66%':{transform:'translate(-20px,20px) scale(0.9)'},'100%':{transform:'translate(0px,0px) scale(1)'}},fadeInUp:{'0%':{opacity:'0',transform:'translateY(20px)'},'100%':{opacity:'1',transform:'translateY(0)'}}}}}
</script>
<style>
body{font-family:'Outfit',sans-serif}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(156,163,175,.4);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:rgba(107,114,128,.6)}
.glass-panel{background:rgba(255,255,255,.85);backdrop-filter:blur(40px);-webkit-backdrop-filter:blur(40px);border:1px solid rgba(255,255,255,.6);box-shadow:0 20px 40px -10px rgba(0,0,0,.1),0 0 0 1px rgba(255,255,255,.4) inset}
.dark .glass-panel{background:rgba(15,23,42,.75);backdrop-filter:blur(40px);-webkit-backdrop-filter:blur(40px);border:1px solid rgba(255,255,255,.1);box-shadow:0 30px 60px -12px rgba(0,0,0,.6),0 0 0 1px rgba(255,255,255,.05) inset}
.btn-gradient{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);background-size:200% auto;color:#fff;transition:.3s ease;box-shadow:0 10px 20px -5px rgba(102,126,234,.4)}
.btn-gradient:hover{background-position:right center;box-shadow:0 15px 25px -5px rgba(102,126,234,.5);transform:translateY(-1px)}
.btn-gradient:active{transform:translateY(1px)}
.input-modern{background:rgba(255,255,255,.7);border:2px solid rgba(209,213,219,.6);color:#1f2937;transition:all .3s ease}
.input-modern:focus{background:#fff;border-color:#667eea;box-shadow:0 0 0 4px rgba(102,126,234,.15);outline:none}
.dark .input-modern{background:rgba(15,23,42,.7);border:2px solid rgba(71,85,105,.6);color:#f8fafc}
.dark .input-modern:focus{background:rgba(15,23,42,.95);border-color:#7f9cf5;box-shadow:0 0 0 4px rgba(127,156,245,.15)}
.tab-active{position:relative;color:#667eea;font-weight:600}
.dark .tab-active{color:#a3bffa}
.tab-active::after{content:'';position:absolute;bottom:-2px;left:0;width:100%;height:3px;background:linear-gradient(90deg,#667eea,#ed64a6);border-radius:3px 3px 0 0}
.drawer-scroll::-webkit-scrollbar{width:5px}
.drawer-scroll::-webkit-scrollbar-thumb{background:rgba(100,116,139,.3);border-radius:3px}
.gradient-text{background:linear-gradient(135deg,#667eea,#ed64a6,#667eea);background-size:300%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:gradText 6s ease-in-out infinite}
@keyframes gradText{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
</style>
<script>
if(localStorage.theme==='dark'||(!('theme' in localStorage)&&window.matchMedia('(prefers-color-scheme:dark)').matches)){document.documentElement.classList.add('dark')}
</script>
</head>
<body class="bg-slate-50 dark:bg-black text-slate-800 dark:text-slate-200 min-h-screen transition-colors duration-300">

<!-- Animated Background -->
<div class="fixed inset-0 overflow-hidden pointer-events-none z-0">
  <div class="absolute top-0 -left-4 w-72 h-72 bg-purple-400 rounded-full mix-blend-multiply filter blur-2xl opacity-15 dark:opacity-10 animate-blob"></div>
  <div class="absolute top-0 -right-4 w-72 h-72 bg-blue-400 rounded-full mix-blend-multiply filter blur-2xl opacity-15 dark:opacity-10 animate-blob" style="animation-delay:2s"></div>
  <div class="absolute -bottom-8 left-20 w-72 h-72 bg-pink-400 rounded-full mix-blend-multiply filter blur-2xl opacity-15 dark:opacity-10 animate-blob" style="animation-delay:4s"></div>
</div>

<!-- App Container -->
<div class="relative z-10 min-h-screen flex flex-col">

<!-- Header -->
<header class="glass-panel mx-4 mt-4 rounded-2xl px-6 py-4 flex items-center gap-4 flex-wrap">
  <h1 class="text-xl font-bold tracking-tight flex items-center gap-2">
    <svg class="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/></svg>
    <span>Skills</span><span class="gradient-text">Sync</span>
  </h1>
  <nav class="flex space-x-1 bg-slate-200/60 dark:bg-slate-800/60 p-1 rounded-xl" id="tabNav">
    <button onclick="switchTab('dashboard')" class="tab-btn px-4 py-2 text-sm font-semibold rounded-lg transition-all duration-300 text-slate-500 hover:text-slate-700 dark:hover:text-slate-200" data-tab="dashboard">Dashboard</button>
    <button onclick="switchTab('skills')" class="tab-btn px-4 py-2 text-sm font-semibold rounded-lg transition-all duration-300 text-slate-500 hover:text-slate-700 dark:hover:text-slate-200" data-tab="skills">Skills</button>
    <button onclick="switchTab('presets')" class="tab-btn px-4 py-2 text-sm font-semibold rounded-lg transition-all duration-300 text-slate-500 hover:text-slate-700 dark:hover:text-slate-200" data-tab="presets">Presets</button>
    <button onclick="switchTab('agents')" class="tab-btn px-4 py-2 text-sm font-semibold rounded-lg transition-all duration-300 text-slate-500 hover:text-slate-700 dark:hover:text-slate-200" data-tab="agents">Agents</button>
  </nav>
  <div class="ml-auto flex items-center gap-2">
    <button onclick="syncAll()" class="btn-gradient px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-1.5">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
      Sync All
    </button>
    <button onclick="toggleTheme()" class="p-2 rounded-xl bg-white/60 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-800 transition-all">
      <svg id="theme-icon-dark" class="hidden w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
      <svg id="theme-icon-light" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>
    </button>
  </div>
</header>

<!-- Main Content -->
<main class="flex-1 mx-4 my-4 overflow-hidden">

  <!-- Dashboard Page -->
  <div id="page-dashboard" class="page h-full overflow-auto rounded-2xl"></div>

  <!-- Skills Page -->
  <div id="page-skills" class="page h-full hidden">
    <div class="flex h-full gap-4">
      <div class="flex-1 flex flex-col glass-panel rounded-2xl overflow-hidden">
        <div class="p-4 border-b border-slate-200/60 dark:border-slate-700/50">
          <div class="relative">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <input id="skillSearch" placeholder="Search skills..." oninput="renderSkills()" class="input-modern w-full pl-10 pr-4 py-2.5 rounded-xl text-sm">
          </div>
        </div>
        <div class="flex-1 overflow-auto"><table class="w-full text-sm"><thead class="sticky top-0 bg-slate-100/80 dark:bg-slate-800/80 backdrop-blur-sm"><tr><th class="px-4 py-3 text-left font-semibold text-slate-500 text-xs uppercase tracking-wider">#</th><th class="px-4 py-3 text-left font-semibold text-slate-500 text-xs uppercase tracking-wider">Status</th><th class="px-4 py-3 text-left font-semibold text-slate-500 text-xs uppercase tracking-wider">Name</th><th class="px-4 py-3 text-left font-semibold text-slate-500 text-xs uppercase tracking-wider">Description</th><th class="px-4 py-3 text-left font-semibold text-slate-500 text-xs uppercase tracking-wider">Agents</th></tr></thead><tbody id="skillBody"></tbody></table></div>
      </div>
      <div class="w-96 glass-panel rounded-2xl overflow-auto drawer-scroll p-5 flex-shrink-0" id="skillDrawer">
        <div class="flex flex-col items-center justify-center h-full text-slate-400 dark:text-slate-500">
          <svg class="w-12 h-12 mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          <p class="text-sm font-medium">Click a skill to preview</p>
        </div>
      </div>
    </div>
  </div>

  <!-- Presets Page -->
  <div id="page-presets" class="page h-full overflow-auto rounded-2xl"></div>

  <!-- Agents Page -->
  <div id="page-agents" class="page h-full overflow-auto rounded-2xl"></div>

</main>
</div>

<!-- Modal -->
<div class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 hidden transition-opacity" id="modalBg">
  <div class="glass-panel rounded-2xl p-6 min-w-[400px] max-w-[560px] mx-4 animate-fade-in-up" id="modal"></div>
</div>

<!-- Toast -->
<div id="toast" class="fixed bottom-6 right-6 px-5 py-3 rounded-xl shadow-2xl transform translate-y-20 opacity-0 transition-all duration-300 z-50 hidden items-center gap-2 backdrop-blur-md font-semibold text-sm border"></div>

<script>
let SKILLS=[],AGENTS=[],PRESETS=[],SYNC_STATUS=[],SEL_SKILL=null;

async function api(path,opts={}){const r=await fetch(path,{headers:{'Content-Type':'application/json'},...opts});return r.json();}
function esc(s){return(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

// Theme
function updateThemeIcons(){const d=document.documentElement.classList.contains('dark');document.getElementById('theme-icon-dark').classList.toggle('hidden',d);document.getElementById('theme-icon-light').classList.toggle('hidden',!d);}
function toggleTheme(){if(document.documentElement.classList.contains('dark')){document.documentElement.classList.remove('dark');localStorage.theme='light'}else{document.documentElement.classList.add('dark');localStorage.theme='dark'}updateThemeIcons();}
updateThemeIcons();

// Toast
function showToast(msg,type='success'){const t=document.getElementById('toast');t.className='fixed bottom-6 right-6 px-5 py-3 rounded-xl shadow-2xl transition-all duration-300 z-50 flex items-center gap-2 backdrop-blur-md font-semibold text-sm border';if(type==='success'){t.classList.add('bg-green-50/90','dark:bg-green-900/90','text-green-700','dark:text-green-100','border-green-200','dark:border-green-800')}else{t.classList.add('bg-red-50/90','dark:bg-red-900/90','text-red-700','dark:text-red-100','border-red-200','dark:border-red-800')}t.innerHTML=`<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${type==='success'?'M5 13l4 4L19 7':'M6 18L18 6M6 6l12 12'}"/></svg>${esc(msg)}`;setTimeout(()=>{t.classList.add('translate-y-20','opacity-0','hidden')},3000);}

// Tabs
function switchTab(name){
  document.querySelectorAll('.page').forEach(p=>p.classList.add('hidden'));
  document.getElementById('page-'+name).classList.remove('hidden');
  document.querySelectorAll('.tab-btn').forEach(b=>{b.classList.remove('bg-white','dark:bg-slate-700','text-primary-600','dark:text-primary-400','shadow-sm');b.classList.add('text-slate-500')});
  const active=document.querySelector(`.tab-btn[data-tab="${name}"]`);if(active){active.classList.add('bg-white','dark:bg-slate-700','text-primary-600','dark:text-primary-400','shadow-sm');active.classList.remove('text-slate-500')}
  if(name==='dashboard')renderDashboard();else if(name==='skills')renderSkills();else if(name==='presets')renderPresets();else if(name==='agents')renderAgents();
}

async function refresh(){
  const d=await api('/api/skills');SKILLS=d.skills||[];
  const a=await api('/api/agents');AGENTS=a.agents||[];SYNC_STATUS=a.sync_status||[];
  const p=await api('/api/presets');PRESETS=p.presets||[];
  const cur=document.querySelector('.tab-btn.bg-white,.tab-btn.text-primary-600');
  const tab=cur?cur.dataset.tab:'dashboard';switchTab(tab);
}

// Dashboard
function renderDashboard(){
  const el=document.getElementById('page-dashboard');
  const total=SKILLS.length,enabled=SKILLS.filter(s=>s.enabled).length;
  el.innerHTML=`<div class="glass-panel rounded-2xl p-6 animate-fade-in-up">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div class="bg-gradient-to-br from-blue-500/10 to-purple-500/10 dark:from-blue-500/20 dark:to-purple-500/20 rounded-2xl p-5 border border-blue-200/30 dark:border-blue-800/30">
        <div class="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider mb-1">Total Skills</div>
        <div class="text-3xl font-bold text-slate-800 dark:text-white">${total}</div>
        <div class="text-xs text-slate-500 mt-1">${enabled} enabled</div>
      </div>
      <div class="bg-gradient-to-br from-green-500/10 to-emerald-500/10 dark:from-green-500/20 dark:to-emerald-500/20 rounded-2xl p-5 border border-green-200/30 dark:border-green-800/30">
        <div class="text-xs font-semibold text-green-600 dark:text-green-400 uppercase tracking-wider mb-1">Agents</div>
        <div class="text-3xl font-bold text-slate-800 dark:text-white">${AGENTS.length}</div>
        <div class="text-xs text-slate-500 mt-1">${SYNC_STATUS.length} configured</div>
      </div>
      <div class="bg-gradient-to-br from-purple-500/10 to-pink-500/10 dark:from-purple-500/20 dark:to-pink-500/20 rounded-2xl p-5 border border-purple-200/30 dark:border-purple-800/30">
        <div class="text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-wider mb-1">Presets</div>
        <div class="text-3xl font-bold text-slate-800 dark:text-white">${PRESETS.length}</div>
      </div>
      <div class="bg-gradient-to-br from-amber-500/10 to-orange-500/10 dark:from-amber-500/20 dark:to-orange-500/20 rounded-2xl p-5 border border-amber-200/30 dark:border-amber-800/30">
        <div class="text-xs font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider mb-1">Sync Mode</div>
        <div class="text-2xl font-bold text-slate-800 dark:text-white">symlink</div>
      </div>
    </div>
    <h2 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Agent Sync Status</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">${SYNC_STATUS.map(a=>`
      <div class="bg-white/50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200/50 dark:border-slate-700/50">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-2 h-2 rounded-full ${a.synced_count===a.total_count?'bg-green-500':'bg-amber-500'} animate-pulse"></div>
          <h3 class="font-bold text-sm text-slate-800 dark:text-white">${esc(a.name)}</h3>
        </div>
        <p class="text-xs text-slate-500 mb-3 font-mono">${esc(a.path)}</p>
        <div class="flex items-center gap-2 mb-2">
          <div class="flex-1 bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden"><div class="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500" style="width:${a.total_count?a.synced_count/a.total_count*100:0}%"></div></div>
          <span class="text-xs font-bold text-slate-600 dark:text-slate-300">${a.synced_count}/${a.total_count}</span>
        </div>
        <div class="flex flex-wrap gap-1">${(a.active_presets||[]).map(p=>`<span class="px-2 py-0.5 text-xs rounded-full bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 font-medium">${esc(p)}</span>`).join('')}</div>
      </div>`).join('')}
    </div>
  </div>`;
}

// Skills
function renderSkills(){
  const tbody=document.getElementById('skillBody');
  const q=(document.getElementById('skillSearch')?.value||'').toLowerCase();
  const rows=SKILLS.filter(s=>!q||s.name.toLowerCase().includes(q)||(s.description||'').toLowerCase().includes(q));
  tbody.innerHTML=rows.map((s,i)=>{
    const sel=SEL_SKILL===s.dir;
    const dots=SYNC_STATUS.map(a=>{const ok=a.synced.includes(s.dir);return`<span class="inline-block w-2 h-2 rounded-full ${ok?'bg-green-400':'bg-red-400/50'}" title="${esc(a.name)}: ${ok?'synced':'missing'}"></span>`}).join('');
    return`<tr class="cursor-pointer transition-colors ${sel?'bg-primary-50 dark:bg-primary-900/20':'hover:bg-slate-50 dark:hover:bg-slate-800/50'} ${!s.enabled?'opacity-40':''}" onclick="selectSkill('${s.dir}')">
      <td class="px-4 py-3 text-slate-400 text-xs">${i+1}</td>
      <td class="px-4 py-3"><span class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs ${s.enabled?'bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-400':'bg-red-100 dark:bg-red-900/40 text-red-500'}">${s.enabled?'✓':'✗'}</span></td>
      <td class="px-4 py-3 font-semibold text-slate-800 dark:text-white">${esc(s.name)}</td>
      <td class="px-4 py-3 text-slate-500 text-xs max-w-[200px] truncate">${esc((s.description||'').substring(0,60))}</td>
      <td class="px-4 py-3"><div class="flex gap-1">${dots}</div></td>
    </tr>`}).join('');
}

async function selectSkill(dir){
  SEL_SKILL=dir;renderSkills();
  const d=await api('/api/skills/'+encodeURIComponent(dir)+'/content');
  const s=d.skill||{};
  const dots=SYNC_STATUS.map(a=>{const ok=a.synced.includes(dir);return`<span class="inline-block w-2.5 h-2.5 rounded-full ${ok?'bg-green-400':'bg-red-400/50'}" title="${esc(a.name)}"></span>`}).join('');
  document.getElementById('skillDrawer').innerHTML=`
    <div class="animate-fade-in-up">
      <h2 class="text-lg font-bold text-slate-800 dark:text-white mb-1">${esc(s.name||dir)}</h2>
      <p class="text-xs text-slate-500 mb-3">${esc(s.description||'')} · ${s.size||0}B</p>
      <div class="flex items-center gap-2 mb-4">
        <span class="px-2 py-0.5 text-xs rounded-full font-medium ${s.enabled?'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300':'bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-300'}">${s.enabled?'Enabled':'Disabled'}</span>
        <div class="flex gap-1 ml-auto">${dots}</div>
      </div>
      <div class="flex gap-2 mb-4">
        <button onclick="toggleSkill('${dir}',${s.enabled})" class="px-3 py-1.5 text-xs font-semibold rounded-lg ${s.enabled?'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200':'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 hover:bg-green-200'} transition-colors">${s.enabled?'Disable':'Enable'}</button>
        <button onclick="editSkillModal('${dir}')" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 transition-colors">Edit</button>
        <button onclick="deleteSkill('${dir}')" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-red-50 dark:bg-red-900/20 text-red-500 hover:bg-red-100 transition-colors">Delete</button>
      </div>
      <div class="border-t border-slate-200 dark:border-slate-700 pt-3">
        <h3 class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Content</h3>
        <pre class="bg-slate-100/80 dark:bg-black/40 rounded-xl p-3 text-xs overflow-auto max-h-[50vh] whitespace-pre-wrap break-words text-slate-700 dark:text-slate-300 font-mono">${esc(d.content||'')}</pre>
      </div>
    </div>`;
}

async function toggleSkill(dir,on){const r=await api('/api/skills/'+encodeURIComponent(dir)+'/'+(on?'disable':'enable'),{method:'POST'});if(r.ok){await refresh();if(SEL_SKILL===dir)selectSkill(dir);showToast(on?'Disabled':'Enabled');}else showToast('Failed','error');}
async function deleteSkill(dir){if(!confirm('Move "'+dir+'" to trash?'))return;const r=await api('/api/skills/'+encodeURIComponent(dir)+'/delete',{method:'POST'});if(r.ok){SEL_SKILL=null;await refresh();showToast('Deleted');}else showToast('Failed','error');}
function editSkillModal(dir){const s=SKILLS.find(x=>x.dir===dir);if(!s)return;document.getElementById('modal').innerHTML=`<h3 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Edit: ${esc(s.name)}</h3><label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Name</label><input id="ename" value="${esc(s.name)}" class="input-modern w-full px-4 py-2.5 rounded-xl mb-3"><label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Description</label><textarea id="edesc" class="input-modern w-full px-4 py-2.5 rounded-xl mb-4 min-h-[80px]">${esc(s.description||'')}</textarea><div class="flex justify-end gap-2"><button onclick="closeModal()" class="px-4 py-2 text-sm font-semibold rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 transition-colors">Cancel</button><button onclick="saveEditSkill('${dir}')" class="btn-gradient px-4 py-2 text-sm font-bold rounded-xl">Save</button></div>`;document.getElementById('modalBg').classList.remove('hidden');}
async function saveEditSkill(dir){const name=document.getElementById('ename').value;const description=document.getElementById('edesc').value;const r=await api('/api/skills/'+encodeURIComponent(dir)+'/edit',{method:'POST',body:JSON.stringify({name,description})});closeModal();if(r.ok){await refresh();selectSkill(dir);showToast('Saved');}else showToast('Failed','error');}
function closeModal(){document.getElementById('modalBg').classList.add('hidden');}
document.getElementById('modalBg').onclick=e=>{if(e.target.id==='modalBg')closeModal();};

// Presets
function renderPresets(){
  const el=document.getElementById('page-presets');
  el.innerHTML=`<div class="glass-panel rounded-2xl p-6 animate-fade-in-up">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-lg font-bold text-slate-800 dark:text-white">Presets (${PRESETS.length})</h2>
      <button onclick="createPresetModal()" class="btn-gradient px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-1.5"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>New Preset</button>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">${PRESETS.map(p=>{
      const skills=p.skills||[];
      const agentBtns=SYNC_STATUS.map(a=>{const isActive=(a.active_presets||[]).includes(p.name);return isActive?`<button onclick="deactivatePreset('${p.name}','${a.name}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 transition-colors">Deactivate ${esc(a.name)}</button>`:`<button onclick="activatePreset('${p.name}','${a.name}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 hover:bg-green-200 transition-colors">Activate ${esc(a.name)}</button>`}).join('');
      return`<div class="bg-white/50 dark:bg-slate-800/50 rounded-xl p-5 border border-slate-200/50 dark:border-slate-700/50 hover:border-primary-300 dark:hover:border-primary-700 transition-colors">
        <h3 class="font-bold text-slate-800 dark:text-white mb-1">${esc(p.name)}</h3>
        <p class="text-xs text-slate-500 mb-3">${esc(p.description||'')}</p>
        <div class="flex flex-wrap gap-1.5 mb-3">${skills.map(s=>`<span class="px-2 py-0.5 text-xs rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-medium">${esc(s)}</span>`).join('')}</div>
        <div class="flex flex-wrap gap-1.5">${agentBtns}</div>
      </div>`}).join('')}
    </div>
  </div>`;
}
async function activatePreset(p,a){const r=await api('/api/presets/'+encodeURIComponent(p)+'/activate',{method:'POST',body:JSON.stringify({agent:a})});if(r.ok){await refresh();showToast('Activated');}else showToast('Failed','error');}
async function deactivatePreset(p,a){const r=await api('/api/presets/'+encodeURIComponent(p)+'/deactivate',{method:'POST',body:JSON.stringify({agent:a})});if(r.ok){await refresh();showToast('Deactivated');}else showToast('Failed','error');}
function createPresetModal(){document.getElementById('modal').innerHTML=`<h3 class="text-lg font-bold text-slate-800 dark:text-white mb-4">New Preset</h3><label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Name</label><input id="pname" class="input-modern w-full px-4 py-2.5 rounded-xl mb-3"><label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Description</label><input id="pdesc" class="input-modern w-full px-4 py-2.5 rounded-xl mb-3"><label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Skills (comma-separated)</label><textarea id="pskills" class="input-modern w-full px-4 py-2.5 rounded-xl mb-4 min-h-[80px]">${SKILLS.map(s=>s.dir).join(', ')}</textarea><div class="flex justify-end gap-2"><button onclick="closeModal()" class="px-4 py-2 text-sm font-semibold rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Cancel</button><button onclick="createPreset()" class="btn-gradient px-4 py-2 text-sm font-bold rounded-xl">Create</button></div>`;document.getElementById('modalBg').classList.remove('hidden');}
async function createPreset(){const name=document.getElementById('pname').value;const description=document.getElementById('pdesc').value;const skills=document.getElementById('pskills').value.split(',').map(s=>s.trim()).filter(Boolean);const r=await api('/api/presets',{method:'POST',body:JSON.stringify({name,description,skills})});closeModal();if(r.ok){await refresh();showToast('Created');}else showToast('Failed','error');}

// Agents
function renderAgents(){
  const el=document.getElementById('page-agents');
  el.innerHTML=`<div class="glass-panel rounded-2xl p-6 animate-fade-in-up">
    <h2 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Installed Agents (${AGENTS.length})</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">${AGENTS.map(a=>`
      <div class="bg-white/50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200/50 dark:border-slate-700/50">
        <div class="flex items-center gap-2 mb-2"><div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div><h3 class="font-bold text-sm text-slate-800 dark:text-white">${esc(a.label)}</h3></div>
        <p class="text-xs text-slate-500 font-mono mb-2 truncate">${esc(a.skills_dir)}</p>
        <div class="text-sm"><span class="font-bold text-green-600 dark:text-green-400">${a.skill_count}</span> <span class="text-slate-500">skills</span></div>
      </div>`).join('')}
    </div>
    <h2 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Scan Projects</h2>
    <div class="flex flex-wrap gap-3 items-end mb-4">
      <div class="flex-1 min-w-[200px]"><label class="block text-xs font-semibold text-slate-500 mb-1">Path</label><input id="scanPath" value="D:\\06_Project" class="input-modern w-full px-4 py-2.5 rounded-xl text-sm font-mono"></div>
      <div class="w-28"><label class="block text-xs font-semibold text-slate-500 mb-1">Depth</label><select id="scanDepth" class="input-modern w-full px-3 py-2.5 rounded-xl text-sm"><option value="2">2</option><option value="3" selected>3</option><option value="4">4</option></select></div>
      <button onclick="doScan()" class="btn-gradient px-5 py-2.5 rounded-xl text-sm font-bold">Scan</button>
      <button onclick="doScanImport()" class="px-5 py-2.5 rounded-xl text-sm font-bold bg-green-500 hover:bg-green-600 text-white transition-colors shadow-lg shadow-green-500/25">Scan & Import</button>
    </div>
    <div id="scanResults" class="hidden bg-slate-100/80 dark:bg-black/40 rounded-xl p-4 mb-8"><pre id="scanOutput" class="text-xs font-mono text-slate-600 dark:text-slate-400 whitespace-pre-wrap"></pre></div>
    <h2 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Sync Configuration</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">${SYNC_STATUS.map(a=>`
      <div class="bg-white/50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200/50 dark:border-slate-700/50">
        <h3 class="font-bold text-sm text-slate-800 dark:text-white mb-1">${esc(a.name)}</h3>
        <p class="text-xs text-slate-500 font-mono mb-2">${esc(a.tool)} · ${esc(a.path)}</p>
        <div class="flex items-center gap-2"><div class="flex-1 bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden"><div class="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500" style="width:${a.total_count?a.synced_count/a.total_count*100:0}%"></div></div><span class="text-xs font-bold text-slate-500">${a.synced_count}/${a.total_count}</span></div>
        <div class="flex flex-wrap gap-1 mt-2">${(a.active_presets||[]).map(p=>`<span class="px-2 py-0.5 text-xs rounded-full bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 font-medium">${esc(p)}</span>`).join('')}</div>
      </div>`).join('')}
    </div>
  </div>`;
}
async function doScan(){const path=document.getElementById('scanPath').value;const depth=document.getElementById('scanDepth').value;document.getElementById('scanResults').classList.remove('hidden');document.getElementById('scanOutput').textContent='Scanning...';const r=await api('/api/scan',{method:'POST',body:JSON.stringify({path,max_depth:parseInt(depth)})});document.getElementById('scanOutput').textContent=JSON.stringify(r,null,2);}
async function doScanImport(){const path=document.getElementById('scanPath').value;const depth=document.getElementById('scanDepth').value;document.getElementById('scanResults').classList.remove('hidden');document.getElementById('scanOutput').textContent='Scanning and importing...';const r=await api('/api/scan/import',{method:'POST',body:JSON.stringify({path,max_depth:parseInt(depth)})});document.getElementById('scanOutput').textContent=JSON.stringify(r,null,2);await refresh();}
async function syncAll(){showToast('Syncing...');const r=await api('/api/sync',{method:'POST'});showToast(r.ok?'Sync complete!':'Sync failed',r.ok?'success':'error');await refresh();}

// Init
(async()=>{await refresh();switchTab('dashboard');})();
</script>
</body>
</html>'''


# ── HTTP Handler ──────────────────────────────────────
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress logs

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

    def _route(self, method):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        parts = path.split("/")

        # Serve HTML
        if path == "" or path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            body = HTML.encode("utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # API routes
        if path == "/api/skills" and method == "GET":
            self._json({"skills": scan_skills()})
            return

        if path == "/api/agents" and method == "GET":
            agents = detect_agents()
            sync_status = get_sync_status()
            self._json({"agents": agents, "sync_status": sync_status})
            return

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
                presets.append({
                    "name": name,
                    "description": pcfg.get("description", ""),
                    "skills": skills,
                })
            self._json({"presets": presets})
            return

        if path == "/api/status" and method == "GET":
            self._json({
                "skills": scan_skills(),
                "agents": detect_agents(),
                "sync_status": get_sync_status(),
            })
            return

        if path == "/api/trash" and method == "GET":
            self._json({"items": load_trash()})
            return

        # /api/sync
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

        # /api/scan
        if path == "/api/scan" and method == "POST":
            body = self._read_body()
            result = scan_projects(body.get("path", "."), body.get("max_depth", 3))
            self._json(result)
            return

        # /api/scan/import
        if path == "/api/scan/import" and method == "POST":
            body = self._read_body()
            scan_path = body.get("path", ".")
            max_depth = body.get("max_depth", 3)
            r = run_ps("scan-agents.ps1", ["-ScanPath", scan_path, "-MaxDepth", str(max_depth), "-Import"])
            self._json({"ok": r["ok"], "output": r["stdout"], "error": r["stderr"]})
            return

        # /api/presets (create)
        if path == "/api/presets" and method == "POST":
            body = self._read_body()
            name = body.get("name", "")
            desc = body.get("description", "")
            skills = body.get("skills", [])
            if not name:
                self._json({"ok": False, "error": "name required"}, 400)
                return
            # Append to config.yaml
            text = Path(CONFIG_FILE).read_text(encoding="utf-8")
            skills_yaml = json.dumps(skills)  # close enough for simple lists
            skills_yaml = "[" + ", ".join(f'"{s}"' for s in skills) + "]"
            new_block = f'  {name}:\n    description: "{desc}"\n    skills: {skills_yaml}\n'
            # Insert before the agents section or at end of presets
            if "\nagents:" in text:
                text = text.replace("\nagents:", new_block + "\nagents:")
            else:
                text += "\n" + new_block
            Path(CONFIG_FILE).write_text(text, encoding="utf-8")
            self._json({"ok": True})
            return

        # /api/skills/<name>/... routes
        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "skills":
            skill_name = parts[3]
            action = parts[4] if len(parts) > 4 else None

            if action == "content" and method == "GET":
                skill_dir = SKILLS_DIR / skill_name
                for fname in ["SKILL.md", "SKILL.md.disabled"]:
                    fp = skill_dir / fname
                    if fp.exists():
                        text = fp.read_text(encoding="utf-8", errors="replace")
                        fm = parse_frontmatter(text)
                        self._json({
                            "skill": {
                                "name": fm.get("name", skill_name),
                                "description": fm.get("description", ""),
                                "enabled": fname == "SKILL.md",
                                "size": fp.stat().st_size,
                                "path": str(fp),
                            },
                            "content": text,
                        })
                        return
                self._json({"error": "not found"}, 404)
                return

            if action == "edit" and method == "POST":
                body = self._read_body()
                skill_dir = SKILLS_DIR / skill_name
                for fname in ["SKILL.md", "SKILL.md.disabled"]:
                    fp = skill_dir / fname
                    if fp.exists():
                        text = fp.read_text(encoding="utf-8")
                        # Update frontmatter
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

            if action == "delete" and method == "POST":
                skill_dir = SKILLS_DIR / skill_name
                if not skill_dir.exists():
                    self._json({"error": "not found"}, 404)
                    return
                trash = load_trash()
                trash.append({
                    "name": skill_name,
                    "deleted_at": datetime.now().isoformat(),
                    "dir": str(skill_dir),
                })
                save_trash(trash)
                # Move to .trash directory
                trash_dir = SCRIPT_DIR / ".trash" / skill_name
                trash_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(skill_dir), str(trash_dir))
                self._json({"ok": True})
                return

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

        # /api/trash/<name>/restore
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

        # /api/presets/<name>/activate|deactivate|add-skill|remove-skill
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "presets":
            preset_name = parts[3]
            action = parts[4]

            if action == "activate" and method == "POST":
                body = self._read_body()
                agent = body.get("agent", "")
                cfg = parse_yaml(CONFIG_FILE)
                agents_cfg = cfg.get("agents", {})
                if agent in agents_cfg:
                    current = agents_cfg[agent].get("active_presets", [])
                    if preset_name not in current:
                        current.append(preset_name)
                    write_yaml_value(CONFIG_FILE, "active_presets", current)
                    # Trigger sync for this agent
                    run_ps("sync.ps1", ["-Agent", agent])
                    self._json({"ok": True})
                else:
                    self._json({"error": "agent not found"}, 404)
                return

            if action == "deactivate" and method == "POST":
                body = self._read_body()
                agent = body.get("agent", "")
                cfg = parse_yaml(CONFIG_FILE)
                agents_cfg = cfg.get("agents", {})
                if agent in agents_cfg:
                    current = agents_cfg[agent].get("active_presets", [])
                    if preset_name in current:
                        current.remove(preset_name)
                    write_yaml_value(CONFIG_FILE, "active_presets", current)
                    run_ps("sync.ps1", ["-Agent", agent])
                    self._json({"ok": True})
                else:
                    self._json({"error": "agent not found"}, 404)
                return

            if action == "add-skill" and method == "POST":
                body = self._read_body()
                skill = body.get("skill", "")
                # Append skill to preset in config.yaml
                text = Path(CONFIG_FILE).read_text(encoding="utf-8")
                # Find the preset's skills line and append
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
                    # Remove the skill from the list
                    skills_str = re.sub(rf'[",\s]*"{re.escape(skill)}"[",\s]*', '', skills_str)
                    skills_str = re.sub(r',\s*,', ',', skills_str).strip().strip(',')
                    text = text[:m.start(2)] + skills_str + text[m.end(2):]
                    Path(CONFIG_FILE).write_text(text, encoding="utf-8")
                    self._json({"ok": True})
                else:
                    self._json({"error": "preset not found"}, 404)
                return

        self._json({"error": "not found"}, 404)

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    print(f"Skills Sync Manager Web UI")
    print(f"  http://127.0.0.1:{port}")
    print(f"  Skills dir: {SKILLS_DIR}")
    print(f"  Config: {CONFIG_FILE}")
    print(f"Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
