/* ── Library Page ────────────────────────────── */
let LIB_FILTER = { search: '', tag: '', source: 'all', showDisabled: true, viewTrash: false };
let LIB_SELECTED = new Set();

function renderLibrary() {
  const el = document.getElementById('page-library');
  let skills = LIB_FILTER.viewTrash ? [] : SKILLS.filter(s => {
    if (!LIB_FILTER.showDisabled && !s.enabled) return false;
    if (LIB_FILTER.search) {
      const q = LIB_FILTER.search.toLowerCase();
      if (!s.name.toLowerCase().includes(q) && !(s.description || '').toLowerCase().includes(q)) return false;
    }
    if (LIB_FILTER.tag === '__untagged__') {
      if (s.tags && s.tags.length > 0) return false;
    } else if (LIB_FILTER.tag) {
      if (!s.tags || !s.tags.includes(LIB_FILTER.tag)) return false;
    }
    return true;
  });

  // Unique tags for filter
  const allTags = new Set();
  SKILLS.forEach(s => (s.tags || []).forEach(t => allTags.add(t)));
  const untaggedCount = SKILLS.filter(s => !s.tags || s.tags.length === 0).length;

  el.innerHTML = `<div class="flex h-full gap-3">
    <!-- Left: Skill List -->
    <div class="flex-1 flex flex-col glass-panel rounded-2xl overflow-hidden">
      <!-- Toolbar -->
      <div class="p-4 border-b border-slate-200/60 dark:border-slate-700/50 space-y-3">
        <div class="flex gap-2">
          <div class="relative flex-1">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <input placeholder="Search skills..." value="${esc(LIB_FILTER.search)}" oninput="LIB_FILTER.search=this.value;renderLibrary()" class="input-modern w-full pl-10 pr-4 py-2.5 rounded-xl text-sm">
          </div>
          <button onclick="installSkillModal()" class="btn-gradient px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-1.5">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
            Install
          </button>
          <button onclick="scanImportModal()" class="px-3 py-2 rounded-xl text-sm font-semibold bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 transition-colors flex items-center gap-1.5">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg>
            Scan & Import
          </button>
          <button onclick="LIB_FILTER.viewTrash=!LIB_FILTER.viewTrash;renderLibrary()" class="px-3 py-2 rounded-xl text-sm font-semibold ${LIB_FILTER.viewTrash ? 'bg-red-100 dark:bg-red-900/30 text-red-600' : 'bg-slate-100 dark:bg-slate-700 text-slate-500'} transition-colors flex items-center gap-1.5">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            ${LIB_FILTER.viewTrash ? 'Back' : 'Trash'}
          </button>
          <button onclick="openFolder(SKILLS_DIR)" class="px-3 py-2 rounded-xl text-sm font-semibold bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 transition-colors flex items-center gap-1.5" title="${esc(SKILLS_DIR)}">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
            Open
          </button>
        </div>
        <!-- Tag filters -->
        <div class="flex flex-wrap gap-1.5 items-center">
          <span class="text-xs font-semibold text-slate-400 mr-1">Tags:</span>
          <span class="tag-chip cursor-pointer ${!LIB_FILTER.tag ? 'ring-2 ring-primary-400' : ''}" onclick="LIB_FILTER.tag='';renderLibrary()">All</span>
          ${[...allTags].map(t => `<span class="tag-chip cursor-pointer ${LIB_FILTER.tag === t ? 'ring-2 ring-primary-400' : ''}" onclick="LIB_FILTER.tag='${esc(t)}';renderLibrary()">${esc(t)}</span>`).join('')}
          ${untaggedCount > 0 ? `<span class="tag-chip cursor-pointer ${LIB_FILTER.tag === '__untagged__' ? 'ring-2 ring-primary-400' : ''}" onclick="LIB_FILTER.tag='__untagged__';renderLibrary()">Untagged (${untaggedCount})</span>` : ''}
        </div>
        <!-- Batch bar -->
        ${LIB_SELECTED.size > 0 ? `<div class="flex items-center gap-2 bg-primary-50 dark:bg-primary-900/20 rounded-xl px-4 py-2">
          <span class="text-sm font-semibold text-primary-600 dark:text-primary-400">${LIB_SELECTED.size} selected</span>
          <button onclick="batchAction('enable')" class="px-3 py-1 text-xs font-semibold rounded-lg bg-green-100 dark:bg-green-900/30 text-green-600 hover:bg-green-200">Enable</button>
          <button onclick="batchAction('disable')" class="px-3 py-1 text-xs font-semibold rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-600 hover:bg-amber-200">Disable</button>
          <button onclick="batchAction('delete')" class="px-3 py-1 text-xs font-semibold rounded-lg bg-red-100 dark:bg-red-900/30 text-red-600 hover:bg-red-200">Delete</button>
          <button onclick="batchAction('export')" class="px-3 py-1 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200">Export</button>
          <button onclick="LIB_SELECTED.clear();renderLibrary()" class="ml-auto text-xs text-slate-400 hover:text-slate-600">Clear</button>
        </div>` : ''}
      </div>
      <!-- Table -->
      <div class="flex-1 overflow-auto">
        <table class="w-full text-sm">
          <thead class="sticky top-0 bg-slate-100/80 dark:bg-slate-800/80 backdrop-blur-sm z-10">
            <tr>
              <th class="px-3 py-3 text-left w-8"><input type="checkbox" class="skill-checkbox" onchange="toggleSelectAll(this.checked)"></th>
              <th class="px-3 py-3 text-left font-semibold text-slate-500 text-xs uppercase tracking-wider">Status</th>
              <th class="px-3 py-3 text-left font-semibold text-slate-500 text-xs uppercase tracking-wider">Name</th>
              <th class="px-3 py-3 text-left font-semibold text-slate-500 text-xs uppercase tracking-wider">Description</th>
              <th class="px-3 py-3 text-left font-semibold text-slate-500 text-xs uppercase tracking-wider">Tags</th>
              <th class="px-3 py-3 text-left font-semibold text-slate-500 text-xs uppercase tracking-wider">Agents</th>
              <th class="px-3 py-3 text-left font-semibold text-slate-500 text-xs uppercase tracking-wider w-8"></th>
            </tr>
          </thead>
          <tbody id="skillBody">
            ${LIB_FILTER.viewTrash ? renderTrashRows() : renderSkillRows(skills)}
          </tbody>
        </table>
      </div>
    </div>
    <!-- Right: Preview Drawer -->
    <div class="w-96 glass-panel rounded-2xl overflow-auto drawer-scroll p-5 flex-shrink-0" id="skillDrawer">
      <div class="flex flex-col items-center justify-center h-full text-slate-400 dark:text-slate-500">
        <svg class="w-12 h-12 mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
        <p class="text-sm font-medium">Click a skill to preview</p>
      </div>
    </div>
  </div>`;
}

