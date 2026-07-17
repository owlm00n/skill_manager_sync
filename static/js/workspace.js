/* ── Global Workspace ────────────────────────── */
let GWS_SELECTED_AGENT = null;
let GWS_SKILLS = [];
let GWS_SELECTED = new Set();

function renderGlobalWS() {
  const el = document.getElementById('page-global-ws');
  if (!GWS_SELECTED_AGENT && INSTALLED_AGENTS.length > 0) GWS_SELECTED_AGENT = INSTALLED_AGENTS[0].key;

  el.innerHTML = `<div class="flex h-full gap-3">
    <!-- Agent List -->
    <div class="w-56 glass-panel rounded-2xl p-3 flex flex-col gap-1 overflow-auto flex-shrink-0">
      <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-2">Agents</h3>
      ${INSTALLED_AGENTS.map(a => `
        <div class="sidebar-item ${GWS_SELECTED_AGENT === a.key ? 'active' : ''}" onclick="selectGWSAgent('${esc(a.key)}')">
          <div class="w-2 h-2 rounded-full ${a.skill_count > 0 ? 'bg-green-500' : 'bg-slate-400'}"></div>
          <span class="truncate text-sm">${esc(a.label)}</span>
          <span class="ml-auto text-xs text-slate-400">${a.skill_count}</span>
        </div>
      `).join('')}
      ${INSTALLED_AGENTS.length === 0 ? '<p class="text-sm text-slate-400 px-3 py-4">No agents detected</p>' : ''}
    </div>
    <!-- Skill List -->
    <div class="flex-1 flex flex-col glass-panel rounded-2xl overflow-hidden">
      <div class="p-4 border-b border-slate-200/60 dark:border-slate-700/50 flex items-center gap-3">
        <h3 class="font-bold text-slate-800 dark:text-white" id="gwsAgentTitle">${GWS_SELECTED_AGENT || 'Select agent'}</h3>
        <button onclick="addSkillsModal()" class="btn-gradient px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
          Add Skills
        </button>
        ${GWS_SELECTED.size > 0 ? `<div class="flex gap-1.5 ml-auto">
          <button onclick="gwsBatchAction('remove')" class="px-3 py-1 text-xs font-semibold rounded-lg bg-red-100 dark:bg-red-900/30 text-red-600">Remove (${GWS_SELECTED.size})</button>
          <button onclick="GWS_SELECTED.clear();renderGlobalWS()" class="px-2 py-1 text-xs text-slate-400">Clear</button>
        </div>` : ''}
      </div>
      <!-- Preset pills -->
      <div class="px-4 py-2 border-b border-slate-200/40 dark:border-slate-700/30 flex flex-wrap gap-1.5" id="gwsPresets"></div>
      <!-- Skills -->
      <div class="flex-1 overflow-auto">
        <table class="w-full text-sm">
          <thead class="sticky top-0 bg-slate-100/80 dark:bg-slate-800/80 backdrop-blur-sm">
            <tr>
              <th class="px-3 py-2 text-left w-8"><input type="checkbox" class="skill-checkbox" onchange="gwsToggleAll(this.checked)"></th>
              <th class="px-3 py-2 text-left font-semibold text-slate-500 text-xs uppercase">Status</th>
              <th class="px-3 py-2 text-left font-semibold text-slate-500 text-xs uppercase">Name</th>
              <th class="px-3 py-2 text-left font-semibold text-slate-500 text-xs uppercase">Source</th>
              <th class="px-3 py-2 text-left font-semibold text-slate-500 text-xs uppercase">Description</th>
            </tr>
          </thead>
          <tbody id="gwsBody">
            <tr><td colspan="5" class="px-4 py-8 text-center text-slate-400">Loading...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>`;

  if (GWS_SELECTED_AGENT) loadGWSAgentSkills(GWS_SELECTED_AGENT);
}

async function selectGWSAgent(key) {
  GWS_SELECTED_AGENT = key;
  GWS_SELECTED.clear();
  renderGlobalWS();
}

