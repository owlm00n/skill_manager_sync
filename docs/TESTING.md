# Skills Sync Manager 测试与调试指南

> 本文档记录 Skills Sync Manager 的测试手段和调试方法，方便用户自行排查问题。
> 默认端口：**8780**（2026-07-22 从 8770 迁移，避免与 cc-hub 的 Hook Manager 端口冲突）

---

## 一、启动与端口

### 1.1 启动服务

```powershell
# 默认端口 8780
python web-ui.py

# 指定端口
python web-ui.py 8781
```

启动成功会输出：
```
Skills Sync Manager Web UI
  http://127.0.0.1:8780
  Skills dir: D:\06_Project\skills_sync\skills
  Config: D:\06_Project\skills_sync\config.yaml
  Static: D:\06_Project\skills_sync\static
Press Ctrl+C to stop.
```

### 1.2 端口占用排查

如果启动后浏览器访问看到的是**其他应用**（如 Hook Manager、Session Manager），说明端口被抢占。

```powershell
# 1. 查看谁占用了 8780（或 8770）
netstat -ano | findstr ":8780"

# 2. 查看进程详情（把 PID 替换为上一步的最后一列数字）
Get-CimInstance Win32_Process -Filter "ProcessId=<PID>" | Select-Object ProcessId, CommandLine | Format-List

# 3. 杀掉占用进程（谨慎）
Stop-Process -Id <PID> -Force
```

### 1.3 cc-hub 端口规划（避免冲突）

cc-hub 体系占用的端口（**不要给 Skills Sync Manager 用**）：

| 模块 | 端口 |
|------|------|
| Session Manager | 8765 |
| Skill Manager | 8766 |
| CC Tools Hub | 8767 |
| Permission Manager | 8768 |
| Memory Manager | 8769 |
| **Hook Manager** | **8770** |
| Agent Manager | 8771 |

**Skills Sync Manager 现在使用 8780**，避开上述区间。

### 1.4 多实例问题

Windows 上 Python `HTTPServer` 默认开启 `allow_reuse_address`，可能导致**多个进程绑定同一端口**，请求被随机路由到其中一个。

症状：改了代码但刷新页面没变化（请求路由到了旧进程）。

排查：
```powershell
# 查看所有 python 进程
Get-Process python | Select-Object Id, StartTime, Path | Format-Table

# 查看每个进程的启动命令
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select-Object ProcessId, CommandLine | Format-List
```

清理：
```powershell
# 杀掉所有 python 进程（谨慎，会杀掉其他 Python 应用）
Get-Process python | Stop-Process -Force

# 然后重新启动
python web-ui.py
```

---

## 二、缓存问题

### 2.1 浏览器缓存静态文件

症状：修改了 `static/js/*.js` 或 `static/css/*.css` 后，浏览器刷新看不到变化。