function renderSkillRows(skills) {
  return skills.map((s, i) => {
    const sel = SEL_SKILL === s.dir;
    const checked = LIB_SELECTED.has(s.dir);
    const tags = (s.tags || []).map(t => `<span class="tag-chip">${esc(t)}</span>`).join('');
    return `<tr class="cursor-pointer transition-colors ${sel ? 'bg-primary-50 dark:bg-primary-900/20' : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'} ${!s.enabled ? 'opacity-40' : ''}" onclick="selectSkill('${esc(s.dir)}')">
      <td class="px-3 py-3"><input type="checkbox" class="skill-checkbox" ${checked ? 'checked' : ''} onclick="event.stopPropagation();toggleSelect('${esc(s.dir)}',this.checked)"></td>
      <td class="px-3 py-3"><span class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs ${s.enabled ? 'bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-400' : 'bg-red-100 dark:bg-red-900/40 text-red-500'}">${s.enabled ? '✓' : '✗'}</span></td>
      <td class="px-3 py-3 font-semibold text-slate-800 dark:text-white">${esc(s.name)}</td>
      <td class="px-3 py-3 text-slate-500 text-xs max-w-[200px] truncate">${esc((s.description || '').substring(0, 60))}</td>
      <td class="px-3 py-3"><div class="flex gap-1 flex-wrap">${tags}</div></td>
      <td class="px-3 py-3"><div class="flex gap-1 flex-wrap">${agentBadgeHTML(s.dir)}</div></td>
      <td class="px-3 py-3">
        <button onclick="event.stopPropagation();openFolder('${escPath(s.folder || '')}')" class="p-1 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors" title="${esc(s.folder || '')}">
          <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
        </button>
      </td>
    </tr>`;
  }).join('');
}