async function loadGWSAgentSkills(agentKey) {
  const r = await api(`/api/workspace/global/${encodeURIComponent(agentKey)}`);
  GWS_SKILLS = r.skills || [];
  const agent = INSTALLED_AGENTS.find(a => a.key === agentKey);
  const title = document.getElementById('gwsAgentTitle');
  if (title && agent) title.textContent = `${agent.label} (${GWS_SKILLS.length} skills)`;

  // Render preset pills
  const presetEl = document.getElementById('gwsPresets');
  if (presetEl) {
    presetEl.innerHTML = PRESETS.map(p => {
      const skills = p.skills || [];
      const agentSkills = GWS_SKILLS.map(s => s.name);
      const matched = skills.filter(s => agentSkills.includes(s)).length;
      const isActive = matched === skills.length && skills.length > 0;
      const isPartial = matched > 0 && matched < skills.length;
      const cls = isActive ? 'active' : (isPartial ? 'partial' : '');
      const badge = isPartial ? `<span class="text-xs bg-amber-500/20 text-amber-500 rounded-full px-1.5">${matched}/${skills.length}</span>` : '';
      return `<span class="preset-pill ${cls}" onclick="togglePresetForAgent('${esc(p.name)}','${esc(agentKey)}')">${esc(p.name)} ${badge}</span>`;
    }).join('');
  }

  // Render skill rows
  const tbody = document.getElementById('gwsBody');
  if (tbody) {
    if (GWS_SKILLS.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="px-4 py-8 text-center text-slate-400">No skills found</td></tr>';
      return;
    }
    tbody.innerHTML = GWS_SKILLS.map(s => {
      const checked = GWS_SELECTED.has(s.name);
      const isCentral = s.source === 'central';
      return `<tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer" onclick="previewGWSSkill('${esc(s.name)}')">
        <td class="px-3 py-2.5"><input type="checkbox" class="skill-checkbox" ${checked ? 'checked' : ''} onclick="event.stopPropagation();gwsToggleSelect('${esc(s.name)}',this.checked)"></td>
        <td class="px-3 py-2.5"><span class="inline-flex items-center justify-center w-5 h-5 rounded-full text-xs ${s.enabled ? 'bg-green-100 dark:bg-green-900/40 text-green-600' : 'bg-red-100 dark:bg-red-900/40 text-red-500'}">${s.enabled ? '✓' : '✗'}</span></td>
        <td class="px-3 py-2.5 font-semibold text-slate-800 dark:text-white">${esc(s.name)}</td>
        <td class="px-3 py-2.5"><span class="source-badge ${isCentral ? 'source-central' : 'source-external'}">${isCentral ? 'Central' : 'External'}</span></td>
        <td class="px-3 py-2.5 text-slate-500 text-xs truncate max-w-[200px]">${esc((s.description || '').substring(0, 60))}</td>
      </tr>`;
    }).join('');
  }
}

function gwsToggleSelect(name, checked) {
  if (checked) GWS_SELECTED.add(name); else GWS_SELECTED.delete(name);
  renderGlobalWS();
}
function gwsToggleAll(checked) {
  if (checked) GWS_SKILLS.forEach(s => GWS_SELECTED.add(s.name)); else GWS_SELECTED.clear();
  renderGlobalWS();
}

async function gwsBatchAction(action) {
  const names = [...GWS_SELECTED];
  if (names.length === 0) return;
  const r = await api(`/api/workspace/global/${encodeURIComponent(GWS_SELECTED_AGENT)}/${action}`, {
    method: 'POST', body: JSON.stringify({ skill_names: names })
  });
  if (r.ok) { GWS_SELECTED.clear(); showToast(`${action} done`); await refresh(); loadGWSAgentSkills(GWS_SELECTED_AGENT); }
  else showToast('Failed', 'error');
}

async function previewGWSSkill(name) {
  // Try to find in central skills first
  const central = SKILLS.find(s => s.dir === name);
  if (central) { navigate('library'); setTimeout(() => selectSkill(name), 100); return; }
  // Otherwise show in workspace drawer
  const gwsSkill = GWS_SKILLS.find(s => s.name === name);
  if (gwsSkill) {
    showToast(`External skill: ${name} (${gwsSkill.path || 'unknown path'})`);
  }
}

