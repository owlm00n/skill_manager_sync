#!/usr/bin/env python
"""
Bug Hub — Unified dashboard for Bugzilla Assistant skills.
bug-core, bug-logs, bug-workspace, keyword-vault, log-analyzer, protocol-parser, code-generator

Usage:
  python bug-hub.py start [port] [--force]     Start the hub (default 8777)
  python bug-hub.py stop [port]                Stop the hub
  python bug-hub.py restart [port]             Stop then start
  python bug-hub.py status [port]              Print server & module status
"""

import os
import sys
import json
import time
import signal
import socket
import subprocess
import urllib.parse
import http.server
import webbrowser
from pathlib import Path
from threading import Thread

# ── Force UTF-8 on Windows ──────────────────────────────────────────
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── Paths ────────────────────────────────────────────────────────────
HOME = Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))
SKILLS_DIR = HOME / ".claude" / "skills"

# Fallback: use actual project skills directory if ~/.claude/skills doesn't exist
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_SKILLS = _SCRIPT_DIR.parent  # bug-hub/../ = skills/
if not SKILLS_DIR.exists() and _PROJECT_SKILLS.exists():
    _proj_name = _PROJECT_SKILLS.name
    if _proj_name == "skills" or (_PROJECT_SKILLS / "bug-core").exists():
        SKILLS_DIR = _PROJECT_SKILLS

BUG_CORE_DIR = SKILLS_DIR / "bug-core"
BUG_LOGS_DIR = SKILLS_DIR / "bug-logs"
BUG_WORKSPACE_DIR = SKILLS_DIR / "bug-workspace"
KEYWORD_VAULT_DIR = SKILLS_DIR / "keyword-vault"
LOG_ANALYZER_DIR = SKILLS_DIR / "log-analyzer"
PROTOCOL_PARSER_DIR = SKILLS_DIR / "protocol-parser"
PAGES_DIR = _SCRIPT_DIR / "pages"

HUB_DIR = HOME / ".claude" / "bug-hub"
PID_FILE = HUB_DIR / "bug-hub.pid"
HUB_DIR.mkdir(parents=True, exist_ok=True)

# ── Add skill dirs to path ───────────────────────────────────────────
for d in [BUG_CORE_DIR, BUG_LOGS_DIR, BUG_WORKSPACE_DIR, KEYWORD_VAULT_DIR,
          LOG_ANALYZER_DIR, PROTOCOL_PARSER_DIR,
          BUG_CORE_DIR / "mcp-server"]:
    if d.exists():
        sys.path.insert(0, str(d))

# ── Module Registry ──────────────────────────────────────────────────

MODULES = [
    {
        "id": "bug-core",
        "name": "Bug Core",
        "icon": "\U0001F41B",
        "desc": "Bugzilla Bug query — multi-instance query, smart summary, search, offline mode",
        "page": "bug-core.html",
        "status": "ready",
    },
    {
        "id": "bug-logs",
        "name": "Bug Logs",
        "icon": "\U0001F4C2",
        "desc": "Log directory query & attachment download — UNC+FTP dual-channel, structured parsing",
        "page": "bug-logs.html",
        "status": "ready",
    },
    {
        "id": "bug-workspace",
        "name": "Bug Workspace",
        "icon": "\U0001F4C1",
        "desc": "Workspace creation & orchestration — folder gen, .url shortcuts, Bug Z template, path history",
        "page": "bug-workspace.html",
        "status": "ready",
    },
    {
        "id": "keyword-vault",
        "name": "Keyword Vault",
        "icon": "\U0001F511",
        "desc": "Debug keyword management — CRUD by direction, role profiles, auto-learn",
        "page": "keyword-vault.html",
        "status": "ready",
    },
    {
        "id": "log-analyzer",
        "name": "Log Analyzer",
        "icon": "\U0001F4CA",
        "desc": "Role-aware log analysis — anomaly detection, timeline reconstruction, interactive viewer",
        "page": "log-analyzer.html",
        "status": "ready",
    },
    {
        "id": "protocol-parser",
        "name": "Protocol Parser",
        "icon": "\U0001F50C",
        "desc": "PD/USB/CC protocol parsing & visualization — AI-driven, any log format",
        "page": "protocol-parser.html",
        "status": "ready",
    },
    {
        "id": "code-generator",
        "name": "Code Generator",
        "icon": "\U0001F4C4",
        "desc": "Debug code generation — 3-level grading (quick debug / full diagnosis / production fix)",
        "page": "code-generator.html",
        "status": "ready",
    },
]


# ── Port check ───────────────────────────────────────────────────────

def is_port_open(port):
    if port is None:
        return False
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=0.3)
        s.close()
        return True
    except (OSError, ConnectionRefusedError, TimeoutError):
        return False


# ── PID helpers ──────────────────────────────────────────────────────

def write_pid(pid):
    HUB_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(pid))


def read_pid():
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except Exception:
        return None


def remove_pid():
    if PID_FILE.exists():
        PID_FILE.unlink()


# ── Dashboard HTML ───────────────────────────────────────────────────