function renderTrashRows() {
  return `<tr><td colspan="6" class="px-4 py-8 text-center text-slate-400">
    <p class="mb-2">Trash view - deleted skills appear here</p>
    <button onclick="loadTrash()" class="btn-gradient px-4 py-2 rounded-xl text-sm font-bold">View Trash</button>
  </td></tr>`;
}

async function loadTrash() {
  const r = await api('/api/trash');
  const items = r.items || [];
  const tbody = document.getElementById('skillBody');
  if (items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="px-4 py-8 text-center text-slate-400">Trash is empty</td></tr>';
    return;
  }
  tbody.innerHTML = items.map((t, i) => `<tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50">
    <td class="px-3 py-3 text-slate-400 text-xs">${i + 1}</td>
    <td class="px-3 py-3"><span class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs bg-red-100 dark:bg-red-900/40 text-red-500">✗</span></td>
    <td class="px-3 py-3 font-semibold text-slate-800 dark:text-white">${esc(t.name)}</td>
    <td class="px-3 py-3 text-slate-500 text-xs">${esc(t.deleted_at || '')}</td>
    <td class="px-3 py-3 text-slate-500 text-xs font-mono truncate">${esc(t.dir || '')}</td>
    <td class="px-3 py-3">
      <button onclick="restoreTrash('${esc(t.name)}')" class="px-2 py-1 text-xs font-semibold rounded-lg bg-green-100 dark:bg-green-900/30 text-green-600 hover:bg-green-200">Restore</button>
    </td>
  </tr>`).join('');
}

async function restoreTrash(name) {
  const r = await api(`/api/trash/${encodeURIComponent(name)}/restore`, { method: 'POST' });
  if (r.ok) { showToast('Restored'); await refresh(); } else showToast(r.error || 'Failed', 'error');
}

/* ── Selection ───────────────────────────────── */
function toggleSelect(dir, checked) {
  if (checked) LIB_SELECTED.add(dir); else LIB_SELECTED.delete(dir);
  renderLibrary();
}
function toggleSelectAll(checked) {
  if (checked) SKILLS.forEach(s => LIB_SELECTED.add(s.dir)); else LIB_SELECTED.clear();
  renderLibrary();
}

async function batchAction(action) {
  const names = [...LIB_SELECTED];
  if (names.length === 0) return;
  if (action === 'delete' && !confirm(`Delete ${names.length} skills?`)) return;
  const r = await api(`/api/skills/batch/${action}`, { method: 'POST', body: JSON.stringify({ names }) });
  if (r.ok) { showToast(`${action} done for ${names.length} skills`); LIB_SELECTED.clear(); await refresh(); }
  else showToast('Failed', 'error');
}

