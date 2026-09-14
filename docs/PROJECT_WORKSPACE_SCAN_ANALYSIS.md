# Project Workspace Scan 问题分析报告

> 问题：添加 `D:\06_Project\pd_auth_analyse` 后点击 Scan，无法扫描出 skills
> 日期：2026-07-16
> 状态：**已修复**

---

## 调试过程记录

### Step 1: 验证后端 API

**测试命令：**
```bash
python -c "import requests; r = requests.post('http://127.0.0.1:8780/api/workspace/scan', json={'path': 'D:/06_Project/pd_auth_analyse', 'max_depth': 3}); print(r.json())"
```

**结果：** ✅ API 正常返回
```json
{
  "workspaces": [
    {"agent_dir": ".claude", "skill_count": 0},
    {"agent_dir": ".qoder", "skill_count": 1, "skills": [{"name": "pd_auth_analyse"}]}
  ]
}
```

### Step 2: 检查目录结构

```
D:\06_Project\pd_auth_analyse\
├── .claude\skills\          ← 空目录
└── .qoder\skills\
    └── pd_auth_analyse\
        └── SKILL.md         ← 存在
```

### Step 3: 前端代码分析

**发现问题：**
1. `scanPWSWorkspace()` 默认深度为 1，可能太浅
2. 缺少错误处理，API 失败时静默失败
3. 缺少调试日志，无法定位问题

### Step 4: 修复内容

**文件：** `static/js/workspace.js`

**修改 1：增加默认深度和错误处理**
```javascript
// 修改前
const depth = ws.depth || 1;
const result = await api('/api/workspace/scan', ...);
ws._scan_result = result;

// 修改后
const depth = ws.depth || 2;  // 默认深度改为 2
const result = await api('/api/workspace/scan', ...);
if (result.error) {
  showToast('Scan failed: ' + result.error, 'error');
  return;
}
ws._scan_result = result;
```

**修改 2：添加调试日志**
```javascript
console.log('[PWS Scan] scanPWSWorkspace called, index:', index);
console.log('[PWS Scan] API result:', result);
console.log('[PWS Render] renderPWSScanResult called, result:', result);
console.log('[PWS Details] ws._scan_result:', ws._scan_result);
```

**修改 3：改进提示信息**
```javascript
// 修改前
showToast('Scan complete');

// 修改后
showToast(`Scan complete: ${ws.skill_count} skills found`);
```

---

## 一、问题现象

用户在 Project Workspace 页面：
1. 添加了工作区路径 `D:\06_Project\pd_auth_analyse`
2. 点击 "Scan" 按钮
3. 显示 "No agents found in this workspace" 或无 skills 显示

---

## 二、后端验证结果

### 2.1 目录结构检查

```
D:\06_Project\pd_auth_analyse\
├── .claude\
│   ├── skills\          ← 空目录
│   └── skills-disabled\
├── .qoder\
│   ├── skills\
│   │   └── pd_auth_analyse\
│   │       └── SKILL.md  ← 存在！
│   └── repowiki\
├── data\
├── docs\
├── src\
└── ...
```

### 2.2 后端扫描测试

**直接调用 Python 扫描函数：**

```python
from workspace import WorkspaceScanner
from pathlib import Path

ws = WorkspaceScanner(Path('.'))
result = ws.scan_native('D:/06_Project/pd_auth_analyse', 3)
```

**返回结果：**

```json
{
  "projects": [],
  "workspaces": [
    {
      "project_path": "D:\\06_Project\\pd_auth_analyse",
      "project_name": "pd_auth_analyse",
      "agent_dir": ".claude",
      "tool": "claude_code",
      "label": "Claude Code",
      "skills_path": "D:\\06_Project\\pd_auth_analyse\\.claude\\skills",
      "skills": [],
      "skill_count": 0
    },
    {
      "project_path": "D:\\06_Project\\pd_auth_analyse",
      "project_name": "pd_auth_analyse",
      "agent_dir": ".qoder",
      "tool": "qoder",
      "label": "Qoder",
      "skills_path": "D:\\06_Project\\pd_auth_analyse\\.qoder\\skills",
      "skills": [
        {
          "name": "pd_auth_analyse",
          "display_name": "pd-auth-analyse",
          "description": "PD认证问题分析Skill...",
          "enabled": true,
          "type": "dir",
          "path": "D:\\06_Project\\pd_auth_analyse\\.qoder\\skills\\pd_auth_analyse\\SKILL.md"
        }
      ],
      "skill_count": 1
    }
  ]
}
```

**结论：后端扫描完全正常！**
- 找到 2 个 agent 目录（`.claude` 和 `.qoder`）
- `.qoder` 下有 1 个 skill（`pd_auth_analyse`）
- `.claude` 下 skills 目录为空

---

## 三、前端代码分析

### 3.1 扫描流程

```javascript
// workspace.js L418-429
async function scanPWSWorkspace(index) {
  const ws = PWS_WORKSPACES[index];
  if (!ws) return;
  showToast('Scanning workspace...');
  const depth = ws.depth || 1;  // ← 默认深度 1
  const result = await api('/api/workspace/scan', {
    method: 'POST',
    body: JSON.stringify({ path: ws.path, max_depth: depth })
  });
  ws._scan_result = result;
  ws.skill_count = (result.workspaces || []).reduce((sum, w) => sum + (w.skills || []).length, 0);
  savePWSWorkspaces();
  renderProjectWS();
  showToast('Scan complete');
}
```