HTML = r'''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bug Hub — Bugzilla Assistant Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    darkMode: "class",
    theme: {
      extend: {
        fontFamily: { sans: ['Outfit', 'sans-serif'] },
        colors: {
          primary: {
            50:'#eef2ff',100:'#e0e7ff',200:'#c3dafe',300:'#a3bffa',400:'#7f9cf5',
            500:'#667eea',600:'#5a67d8',700:'#4c51bf',800:'#434190',900:'#3c366b',
          }
        },
        animation: {
          'blob':'blob 7s infinite',
          'fade-in-up':'fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) both',
          'float':'float 6s ease-in-out infinite',
          'gradient-text':'gradientText 6s ease-in-out infinite',
        }
      }
    }
  }
</script>
<style>
  body { font-family:'Outfit',sans-serif; }
  ::-webkit-scrollbar{width:8px;height:8px}
  ::-webkit-scrollbar-track{background:transparent}
  ::-webkit-scrollbar-thumb{background:rgba(156,163,175,0.5);border-radius:4px}
  ::-webkit-scrollbar-thumb:hover{background:rgba(107,114,128,0.8)}

  #preloader{position:fixed;inset:0;background:#000;z-index:9999;display:flex;justify-content:center;align-items:center;transition:opacity .6s cubic-bezier(0.16,1,0.3,1),visibility .6s}
  #preloader.fade-out{opacity:0;visibility:hidden}
  .spinner{width:60px;height:60px;position:relative}
  .spinner::before,.spinner::after{content:'';position:absolute;inset:0;border-radius:50%;border:4px solid transparent}
  .spinner::before{border-top-color:#667eea;border-right-color:#667eea;animation:spin 1.5s linear infinite}
  .spinner::after{border-bottom-color:#ed64a6;border-left-color:#ed64a6;animation:spin 1s linear infinite reverse}
  @keyframes spin{100%{transform:rotate(360deg)}}

  .glass-panel{
    background:rgba(255,255,255,0.85);
    backdrop-filter:blur(40px);-webkit-backdrop-filter:blur(40px);
    border:1px solid rgba(255,255,255,0.6);
    box-shadow:0 20px 40px -10px rgba(0,0,0,0.1),0 0 0 1px rgba(255,255,255,0.4) inset;
  }
  .dark .glass-panel{
    background:rgba(15,23,42,0.75);
    border:1px solid rgba(255,255,255,0.1);
    box-shadow:0 30px 60px -12px rgba(0,0,0,0.6),0 0 0 1px rgba(255,255,255,0.05) inset;
  }

  .module-card{
    background:rgba(255,255,255,0.7);
    backdrop-filter:blur(40px);-webkit-backdrop-filter:blur(40px);
    border:1px solid rgba(255,255,255,0.5);
    box-shadow:0 10px 30px -10px rgba(0,0,0,0.1),0 0 0 1px rgba(255,255,255,0.3) inset;
    border-radius:24px;padding:32px 24px;cursor:pointer;position:relative;overflow:hidden;
    transition:transform .5s cubic-bezier(0.16,1,0.3,1),box-shadow .5s cubic-bezier(0.16,1,0.3,1),border-color .3s ease;
  }
  .dark .module-card{
    background:rgba(15,23,42,0.65);
    border:1px solid rgba(255,255,255,0.08);
    box-shadow:0 20px 50px -12px rgba(0,0,0,0.6),0 0 0 1px rgba(255,255,255,0.04) inset;
  }
  .module-card::before{
    content:'';position:absolute;top:0;left:0;right:0;height:3px;
    background:linear-gradient(90deg,#667eea,#ed64a6,#4f46e5);
    opacity:0;transition:opacity .3s ease;
  }
  .module-card:hover{
    transform:translateY(-6px);
    border-color:rgba(102,126,234,0.5);
    box-shadow:0 25px 50px -12px rgba(102,126,234,0.25),0 0 0 1px rgba(102,126,234,0.2) inset;
  }
  .module-card:hover::before{opacity:1}

  .top-glass{
    background:rgba(255,255,255,0.7);
    backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
    border-bottom:1px solid rgba(255,255,255,0.4);
  }
  .dark .top-glass{
    background:rgba(15,23,42,0.7);
    border-bottom:1px solid rgba(255,255,255,0.06);
  }

  .side-glass{
    background:rgba(255,255,255,0.7);
    backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
    border-right:1px solid rgba(255,255,255,0.4);
  }
  .dark .side-glass{
    background:rgba(15,23,42,0.7);
    border-right:1px solid rgba(255,255,255,0.06);
  }

  .nav-item{
    display:flex;align-items:center;gap:12px;
    padding:12px 16px;font-size:14px;font-weight:500;
    cursor:pointer;border-left:3px solid transparent;
    color:#475569;transition:all .3s cubic-bezier(0.16,1,0.3,1);
  }
  .dark .nav-item{color:#cbd5e1}
  .nav-item:hover{background:rgba(102,126,234,0.08);color:#667eea}
  .dark .nav-item:hover{color:#a3bffa}
  .nav-item.active{
    background:rgba(102,126,234,0.12);
    border-left-color:#667eea;
    color:#667eea;
  }
  .dark .nav-item.active{color:#a3bffa}

  .home-item{
    display:flex;align-items:center;gap:12px;
    padding:12px 16px;font-size:14px;font-weight:600;
    cursor:pointer;border-left:3px solid transparent;
    color:#475569;transition:all .3s cubic-bezier(0.16,1,0.3,1);
  }
  .dark .home-item{color:#cbd5e1}
  .home-item:hover{background:rgba(102,126,234,0.08);color:#667eea}

  .gradient-title{
    background:linear-gradient(90deg,#1e40af,#ec4899,#4f46e5);
    background-size:300% auto;
    -webkit-background-clip:text;background-clip:text;
    -webkit-text-fill-color:transparent;color:transparent;
  }

  .badge-active{
    background:rgba(102,126,234,0.15);color:#667eea;
    border:1px solid rgba(102,126,234,0.3);
  }
  .dark .badge-active{background:rgba(127,156,245,0.15);color:#a3bffa;border-color:rgba(127,156,245,0.3)}

  .dot-ping-wrap{position:relative;display:inline-flex;width:10px;height:10px}
  .dot-ping-wrap .ping{position:absolute;inset:0;border-radius:50%;opacity:0.7;animation:ping 2s infinite}
  .dot-ping-wrap .dot{position:relative;border-radius:50%;width:10px;height:10px}
  @keyframes ping{0%{transform:scale(1);opacity:0.7}75%,100%{transform:scale(2.2);opacity:0}}
  .dot-green{background:#3fb950}
  .dot-green.ping{background:#3fb950}
  .dot-gray{background:#64748b}
  .dot-gray.ping{background:#64748b;display:none}

  .btn-gradient{
    background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
    background-size:200% auto;color:#fff;
    transition:.5s ease;
    box-shadow:0 10px 20px -5px rgba(102,126,234,0.4);
  }
  .btn-gradient:hover{
    background-position:right center;
    box-shadow:0 15px 25px -5px rgba(102,126,234,0.5);
    transform:translateY(-2px);
  }

  .aurora{
    position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden;
  }
  .aurora::before{
    content:'';position:absolute;inset:-50%;
    background:repeating-linear-gradient(45deg,
      rgba(96,165,250,0.15) 0px,rgba(96,165,250,0.15) 40px,
      rgba(232,121,249,0.15) 40px,rgba(232,121,249,0.15) 80px,
      rgba(94,234,212,0.15) 80px,rgba(94,234,212,0.15) 120px);
    filter:blur(120px);
    mix-blend-mode:difference;
    animation:aurora 40s linear infinite;
  }
  @keyframes aurora{0%{transform:translate(0,0)}100%{transform:translate(-200px,-200px)}}
  .blob{position:absolute;border-radius:50%;mix-blend-mode:multiply;filter:blur(64px);opacity:0.35;animation:blob 7s infinite}
  .dark .blob{opacity:0.25}
  @keyframes blob{0%{transform:translate(0,0) scale(1)}33%{transform:translate(30px,-50px) scale(1.1)}66%{transform:translate(-20px,20px) scale(0.9)}100%{transform:translate(0,0) scale(1)}}

  #iframe-wrap iframe{width:100%;height:100%;border:none;background:#fff}
  .dark #iframe-wrap iframe{background:#0f172a}
</style>
<script>
  if (localStorage.theme === 'light') document.documentElement.classList.remove('dark');
  else document.documentElement.classList.add('dark');
</script>
</head>
<body class="transition-colors duration-500 bg-slate-50 dark:bg-black font-sans text-slate-800 dark:text-slate-200 min-h-screen flex flex-col">

<!-- PRELOADER -->
<div id="preloader"><div class="spinner"></div></div>

<!-- ANIMATED BACKGROUND -->
<div class="aurora">
  <div class="blob bg-purple-400" style="width:288px;height:288px;top:-40px;left:-40px;"></div>
  <div class="blob bg-blue-400" style="width:288px;height:288px;top:-40px;right:-40px;animation-delay:2s;"></div>
  <div class="blob bg-pink-400" style="width:288px;height:288px;bottom:-40px;left:25%;animation-delay:4s;"></div>
</div>

<!-- TOP BAR -->
<div class="top-glass relative z-20 px-6 h-14 flex items-center justify-between flex-shrink-0">
  <div class="flex items-center gap-3">
    <button id="backBtn" class="hidden p-2 rounded-lg hover:bg-slate-200/60 dark:hover:bg-slate-800/60 transition" aria-label="Back">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path></svg>
    </button>
    <div class="text-xl font-extrabold tracking-tight text-slate-900 dark:text-white">
      <span class="gradient-title animate-gradient-text">Bug Hub</span>
    </div>
  </div>
  <div class="flex items-center gap-4">
    <div id="topStatus" class="text-xs font-medium text-slate-600 dark:text-slate-400 flex items-center gap-2"></div>
    <button onclick="toggleTheme()" class="p-2 rounded-lg bg-slate-200/60 dark:bg-slate-800/60 border border-slate-300/40 dark:border-slate-700/50 text-slate-600 dark:text-slate-300 hover:bg-slate-300/60 dark:hover:bg-slate-700/60 transition" aria-label="Toggle theme">
      <svg id="theme-icon-dark" class="hidden w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>
      <svg id="theme-icon-light" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path></svg>
    </button>
  </div>
</div>

<!-- MAIN AREA -->
<div id="main" class="relative z-10 flex flex-1 overflow-hidden">

  <!-- SIDEBAR -->
  <div id="sidebar" class="side-glass w-64 flex-col hidden flex-shrink-0">
    <a class="home-item border-b border-slate-200/40 dark:border-slate-800/40" onclick="showGrid()">
      <span class="text-xl">&#127968;</span><span>Dashboard</span>
    </a>
    <div class="px-4 py-2 text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">Skills</div>
    <div id="navItems" class="flex-1 overflow-y-auto py-2"></div>
  </div>

  <!-- CONTENT -->
  <div id="content" class="flex-1 relative overflow-hidden">
    <!-- GRID VIEW -->
    <div id="grid-wrap" class="absolute inset-0 overflow-auto">
      <div class="min-h-full flex flex-col items-center justify-start px-6 py-12 lg:py-16">
        <div class="text-center mb-10 animate-fade-in-up">
          <div class="inline-flex items-center justify-center gap-2 px-4 py-1.5 mb-5 rounded-full bg-primary-100 dark:bg-primary-900/40 border border-primary-200 dark:border-primary-800 text-xs font-semibold text-primary-700 dark:text-primary-300">
            <span class="dot-ping-wrap"><span class="ping dot-green"></span><span class="dot dot-green"></span></span>
            <span>Bugzilla Assistant Suite</span>
          </div>
          <h1 class="text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white mb-3">
            All Your <span class="gradient-title animate-gradient-text">Bug Tools</span> in One Place
          </h1>
          <p class="text-sm md:text-base text-slate-500 dark:text-slate-400 max-w-xl mx-auto">
            Bug query, log analysis, protocol parsing, code generation — unified dashboard for debugging workflow.
          </p>
        </div>
        <div id="grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 w-full max-w-5xl animate-fade-in-up" style="animation-delay:.15s"></div>
      </div>
    </div>

    <!-- IFRAME VIEW -->
    <div id="iframe-wrap" class="absolute inset-0 hidden">
      <iframe id="theIframe" src="about:blank" title="skill-page"></iframe>
    </div>
  </div>

</div>

<!-- TOAST -->
<div id="toast" class="fixed bottom-6 right-6 px-5 py-3 rounded-xl shadow-2xl backdrop-blur-md font-semibold text-sm translate-y-24 opacity-0 transition-all duration-400 z-50 hidden flex items-center gap-2">
  <span id="toast-text"></span>
</div>

<script>
let modules = [];
let activeModuleId = null;

const gridWrap = document.getElementById('grid-wrap');
const grid = document.getElementById('grid');
const sidebar = document.getElementById('sidebar');
const navItems = document.getElementById('navItems');
const backBtn = document.getElementById('backBtn');
const iframeWrap = document.getElementById('iframe-wrap');
const theIframe = document.getElementById('theIframe');
const topStatus = document.getElementById('topStatus');

async function api(path, opts){
  const r = await fetch(path, opts||{});
  return r.json();
}

async function loadModules(){
  try {
    const data = await api('/api/modules');
    modules = data.modules;
  } catch(e){ console.error('Failed to load modules', e); modules = []; }
  updateTopStatus();
  renderGrid();
  renderNav();
}

function updateTopStatus(){
  const total = modules.length;
  topStatus.innerHTML = `<span class="dot-ping-wrap"><span class="ping dot-green"></span><span class="dot dot-green"></span></span> ${total} skills ready`;
}

function escHtml(s){
  return (s||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function renderGrid(){
  grid.innerHTML = modules.map((m,i)=>`
    <div class="module-card animate-fade-in-up" style="animation-delay:${0.2 + i*0.08}s" onclick="openModule('${m.id}')">
      <div class="text-5xl mb-4 text-center">${m.icon}</div>
      <div class="text-center text-lg font-bold text-slate-900 dark:text-white mb-2">${escHtml(m.name)}</div>
      <div class="text-center mb-3">
        <span class="inline-block px-3 py-1 rounded-full text-[11px] font-semibold badge-active">
          Active
        </span>
      </div>
      <div class="text-xs text-slate-500 dark:text-slate-400 text-center leading-relaxed">${escHtml(m.desc)}</div>
    </div>
  `).join('');
}

function renderNav(){
  navItems.innerHTML = modules.map(m=>`
    <div class="nav-item ${activeModuleId===m.id?'active':''}" onclick="openModule('${m.id}')">
      <span class="text-xl">${m.icon}</span>
      <span class="flex-1">${escHtml(m.name)}</span>
    </div>
  `).join('');
}

function showGrid(){
  activeModuleId = null;
  sidebar.classList.add('hidden');
  sidebar.classList.remove('flex');
  backBtn.classList.add('hidden');
  gridWrap.classList.remove('hidden');
  iframeWrap.classList.add('hidden');
  theIframe.src = 'about:blank';
  window.location.hash = '';
  renderNav();
}

function openModule(id){
  const m = modules.find(x=>x.id===id);
  if(!m) return;
  activeModuleId = id;
  window.location.hash = '#' + id;
  renderNav();

  sidebar.classList.remove('hidden');
  sidebar.classList.add('flex');
  backBtn.classList.remove('hidden');
  gridWrap.classList.add('hidden');
  iframeWrap.classList.remove('hidden');
  theIframe.src = '/pages/' + m.page;
}

backBtn.addEventListener('click', showGrid);

function handleHash(){
  const hash = window.location.hash.replace('#','');
  if(hash && modules.some(m=>m.id===hash)) openModule(hash);
  else showGrid();
}
window.addEventListener('hashchange', handleHash);

function toggleTheme(){
  const isDark = document.documentElement.classList.contains('dark');
  document.documentElement.classList.toggle('dark');
  localStorage.theme = isDark ? 'light' : 'dark';
  updateThemeIcons();
}
function updateThemeIcons(){
  const isDark = document.documentElement.classList.contains('dark');
  document.getElementById('theme-icon-dark').classList.toggle('hidden', isDark);
  document.getElementById('theme-icon-light').classList.toggle('hidden', !isDark);
}
updateThemeIcons();

function showToast(msg){
  const t = document.getElementById('toast');
  document.getElementById('toast-text').textContent = msg;
  t.classList.remove('hidden');
  requestAnimationFrame(()=>{ t.classList.remove('translate-y-24','opacity-0'); });
  setTimeout(()=>{ t.classList.add('translate-y-24','opacity-0'); setTimeout(()=>t.classList.add('hidden'),400); }, 3000);
}

window.addEventListener('load', function(){
  setTimeout(function(){
    const p = document.getElementById('preloader');
    p.classList.add('fade-out');
    setTimeout(()=>p.style.display='none', 600);
  }, 300);
});

(async function(){
  await loadModules();
  handleHash();
})();
</script>
</body>
</html>'''