/* ── Skill Preview ───────────────────────────── */
async function selectSkill(dir) {
  SEL_SKILL = dir;
  renderLibrary();
  const d = await api('/api/skills/' + encodeURIComponent(dir) + '/content');
  const s = d.skill || {};
  const tags = (s.tags || []).map(t => `<span class="tag-chip">${esc(t)}</span>`).join(' ');

  document.getElementById('skillDrawer').innerHTML = `
    <div class="animate-fade-in-up">
      <h2 class="text-lg font-bold text-slate-800 dark:text-white mb-1">${esc(s.name || dir)}</h2>
      <p class="text-xs text-slate-500 mb-1">${esc(s.description || '')} · ${s.size || 0}B</p>
      <p class="text-xs text-slate-400 font-mono mb-3 truncate" title="${esc(s.folder || '')}">${esc(s.folder || '')}</p>
      <div class="flex items-center gap-2 mb-3">
        <span class="px-2 py-0.5 text-xs rounded-full font-medium ${s.enabled ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300' : 'bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-300'}">${s.enabled ? 'Enabled' : 'Disabled'}</span>
        ${tags}
      </div>
      <!-- Agent badges -->
      <div class="flex items-center gap-2 mb-4">
        <span class="text-xs font-semibold text-slate-400">Agents:</span>
        <div class="flex gap-1.5 flex-wrap">${agentBadgeHTML(dir, 'md')}</div>
      </div>
      <!-- Actions -->
      <div class="flex gap-2 mb-4 flex-wrap">
        <button onclick="toggleSkill('${dir}',${s.enabled})" class="px-3 py-1.5 text-xs font-semibold rounded-lg ${s.enabled ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200' : 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 hover:bg-green-200'} transition-colors">${s.enabled ? 'Disable' : 'Enable'}</button>
        <button onclick="editSkillModal('${dir}')" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 transition-colors">Edit</button>
        <button onclick="tagSkillModal('${dir}')" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 hover:bg-primary-200 transition-colors">Tags</button>
        <button onclick="openFolder('${escPath(s.folder || '')}')" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 hover:bg-amber-200 transition-colors flex items-center gap-1" title="${esc(s.folder || '')}">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
          Open Folder
        </button>
        <button onclick="deleteSkill('${dir}')" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-red-50 dark:bg-red-900/20 text-red-500 hover:bg-red-100 transition-colors">Delete</button>
      </div>
      <!-- Content -->
      <div class="border-t border-slate-200 dark:border-slate-700 pt-3">
        <h3 class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Content</h3>
        <pre class="bg-slate-100/80 dark:bg-black/40 rounded-xl p-3 text-xs overflow-auto max-h-[50vh] whitespace-pre-wrap break-words text-slate-700 dark:text-slate-300 font-mono">${esc(d.content || '')}</pre>
      </div>
    </div>`;
}

async function toggleSkill(dir, on) {
  const r = await api('/api/skills/' + encodeURIComponent(dir) + '/' + (on ? 'disable' : 'enable'), { method: 'POST' });
  if (r.ok) { await refresh(); if (SEL_SKILL === dir) selectSkill(dir); showToast(on ? 'Disabled' : 'Enabled'); } else showToast('Failed', 'error');
}
async function deleteSkill(dir) {
  if (!confirm('Move "' + dir + '" to trash?')) return;
  const r = await api('/api/skills/' + encodeURIComponent(dir) + '/delete', { method: 'POST' });
  if (r.ok) { SEL_SKILL = null; await refresh(); showToast('Deleted'); } else showToast('Failed', 'error');
}

