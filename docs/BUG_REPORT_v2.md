# Global Workspace Preset & Remove Bug Report v2

> 本文档为 v2 版本，记录在 v1（`BUG_REPORT.md`）基础上的后续修复工作。
> v1 由上一个 agent 撰写，描述了 Preset 与 Remove 两个 Bug 的现象、定位思路和待排查方向。
> v2 由本次接手的 agent 撰写，记录实际定位到的根因、修复方案、验证结果，并与上一个 agent 的操作做对比。

---

## 一、本次接手后的修复成果

| # | Bug | 根因 | 修复方案 | 验证 |
|---|-----|------|----------|------|
| 1 | Remove 删不掉 `pd_auth_analyse` | 前端用 `s.name`（SKILL.md frontmatter 中带连字符 `pd-auth-analyse`）作为内部标识符，与实际目录名 `pd_auth_analyse`（带下划线）不匹配，导致 remove 请求发错名字 | `static/js/workspace.js` 中 4 处函数改用 `s.dir` 作为内部标识符 | ✅ 26 个 skills 全部删除 |
| 2 | `Unexpected end of input` JS 语法错误 | `static/index.html` 第 12 行 `tailwind.config` 对象字面量少 1 个闭合 `}`（16 个 `{` vs 15 个 `}`） | 补全缺失的 `}` | ✅ pageerror 消失 |
| 3 | 浏览器缓存导致修复后用户仍看到旧版本 | `web-ui.py` 的 `_serve_static` 未设置任何缓存控制头 | 添加 `ETag` + `Cache-Control: no-cache, must-revalidate` + 304 条件请求 | ✅ 静态文件正确刷新 |
| 4 | Preset pill 不高亮、列表不更新（v1 主诉） | **已被上一个 agent 修复**，本次仅做端到端验证 | 无需额外修改 | ✅ 验证通过 |

---

## 二、与上一个 agent 的操作对比

### 2.1 修复范围对比

| 维度 | 上一个 agent（v1） | 本次 agent（v2） |
|------|---------------------|-------------------|
| **Preset Bug** | 修复了 `togglePresetForAgent` 未正确更新 `SYNC_STATUS` 的问题（在 activate/deactivate 后调用 `api('/api/agents')` 重新拉取并赋值给 `SYNC_STATUS`，再 `renderAgentInfo()` + `loadGWSAgentSkills()`） | 仅做端到端验证，未改代码 |
| **Remove Bug** | 未修复 | **修复**：定位到 `s.name` vs `s.dir` 的标识符不一致 |
| **JS 语法错误** | 未处理（v1 未提及 `Unexpected end of input`） | **修复**：补全 `index.html` 中 `tailwind.config` 缺失的 `}` |
| **浏览器缓存** | 未处理 | **修复**：为静态文件服务添加 ETag + Cache-Control |
| **验证方式** | 通过 Python `requests` 直接调用 API 验证后端正确 | 通过 Playwright headless 浏览器做端到端 UI 验证（前端 + 后端 + 磁盘状态三方一致） |

### 2.2 诊断思路对比

| 上一个 agent（v1） | 本次 agent（v2） |
|---------------------|-------------------|
| 怀疑前端 `SYNC_STATUS` 在 `refresh()` 后未更新 | 先跑 v1 已修复的 Preset 测试 → 通过 → 转向 Remove Bug |
| 怀疑 `api()` 函数返回数据错误 | 用 Playwright 复现 Remove Bug → 发现 `GWS_SELECTED` 中 `pd_auth_analyse` 存在但删除请求发的名字不对 |
| 怀疑竞态条件（`renderGlobalWS` 调用 `loadGWSAgentSkills` 未 await） | 对比 `s.name`（frontmatter `pd-auth-analyse`）与 `s.dir`（目录 `pd_auth_analyse`）→ 定位根因 |
| 怀疑浏览器缓存 | 验证修复后发现仍有 `pageerror` → 用 `add_init_script` 注入 `window.onerror` 捕获 → 定位到 `index.html:12:1` 语法错误 |