# ── HTTP Handler ─────────────────────────────────────────────────────

class HubHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _html(self, html_str):
        data = html_str.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _serve_file(self, path, content_type="text/html; charset=utf-8"):
        try:
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self._json({"error": "page not found"}, 404)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        body = self.rfile.read(length)
        return json.loads(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        p = u.path.rstrip("/")

        if p in ("", "/"):
            return self._html(HTML)

        if p == "/api/modules":
            return self._json({"modules": MODULES})

        if p == "/api/health":
            return self._json({"ok": True})

        # ── keyword-vault API ──
        if p == "/api/keyword-vault/directions":
            return self._handle_kw_directions()
        if p == "/api/keyword-vault/keywords":
            return self._handle_kw_keywords()
        if p == "/api/keyword-vault/export":
            return self._handle_kw_export()

        # ── bug-workspace path history ──
        if p == "/api/bug-workspace/paths":
            return self._handle_workspace_paths_get()

        # Serve static pages
        if p.startswith("/pages/"):
            page_name = p[len("/pages/"):]
            page_path = PAGES_DIR / page_name
            return self._serve_file(page_path)

        # Serve generated report files from HUB_DIR
        if p.startswith("/reports/"):
            report_name = p[len("/reports/"):]
            report_path = HUB_DIR / report_name
            return self._serve_file(report_path)

        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        p = u.path.rstrip("/")

        # ── bug-core API ──
        if p == "/api/bug-core/query":
            return self._handle_bug_core_query()

        # ── bug-logs API ──
        if p == "/api/bug-logs/list":
            return self._handle_bug_logs_list()

        # ── bug-workspace API ──
        if p == "/api/bug-workspace/create":
            return self._handle_bug_workspace_create()
        if p == "/api/bug-workspace/paths/save":
            return self._handle_workspace_paths_save()
        if p == "/api/bug-workspace/paths/delete":
            return self._handle_workspace_paths_delete()
        if p == "/api/bug-workspace/open":
            return self._handle_workspace_open()

        # ── keyword-vault API ──
        if p == "/api/keyword-vault/add":
            return self._handle_kw_add()
        if p == "/api/keyword-vault/delete":
            return self._handle_kw_delete()
        if p == "/api/keyword-vault/auto-learn":
            return self._handle_kw_auto_learn()
        if p == "/api/keyword-vault/new-direction":
            return self._handle_kw_new_direction()

        # ── log-analyzer API ──
        if p == "/api/log-analyzer/generate":
            return self._handle_log_analyzer_generate()
        if p == "/api/log-analyzer/filter-and-parse":
            return self._handle_filter_and_parse()

        # ── protocol-parser API ──
        if p == "/api/protocol-parser/generate":
            return self._handle_protocol_parser_generate()

        # ── code-generator API ──
        if p == "/api/code-generator/generate":
            return self._handle_code_generator()

        return self._json({"error": "not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── API Handlers ──────────────────────────────────────────────

    def _guess_instance(self, bug_id):
        """Auto-detect Bugzilla instance from bug ID prefix."""
        bug_id = str(bug_id).strip().upper()
        if bug_id.startswith("SPCSS"):
            return "unisoc"
        # Try to find from local cache
        local_data = SKILLS_DIR / "bug-core" / "data" / "sample_bugs.json"
        if local_data.exists():
            try:
                cache = json.loads(local_data.read_text(encoding="utf-8"))
                for item in cache if isinstance(cache, list) else cache.get("bugs", []):
                    if str(item.get("bug_id", "")) == bug_id:
                        return item.get("instance", "kernel")
            except Exception:
                pass
        return "kernel"

    def _handle_bug_core_query(self):
        body = self._read_body()
        bug_id = body.get("bug_id", "")
        instance = body.get("instance") or self._guess_instance(bug_id)
        try:
            from bug_core import fetch_bug_rest
            result = fetch_bug_rest(str(bug_id), instance)
            # add instance info to result for downstream use
            if isinstance(result, dict):
                result["_instance"] = instance
            return self._json({"ok": True, "data": result})
        except Exception as e:
            err = str(e)
            hint = ""
            if "401" in err or "Unauthorized" in err:
                hint = " (API key may be missing or expired for this instance)"
            elif "400" in err or "Bad Request" in err:
                hint = f" (Bug not found on {instance}, try a different instance)"
            return self._json({"ok": False, "error": err + hint, "instance": instance})

    def _handle_bug_logs_list(self):
        body = self._read_body()
        bug_id = body.get("bug_id", "")
        instance = body.get("instance") or self._guess_instance(bug_id)
        try:
            from bug_logs import fetch_bug_with_logs
            result = fetch_bug_with_logs(str(bug_id), instance)
            if isinstance(result, dict):
                result["_instance"] = instance
            return self._json({"ok": True, "data": result})
        except Exception as e:
            err = str(e)
            hint = ""
            if "401" in err or "Unauthorized" in err:
                hint = " (API key required)"
            return self._json({"ok": False, "error": err + hint, "instance": instance})

    def _handle_bug_workspace_create(self):
        body = self._read_body()
        bug_id = body.get("bug_id", "")
        instance = body.get("instance") or self._guess_instance(bug_id)
        base_path = body.get("base_path") or None
        download = body.get("download", False)
        refresh = body.get("refresh", False)
        normalize_action = body.get("normalize_action", "copy_new")

        # Fetch bug info for full context
        try:
            from bug_core import fetch_bug_rest as fetch_bug
            bug_info = fetch_bug(str(bug_id), instance)
            if isinstance(bug_info, dict):
                bug_info["instance"] = instance
                if "error" in bug_info:
                    # Bug not found on guessed instance, report error
                    return self._json({"ok": False, "error": bug_info["error"], "instance": instance})
        except Exception as e:
            import traceback
            print(f"[WARN] Bug fetch failed for {bug_id}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return self._json({"ok": False, "error": f"Failed to fetch bug {bug_id}: {e}"})

        if base_path:
            bug_info["base_path"] = base_path

        try:
            from bug_workspace import generate_workspace_with_download
            result = generate_workspace_with_download(
                bug_info, base_path=base_path,
                download=download, refresh=refresh,
                normalize_action=normalize_action, copy_bug_z=True)

            print(f"[DEBUG] result keys: {list(result.keys())}, success: {result.get('success')}, folder keys: {list(result.get('folder', {}).keys())}", file=sys.stderr)

            # Build response with parameter fields matching original tool
            folder = result.get("folder", {})
            return self._json({"ok": True, "data": {
                "success": result.get("success", False),
                "bug_id": result.get("bug_id", bug_id),
                "bug_title": result.get("bug_title", ""),
                "base_path": result.get("base_path", ""),
                "ftp_path": result.get("ftp_path", ""),
                "path_url": result.get("path_url", ""),
                "folder_name": folder.get("folder_name", ""),
                "folder_path": folder.get("folder_path", ""),
                "attachment_folder": folder.get("attachment_folder", ""),
                "shortcut_file": folder.get("shortcut_file", ""),
                "attachment_shortcut": folder.get("attachment_shortcut", ""),
                "summary_file": folder.get("summary_file", ""),
                "rayfile_commands": folder.get("rayfile_commands", []),
                "bug_z_copied": result.get("bug_z_copied", False),
                "download": result.get("download", {}),
                "normalized": result.get("normalized", {}),
                "errors": result.get("errors", []),
            }})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)})

    def _handle_workspace_paths_get(self):
        """Get workspace path history."""
        try:
            from bug_workspace import load_workspace_paths
            paths = load_workspace_paths()
            return self._json({"ok": True, "data": {"paths": paths}})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)})

    def _handle_workspace_paths_save(self):
        """Save a new path to workspace path history."""
        body = self._read_body()
        path = body.get("path", "")
        if not path:
            return self._json({"ok": False, "error": "path is required"})
        try:
            from bug_workspace import load_workspace_paths, save_workspace_paths
            paths = load_workspace_paths()
            # Deduplicate: remove if exists, then insert at front
            paths = [p for p in paths if p != path]
            paths.insert(0, path)
            save_workspace_paths(paths)
            return self._json({"ok": True, "data": {"paths": paths}})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)})

    def _handle_workspace_paths_delete(self):
        """Delete a path from workspace path history."""
        body = self._read_body()
        path = body.get("path", "")
        if not path:
            return self._json({"ok": False, "error": "path is required"})
        try:
            from bug_workspace import load_workspace_paths, save_workspace_paths
            paths = load_workspace_paths()
            paths = [p for p in paths if p != path]
            save_workspace_paths(paths)
            return self._json({"ok": True, "data": {"paths": paths}})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)})

    def _handle_workspace_open(self):
        """Open a path in Windows Explorer."""
        body = self._read_body()
        path = body.get("path", "")
        if not path:
            return self._json({"ok": False, "error": "path is required"})
        try:
            from bug_workspace import open_workspace_path
            ok = open_workspace_path(path)
            return self._json({"ok": ok, "data": {"opened": ok, "path": path}})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)})

    def _handle_kw_directions(self):
        try:
            from keyword_vault import list_directions
            dirs = list_directions()
            return self._json({"ok": True, "data": dirs})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)})

    def _handle_kw_keywords(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        direction = qs.get("direction", [""])[0]
        try:
            from keyword_vault import get_keywords
            result = get_keywords(direction) if direction else {"keywords": {}}
            return self._json({"ok": True, "data": result})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)})

    def _handle_kw_export(self):
        try:
            from keyword_vault import export_for_viewer
            result = export_for_viewer()
            return self._json({"ok": True, "data": result})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)})

    def _handle_kw_add(self):
        body = self._read_body()
        try:
            from keyword_vault import add_keyword
            result = add_keyword(body.get("direction", ""), body.get("keyword", ""))
            return self._json({"ok": True, "data": result})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)})

    def _handle_kw_delete(self):
        body = self._read_body()
        try:
            from keyword_vault import remove_keyword
            result = remove_keyword(body.get("direction", ""), body.get("keyword", ""))
            return self._json({"ok": True, "data": result})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)})

    def _handle_kw_auto_learn(self):
        body = self._read_body()
        try:
            from keyword_vault import auto_learn
            result = auto_learn(body.get("text", ""), body.get("direction", None))
            return self._json({"ok": True, "data": result})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)})

    def _handle_kw_new_direction(self):
        body = self._read_body()
        try:
            from keyword_vault import add_direction
            result = add_direction(body.get("id", ""), body.get("name", ""))
            if "error" in result:
                return self._json({"ok": False, "error": result["error"]})
            return self._json({"ok": True, "data": result})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)})

    def _handle_filter_and_parse(self):
        """Filter log by direction keywords, then parse protocols from filtered log."""
        body = self._read_body()
        logfile = body.get("logfile", "")
        direction = body.get("direction", "")
        protocol = body.get("protocol", "auto")

        if not logfile:
            return self._json({"ok": False, "error": "logfile is required"})
        if not Path(logfile).exists():
            return self._json({"ok": False, "error": f"Log file not found: {logfile}"})

        try:
            # Step 1: Get keywords from keyword-vault for this direction
            from keyword_vault import export_for_viewer
            vault_data = export_for_viewer()
            direction_info = vault_data.get("directions", {}).get(direction, {})
            keywords = direction_info.get("keywords", []) if direction_info else vault_data.get("all_keywords", [])

            if not keywords and direction:
                return self._json({"ok": False, "error": f"No keywords found for direction: {direction}"})

            # Step 2: Filter log with keywords using grep
            import re
            log_text = Path(logfile).read_text(encoding="utf-8", errors="replace")
            log_lines = log_text.splitlines()

            # Build regex pattern from keywords (PD-specific: match literal substrings)
            escaped_kw = [re.escape(kw) for kw in keywords if kw.strip()]
            if not escaped_kw:
                return self._json({"ok": False, "error": "No valid keywords to filter with"})

            pattern = re.compile("|".join(escaped_kw), re.IGNORECASE)
            filtered_lines = []
            matched_keywords = set()
            for line in log_lines:
                matches = pattern.findall(line)
                if matches:
                    filtered_lines.append(line)
                    matched_keywords.update(m.lower() for m in matches)

            filtered_log = "\n".join(filtered_lines)

            # Step 3: Write filtered log to temp file
            filtered_path = HUB_DIR / f"_filtered_{direction}.log"
            filtered_path.write_text(filtered_log, encoding="utf-8")

            # Step 4: Run protocol parser on filtered log
            from protocol_combiner import parse_all, generate_report
            data = parse_all(str(filtered_path))
            output_html = str(HUB_DIR / "protocol_report_output.html")
            report_result = generate_report(data, output_html)

            report_html = ""
            if report_result and Path(report_result).exists():
                report_html = Path(report_result).read_text(encoding="utf-8", errors="replace")

            report_name = Path(output_html).name
            return self._json({"ok": True, "data": {
                "direction": direction,
                "direction_name": direction_info.get("name", direction),
                "keywords_used": sorted(matched_keywords),
                "keyword_count": len(escaped_kw),
                "total_lines": len(log_lines),
                "filtered_lines": len(filtered_lines),
                "filtered_log": filtered_log[:100000],
                "filtered_log_path": str(filtered_path),
                "report_url": f"/reports/{report_name}",
                "parsed": {k: v for k, v in data.items() if not k.endswith("_error")},
                "report_html": report_html[:200000],
                "report_html_path": report_result,
            }})
        except Exception as e:
            import traceback
            return self._json({"ok": False, "error": str(e), "traceback": traceback.format_exc()})

    def _handle_log_analyzer_generate(self):
        body = self._read_body()
        logfile = body.get("logfile", "")
        direction = body.get("direction", "")
        role = body.get("role", "")
        try:
            from log_viewer_v2 import generate_viewer
            output_html = str(HUB_DIR / "log_viewer_output.html")
            result = generate_viewer(
                logfile=logfile or None,
                output_html=output_html,
                direction=direction,
                role=role,
                standalone=True)
            # Read generated HTML for inline display
            report = ""
            if result and Path(result).exists():
                report = Path(result).read_text(encoding="utf-8", errors="replace")
            report_name = Path(output_html).name
            return self._json({"ok": True, "data": {
                "html_path": result,
                "report_url": f"/reports/{report_name}",
                "report_html": report[:200000] if report else ""
            }})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)})

    def _handle_protocol_parser_generate(self):
        body = self._read_body()
        logfile = body.get("logfile", "")
        try:
            from protocol_combiner import parse_all, generate_report
            data = parse_all(str(logfile))
            output_html = str(HUB_DIR / "protocol_report_output.html")
            result = generate_report(data, output_html)
            report = ""
            if result and Path(result).exists():
                report = Path(result).read_text(encoding="utf-8", errors="replace")
            report_name = Path(output_html).name
            return self._json({"ok": True, "data": {
                "html_path": result,
                "report_url": f"/reports/{report_name}",
                "parsed": {k: v for k, v in data.items() if not k.endswith("_error")},
                "report_html": report[:200000] if report else ""
            }})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)})

    def _handle_code_generator(self):
        body = self._read_body()
        description = body.get("description", "")
        driver_type = body.get("driver_type", "kernel")
        level = body.get("level", "1")
        try:
            templates_dir = SKILLS_DIR / "code-generator" / "templates"
            template_file = templates_dir / f"debug_level{level}.c"
            template = ""
            if template_file.exists():
                template = template_file.read_text(encoding="utf-8")
            code = f"// Level: {level}\n// Driver: {driver_type}\n// Problem: {description}\n\n{template}"
            return self._json({"ok": True, "data": {
                "code": code,
                "level": level,
                "driver_type": driver_type,
                "instructions": "Compile with appropriate kernel build flags.",
                "tests": "Verify with targeted test scenarios."
            }})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)})


