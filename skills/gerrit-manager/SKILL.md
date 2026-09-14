---
name: gerrit-manager
description: >
  Gerrit 提交全流程管理 — commit message 规范 hook（Bug ID + 结构化字段）、
  pre-push 确认拦截、SSH 双域配置、git push 工作流、patch diff 下载。
  覆盖从 Gerrit patch 拉取到本地 git commit 再到 Gerrit push 的完整链路。
  用户说"提交规范"、"Gerrit hook"、"SSH 配置"、"push 到 Gerrit"、"提交格式"、
  "拉patch"、"下载diff"、"gerrit patch"时触发。
version: 2.0.0
---

# Gerrit Manager — Gerrit 提交管理

## 概述

管理 Gerrit 代码提交的完整链路，包含四大功能：

1. **Commit Message Hook** — 结构化模板 + Bug ID 校验 + Change-Id 自动生成
2. **Pre-Push Hook** — push 前完整展示 commit 信息 + 交互式确认
3. **SSH 双域配置** — `gerrit.unisoc.com`（内网）+ `exgerrit.unisoc.com`（外网）
4. **Push 工作流** — 正确的 Gerrit push 命令和分支映射

> **格式强制机制**：Gerrit 服务端 `sprd_commit_monitor` 机器人自动对不规范的 commit message 打 -2 拒绝。本 skill 的 hook 在客户端提前校验，确保 push 前格式就符合规范，避免被服务端拒绝。

## 何时使用

### 手动触发
- 用户说"配置 Gerrit 提交 hook"、"安装 commit-msg hook"
- 用户说"设置 SSH 双域"、"配置 Gerrit SSH"
- 用户说"push 到 Gerrit"、"提交代码到 Gerrit"
- 用户说"提交格式不对"、"commit message 规范"
- 用户说"gerrit 环境配置"、"gerrit 初始化"
- 用户说"拉 Gerrit patch"、"下载 diff"

### 自动化联动
- 其他 skill 需要提交代码到 Gerrit → 通过描述触发 AI 判断并调用本 skill
- EAI 开发指南中的 Gerrit 提交流程 → 参考本 skill 的 hook 和 push 规范

## 功能一：Commit Message Hook

### Hook 概述

单文件 POSIX sh 脚本，部署为 `.git/hooks/commit-msg`，**完全替代**标准 Gerrit commit-msg hook。

**三种工作模式：**

| 模式 | 触发条件 | 行为 |
|------|---------|------|
| **模板模式** | 提交信息为空（只有注释） | 生成完整结构化模板，预填 Bug ID（从分支名提取） |
| **校验模式** | 提交信息非空 | 7 项强制校验 + 2 项警告 |
| **跳过模式** | merge/squash/amend | 只添加 Change-Id + trailer，跳过校验 |

### Commit Message 格式

```
Bug #<7位数字> <project>: <tag>: <描述>

[root cause  ]:<填入根本原因>
[changes     ]:<填入改动内容>
[side effects]:<填入副作用，无则填 no>
[self test   ]:<自测结果，yes/no>
[download normally]:<下载是否正常，yes/no/NA>
[power on/off normally]:<开关机是否正常，yes/no/NA>
[do common repository/branch inspection]:<仓库分支检查结果，yes/no/NA>
[is there dependence]:<是否有依赖，no 或填写依赖>
[confirm dependent commit]:<确认依赖提交，no 或填写 commit>
[board]:<板卡名称，NA>
[test case]:<测试用例描述>
[reviewers]:<评审人>

<详细描述>
- <改动点1>
- <改动点2>

测试结果：
- <测试结果1>
- <测试结果2>

commit_template_version:v1
Signed-off-by: <name> <email>
Change-Id: I...（自动生成）
```

**示例：**