function editSkillModal(dir) {
  const s = SKILLS.find(x => x.dir === dir); if (!s) return;
  openModal(`<h3 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Edit: ${esc(s.name)}</h3>
    <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Name</label>
    <input id="ename" value="${esc(s.name)}" class="input-modern w-full px-4 py-2.5 rounded-xl mb-3">
    <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Description</label>
    <textarea id="edesc" class="input-modern w-full px-4 py-2.5 rounded-xl mb-4 min-h-[80px]">${esc(s.description || '')}</textarea>
    <div class="flex justify-end gap-2">
      <button onclick="closeModal()" class="px-4 py-2 text-sm font-semibold rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Cancel</button>
      <button onclick="saveEditSkill('${dir}')" class="btn-gradient px-4 py-2 text-sm font-bold rounded-xl">Save</button>
    </div>`);
}
async function saveEditSkill(dir) {
  const name = document.getElementById('ename').value;
  const description = document.getElementById('edesc').value;
  const r = await api('/api/skills/' + encodeURIComponent(dir) + '/edit', { method: 'POST', body: JSON.stringify({ name, description }) });
  closeModal();
  if (r.ok) { await refresh(); selectSkill(dir); showToast('Saved'); } else showToast('Failed', 'error');
}

/* ── Tag Modal ───────────────────────────────── */
function tagSkillModal(dir) {
  const s = SKILLS.find(x => x.dir === dir); if (!s) return;
  const currentTags = (s.tags || []);
  openModal(`<h3 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Tags: ${esc(s.name)}</h3>
    <div class="flex flex-wrap gap-2 mb-4">${currentTags.map(t => `<span class="tag-chip">${esc(t)} <span class="cursor-pointer ml-1 text-red-400 hover:text-red-600" onclick="removeTag('${dir}','${esc(t)}')">&times;</span></span>`).join('') || '<span class="text-slate-400 text-sm">No tags</span>'}</div>
    <div class="flex gap-2">
      <input id="newTag" placeholder="Add tag..." class="input-modern flex-1 px-4 py-2.5 rounded-xl text-sm">
      <button onclick="addTag('${dir}')" class="btn-gradient px-4 py-2 rounded-xl text-sm font-bold">Add</button>
    </div>
    <div class="flex justify-end mt-4"><button onclick="closeModal()" class="px-4 py-2 text-sm font-semibold rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Close</button></div>`);
}
async function addTag(dir) {
  const tag = document.getElementById('newTag').value.trim(); if (!tag) return;
  const r = await api(`/api/skills/${encodeURIComponent(dir)}/tags`, { method: 'POST', body: JSON.stringify({ action: 'add', tag }) });
  if (r.ok) { await refresh(); tagSkillModal(dir); showToast('Tag added'); } else showToast('Failed', 'error');
}
async function removeTag(dir, tag) {
  const r = await api(`/api/skills/${encodeURIComponent(dir)}/tags`, { method: 'POST', body: JSON.stringify({ action: 'remove', tag }) });
  if (r.ok) { await refresh(); tagSkillModal(dir); showToast('Tag removed'); } else showToast('Failed', 'error');
}

/* ── Install Modal ───────────────────────────── */
function installSkillModal() {
  openModal(`<h3 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Install Skill</h3>
    <div class="space-y-4">
      <div>
        <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">From Local Path</label>
        <p class="text-xs text-slate-400 mb-1">Folder should contain SKILL.md file, e.g. <code class="bg-slate-100 dark:bg-slate-700 px-1 rounded">D:\\skills\\my-skill\\</code></p>
        <div class="flex gap-2">
          <input id="installPath" placeholder="D:\\path\\to\\skill-folder" class="input-modern flex-1 px-4 py-2.5 rounded-xl text-sm font-mono">
          <button onclick="installLocal()" class="btn-gradient px-4 py-2 rounded-xl text-sm font-bold">Install</button>
        </div>
      </div>
      <div class="border-t border-slate-200 dark:border-slate-700 pt-4">
        <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">From Git Repository</label>
        <div class="flex gap-2">
          <input id="installGit" placeholder="https://github.com/user/repo.git" class="input-modern flex-1 px-4 py-2.5 rounded-xl text-sm font-mono">
          <button onclick="installGit()" class="btn-gradient px-4 py-2 rounded-xl text-sm font-bold">Clone</button>
        </div>
      </div>
    </div>
    <div class="flex justify-end mt-4"><button onclick="closeModal()" class="px-4 py-2 text-sm font-semibold rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Cancel</button></div>`);
}
async function installLocal() {
  const path = document.getElementById('installPath').value.trim(); if (!path) return;
  showToast('Installing...');
  const r = await api('/api/skills/install/local', { method: 'POST', body: JSON.stringify({ path }) });
  closeModal();
  if (r.ok) { await refresh(); showToast('Installed'); } else showToast(r.error || 'Failed', 'error');
}
async function installGit() {
  const url = document.getElementById('installGit').value.trim(); if (!url) return;
  showToast('Cloning...');
  const r = await api('/api/skills/install/git', { method: 'POST', body: JSON.stringify({ url }) });
  closeModal();
  if (r.ok) { await refresh(); showToast('Installed'); } else showToast(r.error || 'Failed', 'error');
}

