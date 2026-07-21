/* ── Global State ─────────────────────────────── */
let SKILLS = [], AGENTS = [], PRESETS = [], SYNC_STATUS = [], TAGS = [];
let SEL_SKILL = null, CURRENT_PAGE = 'dashboard';
let INSTALLED_AGENTS = []; // agents with installed=true from detect_agents
let SKILLS_DIR = ''; // root skills directory path
let SYNC_MODE = 'junction'; // current sync mode: symlink | junction | copy

/* ── API Helper ──────────────────────────────── */
async function api(path, opts = {}) {
  try {
    const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...opts });
    return await r.json();
  } catch (e) {
    console.error('API error:', path, e);
    return { error: e.message };
  }
}

function esc(s) {
  return (s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
/* Escape for use inside onclick="...('PATH')" attributes - doubles backslashes */
function escPath(s) {
  return esc((s || '').replace(/\\/g, '\\\\'));
}

/* ── Theme ───────────────────────────────────── */
function updateThemeIcons() {
  const d = document.documentElement.classList.contains('dark');
  document.getElementById('theme-icon-dark').classList.toggle('hidden', d);
  document.getElementById('theme-icon-light').classList.toggle('hidden', !d);
}
function toggleTheme() {
  if (document.documentElement.classList.contains('dark')) {
    document.documentElement.classList.remove('dark'); localStorage.theme = 'light';
  } else {
    document.documentElement.classList.add('dark'); localStorage.theme = 'dark';
  }
  updateThemeIcons();
}
updateThemeIcons();

/* ── Toast ───────────────────────────────────── */
function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.className = 'fixed bottom-6 right-6 px-5 py-3 rounded-xl shadow-2xl transition-all duration-300 z-50 flex items-center gap-2 backdrop-blur-md font-semibold text-sm border';
  if (type === 'success') {
    t.classList.add('bg-green-50/90', 'dark:bg-green-900/90', 'text-green-700', 'dark:text-green-100', 'border-green-200', 'dark:border-green-800');
  } else {
    t.classList.add('bg-red-50/90', 'dark:bg-red-900/90', 'text-red-700', 'dark:text-red-100', 'border-red-200', 'dark:border-red-800');
  }
  const icon = type === 'success' ? 'M5 13l4 4L19 7' : 'M6 18L18 6M6 6l12 12';
  t.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${icon}"/></svg>${esc(msg)}`;
  setTimeout(() => { t.classList.add('translate-y-20', 'opacity-0', 'hidden'); }, 3000);
}

/* ── Modal ───────────────────────────────────── */
function openModal(html) {
  document.getElementById('modal').innerHTML = html;
  document.getElementById('modalBg').classList.remove('hidden');
}
function closeModal() {
  document.getElementById('modalBg').classList.add('hidden');
}
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('modalBg').onclick = e => { if (e.target.id === 'modalBg') closeModal(); };
});

/* ── Navigation ──────────────────────────────── */
const PAGE_TITLES = {
  'dashboard': 'Dashboard', 'library': 'Library', 'global-ws': 'Global Workspace',
  'project-ws': 'Project Workspace', 'presets': 'Presets', 'backup': 'Backup'
};
const RENDERERS = {
  'dashboard': () => renderDashboard(), 'library': () => renderLibrary(),
  'global-ws': () => renderGlobalWS(), 'project-ws': () => renderProjectWS(),
  'presets': () => renderPresets(), 'backup': () => { renderBackup(); checkBackupStatus(); }
};

function navigate(page) {
  CURRENT_PAGE = page;
  document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
  const el = document.getElementById('page-' + page);
  if (el) el.classList.remove('hidden');
  document.querySelectorAll('.sidebar-item').forEach(s => {
    s.classList.toggle('active', s.dataset.page === page);
  });
  document.getElementById('pageTitle').textContent = PAGE_TITLES[page] || page;
  if (RENDERERS[page]) RENDERERS[page]();
}

/* ── Data Refresh ────────────────────────────── */
async function refresh() {
  const [sd, ad, pd, td, settings] = await Promise.all([
    api('/api/skills'), api('/api/agents'), api('/api/presets'), api('/api/tags'), api('/api/settings')
  ]);
  SKILLS = sd.skills || [];
  SKILLS_DIR = sd.skills_dir || '';
  AGENTS = ad.agents || [];
  SYNC_STATUS = ad.sync_status || [];
  PRESETS = pd.presets || [];
  TAGS = td.tags || [];
  SYNC_MODE = settings.default_mode || 'junction';
  INSTALLED_AGENTS = AGENTS.filter(a => a.installed);
  // Sync the dropdown value
  const modeSelect = document.getElementById('syncModeSelect');
  if (modeSelect) modeSelect.value = SYNC_MODE;
  // Re-render current page
  if (RENDERERS[CURRENT_PAGE]) RENDERERS[CURRENT_PAGE]();
}

/* ── Sync All ────────────────────────────────── */
async function syncAll() {
  showToast('Syncing all...');
  const r = await api('/api/sync', { method: 'POST' });
  showToast(r.ok ? 'Sync complete!' : 'Sync failed', r.ok ? 'success' : 'error');
  await refresh();
}

/* ── Agent Badge Helper ──────────────────────── */
function agentBadgeHTML(skillDir, size = 'sm') {
  return INSTALLED_AGENTS.map(a => {
    const ok = a.synced && a.synced.includes(skillDir);
    const cls = ok ? 'synced' : 'unsynced';
    const initial = a.label.charAt(0);
    const title = `${a.label}: ${ok ? 'synced' : 'not synced'}`;
    return `<span class="agent-badge ${cls}" title="${esc(title)}" onclick="event.stopPropagation();toggleAgentSkill('${esc(skillDir)}','${esc(a.key)}',${ok})">${initial}</span>`;
  }).join('');
}

async function toggleAgentSkill(skillName, agentKey, isSynced) {
  const action = isSynced ? 'remove' : 'install';
  const r = await api(`/api/skills/${encodeURIComponent(skillName)}/toggle-agent`, {
    method: 'POST', body: JSON.stringify({ agent_key: agentKey, action })
  });
  if (r.ok) { showToast(`${action === 'install' ? 'Installed' : 'Removed'} for ${agentKey}`); await refresh(); }
  else showToast(r.error || 'Failed', 'error');
}

/* ── Open Folder Helper ──────────────────────── */
async function openFolder(path) {
  const r = await api('/api/open-folder', { method: 'POST', body: JSON.stringify({ path }) });
  if (!r.ok) showToast('Cannot open folder', 'error');
}

/* ── Init is in index.html after all scripts loaded ── */