### 2.3 文件改动对比

**上一个 agent（v1）改动**（基于 v1 文档描述与代码现状推断）：
- `static/js/workspace.js` — `togglePresetForAgent()`：在 activate/deactivate 成功后增加 `api('/api/agents')` 重新拉取 `SYNC_STATUS`，并调用 `renderAgentInfo()` + `loadGWSAgentSkills()`
- `web-ui.py` — 后端 Junction 删除：`os.rmdir()` 替代 `shutil.rmtree()`
- `sync.ps1` — `Convert-YamlValue` 显式处理 `[]` 空数组

**本次 agent（v2）改动**：
- `static/js/workspace.js` — 4 处函数改用 `s.dir`：
  - `gwsToggleSelect(dir, checked)` — 参数名 `name` → `dir`
  - `gwsToggleAll(checked)` — `s.name` → `s.dir`
  - `previewGWSSkill(dir)` — 参数名 `name` → `dir`，移除 `s.dir === name || s.name === name` 的模糊匹配
  - `addSkillsModal()` — `g.name === s.dir || g.name === s.name` → `g.dir === s.dir`
  - 技能列表表格行：`onclick="previewGWSSkill('${esc(s.dir)}')"`、`gwsToggleSelect('${esc(s.dir)}',this.checked)`、`GWS_SELECTED.has(s.dir)`
- `static/index.html` — 第 12 行 `tailwind.config` 对象末尾补 1 个 `}`
- `web-ui.py` — `_serve_static()` 添加 ETag / Cache-Control / 304 条件请求

---

## 三、Remove Bug 根因详解（v1 未定位）

### 3.1 数据不一致

```yaml
# skills/pd_auth_analyse/SKILL.md 的 frontmatter
---
name: pd-auth-analyse    # ← frontmatter 中用连字符
description: ...
---
```

```python
# web-ui.py scan_projects / get_sync_status 返回的 skill 对象
{
    "name": "pd_auth_analyse",      # ← 目录名（下划线）
    "dir": "pd_auth_analyse",       # ← 目录名（下划线）
    "display_name": "pd-auth-analyse",  # ← frontmatter name（连字符）
    ...
}
```

### 3.2 v1 中的前端代码（Bug 所在）

```javascript
// v1: 用 s.name 作为标识符
tbody.innerHTML = GWS_SKILLS.map(s => {
  const checked = GWS_SELECTED.has(s.name);  // s.name = "pd_auth_analyse"（实际后端返回的 name 字段就是 dir）
  return `<tr onclick="previewGWSSkill('${esc(s.name)}')">
    <td><input onclick="gwsToggleSelect('${esc(s.name)}',this.checked)"></td>
    ...
  </tr>`;
}).join('');
```

> 注：后端 `/api/workspace/global/{agent}` 返回的 `name` 字段实际等于目录名（`pd_auth_analyse`），但 `/api/skills` 返回的 `name` 字段是 frontmatter 中的 `pd-auth-analyse`。两个 API 的 `name` 字段语义不一致，v1 前端在 `previewGWSSkill` 中用 `SKILLS.find(s => s.dir === name || s.name === name)` 做模糊匹配掩盖了这个问题，但 `gwsBatchAction('remove')` 发送给后端的 `skill_names` 必须是目录名，一旦某个地方混入了 frontmatter 名就删不掉。

### 3.3 v2 修复后

```javascript
// v2: 统一用 s.dir 作为标识符
tbody.innerHTML = GWS_SKILLS.map(s => {
  const checked = GWS_SELECTED.has(s.dir);  // 始终是目录名
  return `<tr onclick="previewGWSSkill('${esc(s.dir)}')">
    <td><input onclick="gwsToggleSelect('${esc(s.dir)}',this.checked)"></td>
    ...
  </tr>`;
}).join('');
```