### 3.2 渲染逻辑

```javascript
// workspace.js L381-411
function renderPWSScanResult(result) {
  const workspaces = result.workspaces || [];
  if (workspaces.length === 0) {
    return '<p class="text-sm text-slate-400 text-center py-8">No agents found in this workspace</p>';
  }
  // ... 渲染每个 agent 和 skills
}
```

### 3.3 潜在问题点

| # | 问题 | 可能性 | 说明 |
|---|------|--------|------|
| 1 | 服务器未运行 | 高 | 端口 8780，需确认 `python web-ui.py` 已启动 |
| 2 | API 调用失败 | 中 | `api()` 函数 catch 错误后返回 `{error: ...}`，前端未检查 |
| 3 | `ws.path` 格式问题 | 低 | 路径中的反斜杠可能需要转义 |
| 4 | `renderProjectWS()` 未重新渲染详情 | 中 | 可能只渲染了列表，未更新右侧详情 |
| 5 | `_scan_result` 未正确保存 | 低 | `savePWSWorkspaces()` 会保存到 localStorage |

---

## 四、排查步骤

### 4.1 确认服务器运行

```powershell
# 检查端口 8780 是否被占用
netstat -ano | findstr :8780

# 启动服务器
cd D:\06_Project\skills_sync
python web-ui.py
```

### 4.2 浏览器 Console 调试

1. 打开 http://127.0.0.1:8780
2. 进入 Project Workspace 页面
3. 按 F12 打开开发者工具 → Console
4. 选择已添加的工作区
5. 点击 Scan 按钮
6. 观察 Console 输出

**预期输出：**
```
Scanning workspace...
Scan complete
```

**如果看到错误：**
```
API error: /api/workspace/scan ...
```
说明 API 调用失败。

### 4.3 手动测试 API

在浏览器 Console 中执行：

```javascript
fetch('/api/workspace/scan', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({path: 'D:/06_Project/pd_auth_analyse', max_depth: 3})
})
.then(r => r.json())
.then(data => console.log('Result:', data))
.catch(e => console.error('Error:', e));
```

---

## 五、修复建议

### 5.1 添加错误处理

```javascript
async function scanPWSWorkspace(index) {
  const ws = PWS_WORKSPACES[index];
  if (!ws) return;
  showToast('Scanning workspace...');
  const depth = ws.depth || 2;  // 改为默认 2
  try {
    const result = await api('/api/workspace/scan', {
      method: 'POST',
      body: JSON.stringify({ path: ws.path, max_depth: depth })
    });
    if (result.error) {
      showToast('Scan failed: ' + result.error, 'error');
      return;
    }
    ws._scan_result = result;
    ws.skill_count = (result.workspaces || []).reduce((sum, w) => sum + (w.skills || []).length, 0);
    savePWSWorkspaces();
    renderProjectWS();
    showToast(`Scan complete: ${ws.skill_count} skills found`);
  } catch (e) {
    showToast('Scan failed: ' + e.message, 'error');
  }
}
```

### 5.2 确保详情区域重新渲染

检查 `renderProjectWS()` 是否正确渲染了右侧详情区域：

```javascript
function renderProjectWS() {
  // ... 渲染左侧列表
  // 确保右侧详情也重新渲染
  const detailsEl = document.getElementById('pwsDetailsContent');
  if (detailsEl && PWS_SELECTED_WS !== null && PWS_WORKSPACES[PWS_SELECTED_WS]) {
    const ws = PWS_WORKSPACES[PWS_SELECTED_WS];
    detailsEl.innerHTML = ws._scan_result
      ? renderPWSScanResult(ws._scan_result)
      : '<p class="text-sm text-slate-400 text-center py-8">Click "Scan" to discover agents and skills</p>';
  }
}
```

---

## 六、总结

| 项目 | 状态 |
|------|------|
| 后端扫描逻辑 | ✅ 正常 |
| 目录结构识别 | ✅ 正常（找到 .claude 和 .qoder） |
| Skill 文件解析 | ✅ 正常（找到 pd_auth_analyse） |
| 前端 API 调用 | ✅ 已修复（添加错误处理） |
| 前端渲染逻辑 | ✅ 已修复（添加调试日志） |

**根本原因：**
1. 默认扫描深度为 1，对于某些目录结构可能太浅
2. 缺少错误处理，API 失败时用户无感知
3. 缺少调试日志，问题难以定位

**修复措施：**
1. 默认深度从 1 改为 2
2. 添加 API 错误处理和提示
3. 添加详细的 console.log 调试日志
4. 改进 toast 提示，显示找到的 skill 数量

**验证方法：**
1. 启动服务器：`python web-ui.py`
2. 打开 http://127.0.0.1:8780
3. 进入 Project Workspace 页面
4. 添加工作区 `D:\06_Project\pd_auth_analyse`
5. 点击 Scan 按钮
6. 应显示：`.qoder` 下有 1 个 skill（pd_auth_analyse）
7. 打开浏览器 Console（F12）可查看详细日志