/* ── Sync Mode ──────────────────────────────── */
const SYNC_MODE_INFO = {
  junction: {
    label: '⚡ Junction',
    desc: 'Junction (目录联接) - 无需管理员权限，功能等同 Symlink。中央库更新后所有 agent 自动生效。',
    pros: '无需权限 | 自动跟随中央库 | 不占额外空间'
  },
  symlink: {
    label: '🔗 Symlink', 
    desc: 'Symbolic Link (符号链接) - 需要管理员权限或开发者模式。功能与 Junction 相同。',
    pros: '自动跟随中央库 | 需要管理员权限'
  },
  copy: {
    label: '📋 Copy',
    desc: 'Copy (复制) - 独立副本，不需要权限。中央库更新后需要手动同步才能更新到 agent。',
    pros: '无需权限 | 独立副本 | 需手动同步更新'
  }
};

async function changeSyncMode(mode) {
  const info = SYNC_MODE_INFO[mode];
  if (!info) return;
  
  // Show explanation modal
  openModal(`
    <h3 class="text-lg font-bold text-slate-800 dark:text-white mb-3">切换同步模式</h3>
    <div class="space-y-3">
      <div class="p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
        <p class="font-semibold text-blue-700 dark:text-blue-300">${info.label}</p>
        <p class="text-sm text-blue-600 dark:text-blue-400 mt-1">${info.desc}</p>
        <p class="text-xs text-blue-500 dark:text-blue-500 mt-2">✓ ${info.pros}</p>
      </div>
      <p class="text-sm text-slate-500 dark:text-slate-400">切换后需要点击 "Sync All" 重新同步所有 agent。</p>
    </div>
    <div class="flex justify-end gap-2 mt-4">
      <button onclick="closeModal()" class="px-4 py-2 text-sm font-semibold rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">取消</button>
      <button onclick="confirmSyncMode('${mode}')" class="btn-gradient px-4 py-2 rounded-xl text-sm font-bold">确认切换</button>
    </div>
  `);
}

async function confirmSyncMode(mode) {
  closeModal();
  showToast(`切换到 ${mode} 模式...`);
  const r = await api('/api/settings/mode', { method: 'POST', body: JSON.stringify({ mode }) });
  if (r.ok) {
    SYNC_MODE = mode;
    document.querySelectorAll('#syncModeSelect').forEach(el => el.value = mode);
    showToast(`已切换到 ${mode} 模式`);
  } else {
    showToast(r.error || 'Failed', 'error');
  }
}

/* ── Scan & Import ─────────────────────────────── */
let LIB_SCAN_PATH = 'D:\\06_Project';
let LIB_SCAN_DEPTH = 3;
let LIB_SCAN_RESULTS = null;