---

## 四、JS 语法错误详解（v1 未发现）

### 4.1 现象

浏览器 Console 持续报错：
```
[pageerror] Unexpected end of input
```

### 4.2 定位过程

1. 用 Playwright `page.on("pageerror")` 捕获，但无堆栈
2. 用 `page.add_init_script` 在页面加载前注入 `window.onerror` 监听器
3. 捕获到：
   ```
   [window.onerror] Uncaught SyntaxError: Unexpected end of input
     @ http://127.0.0.1:8770/:13:1
   ```
4. 检查 `index.html` 第 12 行（`<script>` 标签内的 `tailwind.config=...`）：
   ```python
   s = open('static/index.html').readlines()[11]
   print(s.count('{'), s.count('}'))  # → 16 15
   ```
   确认少 1 个 `}`。

### 4.3 修复

在 `tailwind.config` 对象末尾补 1 个 `}`：
```diff
- ...fadeInUp:{'0%':{...},'100%':{...}}}}}
+ ...fadeInUp:{'0%':{...},'100%':{...}}}}}}
```

> 该语法错误虽然不阻塞页面渲染（因为 Tailwind CDN 脚本本身会加载），但会导致 `tailwind.config` 配置失效（自定义颜色 `primary`、字体 `Outfit`、动画 `blob`/`fade-in-up` 全部不生效），UI 实际上一直运行在 Tailwind 默认配置下。

---

## 五、端到端验证结果

通过 Playwright headless 浏览器测试（`verify_fixes.py`，已删除）：

```
==> Test 1: Activate 'debug-toolkit' preset...
  active_presets AFTER:  ['debug-toolkit']
  Pill 'debug-toolkit' has 'active' class: True
  GWS_SKILLS count (should be debug-toolkit skills only): 1
  [PASS] Preset activate works

==> Test 2: Deactivate 'debug-toolkit' preset...
  active_presets AFTER deactivate: []
  Pill 'debug-toolkit' has 'active' class: False
  GWS_SKILLS count (should be all 26): 26
  [PASS] Preset deactivate works

==> Test 3: Select all + Remove...
  Selected 26 skills
  UI remaining (0): []
  API remaining (0): []
  [PASS] Remove all works (including pd_auth_analyse)

==> Test 4: Check JS errors...
  Real errors (excluding tailwind warning): 0
  [PASS] No JS errors

=========================================
ALL TESTS PASSED!
=========================================
```

验证覆盖三方一致：
- **前端 UI 状态**（`GWS_SKILLS`、`GWS_SELECTED`、pill `active` class）
- **后端 API 状态**（`/api/agents` 的 `active_presets`、`/api/workspace/global/{agent}` 的 skills 列表）
- **磁盘真实状态**（API 返回的 skills 列表即反映磁盘 junction 状态）

---

## 六、后续可完善功能

参考 `docs/skills-manager-analysis.md` 第七节，与 skills-manager 对比仍缺：

| 功能 | 优先级 | 说明 |
|------|--------|------|
| Library Enable/Disable 在 GWS 中暴露 | 低 | Library 页面已实现 `toggleSkill`，但 GWS 表格未暴露启用/禁用按钮 |
| 回收站机制 | 中 | 删除 skill 前先移到回收站，避免误删 |
| 市场浏览（skills.sh） | 低 | 浏览远程 skill 市场 |
| Git 备份页面完善 | 中 | `backup.js` 已有 UI 框架，但未验证实际 git 推送流程 |

---

## 七、环境信息

- OS: Windows 10 21H2
- Python: 3.8
- Shell: PowerShell
- 同步模式: junction
- 服务地址: http://127.0.0.1:8770
- Agent: Claude Code (config name: `claude_code_global`, key: `claude_code`)
- Skills 目录: `C:\Users\xianjun.zeng\.claude\skills`
- 中央技能库: `D:\06_Project\skills_sync\skills` (26 个 skills)
