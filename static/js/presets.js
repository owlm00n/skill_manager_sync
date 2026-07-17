/* ── Presets Page ────────────────────────────── */
function renderPresets() {
  const el = document.getElementById('page-presets');
  el.innerHTML = `<div class="glass-panel rounded-2xl p-6 animate-fade-in-up">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-lg font-bold text-slate-800 dark:text-white">Presets (${PRESETS.length})</h2>
      <button onclick="createPresetModal()" class="btn-gradient px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-1.5">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
        New Preset
      </button>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      ${PRESETS.map(p => renderPresetCard(p)).join('')}
    </div>
  </div>`;
}

function renderPresetCard(p) {
  const skills = p.skills || [];
  // Per-agent status
  const agentStatus = INSTALLED_AGENTS.map(a => {
    const agentSync = SYNC_STATUS.find(s => s.name === a.key || s.tool === a.key);
    const isActive = agentSync && (agentSync.active_presets || []).includes(p.name);
    // Check actual skill presence
    const agentSkills = a.synced || [];
    const matched = skills.filter(s => agentSkills.includes(s)).length;
    const isPartial = matched > 0 && matched < skills.length;
    const isFull = matched === skills.length && skills.length > 0;
    return { agent: a, isActive, isPartial, isFull, matched, total: skills.length };
  });

  const activeCount = agentStatus.filter(s => s.isActive).length;
  const partialCount = agentStatus.filter(s => s.isPartial && !s.isActive).length;

  return `<div class="bg-white/50 dark:bg-slate-800/50 rounded-xl p-5 border border-slate-200/50 dark:border-slate-700/50 hover:border-primary-300 dark:hover:border-primary-700 transition-colors">
    <div class="flex items-center gap-2 mb-2">
      <h3 class="font-bold text-slate-800 dark:text-white">${esc(p.name)}</h3>
      ${activeCount > 0 ? `<span class="px-2 py-0.5 text-xs rounded-full bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-400 font-medium">${activeCount} active</span>` : ''}
      <div class="ml-auto flex gap-1">
        <button onclick="editPresetModal('${esc(p.name)}')" class="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400" title="Edit">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
        </button>
      </div>
    </div>
    <p class="text-xs text-slate-500 mb-3">${esc(p.description || '')}</p>
    <!-- Skills list -->
    <div class="flex flex-wrap gap-1.5 mb-3">
      ${skills.map(s => {
        const exists = SKILLS.find(sk => sk.dir === s);
        return `<span class="px-2 py-0.5 text-xs rounded-full ${exists ? 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300' : 'bg-red-100 dark:bg-red-900/30 text-red-500'} font-medium">${esc(s)}</span>`;
      }).join('')}
    </div>
    <!-- Agent buttons -->
    <div class="flex flex-wrap gap-1.5">
      ${agentStatus.map(s => {
        if (!s.agent.installed) return '';
        if (s.isActive) {
          return `<button onclick="deactivatePreset('${esc(p.name)}','${esc(s.agent.key)}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 transition-colors">Deactivate ${esc(s.agent.label)}</button>`;
        } else if (s.isPartial) {
          return `<button onclick="activatePreset('${esc(p.name)}','${esc(s.agent.key)}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 hover:bg-amber-200 transition-colors">${s.matched}/${s.total} - Activate</button>`;
        } else {
          return `<button onclick="activatePreset('${esc(p.name)}','${esc(s.agent.key)}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 hover:bg-green-200 transition-colors">Activate ${esc(s.agent.label)}</button>`;
        }
      }).join('')}
    </div>
  </div>`;
}

async function activatePreset(p, a) {
  const r = await api('/api/presets/' + encodeURIComponent(p) + '/activate', {
    method: 'POST', body: JSON.stringify({ agent: a })
  });
  if (r.ok) { await refresh(); showToast('Activated'); } else showToast(r.error || 'Failed', 'error');
}

async function deactivatePreset(p, a) {
  const r = await api('/api/presets/' + encodeURIComponent(p) + '/deactivate', {
    method: 'POST', body: JSON.stringify({ agent: a })
  });
  if (r.ok) { await refresh(); showToast('Deactivated'); } else showToast(r.error || 'Failed', 'error');
}

