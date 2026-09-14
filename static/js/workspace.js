/* ── Global Workspace (merged with Agents) ───────── */
let GWS_SELECTED_AGENT = null;
let GWS_SKILLS = [];
let GWS_SELECTED = new Set();
let GWS_SCANNED = false; // Track if we've auto-scanned

async function scanAgents() {
	showToast('Scanning for agents...');
	const r = await api('/api/agents/scan', { method: 'POST' });
	if (r.agents) {
		// Update global state with scanned agents
		AGENTS = r.agents;
		SYNC_STATUS = r.sync_status || [];
		INSTALLED_AGENTS = AGENTS.filter(a => a.installed);
		const newCount = r.new_count || 0;
		if (newCount > 0) {
			showToast(`Found ${newCount} new agent(s)!`);
		} else {
			showToast('Scan complete, no new agents');
		}
		renderGlobalWS();
	} else {
		showToast('Scan failed', 'error');
	}
}

function renderGlobalWS() {
	const el = document.getElementById('page-global-ws');
	if (!GWS_SELECTED_AGENT && INSTALLED_AGENTS.length > 0) GWS_SELECTED_AGENT = INSTALLED_AGENTS[0].key;
	// Auto-scan on first visit to this page
	if (!GWS_SCANNED) {
		GWS_SCANNED = true;
		setTimeout(() => scanAgents(), 100);
	}

	el.innerHTML = `<div class="flex h-full gap-3">
    <!-- Agent List -->
    <div class="w-64 glass-panel rounded-2xl p-3 flex flex-col gap-1 overflow-auto flex-shrink-0">
      <div class="flex items-center justify-between px-3 py-2">
        <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Agents</h3>
        <button onclick="scanAgents()" class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors" title="Scan for new agents">
          <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
        </button>
      </div>
      ${INSTALLED_AGENTS.map(a => `
        <div class="sidebar-item ${GWS_SELECTED_AGENT === a.key ? 'active' : ''}" onclick="selectGWSAgent('${esc(a.key)}')">
          <div class="w-2 h-2 rounded-full ${a.skill_count > 0 ? 'bg-green-500' : 'bg-slate-400'}"></div>
          <span class="truncate text-sm flex-1">${esc(a.label)}</span>
          <span class="text-xs text-slate-400 mr-1">${a.skill_count}</span>
          <button onclick="event.stopPropagation();openFolder('${escPath(a.skills_dir)}')" class="p-0.5 rounded hover:bg-slate-200 dark:hover:bg-slate-700" title="${esc(a.skills_dir)}">
            <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
          </button>
        </div>
      `).join('')}
      ${INSTALLED_AGENTS.length === 0 ? '<p class="text-sm text-slate-400 px-3 py-4">No agents detected</p>' : ''}
      <!-- All agents list (including not installed) -->
      ${AGENTS.filter(a => !a.installed).map(a => `
        <div class="sidebar-item opacity-40" title="Not installed">
          <div class="w-2 h-2 rounded-full bg-slate-400"></div>
          <span class="truncate text-sm">${esc(a.label)}</span>
        </div>
      `).join('')}
    </div>
    <!-- Main Content -->
    <div class="flex-1 flex flex-col gap-3 overflow-hidden">
      <!-- Agent Info + Sync Status -->
      <div class="glass-panel rounded-2xl p-4 flex-shrink-0" id="gwsAgentInfo"></div>
      <!-- Skills Section -->
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
                <th class="px-3 py-2 text-left font-semibold text-slate-500 text-xs uppercase">Enabled</th>
                <th class="px-3 py-2 text-left font-semibold text-slate-500 text-xs uppercase">Name</th>
                <th class="px-3 py-2 text-left font-semibold text-slate-500 text-xs uppercase">Library</th>
                <th class="px-3 py-2 text-left font-semibold text-slate-500 text-xs uppercase">Description</th>
              </tr>
            </thead>
            <tbody id="gwsBody">
              <tr><td colspan="5" class="px-4 py-8 text-center text-slate-400">Loading...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>`;

	renderAgentInfo();
	if (GWS_SELECTED_AGENT) loadGWSAgentSkills(GWS_SELECTED_AGENT);
}