**已在 [web-ui.py](file:///d:/06_Project/skills_sync/web-ui.py) 的 `_serve_static` 中修复**：添加了 `ETag` + `Cache-Control: no-cache, must-revalidate` + 304 条件请求。

手动验证：
1. F12 → Network 面板
2. 刷新页面，查看 JS 文件的 Response Headers
3. 应该看到 `Cache-Control: no-cache, must-revalidate` 和 `ETag: "..."`
4. 第二次刷新应该返回 `304 Not Modified`

强制刷新：
- `Ctrl + F5`（硬刷新，忽略缓存）
- 或 F12 → Network → 勾选 "Disable cache" → 刷新

### 2.2 Python 模块缓存

症状：修改了 `web-ui.py` 但重启后行为没变。

原因：可能有旧的 python 进程还在跑（见 1.4）。

解决：
```powershell
# 确保杀掉所有旧进程
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*web-ui.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

# 重新启动
python web-ui.py
```

---

## 三、API 测试

### 3.1 基础 API 调试

所有 API 都在 `/api/` 路径下，返回 JSON。可以用 Python 快速测试：

```python
import json, urllib.request

BASE = "http://127.0.0.1:8780"

# GET 请求
r = json.loads(urllib.request.urlopen(BASE + "/api/agents").read())
print(json.dumps(r, indent=2, ensure_ascii=False))

# POST 请求
req = urllib.request.Request(
    BASE + "/api/presets/all/activate",
    data=json.dumps({"agent": "claude_code"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
r = json.loads(urllib.request.urlopen(req).read())
print(json.dumps(r, indent=2, ensure_ascii=False))
```

### 3.2 常用 API 列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/agents` | 获取所有 agent 同步状态 |
| GET | `/api/skills` | 获取中央库所有 skills |
| GET | `/api/workspace/global/{agent}` | 获取 agent 的全局 skills |
| POST | `/api/presets/{name}/activate` | 激活 preset（body: `{"agent":"claude_code"}`） |
| POST | `/api/presets/{name}/deactivate` | 停用 preset |
| POST | `/api/sync` | 执行同步（body: `{}`） |
| POST | `/api/workspace/global/{agent}/sync` | 同步指定 agent 的 skills |
| GET | `/api/backup/status` | Git 仓库状态 |
| POST | `/api/backup/now` | 立即备份（commit + push） |
| POST | `/api/backup/pull` | 从 remote pull |
| GET | `/api/backup/history` | 最近 20 条 commit |

### 3.3 PowerShell 调用 API

```powershell
# GET
Invoke-RestMethod -Uri "http://127.0.0.1:8780/api/agents"

# POST
Invoke-RestMethod -Uri "http://127.0.0.1:8780/api/presets/all/activate" `
    -Method POST `
    -ContentType "application/json" `
    -Body '{"agent":"claude_code"}'
```

---

## 四、Preset 逻辑测试

### 4.1 Preset 语义（2026-07-21 更新）

**最终同步集 = (激活 preset 的 skills 并集) ∪ (不在任何 preset 中的 free skills)**

- 被 preset 引用的 skill：**只有对应 preset 激活时才同步**
- 不在任何 preset 中的 skill：**始终同步**

### 4.2 手动测试 Preset

```python
import json, urllib.request, time

BASE = "http://127.0.0.1:8780"
AGENT = "claude_code"
SKILLS_DIR = r"C:\Users\xianjun.zeng\.claude\skills"

def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(BASE + path, data=data,
        headers={"Content-Type": "application/json"}, method=method)
    return json.loads(urllib.request.urlopen(req).read())

def disk_skills():
    from pathlib import Path
    d = Path(SKILLS_DIR)
    if not d.exists(): return []
    return sorted([x.name for x in d.iterdir() if x.is_dir() and not x.name.startswith(".")])

# 1. 重置：停用所有 preset，然后激活 all
for p in ["debug-toolkit", "protocol-dev", "management", "all", "bug"]:
    try: api(f"/api/presets/{p}/deactivate", "POST", {"agent": AGENT})
    except: pass
api("/api/presets/all/activate", "POST", {"agent": AGENT})
time.sleep(1)
print(f"After activate 'all': {len(disk_skills())} skills on disk")  # 应为 26

# 2. 停用 all → 应该清空
api("/api/presets/all/deactivate", "POST", {"agent": AGENT})
time.sleep(2)
print(f"After deactivate 'all': {len(disk_skills())} skills on disk")  # 应为 0

# 3. 激活 debug-toolkit → 应该只有 bug-core
api("/api/presets/debug-toolkit/activate", "POST", {"agent": AGENT})
time.sleep(2)
print(f"After activate 'debug-toolkit': {disk_skills()}")  # 应为 ['bug-core']

# 4. 恢复
api("/api/presets/debug-toolkit/deactivate", "POST", {"agent": AGENT})
api("/api/presets/all/activate", "POST", {"agent": AGENT})
```

---

## 五、Backup 功能测试

### 5.1 命令行测试 Git

```powershell
# 在项目目录执行
cd D:\06_Project\skills_sync

# 检查 remote
git remote -v
# 应输出: origin  https://github.com/owlm00n/skill_manager_sync.git

# 手动 commit + push（模拟 backup/now）
git add -A
git commit -m "test backup"
git push origin HEAD

# 查看 git 状态
git status

# 查看最近提交
git log --oneline -5
```

### 5.2 API 测试 Backup

```python
import json, urllib.request

BASE = "http://127.0.0.1:8780"

def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(BASE + path, data=data,
        headers={"Content-Type": "application/json"}, method=method)
    return json.loads(urllib.request.urlopen(req).read())

# 状态
print(json.dumps(api("/api/backup/status"), indent=2, ensure_ascii=False))

# 立即备份
r = api("/api/backup/now", "POST", {})
print(json.dumps(r, indent=2, ensure_ascii=False))
# 成功响应应包含:
#   "ok": true
#   "commit_ok": true
#   "pushed": true

# 历史
print(json.dumps(api("/api/backup/history"), indent=2, ensure_ascii=False))
```

### 5.3 Backup 失败排查

如果 `ok: false`：

1. **`commit_ok: false`** → 检查 `commit_error` 字段
   - 可能是 git 没配置 user.email / user.name
   - 解决：`git config --global user.email "you@example.com"` + `git config --global user.name "Your Name"`

2. **`pushed: false`** → 检查 `push_error` 字段
   - 可能是认证失败（HTTPS 需要 token）
   - 可能是 remote 不存在
   - 排查：
     ```powershell
     git push origin HEAD
     # 看具体错误
     ```

3. **`nothing_to_commit: true`** → 不是错误，表示没有改动需要提交，`ok` 应为 `true`

---

## 六、Playwright 端到端测试

### 6.1 安装

```powershell
pip install playwright
playwright install chromium
```

### 6.2 基础测试模板

```python
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8780"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_context().new_page()

    # 捕获 JS 错误
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}") if m.type == "error" else None)

    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(1500)

    # 导航到各页面
    for nav in ["dashboard", "library", "global-ws", "project-ws", "presets", "backup"]:
        page.evaluate(f"navigate('{nav}')")
        page.wait_for_timeout(1000)
        print(f"{nav}: OK")

    # 检查 JS 错误
    real_errors = [e for e in errors if "cdn.tailwindcss.com" not in e]
    print(f"\nJS errors: {len(real_errors)}")
    for e in real_errors:
        print(f"  {e}")

    browser.close()