function createPresetModal() {
  openModal(`<h3 class="text-lg font-bold text-slate-800 dark:text-white mb-4">New Preset</h3>
    <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Name</label>
    <input id="pname" class="input-modern w-full px-4 py-2.5 rounded-xl mb-3">
    <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Description</label>
    <input id="pdesc" class="input-modern w-full px-4 py-2.5 rounded-xl mb-3">
    <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-2">Skills</label>
    <div class="max-h-[30vh] overflow-auto space-y-1 mb-4 border border-slate-200 dark:border-slate-700 rounded-xl p-2">
      ${SKILLS.map(s => `<label class="flex items-center gap-2 p-1.5 rounded hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer">
        <input type="checkbox" class="skill-checkbox preset-skill-cb" value="${esc(s.dir)}">
        <span class="text-sm text-slate-700 dark:text-slate-300">${esc(s.name)}</span>
      </label>`).join('')}
    </div>
    <div class="flex justify-between">
      <button onclick="document.querySelectorAll('.preset-skill-cb').forEach(c=>c.checked=true)" class="text-xs text-primary-500 hover:underline">Select All</button>
      <div class="flex gap-2">
        <button onclick="closeModal()" class="px-4 py-2 text-sm font-semibold rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Cancel</button>
        <button onclick="createPreset()" class="btn-gradient px-4 py-2 text-sm font-bold rounded-xl">Create</button>
      </div>
    </div>`);
}

async function createPreset() {
  const name = document.getElementById('pname').value;
  const description = document.getElementById('pdesc').value;
  const skills = [...document.querySelectorAll('.preset-skill-cb:checked')].map(c => c.value);
  if (!name) { showToast('Name required', 'error'); return; }
  const r = await api('/api/presets', { method: 'POST', body: JSON.stringify({ name, description, skills }) });
  closeModal();
  if (r.ok) { await refresh(); showToast('Created'); } else showToast(r.error || 'Failed', 'error');
}

function editPresetModal(name) {
  const p = PRESETS.find(x => x.name === name); if (!p) return;
  const skills = p.skills || [];
  openModal(`<h3 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Edit: ${esc(name)}</h3>
    <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Description</label>
    <input id="epdesc" value="${esc(p.description || '')}" class="input-modern w-full px-4 py-2.5 rounded-xl mb-3">
    <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-2">Skills</label>
    <div class="max-h-[30vh] overflow-auto space-y-1 mb-4 border border-slate-200 dark:border-slate-700 rounded-xl p-2">
      ${SKILLS.map(s => `<label class="flex items-center gap-2 p-1.5 rounded hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer">
        <input type="checkbox" class="skill-checkbox preset-skill-cb" value="${esc(s.dir)}" ${skills.includes(s.dir) ? 'checked' : ''}>
        <span class="text-sm text-slate-700 dark:text-slate-300">${esc(s.name)}</span>
      </label>`).join('')}
    </div>
    <div class="flex justify-between">
      <button onclick="document.querySelectorAll('.preset-skill-cb').forEach(c=>c.checked=!c.checked)" class="text-xs text-primary-500 hover:underline">Toggle All</button>
      <div class="flex gap-2">
        <button onclick="closeModal()" class="px-4 py-2 text-sm font-semibold rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Cancel</button>
        <button onclick="savePresetEdit('${esc(name)}')" class="btn-gradient px-4 py-2 text-sm font-bold rounded-xl">Save</button>
      </div>
    </div>`);
}

async function savePresetEdit(oldName) {
  const description = document.getElementById('epdesc').value;
  const skills = [...document.querySelectorAll('.preset-skill-cb:checked')].map(c => c.value);
  const r = await api('/api/presets/' + encodeURIComponent(oldName) + '/edit', {
    method: 'POST', body: JSON.stringify({ description, skills })
  });
  closeModal();
  if (r.ok) { await refresh(); showToast('Saved'); } else showToast(r.error || 'Failed', 'error');
}
