---
name: skill-creator
description: 统一在中央仓库创建新 skill 的约定与流程。当用户要求创建/新建/添加一个 skill 时使用本技能，强制写入中央仓库 d:\06_Project\skills_sync\skills\ 而不是各 agent 自己的目录，避免管理混乱。
---

# Skill Creator (中央仓库统一创建约定)

本技能约束所有 agent 在**创建新 skill** 时遵守统一路径与流程，避免 skill 散落在 `~/.claude/skills/`、`<cwd>/.claude/skills/`、`~/.trae-cn/skills/` 等各 agent 私有目录导致管理混乱。

## 核心约定（必读）

1. **唯一写入位置**：新 skill **必须**创建在中央仓库：
   ```
   d:\06_Project\skills_sync\skills\<skill-name>\SKILL.md
   ```
   等价于 `~/.claude/skills/<skill-name>/` 在 sync 后通过 junction 指向中央仓库。

2. **禁止就地创建**：不要直接在 `~/.claude/skills/`、`~/.trae-cn/skills/`、`~/.hermes/skills/`、`<cwd>/.claude/skills/` 等 agent 目录里 `mkdir + Write SKILL.md`。这些目录由 `sync.ps1` 统一管理，就地创建会被同步逻辑覆盖或视为 stale 而清理。

3. **目录名 = 内部标识**：用 `s.dir`（目录名）作为内部 ID，frontmatter 的 `name:` 字段可以不同但建议与目录名一致，避免删除时找不到。

## 创建流程

### 步骤 1：在中央仓库创建目录与模板

调用中央仓库提供的创建 API（推荐）：

```bash
curl -X POST http://127.0.0.1:8780/api/skills/create \
  -H "Content-Type: application/json" \
  -d '{"name": "my-skill", "description": "这个 skill 做什么"}'
```

或等价的 PowerShell（当 Web UI 未启动时）：

```powershell
cd d:\06_Project\skills_sync
.\add-skill.ps1 -Name "my-skill" -Description "这个 skill 做什么"
```

两种方式都会在 `d:\06_Project\skills_sync\skills\my-skill\SKILL.md` 生成带 frontmatter 的模板。

### 步骤 2：编辑 SKILL.md 内容

打开 `d:\06_Project\skills_sync\skills\my-skill\SKILL.md`，按照下文的「SKILL.md 规范」填写。可附 `references/`、`scripts/`、`prompts/` 等子目录存放支持文件。

### 步骤 3：加入 preset（必须）

新 skill 必须归入某个 preset 才会被分发到 agent。未归属任何 preset 的 skill 仅存在于中央仓库，不会被同步。

```bash
curl -X POST http://127.0.0.1:8780/api/presets/<preset-name>/add-skill \
  -H "Content-Type: application/json" \
  -d '{"skill": "my-skill"}'
```

可用 preset（按场景选择）：
- `universal` — 所有 agent 通用基础
- `debug-toolkit` — Bug 调试工具
- `protocol` — USB/PD 协议分析
- `bug-full` — Bug 全流程
- `cc-management` — CC 专属管理工具
- `slides` — PPT/幻灯片
- `knowledge` — 知识库/外部集成

### 步骤 4：同步到各 agent

```bash
curl -X POST http://127.0.0.1:8780/api/sync \
  -H "Content-Type: application/json" \
  -d '{"mode": "junction"}'
```

或：

```powershell
cd d:\06_Project\skills_sync
.\sync.ps1
```

sync 完成后，所有配置了的 agent 目录会通过 junction/symlink 指向中央仓库的 `my-skill/`。

## SKILL.md 规范

```markdown
---
name: my-skill
description: 一句话说明做什么、何时触发。Claude 通过这句话判断是否自动加载，越具体越好。
---

# My Skill

## 何时使用
- 触发场景列表

## 执行步骤
1. ...
2. ...

## 支持文件
- references/xxx.md — 仅在需要时才被 Claude 读取（渐进式披露）
- scripts/xxx.py — 可执行脚本
```

**frontmatter 必填字段**：
- `name`：skill 标识，建议与目录名一致
- `description`：触发描述，写明做什么 + 何时用

**可选字段**：
- `allowed-tools`：限制可用工具，如 `allowed-tools: WebSearch, Bash`
- `disable-model-invocation: true`：禁止 AI 自动调用，只能 `/skill-name` 手动触发

## 命名约定

- 目录名使用小写 + 连字符：`my-skill`、`bug-core`、`log-analyzer`
- 不要用空格、下划线、大写（除非与外部生态对齐，如 `Powerpoint-PPTX`）
- 名称冲突时优先重命名新 skill，避免覆盖

## 常见错误

| 错误 | 后果 | 正确做法 |
|---|---|---|
| 在 `~/.claude/skills/` 就地 mkdir | sync 后被识别为 stale 而删除 | 写入中央仓库 `d:\06_Project\skills_sync\skills\` |
| 创建后不加入任何 preset | skill 不会被同步到任何 agent | 创建后必须加入对应 preset |
| frontmatter name 与目录名不一致 | 删除时找不到目标 | 保持 name = 目录名 |
| description 写「帮助用户」 | Claude 无法自动触发 | 写明做什么 + 何时触发 |
| 不跑 sync 就以为生效 | agent 看不到新 skill | 创建后必须 sync |

## 兜底：reverse-sync

若发现 agent 目录里已有「野生」skill（中央仓库没有的），可触发反向同步回收：

```bash
curl -X POST http://127.0.0.1:8780/api/skills/reverse-sync \
  -H "Content-Type: application/json" \
  -d '{}'
```

会扫描所有配置的 agent 目录，把中央仓库缺失的 skill 复制回 `d:\06_Project\skills_sync\skills\`，然后再次 sync 统一分发。

## 相关技能

- `skill-manager`：管理已加载 skill 的启用/禁用/编辑/删除（操作 `~/.claude/skills` 等 agent 目录）
- `hook-manager`：管理 Claude Code hooks
- `find-skills`：从外部生态搜索并安装 skill
