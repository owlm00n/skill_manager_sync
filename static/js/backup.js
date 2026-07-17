/* ── Backup Page ─────────────────────────────── */
function renderBackup() {
  const el = document.getElementById('page-backup');
  el.innerHTML = `<div class="glass-panel rounded-2xl p-6 animate-fade-in-up">
    <h2 class="text-lg font-bold text-slate-800 dark:text-white mb-6">Backup & Sync</h2>

    <!-- Status -->
    <div class="bg-gradient-to-br from-blue-500/10 to-purple-500/10 dark:from-blue-500/20 dark:to-purple-500/20 rounded-2xl p-5 border border-blue-200/30 dark:border-blue-800/30 mb-6">
      <div class="flex items-center gap-3 mb-2">
        <svg class="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg>
        <h3 class="font-bold text-slate-800 dark:text-white">Git Repository Backup</h3>
      </div>
      <p class="text-sm text-slate-500 mb-4">Connect a Git remote to backup your skills library and sync across devices.</p>
      <div id="backupStatus" class="text-sm text-slate-600 dark:text-slate-400">
        <span class="text-amber-500 font-medium">Not configured</span> — Set up a remote repository below.
      </div>
    </div>

    <!-- Configure -->
    <div class="bg-white/50 dark:bg-slate-800/50 rounded-xl p-5 border border-slate-200/50 dark:border-slate-700/50 mb-6">
      <h3 class="font-bold text-sm text-slate-800 dark:text-white mb-3">Remote Configuration</h3>
      <div class="space-y-3">
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">Git Remote URL</label>
          <input id="backupRemoteUrl" placeholder="https://github.com/user/skills-backup.git" class="input-modern w-full px-4 py-2.5 rounded-xl text-sm font-mono">
        </div>
        <div class="flex gap-2">
          <button onclick="configureBackup()" class="btn-gradient px-4 py-2 rounded-xl text-sm font-bold">Save Config</button>
          <button onclick="checkBackupStatus()" class="px-4 py-2 rounded-xl text-sm font-semibold bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">Check Status</button>
        </div>
      </div>
    </div>

    <!-- Manual Backup -->
    <div class="bg-white/50 dark:bg-slate-800/50 rounded-xl p-5 border border-slate-200/50 dark:border-slate-700/50 mb-6">
      <h3 class="font-bold text-sm text-slate-800 dark:text-white mb-3">Manual Backup</h3>
      <p class="text-xs text-slate-500 mb-3">Commit and push current skills to the remote repository.</p>
      <div class="flex gap-2">
        <button onclick="doBackupNow()" class="btn-gradient px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-1.5">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg>
          Back Up Now
        </button>
        <button onclick="doGitPull()" class="px-4 py-2 rounded-xl text-sm font-semibold bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 hover:bg-green-200 flex items-center gap-1.5">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
          Pull from Remote
        </button>
      </div>
    </div>

    <!-- Git Log -->
    <div class="bg-white/50 dark:bg-slate-800/50 rounded-xl p-5 border border-slate-200/50 dark:border-slate-700/50">
      <h3 class="font-bold text-sm text-slate-800 dark:text-white mb-3">Recent Git History</h3>
      <div id="gitLog" class="text-sm text-slate-500">
        <button onclick="loadGitLog()" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200">Load History</button>
      </div>
    </div>
  </div>`;
}

async function configureBackup() {
  const url = document.getElementById('backupRemoteUrl').value.trim();
  if (!url) { showToast('Enter a URL', 'error'); return; }
  const r = await api('/api/backup/configure', { method: 'POST', body: JSON.stringify({ remote_url: url }) });
  if (r.ok) { showToast('Configured'); checkBackupStatus(); } else showToast(r.error || 'Failed', 'error');
}

async function checkBackupStatus() {
  const r = await api('/api/backup/status');
  const el = document.getElementById('backupStatus');
  if (r.remote) {
    el.innerHTML = `<span class="text-green-500 font-medium">Connected</span> — ${esc(r.remote)}<br><span class="text-xs text-slate-400">Last commit: ${esc(r.last_commit || 'unknown')}</span>`;
    document.getElementById('backupRemoteUrl').value = r.remote;
  } else {
    el.innerHTML = '<span class="text-amber-500 font-medium">Not configured</span> — Set up a remote repository below.';
  }
}

async function doBackupNow() {
  showToast('Backing up...');
  const r = await api('/api/backup/now', { method: 'POST' });
  if (r.ok) { showToast('Backup complete'); } else showToast(r.error || 'Failed', 'error');
}

async function doGitPull() {
  showToast('Pulling...');
  const r = await api('/api/backup/pull', { method: 'POST' });
  if (r.ok) { showToast('Pull complete'); await refresh(); } else showToast(r.error || 'Failed', 'error');
}

async function loadGitLog() {
  const el = document.getElementById('gitLog');
  el.innerHTML = '<p class="text-slate-400">Loading...</p>';
  const r = await api('/api/backup/history');
  if (r.commits && r.commits.length > 0) {
    el.innerHTML = r.commits.map(c => `
      <div class="flex items-center gap-3 py-2 border-b border-slate-200/50 dark:border-slate-700/30">
        <span class="text-xs font-mono text-slate-400 w-20">${esc(c.date || '')}</span>
        <span class="text-sm text-slate-700 dark:text-slate-300">${esc(c.message || '')}</span>
        <span class="ml-auto text-xs font-mono text-slate-400">${esc(c.hash || '').substring(0, 7)}</span>
      </div>
    `).join('');
  } else {
    el.innerHTML = '<p class="text-slate-400">No commits found</p>';
  }
}