```
Bug #3502855 EAI-cuijian: feat: Add smart_create_bug skill

[root cause  ]:need a skill to create bug quickly from CLI
[changes     ]:add smart_create_bug skill with interactive prompts
[side effects]:no
[self test   ]:yes
[download normally]:yes
[power on/off normally]:yes
[do common repository/branch inspection]:yes
[is there dependence]:no
[confirm dependent commit]:no
[board]:NA
[test case]:tested with agent task workflow
[reviewers]:cuijian

- Add smart_create_bug skill under EAI/employees/cuijian/skills/
- Support interactive Bug ID input
- Auto-fill template fields

测试结果：
- Skill creates bug successfully via Bugzilla API
- All validation checks passed

commit_template_version:v1
Signed-off-by: xianjun.zeng <xianjun.zeng@unisoc.com>
Change-Id: I87edb59e...
```

### Bug ID 获取

Bug ID 从 **分支名** 自动提取。支持的分支名格式：

| 分支名 | 提取结果 |
|--------|---------|
| `bug/3502855` | `3502855` |
| `fix/3502855-fix-crash` | `3502855` |
| `feature/3502855-new-api` | `3502855` |
| `3502855` | `3502855` |

**规则**：取分支名中第一个恰好 7 位的数字串。如果分支名中没有 7 位数字，hook 模板中会标记 `<Bug #7位数字>` 提示手动填写。

**调试用途**：可以使用 `7777777` 作为调试 Bug ID。

**独立脚本**：`scripts/extract_bug_id.sh` 可单独调用：

```bash
# 从分支名提取
sh scripts/extract_bug_id.sh

# 提取不到时交互式输入
sh scripts/extract_bug_id.sh --interactive

# 静默模式（只输出 Bug ID）
sh scripts/extract_bug_id.sh --quiet
```

### 校验规则

| 级别 | 规则 | 说明 |
|:----:|------|------|
| ❌ 强制 | 首行必须以 `Bug #` 开头，后跟 7 位数字 | 不满足则拒绝提交 |
| ❌ 强制 | 必须包含 `[root cause  ]` 字段 | 不满足则拒绝提交 |
| ❌ 强制 | 必须包含 `[changes     ]` 字段 | 不满足则拒绝提交 |
| ❌ 强制 | 必须包含 `[self test   ]` 字段 | 不满足则拒绝提交 |
| ❌ 强制 | 必须包含 `commit_template_version:v1` | 自动添加 |
| ❌ 强制 | 必须包含 `Signed-off-by:` | 自动添加 |
| ❌ 强制 | 必须包含 `Change-Id:` | 自动添加 |
| ⚠️ 警告 | 描述长度 ≥ 5 字符 | 建议修正，不阻止提交 |
| ⚠️ 警告 | 首行 ≤ 72 字符 | 建议修正，不阻止提交 |

## 功能二：Pre-Push Hook

### 概述

Pre-push hook 在 `git push` 执行前拦截，展示完整提交信息后要求用户确认。

**交互流程：**

```
git push
  → pre-push hook 拦截
  → 显示 Remote 信息
  → 显示完整 commit message
  → 显示改动文件列表 (git diff --stat)
  → 显示 diff 摘要 (git diff --shortstat)
  → 提示: "确认 push？[y/N] (30秒超时默认取消)"
  → y → 继续 push
  → N/超时/Ctrl+C → 取消 push
```

### 行为规则

| 输入 | 结果 |
|------|------|
| `y` / `Y` | ✅ 继续 push |
| 任何其他输入 | ❌ 取消 push |
| 30 秒超时 | ❌ 取消 push（默认安全） |
| Ctrl+C | ❌ 取消 push |

## 功能三：SSH 双域配置

### 背景

展锐有两个 Gerrit 服务器，使用**同一对 SSH 密钥**：

| 服务器 | 域名 | SSH 端口 | 用途 |
|--------|------|:--------:|------|
| 内网 Gerrit | `gerrit.unisoc.com` | 29418 | 内部代码评审 |
| 外网 Gerrit | `exgerrit.unisoc.com` | 29418 | 低密级代码外网操作 |

### 快速配置

```bash
# 运行 SSH 配置脚本
sh D:/06_Project/skills_sync/skills/gerrit-manager/scripts/ssh_setup.sh

# 或指定用户
sh D:/06_Project/skills_sync/skills/gerrit-manager/scripts/ssh_setup.sh --user <username>
```

### SSH 密钥注册

确保公钥已在两个 Gerrit 注册：

