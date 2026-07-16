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
HTML = r'''<!doctype html>
<html><head><meta charset="utf-8"><title>Skills Sync Manager</title>
<style>
:root{--bg:#111;--bg2:#1a1a1a;--bg3:#222;--bg4:#2a2a2a;--border:#333;--text:#e0e0e0;--text2:#999;--accent:#3b82f6;--green:#22c55e;--red:#ef4444;--yellow:#eab308;--purple:#a855f7}
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
body{background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{background:var(--bg2);padding:10px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:16px;flex-shrink:0}
header h1{font-size:16px;white-space:nowrap}
.tabs{display:flex;gap:2px;background:var(--bg3);border-radius:6px;padding:2px}
.tab{padding:6px 16px;border-radius:4px;cursor:pointer;font-size:13px;color:var(--text2);transition:all .15s}
.tab:hover{color:var(--text)}
.tab.active{background:var(--accent);color:#fff}
.header-actions{margin-left:auto;display:flex;gap:8px;align-items:center}
.btn{padding:6px 14px;border-radius:4px;border:none;cursor:pointer;font-size:12px;color:#fff;transition:opacity .15s}
.btn:hover{opacity:.85}
.btn-primary{background:var(--accent)}
.btn-success{background:var(--green)}
.btn-danger{background:var(--red)}
.btn-secondary{background:#444}
.btn-sm{padding:4px 10px;font-size:11px}
main{flex:1;overflow:hidden;display:flex}
.page{display:none;flex:1;overflow:hidden}
.page.active{display:flex}
/* Dashboard */
#dashboard{flex-direction:column;padding:20px;gap:20px;overflow:auto}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.stat-card{background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:16px}
.stat-card .label{font-size:12px;color:var(--text2);margin-bottom:4px}
.stat-card .value{font-size:28px;font-weight:700}
.stat-card .sub{font-size:11px;color:var(--text2);margin-top:4px}
.section-title{font-size:14px;font-weight:600;margin-bottom:8px;color:var(--text2)}
.agent-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.agent-card{background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:14px}
.agent-card h3{font-size:14px;margin-bottom:8px}
.agent-card .meta{font-size:11px;color:var(--text2)}
.preset-list{display:flex;flex-wrap:wrap;gap:6px}
.preset-tag{background:var(--bg4);border:1px solid var(--border);border-radius:12px;padding:3px 10px;font-size:11px}
.preset-tag.active{border-color:var(--green);color:var(--green)}
/* Skills page */
#skills-page{flex-direction:row}
.skill-table-wrap{flex:1;overflow:auto;border-right:1px solid var(--border)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:var(--bg2);position:sticky;top:0;padding:8px 12px;text-align:left;font-weight:600;font-size:12px;color:var(--text2);border-bottom:1px solid var(--border);cursor:pointer;user-select:none}
td{padding:7px 12px;border-bottom:1px solid var(--bg3)}
tr.clickable:hover{background:var(--bg3)}
tr.selected{background:#1e3a5f}
tr.disabled{opacity:.5}
.badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:10px;background:var(--bg4);border:1px solid var(--border)}
.toggle{cursor:pointer;font-size:16px}
.toggle.on{color:var(--green)}
.toggle.off{color:var(--red)}
.drawer{width:480px;background:var(--bg2);overflow:auto;padding:16px;flex-shrink:0}
.drawer h2{font-size:15px;margin-bottom:8px}
.drawer .meta{font-size:11px;color:var(--text2);margin-bottom:4px}
.drawer pre{background:var(--bg);padding:12px;border-radius:4px;overflow:auto;font-size:12px;white-space:pre-wrap;word-break:break-word;max-height:55vh;margin-top:12px}
.drawer .actions{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
.sync-icons{display:flex;gap:4px;margin-top:6px}
.sync-dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.sync-dot.ok{background:var(--green)}
.sync-dot.miss{background:var(--red)}
.sync-dot.na{background:#555}
/* Presets page */
#presets-page{flex-direction:column;padding:20px;overflow:auto;gap:16px}
.preset-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}
.preset-card{background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:16px}
.preset-card h3{font-size:14px;margin-bottom:4px}
.preset-card .desc{font-size:12px;color:var(--text2);margin-bottom:10px}
.preset-card .skill-chips{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:10px}
.preset-card .chip{background:var(--bg4);border-radius:10px;padding:2px 8px;font-size:11px}
.preset-card .agent-status{font-size:11px;color:var(--text2);margin-top:8px}
/* Agents page */
#agents-page{flex-direction:column;padding:20px;overflow:auto;gap:16px}
.scan-bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.scan-bar input{background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:6px 10px;border-radius:4px;font-size:13px;width:300px}
.scan-bar select{background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:6px 10px;border-radius:4px;font-size:13px}
.scan-results{background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:14px;font-size:12px;max-height:300px;overflow:auto}
.scan-results pre{white-space:pre-wrap}
/* Search */
.search-bar{padding:8px 12px;background:var(--bg2);border-bottom:1px solid var(--border)}
.search-bar input{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--border);padding:6px 10px;border-radius:4px;font-size:13px}
/* Modal */
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.6);display:none;align-items:center;justify-content:center;z-index:100}
.modal-bg.show{display:flex}
.modal{background:var(--bg4);padding:20px;border-radius:8px;min-width:400px;max-width:600px;border:1px solid var(--border)}
.modal h3{margin-bottom:12px;font-size:15px}
.modal input,.modal textarea,.modal select{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--border);padding:8px;border-radius:4px;font-size:13px;margin-bottom:10px}
.modal textarea{min-height:80px;resize:vertical}
.modal .row{display:flex;gap:8px;justify-content:flex-end;margin-top:8px}
.toast{position:fixed;bottom:20px;right:20px;background:var(--bg4);border:1px solid var(--border);padding:10px 18px;border-radius:6px;font-size:13px;z-index:200;opacity:0;transition:opacity .3s}
.toast.show{opacity:1}
</style></head><body>
<header>
  <h1>Skills Sync Manager</h1>
  <div class="tabs">
    <div class="tab active" onclick="switchTab('dashboard')">Dashboard</div>
    <div class="tab" onclick="switchTab('skills')">Skills</div>
    <div class="tab" onclick="switchTab('presets')">Presets</div>
    <div class="tab" onclick="switchTab('agents')">Agents</div>
  </div>
  <div class="header-actions">
    <button class="btn btn-primary btn-sm" onclick="syncAll()">Sync All</button>
    <button class="btn btn-secondary btn-sm" onclick="refresh()">Refresh</button>
  </div>
</header>
<main>
  <!-- Dashboard -->
  <div id="dashboard" class="page active"></div>
  <!-- Skills -->
  <div id="skills-page" class="page">
    <div style="flex:1;display:flex;flex-direction:column;overflow:hidden">
      <div class="search-bar"><input id="skillSearch" placeholder="Search skills..." oninput="renderSkills()"></div>
      <div class="skill-table-wrap"><table id="skillTbl"><thead></thead><tbody></tbody></table></div>
    </div>
    <div class="drawer" id="skillDrawer"><em style="color:var(--text2)">Click a row to preview.</em></div>
  </div>
  <!-- Presets -->
  <div id="presets-page" class="page"></div>
  <!-- Agents -->
  <div id="agents-page" class="page"></div>
</main>
<div class="modal-bg" id="modalBg"><div class="modal" id="modal"></div></div>
<div class="toast" id="toast"></div>
<script>
let SKILLS=[],AGENTS=[],PRESETS=[],SYNC_STATUS=[],SEL_SKILL=null;

async function api(path,opts={}){
  const r=await fetch(path,{headers:{'Content-Type':'application/json'},...opts});
  return r.json();
}
function toast(msg,ms){const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),ms||2000);}
function esc(s){return(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

function switchTab(name){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  const tabs=document.querySelectorAll('.tab');
  const map={dashboard:0,skills:1,presets:2,agents:3};
  tabs[map[name]].classList.add('active');
  document.getElementById(name==='dashboard'?'dashboard':name==='skills'?'skills-page':name==='presets'?'presets-page':'agents-page').classList.add('active');
  if(name==='dashboard')renderDashboard();
  if(name==='skills')renderSkills();
  if(name==='presets')renderPresets();
  if(name==='agents')renderAgents();
}

async function refresh(){
  const d=await api('/api/skills');SKILLS=d.skills||[];
  const a=await api('/api/agents');AGENTS=a.agents||[];SYNC_STATUS=a.sync_status||[];
  const p=await api('/api/presets');PRESETS=p.presets||[];
  const cur=document.querySelector('.tab.active')?.textContent?.toLowerCase();
  if(cur==='dashboard')renderDashboard();
  else if(cur==='skills')renderSkills();
  else if(cur==='presets')renderPresets();
  else if(cur==='agents')renderAgents();
  toast('Refreshed');
}

// ── Dashboard ──
function renderDashboard(){
  const el=document.getElementById('dashboard');
  const totalSkills=SKILLS.length;
  const enabledSkills=SKILLS.filter(s=>s.enabled).length;
  const installedAgents=AGENTS.length;
  el.innerHTML=`
    <div class="stats">
      <div class="stat-card"><div class="label">Total Skills</div><div class="value">${totalSkills}</div><div class="sub">${enabledSkills} enabled</div></div>
      <div class="stat-card"><div class="label">Installed Agents</div><div class="value">${installedAgents}</div><div class="sub">${SYNC_STATUS.length} configured</div></div>
      <div class="stat-card"><div class="label">Presets</div><div class="value">${PRESETS.length}</div></div>
      <div class="stat-card"><div class="label">Sync Mode</div><div class="value" style="font-size:20px">${SYNC_STATUS[0]?.tool||'N/A'}</div><div class="sub">symlink</div></div>
    </div>
    <div class="section-title">Agent Sync Status</div>
    <div class="agent-grid">${SYNC_STATUS.map(a=>`
      <div class="agent-card">
        <h3>${esc(a.name)}</h3>
        <div class="meta">${esc(a.tool)} &middot; ${esc(a.path)}</div>
        <div style="margin-top:8px">
          <span style="color:var(--green)">${a.synced_count}</span> / <span>${a.total_count}</span> synced
        </div>
        <div style="background:var(--bg);border-radius:4px;height:6px;margin-top:6px;overflow:hidden">
          <div style="background:var(--green);height:100%;width:${a.total_count?a.synced_count/a.total_count*100:0}%;transition:width .3s"></div>
        </div>
        <div class="preset-list" style="margin-top:8px">
          ${(a.active_presets||[]).map(p=>`<span class="preset-tag active">${esc(p)}</span>`).join('')}
        </div>
      </div>`).join('')}
    </div>`;
}

// ── Skills ──
function renderSkills(){
  const thead=document.querySelector('#skillTbl thead');
  const tbody=document.querySelector('#skillTbl tbody');
  thead.innerHTML='<tr><th>#</th><th>On</th><th>Name</th><th>Description</th><th>Size</th><th>Agents</th></tr>';
  const q=(document.getElementById('skillSearch')?.value||'').toLowerCase();
  const rows=SKILLS.filter(s=>{
    if(q&&!s.name.toLowerCase().includes(q)&&!(s.description||'').toLowerCase().includes(q))return false;
    return true;
  });
  tbody.innerHTML=rows.map((s,i)=>{
    const cls=(SEL_SKILL===s.dir?'selected ':'')+(s.enabled?'':'disabled');
    const agentDots=SYNC_STATUS.map(a=>{
      const ok=a.synced.includes(s.dir);
      return `<span class="sync-dot ${ok?'ok':'miss'}" title="${esc(a.name)}: ${ok?'synced':'missing'}"></span>`;
    }).join('');
    return `<tr class="clickable ${cls}" onclick="selectSkill('${s.dir}')">
      <td>${i+1}</td>
      <td><span class="toggle ${s.enabled?'on':'off'}" onclick="event.stopPropagation();toggleSkill('${s.dir}',${s.enabled})">${s.enabled?'●':'○'}</span></td>
      <td>${esc(s.name)}</td>
      <td style="color:var(--text2)">${esc((s.description||'').substring(0,50))}</td>
      <td style="color:var(--text2)">${s.size}B</td>
      <td><div class="sync-icons">${agentDots}</div></td>
    </tr>`;
  }).join('');
}

async function selectSkill(dir){
  SEL_SKILL=dir;renderSkills();
  const d=await api(`/api/skills/${encodeURIComponent(dir)}/content`);
  const s=d.skill||{};
  const agentDots=SYNC_STATUS.map(a=>{
    const ok=a.synced.includes(dir);
    return `<span class="sync-dot ${ok?'ok':'miss'}" title="${esc(a.name)}: ${ok?'synced':'missing'}"></span>`;
  }).join('');
  document.getElementById('skillDrawer').innerHTML=`
    <h2>${esc(s.name||dir)}</h2>
    <div class="meta">${esc(s.description||'')} &middot; ${s.size||0} bytes &middot; ${s.enabled?'enabled':'disabled'}</div>
    <div class="meta" style="word-break:break-all">${esc(s.path||'')}</div>
    <div class="sync-icons" style="margin:6px 0">${agentDots} <span style="font-size:11px;color:var(--text2);margin-left:4px">sync status</span></div>
    <div class="actions">
      <button class="btn btn-sm ${s.enabled?'btn-danger':'btn-success'}" onclick="toggleSkill('${dir}',${s.enabled})">${s.enabled?'Disable':'Enable'}</button>
      <button class="btn btn-sm btn-secondary" onclick="editSkillModal('${dir}')">Edit</button>
      <button class="btn btn-sm btn-danger" onclick="deleteSkill('${dir}')">Delete</button>
    </div>
    <h3 style="font-size:13px;color:var(--text2);margin-top:8px">Content</h3>
    <pre>${esc(d.content||'')}</pre>`;
}

async function toggleSkill(dir,currentlyEnabled){
  const action=currentlyEnabled?'disable':'enable';
  const r=await api(`/api/skills/${encodeURIComponent(dir)}/${action}`,{method:'POST'});
  if(r.ok){await refresh();if(SEL_SKILL===dir)selectSkill(dir);toast(r.ok?`${action}d`:'Failed');}
  else toast('Failed: '+(r.error||''));
}

async function deleteSkill(dir){
  if(!confirm(`Move "${dir}" to trash?`))return;
  const r=await api(`/api/skills/${encodeURIComponent(dir)}/delete`,{method:'POST'});
  if(r.ok){SEL_SKILL=null;document.getElementById('skillDrawer').innerHTML='<em style="color:var(--text2)">deleted.</em>';await refresh();toast('Deleted');}
  else toast('Failed');
}

function editSkillModal(dir){
  const s=SKILLS.find(x=>x.dir===dir);if(!s)return;
  const m=document.getElementById('modal');
  m.innerHTML=`<h3>Edit: ${esc(s.name)}</h3>
    <label>Name</label><input id="ename" value="${esc(s.name)}">
    <label>Description</label><textarea id="edesc">${esc(s.description||'')}</textarea>
    <div class="row"><button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="saveEditSkill('${dir}')">Save</button></div>`;
  document.getElementById('modalBg').classList.add('show');
}

async function saveEditSkill(dir){
  const name=document.getElementById('ename').value;
  const description=document.getElementById('edesc').value;
  const r=await api(`/api/skills/${encodeURIComponent(dir)}/edit`,{method:'POST',body:JSON.stringify({name,description})});
  closeModal();
  if(r.ok){await refresh();selectSkill(dir);toast('Saved');}
  else toast('Failed');
}

function closeModal(){document.getElementById('modalBg').classList.remove('show');}
document.getElementById('modalBg').onclick=e=>{if(e.target.id==='modalBg')closeModal();};

// ── Presets ──
function renderPresets(){
  const el=document.getElementById('presets-page');
  el.innerHTML=`
    <div style="display:flex;justify-content:space-between;align-items:center">
      <div class="section-title">Presets (${PRESETS.length})</div>
      <button class="btn btn-primary btn-sm" onclick="createPresetModal()">+ New Preset</button>
    </div>
    <div class="preset-cards">${PRESETS.map(p=>{
      const skills=p.skills||[];
      const agentStatus=SYNC_STATUS.map(a=>{
        const isActive=(a.active_presets||[]).includes(p.name);
        return `<div class="agent-status">${esc(a.name)}: ${isActive?'<span style="color:var(--green)">✓ Active</span>':'<span style="color:var(--text2)">inactive</span>'}</div>`;
      }).join('');
      return `<div class="preset-card">
        <h3>${esc(p.name)}</h3>
        <div class="desc">${esc(p.description||'')}</div>
        <div class="skill-chips">${skills.map(s=>`<span class="chip">${esc(s)}</span>`).join('')}</div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          ${SYNC_STATUS.map(a=>{
            const isActive=(a.active_presets||[]).includes(p.name);
            return isActive
              ?`<button class="btn btn-sm btn-danger" onclick="deactivatePreset('${p.name}','${a.name}')">Deactivate (${esc(a.name)})</button>`
              :`<button class="btn btn-sm btn-success" onclick="activatePreset('${p.name}','${a.name}')">Activate (${esc(a.name)})</button>`;
          }).join('')}
        </div>
        ${agentStatus}
      </div>`;
    }).join('')}</div>`;
}

async function activatePreset(preset,agent){
  const r=await api(`/api/presets/${encodeURIComponent(preset)}/activate`,{method:'POST',body:JSON.stringify({agent})});
  if(r.ok){await refresh();toast('Activated');}else toast('Failed');
}
async function deactivatePreset(preset,agent){
  const r=await api(`/api/presets/${encodeURIComponent(preset)}/deactivate`,{method:'POST',body:JSON.stringify({agent})});
  if(r.ok){await refresh();toast('Deactivated');}else toast('Failed');
}

function createPresetModal(){
  const allSkills=SKILLS.map(s=>s.dir);
  const m=document.getElementById('modal');
  m.innerHTML=`<h3>New Preset</h3>
    <label>Name</label><input id="pname">
    <label>Description</label><input id="pdesc">
    <label>Skills (comma-separated)</label><textarea id="pskills" placeholder="skill-a,skill-b,...">${allSkills.join(',')}</textarea>
    <div class="row"><button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="createPreset()">Create</button></div>`;
  document.getElementById('modalBg').classList.add('show');
}

async function createPreset(){
  const name=document.getElementById('pname').value;
  const description=document.getElementById('pdesc').value;
  const skills=document.getElementById('pskills').value.split(',').map(s=>s.trim()).filter(Boolean);
  const r=await api('/api/presets',{method:'POST',body:JSON.stringify({name,description,skills})});
  closeModal();
  if(r.ok){await refresh();toast('Created');}else toast('Failed');
}

// ── Agents ──
function renderAgents(){
  const el=document.getElementById('agents-page');
  el.innerHTML=`
    <div class="section-title">Installed Agents (${AGENTS.length})</div>
    <div class="agent-grid">${AGENTS.map(a=>`
      <div class="agent-card">
        <h3>${esc(a.label)}</h3>
        <div class="meta">${esc(a.skills_dir)}</div>
        <div style="margin-top:6px"><span style="color:var(--green)">${a.skill_count}</span> skills installed</div>
      </div>`).join('')}
    </div>
    <div class="section-title" style="margin-top:16px">Scan Projects</div>
    <div class="scan-bar">
      <input id="scanPath" placeholder="Path to scan (e.g. D:\\06_Project)" value="D:\\06_Project">
      <select id="scanDepth"><option value="2">Depth 2</option><option value="3" selected>Depth 3</option><option value="4">Depth 4</option></select>
      <button class="btn btn-primary btn-sm" onclick="doScan()">Scan</button>
      <button class="btn btn-success btn-sm" onclick="doScanImport()">Scan & Import</button>
    </div>
    <div class="scan-results" id="scanResults" style="display:none"><pre id="scanOutput"></pre></div>
    <div class="section-title" style="margin-top:16px">Sync Configuration</div>
    <div class="agent-grid">${SYNC_STATUS.map(a=>`
      <div class="agent-card">
        <h3>${esc(a.name)}</h3>
        <div class="meta">${esc(a.tool)} &middot; ${esc(a.path)}</div>
        <div style="margin-top:6px">${a.synced_count}/${a.total_count} synced</div>
        <div class="preset-list" style="margin-top:6px">
          ${(a.active_presets||[]).map(p=>`<span class="preset-tag active">${esc(p)}</span>`).join('')}
        </div>
      </div>`).join('')}
    </div>`;
}

async function doScan(){
  const path=document.getElementById('scanPath').value;
  const depth=document.getElementById('scanDepth').value;
  document.getElementById('scanResults').style.display='block';
  document.getElementById('scanOutput').textContent='Scanning...';
  const r=await api('/api/scan',{method:'POST',body:JSON.stringify({path,max_depth:parseInt(depth)})});
  document.getElementById('scanOutput').textContent=JSON.stringify(r,null,2);
}
async function doScanImport(){
  const path=document.getElementById('scanPath').value;
  const depth=document.getElementById('scanDepth').value;
  document.getElementById('scanResults').style.display='block';
  document.getElementById('scanOutput').textContent='Scanning and importing...';
  const r=await api('/api/scan/import',{method:'POST',body:JSON.stringify({path,max_depth:parseInt(depth)})});
  document.getElementById('scanOutput').textContent=JSON.stringify(r,null,2);
  await refresh();
}

async function syncAll(){
  toast('Syncing...');
  const r=await api('/api/sync',{method:'POST'});
  toast(r.ok?'Sync complete!':'Sync failed');
  await refresh();
}

// ── Init ──
(async()=>{
  await refresh();
})();
</script></body></html>'''


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