function renderAgentInfo() {
	const el = document.getElementById('gwsAgentInfo');
	if (!el) return;
	const agent = INSTALLED_AGENTS.find(a => a.key === GWS_SELECTED_AGENT);
	if (!agent) { el.innerHTML = '<p class="text-sm text-slate-400">Select an agent</p>'; return; }
	const agentSync = SYNC_STATUS.find(s => s.name === GWS_SELECTED_AGENT || s.tool === GWS_SELECTED_AGENT);
	el.innerHTML = `<div class="flex items-start gap-4">
    <div class="flex-1">
      <div class="flex items-center gap-2 mb-1">
        <div class="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse"></div>
        <h3 class="font-bold text-slate-800 dark:text-white">${esc(agent.label)}</h3>
        <span class="text-xs text-slate-400 font-mono">${esc(agent.key)}</span>
      </div>
      <div class="flex items-center gap-1 mb-2">
        <p class="text-xs text-slate-500 font-mono flex-1 truncate" title="${esc(agent.skills_dir)}">${esc(agent.skills_dir)}</p>
        <button onclick="openFolder('${escPath(agent.skills_dir)}')" class="p-1 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors" title="Open folder">
          <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
        </button>
      </div>
      ${agentSync ? `<div class="flex items-center gap-2">
        <div class="flex-1 bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden max-w-[200px]">
          <div class="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500" style="width:${agentSync.total_count ? agentSync.synced_count / agentSync.total_count * 100 : 0}%"></div>
        </div>
        <span class="text-xs font-bold text-slate-500">${agentSync.synced_count}/${agentSync.total_count} synced</span>
        <div class="flex gap-1 ml-2">${(agentSync.active_presets || []).map(p => `<span class="px-2 py-0.5 text-xs rounded-full bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 font-medium">${esc(p)}</span>`).join('')}</div>
      </div>` : ''}
    </div>
  </div>`;
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
		// Get the agent's active_presets from SYNC_STATUS
		const agentSync = SYNC_STATUS.find(a => a.name === agentKey || a.tool === agentKey);
		const activePresets = (agentSync && agentSync.active_presets) || [];

		presetEl.innerHTML = PRESETS.map(p => {
			const isActive = activePresets.includes(p.name);
			const cls = isActive ? 'active' : '';
			return `<span class="preset-pill ${cls}" onclick="togglePresetForAgent('${esc(p.name)}','${esc(agentKey)}')">${esc(p.name)}</span>`;
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
			const checked = GWS_SELECTED.has(s.dir);
			const isCentral = s.source === 'central' || s.in_central;
			const isLink = !!s.is_link;
			// Library badge: Linked (junction/symlink to central) > In Library (copy) > Local (not synced)
			let libraryBadge;
			if (isLink) {
				libraryBadge = `<span class="source-badge source-central inline-flex items-center gap-1" title="Linked to central Library (junction/symlink)"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/></svg>Linked</span>`;
			} else if (isCentral) {
				libraryBadge = `<span class="source-badge source-central" title="Exists in central Library (local copy)">In Library</span>`;
			} else {
				libraryBadge = `<span class="source-badge source-external" title="Only in this agent, not synced to central Library">Local</span>`;
			}
			return `<tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer" onclick="previewGWSSkill('${esc(s.dir)}')">
        <td class="px-3 py-2.5"><input type="checkbox" class="skill-checkbox" ${checked ? 'checked' : ''} onclick="event.stopPropagation();gwsToggleSelect('${esc(s.dir)}',this.checked)"></td>
        <td class="px-3 py-2.5"><span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${s.enabled ? 'bg-green-100 dark:bg-green-900/40 text-green-600' : 'bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400'}">${s.enabled ? 'On' : 'Off'}</span></td>
        <td class="px-3 py-2.5 font-semibold text-slate-800 dark:text-white">${esc(s.name)}</td>
        <td class="px-3 py-2.5">${libraryBadge}</td>
        <td class="px-3 py-2.5 text-slate-500 text-xs truncate max-w-[200px]">${esc((s.description || '').substring(0, 60))}</td>
      </tr>`;
		}).join('');
	}
}

function gwsToggleSelect(dir, checked) {
	if (checked) GWS_SELECTED.add(dir); else GWS_SELECTED.delete(dir);
	renderGlobalWS();
}
function gwsToggleAll(checked) {
	if (checked) GWS_SKILLS.forEach(s => GWS_SELECTED.add(s.dir)); else GWS_SELECTED.clear();
	renderGlobalWS();
}

async function gwsBatchAction(action) {
	const names = [...GWS_SELECTED];
	if (names.length === 0) return;
	const r = await api(`/api/workspace/global/${encodeURIComponent(GWS_SELECTED_AGENT)}/${action}`, {
		method: 'POST', body: JSON.stringify({ skill_names: names })
	});
	if (r.ok) {
		GWS_SELECTED.clear();
		showToast(`${action} done`);
		// Reload data fresh
		const ad = await api('/api/agents');
		SYNC_STATUS = ad.sync_status || [];
		AGENTS = ad.agents || [];
		INSTALLED_AGENTS = AGENTS.filter(a => a.installed);
		renderAgentInfo();
		await loadGWSAgentSkills(GWS_SELECTED_AGENT);
	} else {
		showToast('Failed', 'error');
	}
}

async function previewGWSSkill(dir) {
	const central = SKILLS.find(s => s.dir === dir);
	if (central) { navigate('library'); setTimeout(() => selectSkill(central.dir), 100); return; }
	const gwsSkill = GWS_SKILLS.find(s => s.dir === dir);
	if (gwsSkill) {
		showToast(`External skill: ${dir} (${gwsSkill.path || gwsSkill.folder || 'unknown path'})`);
	}
}