| Gerrit | SSH Keys 管理页面 |
|--------|------------------|
| 内网 | https://gerrit.unisoc.com/gerrit/settings/#SSHKeys |
| 外网 | https://exgerrit.unisoc.com/gerrit/settings/#SSHKeys |

```bash
# 查看本地公钥
cat ~/.ssh/id_rsa.pub

# 验证连接
ssh -T -p 29418 xianjun.zeng@gerrit.unisoc.com
ssh -T -p 29418 xianjun.zeng@exgerrit.unisoc.com
# 预期输出: "gerrit: " 开头的欢迎信息
```

## 功能四：Push 工作流

### 基本 Push 命令

```bash
# 推送到内网 Gerrit
git push ssh://xianjun.zeng@gerrit.unisoc.com:29418/<repo_path> \
    HEAD:refs/for/<branch>

# 推送到外网 Gerrit（低密级代码）
git push ssh://xianjun.zeng@exgerrit.unisoc.com:29418/<repo_path> \
    HEAD:refs/for/<branch>
```

### Push 前检查清单

1. ✅ **Bug ID**：首行包含 `Bug #<7位数字>`
2. ✅ **结构化字段**：`[root cause]`, `[changes]`, `[self test]` 必填
3. ✅ **Change-Id**：已自动生成
4. ✅ **commit-msg hook** 校验通过
5. ✅ **pre-push hook** 已安装，push 前确认
6. ✅ **SSH 配置**：`ssh -T -p 29418` 验证通过
7. ✅ **目标分支**：确认 `refs/for/<branch>`
8. ✅ **目标 Gerrit**：内网 `gerrit` vs 外网 `exgerrit`

### 常见 Push 错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `sprd_commit_monitor -2` | 格式不符合规范 | 确保 commit-msg hook 已安装并通过校验 |
| `Permission denied (publickey)` | SSH 密钥未注册或不匹配 | 检查 SSH Keys 设置 |
| `! [remote rejected] ... (no new changes)` | 没有新的 commit | 确认有新的 commit 再 push |
| `! [remote rejected] ... (change ... closed)` | Change 已合入或关闭 | 重新提交新的 Change-Id |
| `! [remote rejected] ... (missing Change-Id)` | commit-msg hook 未安装 | 安装本 skill 的 hook |
| `fatal: unable to access ... SSL certificate problem` | 使用 HTTPS 而非 SSH | 改用 SSH 协议 |

## 完整工作流

### 阶段 1：环境检查

```bash
# 1. 检查 SSH 配置
cat ~/.ssh/config | grep -A4 "gerrit"

# 2. 验证 SSH 连接
ssh -T -p 29418 xianjun.zeng@gerrit.unisoc.com
ssh -T -p 29418 xianjun.zeng@exgerrit.unisoc.com

# 3. 检查 hook 是否安装
ls -la <repo>/.git/hooks/commit-msg
ls -la <repo>/.git/hooks/pre-push
```

### 阶段 2：安装 Hook（如未安装）

```bash
# 方式 A：单个仓库安装
sh D:/06_Project/skills_sync/skills/gerrit-manager/scripts/install_hooks.sh --repo <repo_path>

# 方式 B：批量安装所有已知仓库
sh D:/06_Project/skills_sync/skills/gerrit-manager/scripts/install_hooks.sh --all
```

### 阶段 3：创建分支（含 Bug ID）

```bash
# 从 Bug ID 创建分支
git checkout -b bug/3502855
```

### 阶段 4：提交代码

```bash
git add <files>
git commit  # hook 自动触发模板/校验
```

### 阶段 5：推送（pre-push 确认）

```bash
git push  # pre-push hook 拦截，展示 commit 信息，要求确认
```

## 安装 Hook

### 方式 A：安装脚本（推荐）

```bash
# 安装到当前仓库
sh D:/06_Project/skills_sync/skills/gerrit-manager/scripts/install_hooks.sh

# 安装到指定仓库
sh D:/06_Project/skills_sync/skills/gerrit-manager/scripts/install_hooks.sh --repo D:/06_Project/ENG_AI

# 批量安装到所有已知仓库
sh D:/06_Project/skills_sync/skills/gerrit-manager/scripts/install_hooks.sh --all

# 检查模式（不实际安装）
sh D:/06_Project/skills_sync/skills/gerrit-manager/scripts/install_hooks.sh --all --dry-run
```