async function togglePresetForAgent(presetName, agentKey) {
  const agent = INSTALLED_AGENTS.find(a => a.key === agentKey);
  const agentSync = SYNC_STATUS.find(a => a.name === agentKey || a.tool === agentKey);
  const isActive = agentSync && (agentSync.active_presets || []).includes(presetName);
  const action = isActive ? 'deactivate' : 'activate';
  const r = await api(`/api/presets/${encodeURIComponent(presetName)}/${action}`, {
    method: 'POST', body: JSON.stringify({ agent: agentKey })
  });
  if (r.ok) { showToast(`${presetName} ${action}d`); await refresh(); loadGWSAgentSkills(agentKey); }
  else showToast('Failed', 'error');
}

/* ── Add Skills Modal ────────────────────────── */
function addSkillsModal() {
  const available = SKILLS.filter(s => !GWS_SKILLS.find(g => g.name === s.dir));
  openModal(`<h3 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Add Skills to Agent</h3>
    <input id="addSkillSearch" placeholder="Search..." oninput="filterAddSkills()" class="input-modern w-full px-4 py-2.5 rounded-xl text-sm mb-3">
    <div id="addSkillList" class="max-h-[40vh] overflow-auto space-y-1 mb-4">
      ${available.map(s => `<label class="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer">
        <input type="checkbox" class="skill-checkbox add-skill-cb" value="${esc(s.dir)}">
        <span class="font-semibold text-sm text-slate-800 dark:text-white">${esc(s.name)}</span>
        <span class="text-xs text-slate-400 truncate">${esc((s.description || '').substring(0, 50))}</span>
      </label>`).join('')}
      ${available.length === 0 ? '<p class="text-sm text-slate-400 py-4 text-center">All skills already added</p>' : ''}
    </div>
    <div class="flex justify-end gap-2">
      <button onclick="closeModal()" class="px-4 py-2 text-sm font-semibold rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Cancel</button>
      <button onclick="doAddSkills()" class="btn-gradient px-4 py-2 text-sm font-bold rounded-xl">Add Selected</button>
    </div>`);
}

function filterAddSkills() {
  const q = document.getElementById('addSkillSearch').value.toLowerCase();
  document.querySelectorAll('.add-skill-cb').forEach(cb => {
    cb.closest('label').style.display = cb.value.toLowerCase().includes(q) ? '' : 'none';
  });
}

async function doAddSkills() {
  const names = [...document.querySelectorAll('.add-skill-cb:checked')].map(cb => cb.value);
  if (names.length === 0) { closeModal(); return; }
  const r = await api(`/api/workspace/global/${encodeURIComponent(GWS_SELECTED_AGENT)}/add`, {
    method: 'POST', body: JSON.stringify({ skill_names: names })
  });
  closeModal();
  if (r.ok) { showToast(`Added ${names.length} skills`); await refresh(); loadGWSAgentSkills(GWS_SELECTED_AGENT); }
  else showToast('Failed', 'error');
}

/* ── Project Workspace ───────────────────────── */
let PWS_PATH = 'D:\\06_Project';
let PWS_DEPTH = 3;
let PWS_RESULTS = null;