# ── CLI Commands ─────────────────────────────────────────────────────

DEFAULT_PORT = 8777
HEALTH_TIMEOUT = 2  # seconds


def _parse_port(argv):
    """Extract port number from CLI args. Returns (port, force, rest_args)."""
    port = DEFAULT_PORT
    force = False
    rest = []
    for a in argv:
        if a in ("--force", "-f"):
            force = True
        elif a.startswith("--port="):
            try:
                port = int(a.split("=", 1)[1])
            except ValueError:
                print(f"Invalid port: {a}", file=sys.stderr)
        else:
            try:
                port = int(a)
            except ValueError:
                rest.append(a)
    return port, force, rest


def _health_check(port):
    """Check if Bug Hub is alive by hitting /api/health. Returns True if responding."""
    try:
        import urllib.request
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/health",
            headers={"User-Agent": "bug-hub-cli"}
        )
        resp = urllib.request.urlopen(req, timeout=HEALTH_TIMEOUT)
        data = json.loads(resp.read().decode())
        return data.get("ok", False)
    except Exception:
        return False


def _find_hub_pid_on_port(port):
    """Find PID of process listening on the given port. Returns PID or None."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if f"127.0.0.1:{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    return int(parts[-1])
        else:
            result = subprocess.run(
                ["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True, timeout=5
            )
            pid_str = result.stdout.strip()
            if pid_str:
                return int(pid_str.split()[-1])
    except Exception:
        pass
    return None


def _kill_process(pid):
    """Kill a process by PID. Returns True if successful."""
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True, timeout=10
            )
        else:
            os.kill(pid, signal.SIGKILL)
        time.sleep(0.5)
        return True
    except Exception:
        return False


def _ensure_stopped(port):
    """Ensure nothing is running on the target port. Returns True if port is free."""
    if not is_port_open(port):
        return True  # port is already free

    # Port is in use. Try to identify and stop.
    pid = _find_hub_pid_on_port(port)
    if pid:
        print(f"Port {port} is in use by PID {pid}. Stopping ...")
        if _kill_process(pid):
            time.sleep(0.3)
            if not is_port_open(port):
                print("  Stopped.")
                remove_pid()
                return True
            else:
                print(f"  Failed to stop PID {pid}, port still in use.")
                return False
        else:
            print(f"  Could not kill PID {pid}.")
            return False
    else:
        print(f"Port {port} is in use by an unknown process.")
        return False


# ── start ───────────────────────────────────────────────────────────

def cmd_start(argv):
    port, force, _ = _parse_port(argv)

    # ── Check if already running via health endpoint (most reliable) ──
    if _health_check(port):
        print(f"Bug Hub is already running on http://127.0.0.1:{port}/")
        if force:
            print("  --force: restarting ...")
            _ensure_stopped(port)
        else:
            print(f"  Use 'restart' or 'start --force' to restart.")
            return

    # ── Fallback: check PID file if health check didn't catch it ──
    existing_pid = read_pid()
    if existing_pid is not None:
        print(f"Stale PID file found (PID {existing_pid}). Cleaning up ...")
        remove_pid()

    # ── Ensure port is free ──
    if is_port_open(port):
        if not _ensure_stopped(port):
            print(f"ERROR: Cannot free port {port}. Is another app using it?", file=sys.stderr)
            sys.exit(1)

    # ── Start server ──
    print(f"Bug Hub starting on http://127.0.0.1:{port}/")

    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", port), HubHandler)
    except OSError as e:
        print(f"ERROR: Cannot bind to port {port}: {e}", file=sys.stderr)
        if "10048" in str(e) or "Address already in use" in str(e):
            print(f"  Port {port} is already in use. Use 'start --force' to kill and restart.", file=sys.stderr)
        sys.exit(1)

    # Only write PID after successful bind
    write_pid(os.getpid())

    url = f"http://127.0.0.1:{port}/"
    print(f"Dashboard -> {url}")
    print("Ctrl+C to stop.")

    Thread(target=lambda: webbrowser.open(url), daemon=True).start()

    def shutdown(signum, frame):
        print("\nShutting down ...")
        remove_pid()
        server.shutdown()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        remove_pid()
        print("Bug Hub stopped.")


# ── stop ────────────────────────────────────────────────────────────

def cmd_stop(argv):
    port, force, _ = _parse_port(argv)

    # First: try health check to confirm it's actually running
    if _health_check(port):
        hub_pid = _find_hub_pid_on_port(port)
        if hub_pid:
            print(f"Bug Hub is running on port {port} (PID {hub_pid}). Stopping ...")
            _kill_process(hub_pid)
            time.sleep(0.5)
            if not _health_check(port):
                remove_pid()
                print("  Bug Hub stopped.")
            else:
                print(f"  WARNING: Port {port} still responding. Process may not have stopped.")
        else:
            print(f"Health check passed on port {port} but cannot find PID. Trying force kill ...")
            _ensure_stopped(port)
        return

    # Not responding on health check. Try PID file as fallback.
    pid = read_pid()
    if pid is not None:
        print(f"Bug Hub not responding on port {port}, but PID file found (PID {pid}).")
        if _kill_process(pid):
            remove_pid()
            print("  Stopped and PID file cleaned.")
        else:
            print(f"  Could not stop PID {pid}. Removing stale PID file.")
            remove_pid()
        return

    # Nothing found
    if is_port_open(port):
        who = _find_hub_pid_on_port(port)
        if who:
            print(f"Port {port} is in use by PID {who} (not Bug Hub?). Use --force to kill.")
        else:
            print(f"Port {port} is in use by an unknown process.")
    else:
        print("Bug Hub is not running (no health response, no PID file, port free).")


# ── restart ─────────────────────────────────────────────────────────

def cmd_restart(argv):
    """Stop (if running) then start."""
    port, force, rest = _parse_port(argv)
    print(f"=== Restarting Bug Hub on port {port} ===")
    # Always try to stop first
    if _health_check(port) or is_port_open(port):
        cmd_stop([str(port), "--force"])
        time.sleep(0.5)
    cmd_start([str(port)] + rest)


# ── status ──────────────────────────────────────────────────────────

def cmd_status(argv):
    port, _, _ = _parse_port(argv)

    print()
    print(f"{'Bug Hub Status':=^50}")
    print()

    # Server status
    if _health_check(port):
        pid = _find_hub_pid_on_port(port) or read_pid()
        print(f"  Server:   \033[92m● RUNNING\033[0m  http://127.0.0.1:{port}/  (PID {pid or '?'})")
    elif is_port_open(port):
        who = _find_hub_pid_on_port(port)
        print(f"  Server:   \033[93m● PORT IN USE\033[0m  port {port} by PID {who or 'unknown'} (not Bug Hub?)")
    elif read_pid():
        print(f"  Server:   \033[91m● DEAD\033[0m  (stale PID file, port {port} free)")
    else:
        print(f"  Server:   \033[90m● STOPPED\033[0m  (port {port} free)")

    print()

    # Module list
    mods = MODULES
    print(f"  {'Skill':<22} {'Page':<22}")
    print(f"  {'-'*44}")
    for m in mods:
        print(f"  {m['icon']} {m['name']:<18} {m['page']:<22}")
    print()


def cmd_help(argv):
    print(__doc__)


COMMANDS = {
    "start": cmd_start,
    "stop": cmd_stop,
    "restart": cmd_restart,
    "status": cmd_status,
    "help": cmd_help,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return

    cmd = sys.argv[1]
    fn = COMMANDS.get(cmd)
    if not fn:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)

    fn(sys.argv[2:])


if __name__ == "__main__":
    main()
