# open-slide 部署到 Claude Code — 部署记录

## 环境信息

- **日期**: 2026-06-26
- **OS**: Windows 10 Enterprise LTSC 2021
- **Node.js**: v24.14.0
- **pnpm**: 10.17.0（通过 `npm install -g pnpm@10.17.0` 安装）
- **仓库**: `D:\06_Project\open-slide\open-slide`（open-slide monorepo）
- **输出项目**: `D:\06_Project\open-slide\my-slides`（scaffolded 幻灯片项目）

## 什么是 open-slide

open-slide 是一个 **Agent 原生的幻灯片框架**。你用自然语言描述你的演示文稿，你的 Coding Agent（如 Claude Code）负责写 React 代码。open-slide 处理画布、缩放、导航、热更新和演示模式。

- 每张幻灯片渲染在 **1920 × 1080** 固定画布上
- 页面是任意 React 组件，不是受限的 DSL
- 提供 5 个 Claude Code Skills：`create-slide`、`slide-authoring`、`apply-comments`、`create-theme`、`current-slide`

## 部署步骤

### Step 1 — 安装 pnpm（已完成）

```bash
npm install -g pnpm@10.17.0
```

> **注意**: 仓库的 `package.json` 指定 `"packageManager": "pnpm@10.17.0"`，需要匹配版本。

### Step 2 — 安装 Monorepo 依赖（已完成）

```bash
cd D:/06_Project/open-slide/open-slide
pnpm install
```

结果：930 个包安装成功，5 个 workspace 项目（`@open-slide/core`、`@open-slide/cli`、`demo`、`web`、root）。

### Step 3 — 构建所有包（已完成）

```bash
pnpm build
```

构建结果（4/4 成功）：

| 包 | 构建工具 | 耗时 |
|---|---|---|
| `@open-slide/core` | tsdown (rolldown) | ~11.7s |
| `@open-slide/cli` | tsdown (rolldown) | ~0.2s |
| `demo` | Vite | ~34.4s |
| `web` | Next.js | ~39.4s |

### Step 4 — Scaffold 幻灯片项目（已完成）

使用本地构建的 CLI 创建新项目：

```bash
cd D:/06_Project/open-slide/open-slide
node packages/cli/dist/cli.js init "../my-slides" --name "my-slides" --no-install --no-git
```

> `--no-install` 跳过自动安装，之后手动 `pnpm install`。

### Step 5 — 安装幻灯片项目依赖（已完成）

```bash
cd D:/06_Project/open-slide/my-slides
pnpm install
```

安装了 446 个包，包括 `@open-slide/core@1.12.1`、`react@18.3.1`、`vite@5.4.21`。

### Step 6 — 同步 Skills（已完成）

```bash
pnpm sync:skills
```

输出：
```
Synced built-in skills:
  ~ apply-comments (updated)
  ~ create-slide (updated)
  ~ create-theme (updated)
  ~ current-slide (updated)
  ~ slide-authoring (updated)
0 added, 5 updated, 0 unchanged.
```

### Step 7 — 启动 Dev Server（验证通过）

```bash
pnpm dev
```

Dev server 成功启动在 `http://localhost:5173`。

**注意**: 首次启动时提示 "Skills out of date"，运行 `pnpm sync:skills` 后解决。

## 项目结构

```
my-slides/
  .claude/skills/              # Claude Code 技能定义
    apply-comments/SKILL.md     # 应用审查评论
    create-slide/SKILL.md       # 创建新幻灯片
    create-theme/SKILL.md       # 创建/提取主题
    current-slide/SKILL.md      # 当前幻灯片上下文解析
    slide-authoring/SKILL.md    # 幻灯片编写技术参考（35KB）
  .agents/skills/              # Agent 技能定义（与 .claude 内容相同）
    ...（同上 5 个 skill）
  slides/                      # 幻灯片内容目录
    getting-started/index.tsx   # 示例幻灯片
  themes/                      # 主题目录
  assets/                      # 全局资源
  CLAUDE.md → AGENTS.md        # Claude Code 入口
  AGENTS.md                    # Agent 指南（硬规则 + 技能使用说明）
  open-slide.config.ts         # open-slide 配置
  package.json                 # 项目配置
```

## Claude Code Skills 说明

| Skill | 用途 | 触发条件 |
|---|---|---|
| `create-slide` | 创建新演示文稿的工作流（询问范围、结构等） | "make slides about X"、"create a presentation" |
| `slide-authoring` | 编写/编辑幻灯片的技术参考 | 任何 `slides/<id>/` 下的文件编辑 |
| `apply-comments` | 处理 `@slide-comment` 标记并应用修改 | 审查后有标记待处理时 |
| `create-theme` | 创建或提取主题（存为 `themes/<id>.md`） | 创建/修改主题时 |
| `current-slide` | 解析用户在 "当前幻灯片" 或 "这个元素" 的引用 | 用户提到当前页面但未命名时 |

## 使用方式

### 方式一：在幻灯片项目目录中启动 Claude Code

```bash
cd D:/06_Project/open-slide/my-slides
claude
```

进入后 Claude Code 会自动识别 `.claude/skills/` 下的 5 个 skill，可以直接使用：
- `/create-slide` — 创建新幻灯片
- `/slide-authoring` — 查看编写规范
- 等等

### 方式二：从任意目录启动，手动指定项目

```bash
claude --project-dir D:/06_Project/open-slide/my-slides
```

### 创建你的第一套幻灯片

在 Claude Code 中输入：
```
/create-slide
```

然后按提示描述主题、风格、页数等即可。

## 遇到的问题和解决方案

### 问题 1：pnpm 未安装

**现象**: `pnpm: command not found`
**解决**: `npm install -g pnpm@10.17.0`

### 问题 2：`pnpm install` 在错误目录执行

**现象**: `No package.json found in D:\06_Project`
**原因**: 工作目录在 `D:\06_Project`，而非 monorepo 目录
**解决**: `cd "D:/06_Project/open-slide/open-slide" && pnpm install`

### 问题 3：`pnpm approve-builds` 交互式选择失败

**现象**: `Error [ERR_USE_AFTER_CLOSE]: readline was closed`
**原因**: pnpm 的交互式多选在非 TTY 环境下不可用
**影响**: esbuild 等构建脚本未执行，但不影响项目运行（esbuild 预编译的二进制文件已存在）

### 问题 4：Scaffolded 项目的 Skills 过期

**现象**: 启动 `pnpm dev` 时提示 "Skills out of date"
**解决**: 运行 `pnpm sync:skills`

### 问题 5：`--no-install` 后需要手动安装

**说明**: `open-slide init` 的 `--no-install` 跳过依赖安装，之后需要手动 `pnpm install`。这是预期行为。

## 总结

open-slide 已成功部署到 Claude Code。scaffolded 项目位于 `D:\06_Project\open-slide\my-slides`，包含 5 个完整的 Claude Code Skills，dev server 可正常启动。

下一步：在 `my-slides` 目录下启动 Claude Code，使用 `/create-slide` 创建第一套幻灯片。
