# Skills Sync Manager — 功能设计与实现状态

> 项目路径：`D:\06_Project\skills_sync`
> 技术栈：Python 3.8 (web-ui.py) + PowerShell (sync.ps1) + 原生 JS 前端
> 服务地址：http://127.0.0.1:8770

---

## 一、项目概述

Skills Sync Manager 是一个多 Agent 技能同步管理工具，用于将中央技能库中的 skills 同步到各种 AI agent 的全局/项目目录。

### 核心概念
```
┌──────────────────────────┐
│   Central Library (技能库) │  ← D:\06_Project\skills_sync\skills\
│   26 个 skills            │     所有 skill 的单一源
└────────────┬─────────────┘
             │  三种同步模式
    ┌────────┼────────┐
    ▼        ▼        ▼
 Junction  Symlink  Copy
 (免管理员) (需管理员) (复制文件)
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
 Claude    Qoder    Hermes  ... (23+ agents)
 ~/.claude  ~/.qoder  ~/.hermes
 /skills/   /skills/  /skills/
```

### 与 skills-manager 的关系
本项目参考了 [skills-manager](https://github.com/xingkongliang/skills-manager) 的功能设计，但采用 Python+PowerShell 混合技术栈，专注于 Windows 环境下的多 agent 技能同步。

---

## 二、已实现功能

### 2.1 中央技能库 (Library)
| 功能 | 状态 | 说明 |
|------|------|------|
| 技能列表展示 | ✅ | 显示所有 skills 的名称、描述、标签 |
| 打开技能文件夹 | ✅ | 点击图标打开中央库目录 |
| 技能详情预览 | ✅ | 查看 SKILL.md 内容 |
| Sync All | ✅ | 一键同步所有 skills 到所有已安装 agents |
| 技能来源显示 | ✅ | 显示 skill 在哪些 agents 中已同步 |

### 2.2 同步模式
| 模式 | 状态 | 说明 |
|------|------|------|
| Junction | ✅ | Windows 目录联接，免管理员权限 |
| Symlink | ✅ | 符号链接，需要管理员权限 |
| Copy | ✅ | 文件复制，独立副本 |
| 模式切换 | ✅ | 公共导航栏下拉切换，带说明弹窗 |

### 2.3 Global Workspace（全局工作区）
| 功能 | 状态 | 说明 |
|------|------|------|
| Agent 列表侧栏 | ✅ | 显示所有已安装的 agents |
| Agent skills 展示 | ✅ | 表格展示选中 agent 的所有 skills |
| 勾选 + Remove | ⚠️ | 批量删除 junction/copy，**前端刷新有问题** |
| Add Skills | ✅ | 从中央库选择 skills 添加到 agent |
| Preset Pills | ⚠️ | 点击激活/去激活 preset，**前端状态更新有问题** |
| 打开 agent 文件夹 | ✅ | 点击图标打开 agent skills 目录 |
| 自动扫描新 agent | ✅ | 扫描按钮发现新安装的 agents |

### 2.4 Project Workspace（项目工作区）
| 功能 | 状态 | 说明 |
|------|------|------|
| 添加关联工作区 | ✅ | 手动添加项目路径 |
| Auto-detect 扫描 | ✅ | 自动扫描指定路径下的 agent 工作区 |
| 扫描深度配置 | ✅ | 2-5 层子目录，齿轮图标设置 |
| Auto-detect 路径配置 | ✅ | 设置弹窗中配置扫描路径 |
| Workspace 列表 | ✅ | 左侧列表 + 右侧详情布局 |
| 打开工作区文件夹 | ✅ | 列表项旁的文件夹图标 |
| Agent 详情展示 | ✅ | 显示扫描到的 agents 和 skills |

### 2.5 Preset（预设）
| 功能 | 状态 | 说明 |
|------|------|------|
| Preset 定义 | ✅ | config.yaml 中定义命名 skill 集合 |
| 后端激活/去激活 | ✅ | API 正常工作，config 正确更新，sync.ps1 正确执行 |
| 前端 UI 更新 | ❌ | **Preset pill 高亮状态不更新** — 前端 bug |
| Preset 编辑 | ✅ | 修改描述和 skills 列表 |
| Preset 创建/删除 | ✅ | 通过 API 管理 |

### 2.6 其他功能
| 功能 | 状态 | 说明 |
|------|------|------|
| Dashboard | ✅ | 总览统计 |
| Agent 自动发现 | ✅ | 扫描 HOME 目录发现 23+ 种 agent |
| 备份页面 | ✅ | 基础备份功能 |
| Tags 标签系统 | ✅ | 技能打标签 + 按标签过滤 |

---

## 三、技术架构

### 3.1 文件结构
```
skills_sync/
├── web-ui.py              # Python 后端 (HTTP 服务器 + API 路由)
├── sync.ps1               # PowerShell 同步脚本 (junction/symlink/copy)
├── scan-agents.ps1        # PowerShell agent 扫描脚本
├── config.yaml            # 配置文件 (agents, presets, default_mode)
├── skills/                # 中央技能库 (26 个 skills)
├── static/
│   ├── index.html         # 单页应用入口
│   ├── css/style.css      # 全局样式 (glassmorphism + gradient)
│   └── js/
│       ├── app.js         # 全局状态管理、refresh()、导航
│       ├── workspace.js   # Global/Project Workspace 逻辑
│       ├── library.js     # Library 页面逻辑
│       └── ...
└── docs/
    ├── skills-manager-analysis.md  # 功能分析文档
    ├── BUG_REPORT.md               # Bug 报告
    └── ...
```

### 3.2 数据流
```
前端 (JS)                    后端 (Python)              PowerShell
    │                            │                          │
    ├── GET /api/agents ────────►│                          │
    │                            ├── detect_agents()        │
    │                            ├── get_sync_status() ─────┤
    │                            │   └── parse_yaml()       │
    │◄── {sync_status: [...]} ──┤                          │
    │                            │                          │
    ├── POST /presets/X/activate►│                          │
    │                            ├── write_yaml_value()     │
    │                            ├── run_ps("sync.ps1") ───►│
    │                            │                          ├── 创建/删除 junction
    │◄── {ok: true} ────────────┤◄── sync result ──────────┤
    │                            │                          │
    ├── POST /workspace/remove ─►│                          │
    │                            ├── 检测 junction          │
    │                            ├── os.rmdir() 删除        │
    │◄── {ok: true} ────────────┤                          │
```

### 3.3 配置结构 (config.yaml)
```yaml
default_mode: junction

presets:
  debug-toolkit:
    description: "调试工具包"
    skills: ["bug-core", "bug-logs", "bug-workspace", ...]
  management:
    description: "管理员工具包"
    skills: ["skill-manager", "session-manager", ...]
  all:
    description: "全部技能"
    skills: ["*"]

agents:
  claude_code_global:
    tool: claude_code
    path: "C:/Users/xianjun.zeng/.claude/skills"
    active_presets: []
    skills: ["*"]
  qoder_auto:
    tool: qoder
    path: "C:/Users/xianjun.zeng/.qoder/skills"
    active_presets: []
    skills: ["*"]
```

---

## 四、Preset 运作逻辑（设计意图）

### 4.1 核心逻辑
```
有 active_presets → 只同步这些 preset 定义的 skills
无 active_presets → 同步全部 skills（skills: ["*"]）
```

### 4.2 Junction 模式
- **激活 preset**：更新 `active_presets` → 运行 sync.ps1 → 只创建 preset 内 skills 的 junction 链接 → 清理不在列表中的旧 junction
- **去激活 preset**：从 `active_presets` 移除 → 运行 sync.ps1 → 如果无 active_presets 则同步全部，否则同步剩余 preset 的 skills

### 4.3 Copy 模式
- **激活 preset**：同上，但操作是复制文件而非创建链接
- **去激活 preset**：同上，删除不需要的 skill 副本

### 4.4 sync.ps1 的 Resolve-SkillsForAgent
```powershell
# 检查 active_presets
# 有 presets → 收集所有 active preset 的 skills（去重）
# 无 presets → 回退到 skills: ["*"]（全部）
# Clean-StaleSkills → 删除不在预期列表中的旧 skills
```

---

## 五、已知 Bug

### 5.1 前端 Preset 状态不更新（未解决）
- **现象**：点击 preset pill 后，pill 不高亮，skills 列表不更新
- **后端验证**：API 正常，config.yaml 正确更新，sync.ps1 正确执行
- **问题定位**：前端 `SYNC_STATUS` 在 `refresh()` 后未正确更新
- **详见**：`docs/BUG_REPORT.md`

### 5.2 前端 Remove 后状态不刷新（未解决）
- **现象**：全选 remove 后，个别 skill 残留显示
- **后端验证**：remove API 正常删除 junction
- **问题定位**：与 5.1 相同的前端状态同步问题

### 5.3 已修复的 Bug
| Bug | 修复 |
|-----|------|
| Junction 删除失败 | `os.rmdir()` 替代 `shutil.rmtree()` |
| YAML 空数组 `[]` 解析错误 | `Convert-YamlValue` 显式处理 |
| 嵌套路径问题 | 修复扫描逻辑避免 `skills/skills` 嵌套 |

---

## 六、Agent 注册表

系统支持 23+ 种 agent，注册在 `AGENT_REGISTRY` 中：

| Key | Label | Skills 路径 |
|-----|-------|------------|
| claude_code | Claude Code | ~/.claude/skills |
| qoder | Qoder | ~/.qoder/skills |
| cursor | Cursor | ~/.cursor/skills |
| hermes | Hermes | ~/.hermes/skills |
| trae_cn | TRAE CN | ~/.trae-cn/skills |
| copilot | GitHub Copilot | ~/.copilot/skills |
| windsurf | Windsurf | ~/.codeium/windsurf/skills |
| ... | ... | ... |

---

## 七、对比 skills-manager

| 功能 | skills-manager | skills_sync |
|------|---------------|-------------|
| 技术栈 | Node.js CLI + Web UI | Python + PowerShell + JS |
| 中央技能库 | ✅ | ✅ |
| Preset 预设 | ✅ (apply 一次性复制) | ✅ (active_presets 持续管理) |
| Global Workspace | ✅ | ✅ |
| Project Workspace | ✅ | ✅ |
| 多 Agent 自动发现 | ✅ | ✅ (23+ agents) |
| Junction 模式 | ❌ | ✅ (Windows 免管理员) |
| Symlink 模式 | ✅ | ✅ |
| Copy 模式 | ✅ | ✅ |
| 市场浏览 | ✅ (skills.sh) | ❌ |
| Git 备份 | ✅ | ❌ |
| 回收站 | ✅ | ❌ |
| Enable/Disable | ✅ (重命名 SKILL.md) | ❌ |