async function togglePresetForAgent(presetName, agentKey) {
	const agentSync = SYNC_STATUS.find(a => a.name === agentKey || a.tool === agentKey);
	const isCurrentlyActive = agentSync && (agentSync.active_presets || []).includes(presetName);
	const action = isCurrentlyActive ? 'deactivate' : 'activate';

	showToast(`${action === 'activate' ? 'Activating' : 'Deactivating'} ${presetName}...`);

	const r = await api(`/api/presets/${encodeURIComponent(presetName)}/${action}`, {
		method: 'POST', body: JSON.stringify({ agent: agentKey })
	});

	if (r.ok) {
		showToast(`${presetName} ${action}d`);
		// Reload data fresh
		const ad = await api('/api/agents');
		SYNC_STATUS = ad.sync_status || [];
		AGENTS = ad.agents || [];
		INSTALLED_AGENTS = AGENTS.filter(a => a.installed);
		// Re-render
		renderAgentInfo();
		await loadGWSAgentSkills(agentKey);
	} else {
		showToast(r.error || 'Failed', 'error');
	}
}

/* ── Add Skills Modal ────────────────────────── */
function addSkillsModal() {
	const available = SKILLS.filter(s => !GWS_SKILLS.find(g => g.dir === s.dir));
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
let PWS_SETTINGS = JSON.parse(localStorage.getItem('pws_settings') || '{}');
let PWS_PATH = PWS_SETTINGS.path || 'D:\\06_Project';
let PWS_DEPTH = PWS_SETTINGS.depth || 3;
let PWS_RESULTS = null;
let PWS_SELECTED_WS = null; // Selected workspace for detailed view
let PWS_SELECTED = new Set(); // Selected skills for batch operations (key: agentDir::skillName)
// Persist workspaces in localStorage
let PWS_WORKSPACES = JSON.parse(localStorage.getItem('pws_workspaces') || '[]');
function savePWSWorkspaces() { localStorage.setItem('pws_workspaces', JSON.stringify(PWS_WORKSPACES)); }

function renderProjectWS() {
	const el = document.getElementById('page-project-ws');
	el.innerHTML = `<div class="flex h-full gap-3">
    <!-- Left: Workspace List -->
    <div class="w-72 glass-panel rounded-2xl flex flex-col flex-shrink-0 overflow-hidden">
      <div class="p-3 border-b border-slate-200/60 dark:border-slate-700/50">
        <div class="flex items-center justify-between mb-2">
          <h3 class="font-bold text-sm text-slate-800 dark:text-white">Workspaces</h3>
          <button onclick="addWorkspaceModal()" class="p-1.5 rounded-lg btn-gradient" title="Add workspace">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
          </button>
        </div>
        <!-- Auto-scan with settings -->
        <div class="flex items-center gap-1">
          <button onclick="autoScanWorkspaces()" class="flex-1 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors flex items-center gap-1.5" title="${esc(PWS_PATH)}">
            <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <span class="truncate">Auto-detect</span>
            <span class="ml-auto text-xs text-slate-400 truncate max-w-[120px]" title="${esc(PWS_PATH)}">${esc(PWS_PATH.split('\\').pop())}</span>
          </button>
          <button onclick="pwsSettingsModal()" class="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300" title="Settings (path: ${esc(PWS_PATH)}, depth: ${PWS_DEPTH})">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.606 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
          </button>
        </div>
      </div>
      <div class="flex-1 overflow-auto p-2">
        ${PWS_WORKSPACES.length === 0 ? '<p class="text-sm text-slate-400 p-3">No workspaces added yet</p>' :
			PWS_WORKSPACES.map((w, i) => {
				const isSelected = PWS_SELECTED_WS === i;
				return `<div class="sidebar-item ${isSelected ? 'active' : ''} mb-1" onclick="selectPWSWorkspace(${i})">
            <svg class="w-4 h-4 text-primary-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
            <div class="flex-1 min-w-0">
              <p class="truncate text-sm font-medium">${esc(w.path.split('\\').pop() || w.path)}</p>
              <p class="truncate text-xs text-slate-400">${w.skill_count ? w.skill_count + ' skills' : 'not scanned'}</p>
            </div>
            <button onclick="event.stopPropagation();openFolder('${escPath(w.path)}')" class="p-0.5 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400 hover:text-primary-500" title="Open folder">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
            </button>
            <button onclick="event.stopPropagation();PWS_WORKSPACES.splice(${i},1);savePWSWorkspaces();if(PWS_SELECTED_WS===${i})PWS_SELECTED_WS=null;renderProjectWS()" class="p-0.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-slate-400 hover:text-red-500">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>`;
			}).join('')}
      </div>
    </div>

    <!-- Right: Workspace Details -->
    <div class="flex-1 glass-panel rounded-2xl flex flex-col overflow-hidden">
      ${PWS_SELECTED_WS !== null && PWS_WORKSPACES[PWS_SELECTED_WS] ? renderPBSDetails(PWS_WORKSPACES[PWS_SELECTED_WS]) : `
      <div class="flex-1 flex items-center justify-center text-slate-400">
        <div class="text-center">
          <svg class="w-16 h-16 mx-auto mb-3 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
          <p class="text-sm">Select a workspace to view details</p>
          <p class="text-xs mt-1">Or click "Auto-detect" to find workspaces</p>
        </div>
      </div>`}
    </div>
  </div>`;
}

function renderPBSDetails(ws) {
	console.log('[PWS Details] renderPBSDetails called, ws:', ws);
	console.log('[PWS Details] ws._scan_result:', ws._scan_result);
	return `<div class="p-4 border-b border-slate-200/60 dark:border-slate-700/50">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-xl bg-primary-100 dark:bg-primary-900/40 flex items-center justify-center">
        <svg class="w-5 h-5 text-primary-600 dark:text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
      </div>
      <div class="flex-1">
        <h3 class="font-bold text-slate-800 dark:text-white">${esc(ws.path.split('\\').pop() || ws.path)}</h3>
        <p class="text-xs text-slate-400 font-mono truncate" title="${esc(ws.path)}">${esc(ws.path)}</p>
      </div>
      <button onclick="scanPWSWorkspace(${PWS_SELECTED_WS})" class="btn-gradient px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
        Scan
      </button>
      <button onclick="openFolder('${escPath(ws.path)}')" class="px-3 py-1.5 rounded-xl text-xs font-semibold bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400">
        Open
      </button>
    </div>
  </div>
  <div class="flex-1 overflow-auto p-4" id="pwsDetailsContent">
    ${ws._scan_result ? renderPWSScanResult(ws._scan_result) : '<p class="text-sm text-slate-400 text-center py-8">Click "Scan" to discover agents and skills in this workspace</p>'}
  </div>`;
}

function renderPWSScanResult(result) {
	console.log('[PWS Render] renderPWSScanResult called, result:', result);
	const workspaces = result.workspaces || [];
	console.log('[PWS Render] workspaces count:', workspaces.length);
	if (workspaces.length === 0) return '<p class="text-sm text-slate-400 text-center py-8">No agents found in this workspace</p>';

	const ws = PWS_WORKSPACES[PWS_SELECTED_WS];
	const projectPath = ws ? ws.path : '';

	return workspaces.map(w => {
		const skills = w.skills || [];
		const agentDir = w.agent_dir;
		const selectedCount = skills.filter(s => PWS_SELECTED.has(`${agentDir}::${s.name}`)).length;
		return `<div class="mb-4 border border-slate-200/60 dark:border-slate-700/50 rounded-xl overflow-hidden">
      <!-- Agent Header -->
      <div class="px-4 py-3 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200/60 dark:border-slate-700/50">
        <div class="flex items-center gap-2 mb-2">
          <span class="px-2 py-0.5 text-xs rounded-full bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-400 font-semibold">${esc(w.label)}</span>
          <span class="text-xs text-slate-400 font-mono">${esc(agentDir)}</span>
          <span class="ml-auto text-xs text-slate-400">${skills.length} skills</span>
        </div>
        <p class="text-xs text-slate-400 font-mono truncate mb-2" title="${esc(w.skills_path)}">${esc(w.skills_path)}</p>
        <!-- Action Bar -->
        <div class="flex flex-wrap gap-1.5">
          <button onclick="pwsAddFromLibraryModal('${esc(agentDir)}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 hover:bg-blue-200">+ Add from Library</button>
          ${selectedCount > 0 ? `
          <button onclick="pwsBatchImport('${esc(agentDir)}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-green-100 dark:bg-green-900/30 text-green-600 hover:bg-green-200" title="Import selected skills into the central Library">+ Add to Library (${selectedCount})</button>
          <button onclick="pwsAddToPresetModal('${esc(agentDir)}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-purple-100 dark:bg-purple-900/30 text-purple-600 hover:bg-purple-200">Add to Preset (${selectedCount})</button>
          <button onclick="pwsToggleSkills('${esc(agentDir)}', true)" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 hover:bg-emerald-200">Enable</button>
          <button onclick="pwsToggleSkills('${esc(agentDir)}', false)" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-600 hover:bg-amber-200">Disable</button>
          <button onclick="pwsRemoveSkills('${esc(agentDir)}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-red-100 dark:bg-red-900/30 text-red-600 hover:bg-red-200">Remove (${selectedCount})</button>
          <button onclick="PWS_SELECTED.clear();renderProjectWS()" class="px-2 py-1 text-xs text-slate-400 hover:text-slate-600">Clear</button>
          ` : ''}
        </div>
      </div>
      <!-- Skills Table -->
      ${skills.length > 0 ? `<table class="w-full text-sm">
        <thead class="bg-slate-100/80 dark:bg-slate-800/80">
          <tr>
            <th class="px-3 py-2 text-left w-8"><input type="checkbox" class="skill-checkbox" onchange="pwsToggleAll('${esc(agentDir)}', this.checked)" ${selectedCount === skills.length && skills.length > 0 ? 'checked' : ''}></th>
            <th class="px-3 py-2 text-left font-semibold text-slate-500 text-xs uppercase w-16">Enabled</th>
            <th class="px-3 py-2 text-left font-semibold text-slate-500 text-xs uppercase">Name</th>
            <th class="px-3 py-2 text-left font-semibold text-slate-500 text-xs uppercase w-28">Library</th>
            <th class="px-3 py-2 text-left font-semibold text-slate-500 text-xs uppercase">Description</th>
            <th class="px-3 py-2 text-right font-semibold text-slate-500 text-xs uppercase w-32">Actions</th>
          </tr>
        </thead>
        <tbody>
          ${skills.map(s => {
			const key = `${agentDir}::${s.name}`;
			const checked = PWS_SELECTED.has(key);
			const isCentral = SKILLS.find(c => c.dir === s.name);
			const isLink = !!s.is_link;
			const skillPath = s.path || '';
			const skillFolder = skillPath.replace(/\\SKILL\.md.*$/i, '').replace(/\.md$/i, '');
			// Library badge: Linked (junction/symlink to central) > In Library (copy) > Local (not synced)
			let libraryBadge;
			if (isLink) {
				libraryBadge = `<span class="source-badge source-central inline-flex items-center gap-1" title="Linked to central Library (junction/symlink)"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/></svg>Linked</span>`;
			} else if (isCentral) {
				libraryBadge = `<span class="source-badge source-central" title="Exists in central Library (local copy)">In Library</span>`;
			} else {
				libraryBadge = `<span class="source-badge source-external" title="Only in this project, not synced to central Library">Local</span>`;
			}
			return `<tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 border-t border-slate-100 dark:border-slate-800">
            <td class="px-3 py-2"><input type="checkbox" class="skill-checkbox" ${checked ? 'checked' : ''} onchange="pwsToggleSelect('${esc(key)}', this.checked)"></td>
            <td class="px-3 py-2"><span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${s.enabled ? 'bg-green-100 dark:bg-green-900/40 text-green-600' : 'bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400'}">${s.enabled ? 'On' : 'Off'}</span></td>
            <td class="px-3 py-2 font-semibold text-slate-800 dark:text-white">${esc(s.display_name || s.name)}</td>
            <td class="px-3 py-2">${libraryBadge}</td>
            <td class="px-3 py-2 text-slate-500 text-xs truncate max-w-[180px]">${esc((s.description || '').substring(0, 50))}</td>
            <td class="px-3 py-2 text-right">
              <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 hover:opacity-100" style="opacity:1">
                ${!isCentral ? `<button onclick="pwsImportSkill('${escPath(projectPath)}', '${esc(agentDir)}', '${esc(s.name)}')" class="p-1 rounded hover:bg-green-100 dark:hover:bg-green-900/30 text-green-600" title="Add to central Library"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg></button>` : `<button disabled class="p-1 rounded text-slate-300 dark:text-slate-600 cursor-not-allowed" title="Already in central Library"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg></button>`}
                <button onclick="pwsAddToPresetModal('${esc(agentDir)}', '${esc(s.name)}')" class="p-1 rounded hover:bg-purple-100 dark:hover:bg-purple-900/30 text-purple-600" title="Add to Preset"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"/></svg></button>
                <button onclick="pwsToggleSkills('${esc(agentDir)}', ${!s.enabled}, '${esc(s.name)}')" class="p-1 rounded hover:bg-amber-100 dark:hover:bg-amber-900/30 text-amber-600" title="${s.enabled ? 'Disable' : 'Enable'}"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/></svg></button>
                <button onclick="pwsRemoveSkills('${esc(agentDir)}', '${esc(s.name)}')" class="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500" title="Remove"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg></button>
                <button onclick="openFolder('${escPath(skillFolder)}')" class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400" title="Open folder"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg></button>
              </div>
            </td>
          </tr>`;
		}).join('')}
        </tbody>
      </table>` : '<p class="text-xs text-slate-400 p-4">No skills found</p>'}
    </div>`;
	}).join('');
}

async function selectPWSWorkspace(index) {
	PWS_SELECTED_WS = index;
	renderProjectWS();
}

async function scanPWSWorkspace(index) {
	console.log('[PWS Scan] scanPWSWorkspace called, index:', index);
	const ws = PWS_WORKSPACES[index];
	if (!ws) {
		console.log('[PWS Scan] ws not found');
		return;
	}
	console.log('[PWS Scan] ws:', ws);
	showToast('Scanning workspace...');
	const depth = ws.depth || 2;
	console.log('[PWS Scan] depth:', depth, 'path:', ws.path);
	const result = await api('/api/workspace/scan', { method: 'POST', body: JSON.stringify({ path: ws.path, max_depth: depth }) });
	console.log('[PWS Scan] API result:', result);
	if (result.error) {
		showToast('Scan failed: ' + result.error, 'error');
		return;
	}
	ws._scan_result = result;
	ws.skill_count = (result.workspaces || []).reduce((sum, w) => sum + (w.skills || []).length, 0);
	console.log('[PWS Scan] skill_count:', ws.skill_count);
	savePWSWorkspaces();
	renderProjectWS();
	showToast(`Scan complete: ${ws.skill_count} skills found`);
}

function pwsSettingsModal() {
	openModal(`<h3 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Project Workspace Settings</h3>
    <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Auto-detect Scan Path</label>
    <input id="pwsSettingsPath" value="${esc(PWS_PATH)}" class="input-modern w-full px-4 py-2.5 rounded-xl text-sm font-mono mb-3">
    <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Auto-detect Depth</label>
    <select id="pwsSettingsDepth" class="input-modern w-full px-3 py-2.5 rounded-xl text-sm mb-4">
      <option value="2" ${PWS_DEPTH == 2 ? 'selected' : ''}>2</option>
      <option value="3" ${PWS_DEPTH == 3 ? 'selected' : ''}>3</option>
      <option value="4" ${PWS_DEPTH == 4 ? 'selected' : ''}>4</option>
      <option value="5" ${PWS_DEPTH == 5 ? 'selected' : ''}>5</option>
    </select>
    <div class="flex justify-end gap-2">
      <button onclick="closeModal()" class="px-4 py-2 text-sm font-semibold rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Cancel</button>
      <button onclick="savePWSSettings()" class="btn-gradient px-4 py-2 text-sm font-bold rounded-xl">Save</button>
    </div>
  `);
}

function savePWSSettings() {
	PWS_PATH = document.getElementById('pwsSettingsPath').value.trim() || 'D:\\06_Project';
	PWS_DEPTH = parseInt(document.getElementById('pwsSettingsDepth').value) || 3;
	localStorage.setItem('pws_settings', JSON.stringify({ path: PWS_PATH, depth: PWS_DEPTH }));
	closeModal();
	renderProjectWS();
	showToast('Settings saved');
}

async function autoScanWorkspaces() {
	showToast('Auto-detecting workspaces...');
	const result = await api('/api/workspace/scan', { method: 'POST', body: JSON.stringify({ path: PWS_PATH, max_depth: PWS_DEPTH }) });
	const workspaces = result.workspaces || [];
	let added = 0;
	for (const w of workspaces) {
		// Check if already associated
		const exists = PWS_WORKSPACES.find(pws => pws.path === w.project_path);
		if (!exists) {
			PWS_WORKSPACES.push({
				path: w.project_path,
				depth: 1,
				skill_count: (w.skills || []).length,
				_scan_result: { workspaces: [w] }
			});
			added++;
		}
	}
	savePWSWorkspaces();
	renderProjectWS();
	showToast(added > 0 ? `Found ${added} new workspace(s)` : 'No new workspaces found');
}

async function importAllUniqueSkills(projectPath) {
	showToast('Importing unique skills...');
	const ws = PWS_WORKSPACES[PWS_SELECTED_WS];
	if (!ws || !ws._scan_result) return;

	let importCount = 0;
	for (const w of ws._scan_result.workspaces || []) {
		for (const s of (w.skills || [])) {
			if (!SKILLS.find(c => c.dir === s.name)) {
				const r = await api('/api/workspace/project/import', {
					method: 'POST', body: JSON.stringify({ path: w.project_path, skill_names: [s.name] })
				});
				if (r.ok) importCount++;
			}
		}
	}
	await refresh();
	showToast(`Imported ${importCount} unique skill(s)`);
}

function addWorkspaceModal() {
	openModal(`<h3 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Add Workspace</h3>
    <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Workspace Path</label>
    <input id="wsPath" placeholder="D:\\06_Project\\my-project" class="input-modern w-full px-4 py-2.5 rounded-xl text-sm font-mono mb-3">
    <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Scan Depth</label>
    <select id="wsDepth" class="input-modern w-full px-3 py-2.5 rounded-xl text-sm mb-4">
      <option value="1">1 (only this directory)</option>
      <option value="2" selected>2</option>
      <option value="3">3</option>
    </select>
    <div class="flex justify-end gap-2">
      <button onclick="closeModal()" class="px-4 py-2 text-sm font-semibold rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Cancel</button>
      <button onclick="doAddWorkspace()" class="btn-gradient px-4 py-2 text-sm font-bold rounded-xl">Add & Scan</button>
    </div>`);
}

async function doAddWorkspace() {
	const wsPath = document.getElementById('wsPath').value.trim();
	const depth = parseInt(document.getElementById('wsDepth').value);
	if (!wsPath) { showToast('Path required', 'error'); return; }
	const wsIndex = PWS_WORKSPACES.length;
	PWS_WORKSPACES.push({ path: wsPath, depth: depth });
	savePWSWorkspaces();
	closeModal();
	PWS_SELECTED_WS = wsIndex;
	renderProjectWS();
	// Auto scan this workspace
	await scanPWSWorkspace(wsIndex);
}

async function importProjectSkill(projectPath, skillName) {
	const r = await api('/api/workspace/project/import', {
		method: 'POST', body: JSON.stringify({ path: projectPath, skill_names: [skillName] })
	});
	if (r.ok) { showToast('Imported'); await refresh(); renderProjectWS(); } else showToast(r.error || 'Failed', 'error');
}

/* ── PWS Selection & Batch Operations ───────── */
function pwsToggleSelect(key, checked) {
	if (checked) PWS_SELECTED.add(key); else PWS_SELECTED.delete(key);
	renderProjectWS();
}

function pwsToggleAll(agentDir, checked) {
	const ws = PWS_WORKSPACES[PWS_SELECTED_WS];
	if (!ws || !ws._scan_result) return;
	const w = ws._scan_result.workspaces.find(x => x.agent_dir === agentDir);
	if (!w) return;
	(w.skills || []).forEach(s => {
		const key = `${agentDir}::${s.name}`;
		if (checked) PWS_SELECTED.add(key); else PWS_SELECTED.delete(key);
	});
	renderProjectWS();
}

function getPwsSelectedSkills(agentDir) {
	return [...PWS_SELECTED]
		.filter(k => k.startsWith(agentDir + '::'))
		.map(k => k.split('::')[1]);
}

async function pwsRescan() {
	PWS_SELECTED.clear();
	if (PWS_SELECTED_WS !== null) await scanPWSWorkspace(PWS_SELECTED_WS);
}

/* ── PWS Single/Batch Import ─────────────────── */
async function pwsImportSkill(projectPath, agentDir, skillName) {
	showToast('Importing...');
	const r = await api('/api/workspace/project/import', {
		method: 'POST', body: JSON.stringify({ path: projectPath, skill_names: [skillName] })
	});
	if (r.ok) {
		const res = (r.results || [])[0];
		if (res && res.ok) {
			showToast(`Imported '${skillName}' to Library`);
			await refresh();
			await pwsRescan();
		} else {
			showToast(res?.error || 'Import failed', 'error');
		}
	} else {
		showToast(r.error || 'Import failed', 'error');
	}
}

async function pwsBatchImport(agentDir) {
	const names = getPwsSelectedSkills(agentDir);
	if (names.length === 0) return;
	const ws = PWS_WORKSPACES[PWS_SELECTED_WS];
	if (!ws) return;
	showToast(`Importing ${names.length} skill(s)...`);
	const r = await api('/api/workspace/project/import', {
		method: 'POST', body: JSON.stringify({ path: ws.path, skill_names: names })
	});
	if (r.ok) {
		const okCount = (r.results || []).filter(x => x.ok).length;
		showToast(`Imported ${okCount} skill(s) to Library`);
		await refresh();
		await pwsRescan();
	} else {
		showToast(r.error || 'Import failed', 'error');
	}
}

/* ── PWS Remove ──────────────────────────────── */
async function pwsRemoveSkills(agentDir, singleSkill) {
	const names = singleSkill ? [singleSkill] : getPwsSelectedSkills(agentDir);
	if (names.length === 0) return;
	const ws = PWS_WORKSPACES[PWS_SELECTED_WS];
	if (!ws) return;
	if (!confirm(`Remove ${names.length} skill(s) from project?\n\n${names.join(', ')}`)) return;
	showToast('Removing...');
	const r = await api('/api/workspace/project/remove', {
		method: 'POST', body: JSON.stringify({ path: ws.path, agent_dir: agentDir, skill_names: names })
	});
	if (r.ok) {
		const okCount = (r.results || []).filter(x => x.ok).length;
		showToast(`Removed ${okCount} skill(s)`);
		await pwsRescan();
	} else {
		showToast(r.error || 'Remove failed', 'error');
	}
}

/* ── PWS Toggle Enable/Disable ───────────────── */
async function pwsToggleSkills(agentDir, enabled, singleSkill) {
	const names = singleSkill ? [singleSkill] : getPwsSelectedSkills(agentDir);
	if (names.length === 0) return;
	const ws = PWS_WORKSPACES[PWS_SELECTED_WS];
	if (!ws) return;
	showToast(enabled ? 'Enabling...' : 'Disabling...');
	const r = await api('/api/workspace/project/toggle', {
		method: 'POST', body: JSON.stringify({ path: ws.path, agent_dir: agentDir, skill_names: names, enabled: enabled })
	});
	if (r.ok) {
		const okCount = (r.results || []).filter(x => x.ok).length;
		showToast(`${enabled ? 'Enabled' : 'Disabled'} ${okCount} skill(s)`);
		await pwsRescan();
	} else {
		showToast(r.error || 'Toggle failed', 'error');
	}
}

/* ── PWS Add from Library ────────────────────── */
function pwsAddFromLibraryModal(agentDir) {
	const ws = PWS_WORKSPACES[PWS_SELECTED_WS];
	if (!ws || !ws._scan_result) return;
	const w = ws._scan_result.workspaces.find(x => x.agent_dir === agentDir);
	const existingNames = (w?.skills || []).map(s => s.name);
	const available = SKILLS.filter(s => !existingNames.includes(s.dir));
	openModal(`<h3 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Add Skills from Library</h3>
    <p class="text-xs text-slate-400 mb-3">Target: ${esc(agentDir)}/skills in ${esc(ws.path.split('\\').pop())}</p>
    <input id="pwsLibSearch" placeholder="Search..." oninput="filterPwsLibSkills()" class="input-modern w-full px-4 py-2.5 rounded-xl text-sm mb-3">
    <div id="pwsLibList" class="max-h-[40vh] overflow-auto space-y-1 mb-4">
      ${available.map(s => `<label class="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer">
        <input type="checkbox" class="skill-checkbox pws-lib-cb" value="${esc(s.dir)}">
        <span class="font-semibold text-sm text-slate-800 dark:text-white">${esc(s.name)}</span>
        <span class="text-xs text-slate-400 truncate">${esc((s.description || '').substring(0, 50))}</span>
      </label>`).join('')}
      ${available.length === 0 ? '<p class="text-sm text-slate-400 py-4 text-center">All library skills already in this project</p>' : ''}
    </div>
    <div class="flex justify-end gap-2">
      <button onclick="closeModal()" class="px-4 py-2 text-sm font-semibold rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Cancel</button>
      <button onclick="pwsDoAddFromLibrary('${esc(agentDir)}')" class="btn-gradient px-4 py-2 text-sm font-bold rounded-xl">Add Selected</button>
    </div>`);
}

function filterPwsLibSkills() {
	const q = document.getElementById('pwsLibSearch').value.toLowerCase();
	document.querySelectorAll('.pws-lib-cb').forEach(cb => {
		cb.closest('label').style.display = cb.value.toLowerCase().includes(q) ? '' : 'none';
	});
}

async function pwsDoAddFromLibrary(agentDir) {
	const names = [...document.querySelectorAll('.pws-lib-cb:checked')].map(cb => cb.value);
	if (names.length === 0) { closeModal(); return; }
	const ws = PWS_WORKSPACES[PWS_SELECTED_WS];
	if (!ws) return;
	closeModal();
	showToast(`Adding ${names.length} skill(s)...`);
	const r = await api('/api/workspace/project/add', {
		method: 'POST', body: JSON.stringify({ path: ws.path, agent_dir: agentDir, skill_names: names })
	});
	if (r.ok) {
		const okCount = (r.results || []).filter(x => x.ok).length;
		const linked = (r.results || []).filter(x => x.linked).length;
		let msg = `Added ${okCount} skill(s) to project`;
		if (linked > 0) msg += ` (${linked} as ${r.mode} links)`;
		showToast(msg);
		await pwsRescan();
	} else {
		showToast(r.error || 'Add failed', 'error');
	}
}

/* ── PWS Add to Preset ───────────────────────── */
function pwsAddToPresetModal(agentDir, singleSkill) {
	const ws = PWS_WORKSPACES[PWS_SELECTED_WS];
	if (!ws) return;
	const selectedSkills = singleSkill ? [singleSkill] : getPwsSelectedSkills(agentDir);
	if (selectedSkills.length === 0 && !singleSkill) {
		showToast('No skills selected', 'error');
		return;
	}
	// Store context for the action
	window._pwsPresetContext = { agentDir, skills: selectedSkills };
	openModal(`<h3 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Add to Preset</h3>
    <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Select Preset</label>
    <select id="pwsPresetSelect" class="input-modern w-full px-3 py-2.5 rounded-xl text-sm mb-4">
      ${PRESETS.map(p => `<option value="${esc(p.name)}">${esc(p.name)}${p.description ? ' - ' + esc(p.description.substring(0, 30)) : ''}</option>`).join('')}
    </select>
    <label class="block text-sm font-semibold text-slate-600 dark:text-slate-400 mb-1">Skills to Add</label>
    <div class="max-h-[30vh] overflow-auto space-y-1 mb-4 bg-slate-50 dark:bg-slate-900/30 rounded-xl p-3">
      ${selectedSkills.map(s => `<div class="flex items-center gap-2 text-sm">
        <span class="w-2 h-2 rounded-full bg-purple-500"></span>
        <span class="text-slate-700 dark:text-slate-300">${esc(s)}</span>
      </div>`).join('')}
    </div>
    <p class="text-xs text-slate-400 mb-4">Skills will be imported to the central Library and added to the preset. In symlink/junction mode, project files will be replaced with links.</p>
    <div class="flex justify-end gap-2">
      <button onclick="closeModal()" class="px-4 py-2 text-sm font-semibold rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Cancel</button>
      <button onclick="pwsDoAddToPreset()" class="btn-gradient px-4 py-2 text-sm font-bold rounded-xl">Add to Preset</button>
    </div>`);
}

async function pwsDoAddToPreset() {
	const ctx = window._pwsPresetContext;
	if (!ctx) return;
	const presetName = document.getElementById('pwsPresetSelect').value;
	const ws = PWS_WORKSPACES[PWS_SELECTED_WS];
	if (!ws || !presetName) return;
	closeModal();
	showToast(`Adding ${ctx.skills.length} skill(s) to preset '${presetName}'...`);
	const r = await api('/api/workspace/project/add-to-preset', {
		method: 'POST',
		body: JSON.stringify({ path: ws.path, agent_dir: ctx.agentDir, skill_names: ctx.skills, preset: presetName })
	});
	if (r.ok) {
		const results = r.results || [];
		const okCount = results.filter(x => x.ok).length;
		const linkedCount = results.filter(x => x.replaced_with_link).length;
		let msg = `${okCount} skill(s) added to preset '${presetName}'`;
		if (linkedCount > 0) {
			msg += `. Project files replaced with ${r.mode} links to central Library.`;
		}
		showToast(msg, 'success', 5000);
		if (r.synced_agents && r.synced_agents.length > 0) {
			console.log('[PWS Preset] Synced agents:', r.synced_agents);
		}
		await refresh();
		await pwsRescan();
	} else {
		showToast(r.error || 'Add to preset failed', 'error');
	}
	window._pwsPresetContext = null;
}