function renderProjectWS() {
  const el = document.getElementById('page-project-ws');
  el.innerHTML = `<div class="glass-panel rounded-2xl p-6 animate-fade-in-up">
    <h2 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Project Workspace</h2>
    <!-- Scan Controls -->
    <div class="flex flex-wrap gap-3 items-end mb-6">
      <div class="flex-1 min-w-[200px]">
        <label class="block text-xs font-semibold text-slate-500 mb-1">Scan Path</label>
        <input id="pwsPath" value="${esc(PWS_PATH)}" class="input-modern w-full px-4 py-2.5 rounded-xl text-sm font-mono">
      </div>
      <div class="w-28">
        <label class="block text-xs font-semibold text-slate-500 mb-1">Depth</label>
        <select id="pwsDepth" class="input-modern w-full px-3 py-2.5 rounded-xl text-sm">
          <option value="2" ${PWS_DEPTH == 2 ? 'selected' : ''}>2</option>
          <option value="3" ${PWS_DEPTH == 3 ? 'selected' : ''}>3</option>
          <option value="4" ${PWS_DEPTH == 4 ? 'selected' : ''}>4</option>
        </select>
      </div>
      <button onclick="scanProjectWS()" class="btn-gradient px-5 py-2.5 rounded-xl text-sm font-bold">Scan</button>
      <button onclick="scanProjectImport()" class="btn-success px-5 py-2.5 rounded-xl text-sm font-bold">Scan & Import</button>
    </div>
    <!-- Results -->
    <div id="pwsResults">${renderProjectResults()}</div>
  </div>`;
}

function renderProjectResults() {
  if (!PWS_RESULTS) return '<p class="text-sm text-slate-400 py-4">Click Scan to discover project skills</p>';
  const projects = PWS_RESULTS.projects || [];
  if (projects.length === 0) return '<p class="text-sm text-slate-400 py-4">No project skills found</p>';

  return projects.map(p => {
    const skills = p.skills || [];
    return `<div class="bg-white/50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200/50 dark:border-slate-700/50 mb-3">
      <div class="flex items-center gap-2 mb-3">
        <svg class="w-5 h-5 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
        <h3 class="font-bold text-sm text-slate-800 dark:text-white">${esc(p.path || p.name || 'Unknown')}</h3>
        <span class="ml-auto text-xs text-slate-400">${skills.length} skills</span>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
        ${skills.map(s => {
          const inCentral = SKILLS.find(c => c.dir === s.name);
          const status = inCentral ? 'central' : 'unique';
          return `<div class="flex items-center gap-2 p-2 rounded-lg bg-slate-50 dark:bg-slate-900/30">
            <span class="source-badge ${status === 'central' ? 'source-central' : 'source-project'}">${status === 'central' ? 'In Library' : 'Unique'}</span>
            <span class="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">${esc(s.name)}</span>
            ${status === 'unique' ? `<button onclick="importProjectSkill('${esc(p.path)}','${esc(s.name)}')" class="ml-auto px-2 py-0.5 text-xs font-semibold rounded bg-green-100 dark:bg-green-900/30 text-green-600 hover:bg-green-200">Import</button>` : ''}
          </div>`;
        }).join('')}
      </div>
    </div>`;
  }).join('');
}

async function scanProjectWS() {
  PWS_PATH = document.getElementById('pwsPath').value;
  PWS_DEPTH = document.getElementById('pwsDepth').value;
  showToast('Scanning...');
  PWS_RESULTS = await api('/api/scan', { method: 'POST', body: JSON.stringify({ path: PWS_PATH, max_depth: parseInt(PWS_DEPTH) }) });
  document.getElementById('pwsResults').innerHTML = renderProjectResults();
  showToast('Scan complete');
}

async function scanProjectImport() {
  PWS_PATH = document.getElementById('pwsPath').value;
  PWS_DEPTH = document.getElementById('pwsDepth').value;
  showToast('Scanning and importing...');
  const r = await api('/api/scan/import', { method: 'POST', body: JSON.stringify({ path: PWS_PATH, max_depth: parseInt(PWS_DEPTH) }) });
  if (r.ok || r.projects) { showToast('Imported'); await refresh(); } else showToast(r.error || 'Failed', 'error');
  PWS_RESULTS = await api('/api/scan', { method: 'POST', body: JSON.stringify({ path: PWS_PATH, max_depth: parseInt(PWS_DEPTH) }) });
  document.getElementById('pwsResults').innerHTML = renderProjectResults();
}

async function importProjectSkill(projectPath, skillName) {
  const r = await api('/api/workspace/project/import', {
    method: 'POST', body: JSON.stringify({ path: projectPath, skill_names: [skillName] })
  });
  if (r.ok) { showToast('Imported'); await refresh(); renderProjectWS(); } else showToast('Failed', 'error');
}
