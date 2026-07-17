/* ── Agents Page ─────────────────────────────── */
function renderAgents() {
  const el = document.getElementById('page-agents');
  el.innerHTML = `<div class="glass-panel rounded-2xl p-6 animate-fade-in-up">
    <h2 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Installed Agents (${AGENTS.length})</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
      ${AGENTS.map(a => `
      <div class="bg-white/50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200/50 dark:border-slate-700/50 ${a.installed ? '' : 'opacity-40'}">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-2 h-2 rounded-full ${a.installed ? 'bg-green-500 animate-pulse' : 'bg-slate-400'}"></div>
          <h3 class="font-bold text-sm text-slate-800 dark:text-white">${esc(a.label)}</h3>
        </div>
        <div class="flex items-center gap-1 mb-2">
          <p class="text-xs text-slate-500 font-mono flex-1 truncate" title="${esc(a.skills_dir)}">${esc(a.skills_dir)}</p>
          <button onclick="openFolder('${esc(a.skills_dir)}')" class="p-1 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors" title="Open folder">
            <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
          </button>
        </div>
        <div class="text-sm">
          <span class="font-bold text-green-600 dark:text-green-400">${a.skill_count}</span>
          <span class="text-slate-500"> skills</span>
        </div>
        ${a.installed ? `<button onclick="navigate('global-ws');setTimeout(()=>selectGWSAgent('${esc(a.key)}'),100)" class="mt-2 px-3 py-1 text-xs font-semibold rounded-lg bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 hover:bg-primary-200 transition-colors">Open Workspace</button>` : ''}
      </div>`).join('')}
    </div>

    <!-- Sync Configuration -->
    <h2 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Sync Configuration</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
      ${SYNC_STATUS.map(a => `
      <div class="bg-white/50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200/50 dark:border-slate-700/50">
        <h3 class="font-bold text-sm text-slate-800 dark:text-white mb-1">${esc(a.name)}</h3>
        <p class="text-xs text-slate-500 font-mono mb-2">${esc(a.tool)} · ${esc(a.path)}</p>
        <div class="flex items-center gap-2">
          <div class="flex-1 bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden">
            <div class="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500" style="width:${a.total_count ? a.synced_count / a.total_count * 100 : 0}%"></div>
          </div>
          <span class="text-xs font-bold text-slate-500">${a.synced_count}/${a.total_count}</span>
        </div>
        <div class="flex flex-wrap gap-1 mt-2">
          ${(a.active_presets || []).map(p => `<span class="px-2 py-0.5 text-xs rounded-full bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 font-medium">${esc(p)}</span>`).join('')}
        </div>
      </div>`).join('')}
    </div>

    <!-- Scan Projects -->
    <h2 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Scan Projects</h2>
    <div class="flex flex-wrap gap-3 items-end mb-4">
      <div class="flex-1 min-w-[200px]">
        <label class="block text-xs font-semibold text-slate-500 mb-1">Path</label>
        <input id="scanPath" value="D:\\06_Project" class="input-modern w-full px-4 py-2.5 rounded-xl text-sm font-mono">
      </div>
      <div class="w-28">
        <label class="block text-xs font-semibold text-slate-500 mb-1">Depth</label>
        <select id="scanDepth" class="input-modern w-full px-3 py-2.5 rounded-xl text-sm">
          <option value="2">2</option>
          <option value="3" selected>3</option>
          <option value="4">4</option>
        </select>
      </div>
      <button onclick="doScan()" class="btn-gradient px-5 py-2.5 rounded-xl text-sm font-bold">Scan</button>
      <button onclick="doScanImport()" class="btn-success px-5 py-2.5 rounded-xl text-sm font-bold">Scan & Import</button>
    </div>
    <div id="scanResults" class="hidden bg-slate-100/80 dark:bg-black/40 rounded-xl p-4">
      <pre id="scanOutput" class="text-xs font-mono text-slate-600 dark:text-slate-400 whitespace-pre-wrap"></pre>
    </div>
  </div>`;
}

async function doScan() {
  const path = document.getElementById('scanPath').value;
  const depth = document.getElementById('scanDepth').value;
  document.getElementById('scanResults').classList.remove('hidden');
  document.getElementById('scanOutput').textContent = 'Scanning...';
  const r = await api('/api/scan', { method: 'POST', body: JSON.stringify({ path, max_depth: parseInt(depth) }) });
  document.getElementById('scanOutput').textContent = JSON.stringify(r, null, 2);
}

async function doScanImport() {
  const path = document.getElementById('scanPath').value;
  const depth = document.getElementById('scanDepth').value;
  document.getElementById('scanResults').classList.remove('hidden');
  document.getElementById('scanOutput').textContent = 'Scanning and importing...';
  const r = await api('/api/scan/import', { method: 'POST', body: JSON.stringify({ path, max_depth: parseInt(depth) }) });
  document.getElementById('scanOutput').textContent = JSON.stringify(r, null, 2);
  await refresh();
}