function scanImportModal() {
  openModal(`<h3 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Scan & Import Skills</h3>
    <p class="text-sm text-slate-500 dark:text-slate-400 mb-3">Scan a directory for agent workspaces and import unique skills into the central library.</p>
    <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Scan Path</label>
    <input id="libScanPath" value="${esc(LIB_SCAN_PATH)}" class="input-modern w-full px-4 py-2.5 rounded-xl text-sm font-mono mb-3">
    <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Depth</label>
    <select id="libScanDepth" class="input-modern w-full px-3 py-2.5 rounded-xl text-sm mb-4">
      <option value="2" ${LIB_SCAN_DEPTH == 2 ? 'selected' : ''}>2</option>
      <option value="3" ${LIB_SCAN_DEPTH == 3 ? 'selected' : ''}>3</option>
      <option value="4" ${LIB_SCAN_DEPTH == 4 ? 'selected' : ''}>4</option>
    </select>
    <div id="libScanResults">${LIB_SCAN_RESULTS ? renderLibScanResults() : ''}</div>
    <div class="flex justify-end gap-2 mt-4">
      <button onclick="closeModal()" class="px-4 py-2 text-sm font-semibold rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Close</button>
      <button onclick="doLibScan()" class="btn-gradient px-4 py-2 text-sm font-bold rounded-xl">Scan</button>
      <button onclick="doLibScanImport()" class="btn-success px-4 py-2 text-sm font-bold rounded-xl">Scan & Import All</button>
    </div>
  `);
}

function renderLibScanResults() {
  if (!LIB_SCAN_RESULTS) return '';
  const workspaces = LIB_SCAN_RESULTS.workspaces || [];
  if (workspaces.length === 0) return '<p class="text-sm text-slate-400 py-2">No workspaces found</p>';
  
  let uniqueCount = 0;
  return workspaces.map(w => {
    const skills = w.skills || [];
    const unique = skills.filter(s => !SKILLS.find(c => c.dir === s.name));
    uniqueCount += unique.length;
    return `<div class="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 mb-2">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-400">${esc(w.label)}</span>
        <span class="text-sm font-medium truncate">${esc(w.project_name)}</span>
        <span class="ml-auto text-xs text-slate-400">${skills.length} skills (${unique.length} unique)</span>
      </div>
      ${unique.length > 0 ? `<div class="flex flex-wrap gap-1 mt-2">
        ${unique.map(s => `<span class="px-2 py-0.5 text-xs rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400">${esc(s.display_name || s.name)}</span>`).join('')}
      </div>` : ''}
    </div>`;
  }).join('') + `<p class="text-xs text-slate-400 mt-2">Found ${uniqueCount} unique skill(s) to import</p>`;
}

async function doLibScan() {
  LIB_SCAN_PATH = document.getElementById('libScanPath').value;
  LIB_SCAN_DEPTH = document.getElementById('libScanDepth').value;
  showToast('Scanning...');
  LIB_SCAN_RESULTS = await api('/api/workspace/scan', { method: 'POST', body: JSON.stringify({ path: LIB_SCAN_PATH, max_depth: parseInt(LIB_SCAN_DEPTH) }) });
  document.getElementById('libScanResults').innerHTML = renderLibScanResults();
  showToast('Scan complete');
}

async function doLibScanImport() {
  LIB_SCAN_PATH = document.getElementById('libScanPath').value;
  LIB_SCAN_DEPTH = document.getElementById('libScanDepth').value;
  showToast('Scanning and importing...');
  LIB_SCAN_RESULTS = await api('/api/workspace/scan', { method: 'POST', body: JSON.stringify({ path: LIB_SCAN_PATH, max_depth: parseInt(LIB_SCAN_DEPTH) }) });
  
  let importCount = 0;
  for (const w of (LIB_SCAN_RESULTS.workspaces || [])) {
    for (const s of (w.skills || [])) {
      if (!SKILLS.find(c => c.dir === s.name)) {
        const r = await api('/api/workspace/project/import', {
          method: 'POST', body: JSON.stringify({ path: w.project_path, skill_names: [s.name] })
        });
        if (r.ok) importCount++;
      }
    }
  }
  closeModal();
  await refresh();
  showToast(`Imported ${importCount} unique skill(s)`);
}
