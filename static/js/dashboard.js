/* ── Dashboard ───────────────────────────────── */
function renderDashboard() {
  const el = document.getElementById('page-dashboard');
  const total = SKILLS.length, enabled = SKILLS.filter(s => s.enabled).length;
  const trashCount = SKILLS.length; // placeholder

  el.innerHTML = `<div class="glass-panel rounded-2xl p-6 animate-fade-in-up">
    <!-- Stats Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div class="bg-gradient-to-br from-blue-500/10 to-purple-500/10 dark:from-blue-500/20 dark:to-purple-500/20 rounded-2xl p-5 border border-blue-200/30 dark:border-blue-800/30">
        <div class="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider mb-1">Total Skills</div>
        <div class="text-3xl font-bold text-slate-800 dark:text-white">${total}</div>
        <div class="text-xs text-slate-500 mt-1">${enabled} enabled</div>
      </div>
      <div class="bg-gradient-to-br from-green-500/10 to-emerald-500/10 dark:from-green-500/20 dark:to-emerald-500/20 rounded-2xl p-5 border border-green-200/30 dark:border-green-800/30">
        <div class="text-xs font-semibold text-green-600 dark:text-green-400 uppercase tracking-wider mb-1">Agents</div>
        <div class="text-3xl font-bold text-slate-800 dark:text-white">${AGENTS.length}</div>
        <div class="text-xs text-slate-500 mt-1">${INSTALLED_AGENTS.length} installed</div>
      </div>
      <div class="bg-gradient-to-br from-purple-500/10 to-pink-500/10 dark:from-purple-500/20 dark:to-pink-500/20 rounded-2xl p-5 border border-purple-200/30 dark:border-purple-800/30">
        <div class="text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-wider mb-1">Presets</div>
        <div class="text-3xl font-bold text-slate-800 dark:text-white">${PRESETS.length}</div>
      </div>
      <div class="bg-gradient-to-br from-amber-500/10 to-orange-500/10 dark:from-amber-500/20 dark:to-orange-500/20 rounded-2xl p-5 border border-amber-200/30 dark:border-amber-800/30">
        <div class="text-xs font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider mb-1">Tags</div>
        <div class="text-3xl font-bold text-slate-800 dark:text-white">${TAGS.length}</div>
        <div class="text-xs text-slate-500 mt-1">${SKILLS.filter(s => !s.tags || s.tags.length === 0).length} untagged</div>
      </div>
    </div>

    <!-- Agent Sync Status -->
    <h2 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Agent Sync Status</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
      ${SYNC_STATUS.map(a => `
      <div class="bg-white/50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200/50 dark:border-slate-700/50">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-2 h-2 rounded-full ${a.synced_count === a.total_count ? 'bg-green-500' : 'bg-amber-500'} animate-pulse"></div>
          <h3 class="font-bold text-sm text-slate-800 dark:text-white">${esc(a.name)}</h3>
          <span class="ml-auto text-xs font-mono text-slate-400">${a.synced_count}/${a.total_count}</span>
        </div>
        <p class="text-xs text-slate-500 mb-3 font-mono truncate">${esc(a.path)}</p>
        <div class="flex items-center gap-2 mb-2">
          <div class="flex-1 bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
            <div class="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500" style="width:${a.total_count ? a.synced_count / a.total_count * 100 : 0}%"></div>
          </div>
        </div>
        <div class="flex flex-wrap gap-1">${(a.active_presets || []).map(p => `<span class="px-2 py-0.5 text-xs rounded-full bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 font-medium">${esc(p)}</span>`).join('')}</div>
      </div>`).join('')}
    </div>

    <!-- Recent Skills -->
    <h2 class="text-lg font-bold text-slate-800 dark:text-white mb-4">Recent Skills</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      ${SKILLS.slice(-6).reverse().map(s => `
      <div class="bg-white/50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200/50 dark:border-slate-700/50 cursor-pointer hover:border-primary-300 dark:hover:border-primary-700 transition-colors" onclick="navigate('library');setTimeout(()=>selectSkill('${esc(s.dir)}'),100)">
        <div class="flex items-center gap-2 mb-1">
          <span class="w-2 h-2 rounded-full ${s.enabled ? 'bg-green-500' : 'bg-red-400'}"></span>
          <h3 class="font-bold text-sm text-slate-800 dark:text-white truncate">${esc(s.name)}</h3>
        </div>
        <p class="text-xs text-slate-500 truncate">${esc((s.description || '').substring(0, 80))}</p>
        <div class="flex gap-1 mt-2 flex-wrap">${(s.tags || []).map(t => `<span class="tag-chip">${esc(t)}</span>`).join('')}</div>
      </div>`).join('')}
    </div>
  </div>`;
}
