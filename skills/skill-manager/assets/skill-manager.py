#!/usr/bin/env python
"""
Skill Manager for Claude Code skills.
Dual-mode: standalone CLI + embedded Web UI.

Usage:
  python skill-manager.py list [--verbose] [--trash] [--source=user|project|plugin]
  python skill-manager.py preview <index>
  python skill-manager.py enable <index>
  python skill-manager.py disable <index>
  python skill-manager.py edit <index> [--name NAME] [--desc TEXT]
  python skill-manager.py delete <index>
  python skill-manager.py undelete [<index>]
  python skill-manager.py web [port]
"""

import os
import re
import sys
import json
import shutil
import datetime
from pathlib import Path

# Force UTF-8 on Windows consoles that default to GBK/CP936
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HOME = Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))
CLAUDE_DIR = HOME / ".claude"
USER_SKILLS_DIR = CLAUDE_DIR / "skills"
PLUGIN_MARKETS_DIR = CLAUDE_DIR / "plugins" / "marketplaces"
MGR_DIR = CLAUDE_DIR / "skill-manager"
TRASH_DIR = MGR_DIR / "trash"

MGR_DIR.mkdir(parents=True, exist_ok=True)
TRASH_DIR.mkdir(parents=True, exist_ok=True)


# ────────────────────────── Scanning ──────────────────────────

def _project_skills_dir():
    cwd = Path.cwd()
    p = cwd / ".claude" / "skills"
    return p if p.is_dir() else None


def _scan_dir(base, source_label):
    """Find all skill folders (containing SKILL.md or SKILL.md.disabled) under base."""
    out = []
    if not base or not Path(base).is_dir():
        return out
    for d in sorted(Path(base).iterdir()):
        if not d.is_dir():
            continue
        active = d / "SKILL.md"
        disabled = d / "SKILL.md.disabled"
        if active.exists():
            out.append((d, active, True, source_label))
        elif disabled.exists():
            out.append((d, disabled, False, source_label))
    return out


def _scan_plugin_skills():
    """Scan ~/.claude/plugins/marketplaces/*/{external_plugins,plugins}/*/skills/*"""
    out = []
    if not PLUGIN_MARKETS_DIR.is_dir():
        return out
    for market in sorted(PLUGIN_MARKETS_DIR.iterdir()):
        if not market.is_dir():
            continue
        for kind in ("external_plugins", "plugins"):
            kdir = market / kind
            if not kdir.is_dir():
                continue
            for plugin in sorted(kdir.iterdir()):
                if not plugin.is_dir():
                    continue
                sdir = plugin / "skills"
                if not sdir.is_dir():
                    continue
                label = f"plugin:{plugin.name}"
                out.extend(_scan_dir(sdir, label))
    return out


def scan_all_skills(source_filter=None):
    """Return list of skill records sorted by source then name."""
    records = []
    if source_filter in (None, "user"):
        records.extend(_scan_dir(USER_SKILLS_DIR, "user"))
    if source_filter in (None, "project"):
        proj = _project_skills_dir()
        if proj:
            records.extend(_scan_dir(proj, "project"))
    if source_filter in (None, "plugin"):
        records.extend(_scan_plugin_skills())

    results = []
    for d, skill_file, enabled, source in records:
        meta = parse_frontmatter(skill_file)
        try:
            st = skill_file.stat()
            size = st.st_size
            mtime = st.st_mtime
        except OSError:
            size, mtime = 0, 0
        results.append({
            "dir": str(d),
            "file": str(skill_file),
            "enabled": enabled,
            "source": source,
            "name": meta.get("name") or d.name,
            "description": meta.get("description") or "",
            "frontmatter": meta,
            "size": size,
            "mtime": mtime,
        })
    results.sort(key=lambda r: (r["source"], r["name"].lower()))
    for i, r in enumerate(results, 1):
        r["index"] = i
    return results


# ────────────────────────── Frontmatter ──────────────────────────

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(path):
    """Minimal YAML frontmatter parser — top-level scalar keys only."""
    out = {}
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    m = FM_RE.match(text)
    if not m:
        return out
    body = m.group(1)
    key = None
    for line in body.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m2 = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if m2:
            key = m2.group(1)
            val = m2.group(2).strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            out[key] = val
    return out


def get_body(path):
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    m = FM_RE.match(text)
    return text[m.end():] if m else text