```

### 6.3 捕获页面 JS 错误（window.onerror 注入）

当 `pageerror` 没有堆栈时，在页面加载前注入 `window.onerror`：

```python
page.add_init_script("""
window.onerror = function(msg, url, line, col, err) {
    console.error('[window.onerror] ' + msg + ' @ ' + url + ':' + line + ':' + col);
};
""")
```

---

## 七、常见问题

### Q1: 启动后浏览器显示的是 Hook Manager

**原因**：8770 端口被 Hook Manager 占用。
**解决**：Skills Sync Manager 默认端口已改为 8780。访问 `http://127.0.0.1:8780`。

### Q2: 改了代码但刷新没变化

**原因 1**：浏览器缓存。按 `Ctrl + F5` 硬刷新。
**原因 2**：旧的 python 进程还在跑。用 `Get-CimInstance Win32_Process` 查看，杀掉旧进程后重启。

### Q3: Preset 取消激活后 skills 没删除

**原因**：旧的 sync.ps1 逻辑是"无 preset 则回退到 skills 字段"。
**解决**：已在 2026-07-21 修复，新逻辑是"被 preset 管理的 skill 只有对应 preset 激活时才同步"。重启服务后生效。

### Q4: Remove 删不掉某些 skill

**原因**：前端用 `s.name`（frontmatter 名，可能带连字符）作为标识符，与实际目录名（带下划线）不匹配。
**解决**：已在 2026-07-21 修复，前端改用 `s.dir` 作为标识符。

### Q5: Backup Now 失败

**原因 1**：commit 失败（git 未配置 user）。
**原因 2**：push 失败（认证问题）。
**排查**：查看 API 响应的 `commit_error` / `push_error` 字段。

### Q6: tailwind.config 配置不生效

**原因**：`static/index.html` 中 `tailwind.config` 对象字面量少一个闭合 `}`。
**解决**：已在 2026-07-21 修复。验证方法：F12 Console 应无 `Unexpected end of input` 错误。

---

## 八、文件清单

### 8.1 核心文件

| 文件 | 说明 |
|------|------|
| [web-ui.py](file:///d:/06_Project/skills_sync/web-ui.py) | Python 后端（HTTP server + API） |
| [sync.ps1](file:///d:/06_Project/skills_sync/sync.ps1) | PowerShell 同步脚本（junction/symlink/copy） |
| [config.yaml](file:///d:/06_Project/skills_sync/config.yaml) | 配置文件（agents、presets、sync mode） |
| [static/index.html](file:///d:/06_Project/skills_sync/static/index.html) | 前端入口 HTML |
| [static/js/app.js](file:///d:/06_Project/skills_sync/static/js/app.js) | 全局状态 + API helper + 路由 |
| [static/js/workspace.js](file:///d:/06_Project/skills_sync/static/js/workspace.js) | Global/Project Workspace 逻辑 |
| [static/js/backup.js](file:///d:/06_Project/skills_sync/static/js/backup.js) | Backup 页面逻辑 |
| [static/js/library.js](file:///d:/06_Project/skills_sync/static/js/library.js) | Library 页面逻辑 |

### 8.2 文档

| 文件 | 说明 |
|------|------|
| [README.md](file:///d:/06_Project/skills_sync/README.md) | 项目说明 |
| [docs/skills-manager-analysis.md](file:///d:/06_Project/skills_sync/docs/skills-manager-analysis.md) | 功能设计与实现状态 |
| [docs/BUG_REPORT.md](file:///d:/06_Project/skills_sync/docs/BUG_REPORT.md) | 原始 Bug 报告（v1） |
| [docs/BUG_REPORT_v2.md](file:///d:/06_Project/skills_sync/docs/BUG_REPORT_v2.md) | Bug 修复记录（v2） |
| [docs/TESTING.md](file:///d:/06_Project/skills_sync/docs/TESTING.md) | 本文档（测试与调试指南） |

---

## 九、环境信息

- OS: Windows 10 21H2
- Python: 3.8 (`C:\Program Files\Python38\python.exe`)
- Shell: PowerShell 5.1
- 同步模式: junction
- 默认端口: 8780
- Remote: `https://github.com/owlm00n/skill_manager_sync.git`
- 中央技能库: `D:\06_Project\skills_sync\skills` (26 个 skills)
- Agent skills 目录: `C:\Users\<user>\.claude\skills`