### 方式 B：手动复制

```bash
# 复制 commit-msg hook
cp D:/06_Project/skills_sync/skills/gerrit-manager/hooks/commit-msg \
   <repo_path>/.git/hooks/commit-msg
chmod +x <repo_path>/.git/hooks/commit-msg

# 复制 pre-push hook
cp D:/06_Project/skills_sync/skills/gerrit-manager/hooks/pre-push \
   <repo_path>/.git/hooks/pre-push
chmod +x <repo_path>/.git/hooks/pre-push
```

### 方式 C：Git 模板目录（全局生效）

```bash
# 设置 git 模板目录，新 clone 的仓库自动安装
git config --global init.templateDir ~/.git-template
mkdir -p ~/.git-template/hooks
cp D:/06_Project/skills_sync/skills/gerrit-manager/hooks/commit-msg \
   ~/.git-template/hooks/commit-msg
cp D:/06_Project/skills_sync/skills/gerrit-manager/hooks/pre-push \
   ~/.git-template/hooks/pre-push
```

## 验证 Hook

```bash
# 测试 commit-msg 模板模式（空提交信息）
echo "" > /tmp/test-commit-msg
.git/hooks/commit-msg /tmp/test-commit-msg
cat /tmp/test-commit-msg

# 测试 commit-msg 格式校验（缺少 Bug ID）
echo "feat: test" > /tmp/test-commit-msg
.git/hooks/commit-msg /tmp/test-commit-msg
echo "Exit code: $?"

# 测试 pre-push hook（dry-run 方式）
echo "refs/heads/master 0000000000000000000000000000000000000000 refs/heads/master abc123" | \
    .git/hooks/pre-push origin ssh://xianjun.zeng@exgerrit.unisoc.com:29418/EAI
```

## 关键文件

| 文件 | 作用 |
|------|------|
| `SKILL.md` | 本文件，完整工作流文档 |
| `hooks/commit-msg` | 结构化模板 + Bug ID 校验 + Change-Id 自动生成 |
| `hooks/pre-push` | push 前展示 commit 信息 + 交互式确认 |
| `scripts/install_hooks.sh` | 批量安装 commit-msg + pre-push 到多个仓库 |
| `scripts/extract_bug_id.sh` | 从分支名提取 Bug ID（7 位数字） |
| `scripts/ssh_setup.sh` | SSH 双域配置脚本 |
| `references/commit_format_mechanism.md` | 格式强制机制分析报告（sprd_commit_monitor） |
| `../code-puller/references/gerrit_servers.md` | Gerrit 服务器配置（共享引用） |
| `../code-puller/references/known_issues.md` | SSH 已知问题知识库（共享引用） |

## 依赖

- **Git** ≥ 2.0（支持 `git commit` hook 和 `git push` hook）
- **OpenSSH**（SSH 连接和密钥管理）
- **Bash**（pre-push hook 的 `read -t` 超时功能，非 bash 降级为无超时）

## 注意事项

1. **覆盖标准 hook**：本 hook 完全替代 Gerrit 官方 commit-msg hook，内置 Change-Id 生成逻辑
2. **POSIX sh 兼容**：commit-msg hook 不依赖 bash，在 Git Bash (Windows) 和 Linux 上均可运行
3. **pre-push 需要 Bash**：30 秒超时确认依赖 Bash 的 `read -t`，在 dash/ash 下降级为无超时
4. **Merge/Squash 自动跳过**：merge commit 和 squash commit 只添加 Change-Id，不校验格式
5. **Bug ID 是核心**：没有 Bug ID 的提交会被 `sprd_commit_monitor` 打 -2 拒绝
6. **与 code-puller 互补**：code-puller 拉代码，gerrit-manager 推代码，互不重叠
7. **SSH 密钥共用**：内外网 Gerrit 使用同一对 SSH 密钥，只需配置一次