def edit_frontmatter(path, updates):
    """Replace top-level scalar keys in frontmatter. Creates .bak. Returns (ok, msg)."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        return False, f"read failed: {e}"
    m = FM_RE.match(text)
    if not m:
        return False, "no frontmatter found"
    fm_body = m.group(1)
    rest = text[m.end():]
    lines = fm_body.split("\n")
    remaining = dict(updates)
    for i, line in enumerate(lines):
        m2 = re.match(r"^([A-Za-z_][\w-]*)(\s*:\s*)(.*)$", line)
        if m2 and m2.group(1) in remaining:
            k = m2.group(1)
            v = remaining.pop(k)
            if v is None:
                continue
            quoted = json.dumps(v, ensure_ascii=False) if (":" in v or "#" in v or v.startswith(("'", '"'))) else v
            lines[i] = f"{k}: {quoted}"
    for k, v in remaining.items():
        if v is None:
            continue
        quoted = json.dumps(v, ensure_ascii=False) if (":" in v or "#" in v) else v
        lines.append(f"{k}: {quoted}")
    new_fm = "\n".join(lines)
    new_text = f"---\n{new_fm}\n---\n{rest}"
    bak = p.with_suffix(p.suffix + ".bak")
    try:
        shutil.copy2(p, bak)
        p.write_text(new_text, encoding="utf-8")
    except OSError as e:
        return False, f"write failed: {e}"
    return True, f"updated; backup at {bak}"


# ────────────────────────── Enable / Disable ──────────────────────────

def set_enabled(record, enabled):
    d = Path(record["dir"])
    active = d / "SKILL.md"
    disabled = d / "SKILL.md.disabled"
    if enabled:
        if active.exists():
            return False, "already enabled"
        if not disabled.exists():
            return False, "no SKILL.md.disabled found"
        disabled.rename(active)
        return True, "enabled"
    else:
        if disabled.exists() and not active.exists():
            return False, "already disabled"
        if not active.exists():
            return False, "no SKILL.md found"
        if disabled.exists():
            disabled.unlink()
        active.rename(disabled)
        return True, "disabled"


# ────────────────────────── Soft Delete ──────────────────────────

def delete_skill(record):
    d = Path(record["dir"])
    if not d.is_dir():
        return False, "directory missing"
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_src = record["source"].replace(":", "_")
    target_parent = TRASH_DIR / safe_src
    target_parent.mkdir(parents=True, exist_ok=True)
    target = target_parent / f"{d.name}__{ts}"
    shutil.move(str(d), str(target))
    origin = target / ".origin"
    origin.write_text(json.dumps({
        "original_dir": str(d),
        "source": record["source"],
        "name": record["name"],
        "deleted_at": ts,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return True, str(target)


def list_trash():
    out = []
    if not TRASH_DIR.is_dir():
        return out
    for src_dir in sorted(TRASH_DIR.iterdir()):
        if not src_dir.is_dir():
            continue
        for entry in sorted(src_dir.iterdir()):
            if not entry.is_dir():
                continue
            origin = entry / ".origin"
            info = {}
            if origin.exists():
                try:
                    info = json.loads(origin.read_text(encoding="utf-8"))
                except Exception:
                    pass
            out.append({
                "trash_path": str(entry),
                "source": info.get("source", src_dir.name),
                "name": info.get("name", entry.name),
                "original_dir": info.get("original_dir", ""),
                "deleted_at": info.get("deleted_at", ""),
            })
    out.sort(key=lambda r: r["deleted_at"], reverse=True)
    for i, r in enumerate(out, 1):
        r["index"] = i
    return out


def restore_trash(entry):
    src = Path(entry["trash_path"])
    orig = Path(entry["original_dir"]) if entry.get("original_dir") else None
    if not orig:
        return False, "no original path recorded"
    if orig.exists():
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        orig = orig.with_name(orig.name + f".restored-{ts}")
    orig.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(orig))
    # Remove .origin sidecar from restored dir
    o = orig / ".origin"
    if o.exists():
        try:
            o.unlink()
        except OSError:
            pass
    return True, str(orig)


# ────────────────────────── CLI ──────────────────────────

def _trunc(s, n):
    s = s or ""
    s = s.replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def cmd_list(argv):
    verbose = "--verbose" in argv or "-v" in argv
    trash = "--trash" in argv
    src = None
    for a in argv:
        if a.startswith("--source="):
            src = a.split("=", 1)[1]
    if trash:
        items = list_trash()
        if not items:
            print("(trash is empty)")
            return
        print(f"{'#':>3}  {'Source':<20} {'Name':<28} Deleted")
        print("-" * 80)
        for it in items:
            print(f"{it['index']:>3}  {it['source']:<20} {_trunc(it['name'],28):<28} {it['deleted_at']}")
        return

    skills = scan_all_skills(source_filter=src)
    if not skills:
        print("(no skills found)")
        return
    print(f"{'#':>3}  {'On':<3} {'Source':<22} {'Name':<28} Description")
    print("-" * 100)
    for s in skills:
        on = "✓" if s["enabled"] else "✗"
        print(f"{s['index']:>3}  {on:<3} {_trunc(s['source'],22):<22} {_trunc(s['name'],28):<28} {_trunc(s['description'],40)}")
        if verbose:
            print(f"       path: {s['file']}")
            for k, v in s["frontmatter"].items():
                if k not in ("name", "description"):
                    print(f"       {k}: {v}")
    print(f"\nTotal: {len(skills)} skills")


def _resolve(idx, source_filter=None):
    skills = scan_all_skills(source_filter=source_filter)
    try:
        n = int(idx)
    except ValueError:
        return None, "index must be integer"
    for s in skills:
        if s["index"] == n:
            return s, None
    return None, f"index {n} out of range (1..{len(skills)})"


def cmd_preview(argv):
    if not argv:
        print("usage: preview <index>"); return
    s, err = _resolve(argv[0])
    if err:
        print(err); return
    print(f"#{s['index']}  {s['name']}   ({'enabled' if s['enabled'] else 'disabled'})")
    print(f"source: {s['source']}")
    print(f"path:   {s['file']}")
    print(f"size:   {s['size']} bytes")
    print()
    try:
        print(Path(s["file"]).read_text(encoding="utf-8", errors="replace"))
    except OSError as e:
        print(f"(read error: {e})")


def cmd_enable(argv):
    if not argv:
        print("usage: enable <index>"); return
    s, err = _resolve(argv[0])
    if err: print(err); return
    ok, msg = set_enabled(s, True)
    print(f"{'OK' if ok else 'ERR'}: {s['name']} — {msg}")


def cmd_disable(argv):
    if not argv:
        print("usage: disable <index>"); return
    s, err = _resolve(argv[0])
    if err: print(err); return
    ok, msg = set_enabled(s, False)
    print(f"{'OK' if ok else 'ERR'}: {s['name']} — {msg}")


def cmd_edit(argv):
    if not argv:
        print("usage: edit <index> [--name NAME] [--desc TEXT]"); return
    s, err = _resolve(argv[0])
    if err: print(err); return
    updates = {}
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--name" and i + 1 < len(argv):
            updates["name"] = argv[i + 1]; i += 2
        elif a == "--desc" and i + 1 < len(argv):
            updates["description"] = argv[i + 1]; i += 2
        elif a.startswith("--name="):
            updates["name"] = a.split("=", 1)[1]; i += 1
        elif a.startswith("--desc="):
            updates["description"] = a.split("=", 1)[1]; i += 1
        else:
            i += 1
    if not updates:
        print("nothing to update"); return
    ok, msg = edit_frontmatter(s["file"], updates)
    print(f"{'OK' if ok else 'ERR'}: {msg}")


def cmd_delete(argv):
    if not argv:
        print("usage: delete <index>"); return
    s, err = _resolve(argv[0])
    if err: print(err); return
    ok, msg = delete_skill(s)
    print(f"{'OK' if ok else 'ERR'}: moved to {msg}" if ok else f"ERR: {msg}")


def cmd_undelete(argv):
    items = list_trash()
    if not items:
        print("(trash empty)"); return
    if argv:
        try:
            n = int(argv[0])
        except ValueError:
            print("index must be integer"); return
        target = next((i for i in items if i["index"] == n), None)
        if not target:
            print(f"index {n} not in trash"); return
        ok, msg = restore_trash(target)
        print(f"{'OK' if ok else 'ERR'}: {msg}")
    else:
        for it in items:
            ok, msg = restore_trash(it)
            print(f"{'OK' if ok else 'ERR'}: {it['name']} -> {msg}")


# ────────────────────────── Web UI ──────────────────────────

HTML = r'''<!doctype html>
<html><head><meta charset="utf-8"><title>Skill Manager</title>
<style>
*{box-sizing:border-box;font-family:-apple-system,Segoe UI,sans-serif}
body{margin:0;background:#1a1a1a;color:#e0e0e0}
header{background:#2a2a2a;padding:12px 20px;border-bottom:1px solid #3a3a3a;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
header h1{font-size:18px;margin:0;color:#fff}
header input,header select{background:#1a1a1a;color:#e0e0e0;border:1px solid #444;padding:6px 10px;border-radius:4px;font-size:13px}
header button{background:#0066cc;color:#fff;border:0;padding:6px 14px;border-radius:4px;cursor:pointer;font-size:13px}
header button:hover{background:#0080ff}
header button.secondary{background:#444}
header label{font-size:13px;cursor:pointer}
main{display:grid;grid-template-columns:1fr 480px;height:calc(100vh - 56px)}
#table-wrap{overflow:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #2a2a2a}
th{background:#252525;position:sticky;top:0;cursor:pointer;user-select:none;font-weight:600}
tr:hover{background:#252525}
tr.selected{background:#1e3a5f}
tr.disabled{opacity:0.55}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;background:#444}
.badge.user{background:#2d5a2d}
.badge.project{background:#5a4a2d}
.badge.plugin{background:#2d4a5a}
.toggle{cursor:pointer;font-size:18px;color:#666}
.toggle.on{color:#4ade80}
.toggle.off{color:#f87171}
#drawer{background:#222;border-left:1px solid #3a3a3a;padding:16px;overflow:auto}
#drawer h2{margin:0 0 12px 0;font-size:16px}
#drawer pre{background:#1a1a1a;padding:12px;border-radius:4px;overflow:auto;font-size:12px;white-space:pre-wrap;word-break:break-word;max-height:60vh}
#drawer .meta{font-size:12px;color:#999;margin-bottom:8px}
#drawer .actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
#drawer .actions button{background:#0066cc;color:#fff;border:0;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px}
#drawer .actions button.danger{background:#cc3333}
#drawer .actions button.secondary{background:#444}
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.7);display:none;align-items:center;justify-content:center;z-index:100}
.modal-bg.show{display:flex}
.modal{background:#2a2a2a;padding:20px;border-radius:8px;min-width:400px;max-width:600px}
.modal h3{margin:0 0 12px 0}
.modal input,.modal textarea{width:100%;background:#1a1a1a;color:#e0e0e0;border:1px solid #444;padding:8px;border-radius:4px;font-size:13px;margin-bottom:10px}
.modal textarea{min-height:80px;resize:vertical;font-family:inherit}
.modal .row{display:flex;gap:8px;justify-content:flex-end;margin-top:8px}
.modal button{padding:6px 14px;border-radius:4px;border:0;cursor:pointer;font-size:13px}
.modal .ok{background:#0066cc;color:#fff}
.modal .cancel{background:#444;color:#fff}
#status{font-size:12px;color:#888;margin-left:auto}
</style></head>
<body>
<header>
  <h1>🧩 Skill Manager</h1>
  <input id="search" placeholder="search name/description..." style="width:220px">
  <select id="srcFilter"><option value="">all sources</option><option value="user">user</option><option value="project">project</option><option value="plugin">plugin</option></select>
  <label><input type="checkbox" id="showDisabled" checked> show disabled</label>
  <button onclick="loadSkills()">↻ refresh</button>
  <button class="secondary" onclick="toggleTrash()">🗑 trash</button>
  <span id="status"></span>
</header>
<main>
  <div id="table-wrap"><table id="tbl"><thead></thead><tbody></tbody></table></div>
  <aside id="drawer"><em style="color:#666">Click a row to preview.</em></aside>
</main>
<div class="modal-bg" id="modalBg"><div class="modal" id="modal"></div></div>
<script>
let SKILLS=[], TRASH=[], MODE='skills', SEL=null;

async function api(path, opts={}){
  const r = await fetch(path, opts);
  return r.json();
}

async function loadSkills(){
  setStatus('loading...');
  const d = await api('/api/skills');
  SKILLS = d.skills;
  MODE = 'skills';
  render();
  setStatus(`${SKILLS.length} skills`);
}

async function loadTrash(){
  setStatus('loading trash...');
  const d = await api('/api/trash');
  TRASH = d.items;
  MODE = 'trash';
  render();
  setStatus(`${TRASH.length} in trash`);
}

function toggleTrash(){
  if(MODE==='trash') loadSkills(); else loadTrash();
}

function setStatus(s){ document.getElementById('status').textContent = s; }

function render(){
  const thead = document.querySelector('#tbl thead');
  const tbody = document.querySelector('#tbl tbody');
  if(MODE==='trash'){
    thead.innerHTML = '<tr><th>#</th><th>Name</th><th>Source</th><th>Deleted</th><th>Original Path</th><th></th></tr>';
    tbody.innerHTML = TRASH.map(t=>`
      <tr><td>${t.index}</td><td>${escape_(t.name)}</td><td><span class="badge">${escape_(t.source)}</span></td>
      <td>${escape_(t.deleted_at)}</td><td style="font-size:11px;color:#888">${escape_(t.original_dir)}</td>
      <td><button onclick="restoreItem(${t.index})">restore</button></td></tr>`).join('');
    return;
  }
  thead.innerHTML = '<tr><th>#</th><th>On</th><th>Name</th><th>Source</th><th>Description</th></tr>';
  const q = document.getElementById('search').value.toLowerCase();
  const sf = document.getElementById('srcFilter').value;
  const showDis = document.getElementById('showDisabled').checked;
  const rows = SKILLS.filter(s=>{
    if(!showDis && !s.enabled) return false;
    if(sf && !s.source.startsWith(sf)) return false;
    if(q && !(s.name.toLowerCase().includes(q) || (s.description||'').toLowerCase().includes(q))) return false;
    return true;
  });
  tbody.innerHTML = rows.map(s=>{
    const cls = (SEL===s.index?'selected ':'') + (s.enabled?'':'disabled');
    const badge = s.source.startsWith('plugin')?'plugin':s.source;
    return `<tr class="${cls}" onclick="selectRow(${s.index})">
      <td>${s.index}</td>
      <td><span class="toggle ${s.enabled?'on':'off'}" onclick="event.stopPropagation();toggle(${s.index})">${s.enabled?'●':'○'}</span></td>
      <td>${escape_(s.name)}</td>
      <td><span class="badge ${badge}">${escape_(s.source)}</span></td>
      <td style="color:#bbb">${escape_(s.description||'')}</td>
    </tr>`;
  }).join('');
}

function escape_(s){ return (s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

async function selectRow(idx){
  SEL = idx; render();
  const d = await api(`/api/skills/${idx}/content`);
  const s = d.skill;
  document.getElementById('drawer').innerHTML = `
    <h2>${escape_(s.name)}</h2>
    <div class="meta">${escape_(s.source)} · ${s.enabled?'enabled':'disabled'} · ${s.size} bytes</div>
    <div class="meta" style="word-break:break-all">${escape_(s.file)}</div>
    <div class="actions">
      <button onclick="toggle(${idx})">${s.enabled?'Disable':'Enable'}</button>
      <button class="secondary" onclick="editModal(${idx})">Edit</button>
      <button class="danger" onclick="deleteItem(${idx})">Delete</button>
    </div>
    <h3 style="margin-top:16px;font-size:14px">Content</h3>
    <pre>${escape_(d.content)}</pre>`;
}

async function toggle(idx){
  const s = SKILLS.find(x=>x.index===idx);
  const action = s.enabled ? 'disable' : 'enable';
  const r = await api(`/api/skills/${idx}/${action}`, {method:'POST'});
  if(r.ok){ await loadSkills(); if(SEL===idx) selectRow(idx); }
  else alert(r.error||'failed');
}

async function deleteItem(idx){
  const s = SKILLS.find(x=>x.index===idx);
  if(!confirm(`Move "${s.name}" to trash?`)) return;
  const r = await api(`/api/skills/${idx}/delete`, {method:'POST'});
  if(r.ok){ SEL=null; document.getElementById('drawer').innerHTML='<em style="color:#666">deleted.</em>'; loadSkills(); }
  else alert(r.error||'failed');
}

async function restoreItem(idx){
  const r = await api(`/api/trash/${idx}/restore`, {method:'POST'});
  if(r.ok) loadTrash();
  else alert(r.error||'failed');
}

function editModal(idx){
  const s = SKILLS.find(x=>x.index===idx);
  const m = document.getElementById('modal');
  m.innerHTML = `<h3>Edit: ${escape_(s.name)}</h3>
    <label>Name</label><input id="ename" value="${escape_(s.name)}">
    <label>Description</label><textarea id="edesc">${escape_(s.description||'')}</textarea>
    <div class="row"><button class="cancel" onclick="closeModal()">Cancel</button>
    <button class="ok" onclick="saveEdit(${idx})">Save</button></div>`;
  document.getElementById('modalBg').classList.add('show');
}

async function saveEdit(idx){
  const name = document.getElementById('ename').value;
  const desc = document.getElementById('edesc').value;
  const r = await api(`/api/skills/${idx}/edit`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name, description: desc})
  });
  closeModal();
  if(r.ok){ await loadSkills(); selectRow(idx); }
  else alert(r.error||'failed');
}

function closeModal(){ document.getElementById('modalBg').classList.remove('show'); }
document.getElementById('modalBg').onclick = e=>{ if(e.target.id==='modalBg') closeModal(); };
document.getElementById('search').oninput = render;
document.getElementById('srcFilter').onchange = render;
document.getElementById('showDisabled').onchange = render;

loadSkills();
</script></body></html>'''


def cmd_web(argv):
    import http.server
    import urllib.parse
    import webbrowser
    from threading import Thread

    port = 8766
    if argv:
        try:
            port = int(argv[0])
        except ValueError:
            pass

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass

        def _json(self, obj, code=200):
            data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _html(self, html):
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _body(self):
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0:
                return {}
            try:
                return json.loads(self.rfile.read(n))
            except Exception:
                return {}

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            p = u.path.rstrip("/")
            if p in ("", "/"):
                return self._html(HTML)
            if p == "/api/skills":
                skills = scan_all_skills()
                public = [{"index": s["index"], "name": s["name"], "description": s["description"],
                           "source": s["source"], "enabled": s["enabled"], "size": s["size"]} for s in skills]
                return self._json({"skills": public})
            if p == "/api/trash":
                return self._json({"items": list_trash()})
            m = re.match(r"^/api/skills/(\d+)/content$", p)
            if m:
                s, err = _resolve(m.group(1))
                if err: return self._json({"error": err}, 404)
                try:
                    content = Path(s["file"]).read_text(encoding="utf-8", errors="replace")
                except OSError as e:
                    content = f"(read error: {e})"
                return self._json({"skill": {"name": s["name"], "source": s["source"], "enabled": s["enabled"],
                                             "file": s["file"], "size": s["size"]}, "content": content})
            return self._json({"error": "not found"}, 404)

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            p = u.path.rstrip("/")
            m = re.match(r"^/api/skills/(\d+)/(enable|disable|delete|edit)$", p)
            if m:
                idx, action = m.group(1), m.group(2)
                s, err = _resolve(idx)
                if err: return self._json({"error": err}, 404)
                if action == "enable":
                    ok, msg = set_enabled(s, True)
                elif action == "disable":
                    ok, msg = set_enabled(s, False)
                elif action == "delete":
                    ok, msg = delete_skill(s)
                elif action == "edit":
                    body = self._body()
                    updates = {}
                    if "name" in body: updates["name"] = body["name"]
                    if "description" in body: updates["description"] = body["description"]
                    if not updates:
                        return self._json({"error": "nothing to update"}, 400)
                    ok, msg = edit_frontmatter(s["file"], updates)
                return self._json({"ok": ok, "msg": msg} if ok else {"error": msg}, 200 if ok else 400)
            m = re.match(r"^/api/trash/(\d+)/restore$", p)
            if m:
                items = list_trash()
                n = int(m.group(1))
                target = next((i for i in items if i["index"] == n), None)
                if not target: return self._json({"error": "not found"}, 404)
                ok, msg = restore_trash(target)
                return self._json({"ok": ok, "msg": msg} if ok else {"error": msg}, 200 if ok else 400)
            return self._json({"error": "not found"}, 404)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"Skill Manager Web UI → {url}")
    print("Ctrl+C to stop.")
    Thread(target=lambda: webbrowser.open(url), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


# ────────────────────────── Main ──────────────────────────

COMMANDS = {
    "list": cmd_list, "preview": cmd_preview, "enable": cmd_enable,
    "disable": cmd_disable, "edit": cmd_edit, "delete": cmd_delete,
    "undelete": cmd_undelete, "web": cmd_web,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return
    cmd = sys.argv[1]
    fn = COMMANDS.get(cmd)
    if not fn:
        print(f"unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)
    fn(sys.argv[2:])


if __name__ == "__main__":
    main()
