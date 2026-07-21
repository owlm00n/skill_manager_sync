# Global Workspace Preset & Remove Bug Report

## 问题概述

Global Workspace 页面有两个功能不正常工作：
1. **Preset 操作不生效**：点击 preset pill 后，UI 状态不更新（pill 不高亮），skills 列表不变化
2. **Remove 删不掉某些 skill**：全选后 remove，会剩下个别 skill（如 `pd_auth_analyse`）删不掉

## 已验证：后端 API 全部正常

通过 Python requests 直接调用 API 验证，后端逻辑完全正确：

```python
# 1. 激活 preset → 成功
POST /api/presets/debug-toolkit/activate  body: {"agent": "claude_code"}
→ {"ok": True, "agent_config": "claude_code_global"}
→ config.yaml 中 active_presets 正确更新为 ["debug-toolkit"]
→ sync.ps1 正确执行，只同步 bug-core（debug-toolkit 唯一定义的 skill）

# 2. 去激活 preset → 成功
POST /api/presets/debug-toolkit/deactivate  body: {"agent": "claude_code"}
→ {"ok": True}
→ active_presets 恢复为 []
→ sync.ps1 同步全部 26 个 skills

# 3. Remove junction → 成功
POST /api/workspace/global/claude_code/remove  body: {"skill_names": ["bug-core"]}
→ {"ok": True, "results": [{"name": "bug-core", "ok": True}]}
→ junction 正确删除
```

## 问题定位：前端状态同步

**核心问题**：`togglePresetForAgent()` 操作成功后，前端重新加载数据时 `SYNC_STATUS` 没有正确更新。

用户 Console 输出显示：
```
[Preset] after refresh, SYNC_STATUS: {
  name: 'claude_code_global',
  tool: 'claude_code',
  active_presets: Array(0),  // ← 应该是 Array(1) ["debug-toolkit"]
  skills: Array(1),
  …
}
```

但后端 `/api/agents` 返回的数据中 `active_presets` 是正确的 `["debug-toolkit"]`。

## 数据流分析

```
用户点击 preset pill
  → togglePresetForAgent(presetName, agentKey)
    → agentKey = GWS_SELECTED_AGENT (值如 "claude_code")
    → SYNC_STATUS.find(a => a.name === agentKey || a.tool === agentKey)
      注意：SYNC_STATUS 中 name="claude_code_global", tool="claude_code"
    → POST /api/presets/{presetName}/activate  body: {agent: "claude_code"}
      → 后端正确更新 config.yaml 并运行 sync.ps1
    → await refresh() 或 直接 api('/api/agents')
      → SYNC_STATUS = ad.sync_status || []
      → 此时 SYNC_STATUS 中 active_presets 应为 ["debug-toolkit"]
    → loadGWSAgentSkills(agentKey)
      → 读取 SYNC_STATUS 渲染 preset pills
      → 实际读到 active_presets = []  ← 问题所在
```

## 关键文件与代码

### 1. `static/js/workspace.js` — 前端核心逻辑

**`togglePresetForAgent()`** (约 L214):
```javascript
async function togglePresetForAgent(presetName, agentKey) {
  const agentSync = SYNC_STATUS.find(a => a.name === agentKey || a.tool === agentKey);
  const isCurrentlyActive = agentSync && (agentSync.active_presets || []).includes(presetName);
  const action = isCurrentlyActive ? 'deactivate' : 'activate';
  const r = await api(`/api/presets/${encodeURIComponent(presetName)}/${action}`, {
    method: 'POST', body: JSON.stringify({ agent: agentKey })
  });
  if (r.ok) {
    // 尝试过两种方式，都不行：
    // 方式1: await refresh()
    // 方式2: 直接 api('/api/agents') 更新 SYNC_STATUS
    const ad = await api('/api/agents');
    SYNC_STATUS = ad.sync_status || [];
    renderAgentInfo();
    await loadGWSAgentSkills(agentKey);
  }
}
```

**`loadGWSAgentSkills()`** 渲染 preset pills (约 L157):
```javascript
const agentSync = SYNC_STATUS.find(a => a.name === agentKey || a.tool === agentKey);
const activePresets = (agentSync && agentSync.active_presets) || [];
presetEl.innerHTML = PRESETS.map(p => {
  const isActive = activePresets.includes(p.name);
  const cls = isActive ? 'active' : '';
  return `<span class="preset-pill ${cls}" onclick="togglePresetForAgent('${esc(p.name)}','${esc(agentKey)}')">${esc(p.name)}</span>`;
}).join('');
```

**`gwsBatchAction()`** 批量 remove (约 L195):
```javascript
async function gwsBatchAction(action) {
  const names = [...GWS_SELECTED];
  const r = await api(`/api/workspace/global/${encodeURIComponent(GWS_SELECTED_AGENT)}/${action}`, {
    method: 'POST', body: JSON.stringify({ skill_names: names })
  });
  if (r.ok) {
    GWS_SELECTED.clear();
    // 同样需要重新加载数据
    const ad = await api('/api/agents');
    SYNC_STATUS = ad.sync_status || [];
    await loadGWSAgentSkills(GWS_SELECTED_AGENT);
  }
}
```

### 2. `static/js/app.js` — 全局状态与 refresh

```javascript
let SYNC_STATUS = [];  // 全局变量

async function refresh() {
  const [sd, ad, pd, td, settings] = await Promise.all([
    api('/api/skills'), api('/api/agents'), api('/api/presets'), api('/api/tags'), api('/api/settings')
  ]);
  SYNC_STATUS = ad.sync_status || [];
  // ...
  if (RENDERERS[CURRENT_PAGE]) RENDERERS[CURRENT_PAGE]();
}

async function api(path, opts = {}) {
  try {
    const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...opts });
    return await r.json();
  } catch (e) {
    console.error('API error:', path, e);
    return { error: e.message };
  }
}
```

### 3. `web-ui.py` — 后端 API

**`/api/agents` GET** (L538):
```python
if path == "/api/agents" and method == "GET":
    self._json({"agents": detect_agents(), "sync_status": get_sync_status()})
```

**`get_sync_status()`** (L278):
```python
def get_sync_status():
    cfg = parse_yaml(CONFIG_FILE) if CONFIG_FILE.exists() else {}
    agents_cfg = cfg.get("agents", {})
    for name, acfg in agents_cfg.items():
        presets = acfg.get("active_presets", [])
        # ... 返回 active_presets 字段
```

**Preset activate** (L886):
```python
if action == "activate" and method == "POST":
    # 更新 config.yaml 的 active_presets
    write_yaml_value(CONFIG_FILE, "active_presets", current, agent_name=config_name)
    sync_result = run_ps("sync.ps1", ["-Agent", config_name])
    self._json({"ok": True, "agent_config": config_name})
```

**Remove** (L1025):
```python
# 检测 junction 并用 os.rmdir 删除
attrs = os.lstat(str(target))
is_junction = bool(attrs.st_file_attributes & 0x400)
if is_junction:
    os.rmdir(str(target))
```

### 4. `config.yaml` — 配置文件

```yaml
agents:
  claude_code_global:
    tool: claude_code
    path: "C:/Users/xianjun.zeng/.claude/skills"
    active_presets: []
    skills: ["*"]
```

## 已修复的后端 Bug（历史）

| Bug | 原因 | 修复 |
|-----|------|------|
| Junction 删除失败 | `shutil.rmtree()` 无法删 junction | 检测 junction 后用 `os.rmdir()` |
| YAML 空数组解析错误 | `active_presets: []` 被解析为字符串 `"[]"` | `Convert-YamlValue` 添加 `if ($val -eq '[]') { return @() }` |

## 需要排查的方向

1. **`api()` 函数是否返回了正确数据**：在 `api('/api/agents')` 后打印返回值，确认 `sync_status` 中 `active_presets` 的值
2. **`SYNC_STATUS` 赋值是否生效**：赋值后立即打印确认
3. **竞态条件**：`renderGlobalWS()` 调用 `loadGWSAgentSkills()` 时未 await，可能导致多次异步调用互相覆盖
4. **`GWS_SELECTED_AGENT` 匹配问题**：值为 `claude_code`，但 `SYNC_STATUS` 中 `name` 是 `claude_code_global`，靠 `tool` 字段匹配
5. **浏览器缓存**：JS 文件可能被缓存，需要确认加载的是最新版本

## 环境信息

- OS: Windows 10 21H2
- Python: 3.8
- Shell: PowerShell
- 同步模式: junction
- 服务地址: http://127.0.0.1:8770
- Agent: Claude Code (config name: `claude_code_global`, key: `claude_code`)
- Skills 目录: `C:\Users\xianjun.zeng\.claude\skills`
- 中央技能库: `D:\06_Project\skills_sync\skills` (26 个 skills)
