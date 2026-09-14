---
name: code-puller
description: >
  从 Gerrit 拉取代码到本地工作区。支持单仓库 git clone 和全平台 repo sync。
  自动检测 F:\05_Code 下是否已有代码，已有则增量更新（git fetch）。
  在当前项目目录创建 CODE_INDEX.md 和快捷方式索引，并在 Bug 工作区同步创建代码 junction。
  SSH 失败时自动执行三级诊断（环境扫描→网络连通性→深度诊断）。
  用户说"拉代码"、"clone 代码"、"拉取 Gerrit"、"下载仓库"、"repo sync"、"同步代码"时触发。
version: 1.0.0
---

# Code Puller — Gerrit 代码拉取

## 何时使用

### 手动触发
- 用户说"拉取 xxx 仓库代码"、"clone Gerrit 代码"
- 用户说"帮我拉一下 <repo>"、"下载 <branch> 的代码"
- 用户说"repo init / repo sync"、"同步平台代码"

### 自动化联动
- bug-core 分析 Bug 时，发现需要源码 → 自动关联本 skill
- 其他 skill 需要访问源码 → 通过描述触发 AI 判断并调用本 skill 的工作流

## 核心参数

| 参数 | 必填 | 来源 | 示例 |
|------|------|------|------|
| `repo_path` | ✅ | 用户输入 / Bug Component 推导 | `bsp/bootloader/edk2` |
| `branch` | ⚠️ | 用户输入 / Bugzilla 描述 / `git ls-remote` | `sprdroid15_vnd_main` |
| `gerrit_host` | ❌ | 默认 `gerrit.unisoc.com` | `gerrit.unisoc.com` |
| `target_root` | ❌ | 默认 `F:\05_Code` | `F:\05_Code` |

## 目标路径规则

```
F:\05_Code\<git_branch>\<repo_name>\
```

> ⚠️ **关键规则**：`<git_branch>` 必须是实际 `git clone -b` 时使用的分支名，**不是** `cf_base_on_ver` 的值。
> 两者可能不同：`cf_base_on_ver` = `SPRDROID13_VND_MAIN_W25.25.5_P1`，但实际 git 分支 = `sprdroid13_vnd_main_r00`。

示例：
- `F:\05_Code\sprdroid13_vnd_main_r00\kernel\`
- `F:\05_Code\sprdroid15_vnd_main\edk2\`
- `F:\05_Code\sprdroid17_vnd_dev_bringup_l8p\edk2\`

同一仓库不同分支在不同目录下并存，互不干扰。

## 完整工作流

### 阶段 0：参数收集

1. **提取 repo_path**：从用户输入识别 Gerrit 仓库路径
   - 用户明确说 "edk2" → 需要进一步确认完整路径
   - 用户说 "bsp/bootloader/edk2" → 直接使用
   - 如果 Bug 信息中有 Component（如 `BSP_Power_Deep/Light/DVFS`），参考 `references/gerrit_servers.md` 的 **Component → Repo 优先级映射**：
     - **Power/PMIC/Charger/USB 等驱动类**：优先 `kernel/linux`，其次 `bsp/bootloader/edk2`
     - **Bootloader 类**：优先 `bsp/bootloader/edk2`，其次 `kernel/linux`

2. **确定 branch**（优先级从高到低）：
   - **0: 查 Bug 字段** → 如果联动 bug-core，直接从 Bug 摘要中提取 `Base On Version`（即 `cf_base_on_ver` 字段），这是最准确的客户分支名
   - **C: 查上下文** → 检查当前对话/Bug 信息中的软件版本号（如 `SPRDROID16_...`、`sprdroid15_...`），参考 `references/branch_guide.md` 的 Android→sprdroid 版本映射
   - **B: 查远程** → 如果 repo 路径已知但分支不确定，先 `git ls-remote --heads ssh://<user>@<host>:29418/<repo>` 列出所有分支，展示给用户选择
   - **A: 问用户** → 以上都无法确定时，直接问用户要哪个分支

3. **确定目标目录**：`F:\05_Code\<git_branch>\<repo_name>\`
   - `git_branch` = 实际 `git clone -b` 使用的分支名（如 `sprdroid13_vnd_main_r00`），**不是** `cf_base_on_ver`
   - `repo_name` 取 repo_path 最后一段（如 `kernel/common` → `common`，但建议用 `kernel`）
   - 如果分支名含特殊字符，做安全替换（`/` → `_`）

### 阶段 1：SSH 连接诊断

**在尝试任何 git 操作前，先执行 Tier 1 快速诊断。** 详细诊断流程见 `references/diagnostic_guide.md`。

#### Tier 1 — 环境扫描（秒级，无网络开销）

按顺序执行以下检查，**每步完成后立即判断是否命中已知问题**：

```bash
# 1. 检测当前 Shell 类型
echo $SHELL
# 判断：/usr/bin/bash → Git Bash；/bin/sh → MSYS2

# 2. 检测 ~/.ssh 实际解析路径
ls -la ~/.ssh/
# 关键：看路径是否包含 "MOBAXT~1" 或 "DOCUME~1"
# 如果包含 → 命中 MobaXterm SSH 路径冲突问题
# → 立即跳转到 references/known_issues.md#mobaxterm-ssh-path

# 3. 检查是否存在多套 SSH 环境
ls -la "$USERPROFILE/.ssh/" 2>/dev/null || ls -la "/c/Users/$USER/.ssh/" 2>/dev/null
# 对比第2步结果，如果路径不同 → 存在多套 SSH 环境

# 4. 列出所有 SSH key 及其指纹
for f in ~/.ssh/id_*; do
  case "$f" in *.pub) continue ;; esac
  echo "=== Key: $f ==="
  ssh-keygen -lf "$f" 2>/dev/null
done
# 记录所有 key 的指纹，后续诊断会用到
```

**如果 Tier 1 命中已知问题 → 直接输出诊断结论，跳到阶段 2。**
**如果 Tier 1 无结论 → 进入 Tier 2。**

#### Tier 2 — 网络连通性（~10s）

```bash
# 5. DNS 解析
nslookup gerrit.unisoc.com 2>&1
# 预期: 10.29.57.243

# 6. TCP 端口连通性
timeout 5 bash -c "echo >/dev/tcp/gerrit.unisoc.com/29418" 2>&1
# 或: nc -z -w3 gerrit.unisoc.com 29418

# 7. 简短 SSH 握手
ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no \
    -p 29418 xianjun.zeng@gerrit.unisoc.com 2>&1
# 看输出：
#   "Permission denied (publickey)" → 认证失败，需要 Tier 3
#   "gerrit: " 或其他欢迎信息 → SSH 认证成功
#   "Connection refused" / timeout → 网络问题，提示用户检查 VPN
```

**如果 SSH 握手成功 → 跳过 Tier 3，直接进入阶段 2。**
**如果 "Permission denied" → 进入 Tier 3。**

#### Tier 3 — 深度诊断（~30s，仅 Tier 2 认证失败时）

```bash
# 8. 完整 SSH 详细日志
ssh -vvv -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
    -p 29418 xianjun.zeng@gerrit.unisoc.com 2>&1 | tail -80

# 自动解析关键行：
#   "Offering public key: <path> RSA SHA256:<fingerprint>"
#     → 确认发送了哪个 key
#   "Server accepts key" / "Accepted publickey"
#     → 服务器接受，认证成功
#   "Permission denied (publickey)"
#     → 服务器拒绝所有 key
#   "Authentications that can continue: publickey,password"
#     → 服务器支持的认证方式列表
```

**诊断输出格式**：

```
=== SSH 诊断结果 ===
Shell: Git Bash
SSH 路径: /c/Users/.../MOBAXT~1/home/.ssh/  ← MobaXterm 路径
⚠️ 命中已知问题: MobaXterm SSH 路径冲突

本地密钥指纹:
  ~/.ssh/id_rsa: SHA256:TuGNLrCjsd1nyLv247emEjxTzUMegL1oMqzapQ2bV18

建议:
1. 检查 Gerrit 网页 Settings → SSH Keys 中注册的公钥指纹是否匹配
2. 如果使用 MobaXterm，确认 Gerrit 上注册的是 MobaXterm 的 key
3. 参考: https://gerrit.unisoc.com/gerrit/settings/#SSHKeys
```

### 阶段 2：检查本地已有代码

```bash
# 检查目标目录是否存在
if [ -d "F:/05_Code/<branch>/<repo_name>" ]; then
  echo "目录已存在，检查 git 状态..."
  cd "F:/05_Code/<branch>/<repo_name>"
  git status --short
  git remote -v
fi
```

**如果目录已存在**：
- 无本地修改 → `git fetch origin` + `git checkout <branch>` + `git reset --hard origin/<branch>`
- 有本地修改 → **警告用户**，展示修改的文件列表，让用户决定：
  - `y` = 放弃本地修改，强制更新
  - `n` = 保留本地修改，不更新
  - `s` = stash 本地修改后再更新

### 阶段 3：拉取代码

#### 单仓库模式（git clone）

```bash
cd "F:/05_Code"
mkdir -p "<branch>"
cd "<branch>"

git clone \
  "ssh://xianjun.zeng@gerrit.unisoc.com:29418/<repo_path>" \
  -b "<branch>" \
  "<repo_name>" 2>&1
```

**如果 clone 失败**：
- 分支名错误（`Remote branch refs/heads/xxx not found`）→ 执行 `git ls-remote --heads` 列出可用分支，让用户选择
- 仓库路径错误（`Repository not found`）→ 执行 `ssh -p 29418 user@gerrit.unisoc.com gerrit ls-projects` 搜索相似仓库名
- 认证失败 → 回到阶段 1 的 Tier 3 深度诊断

#### Repo 模式（repo sync）

```bash
mkdir -p "F:/05_Code/<branch>"
cd "F:/05_Code/<branch>"

repo init -u "ssh://xianjun.zeng@gerrit.unisoc.com:29418/<manifest_repo>" \
    -b "<branch>" -m <manifest_xml> 2>&1

# 智能重试：最多 3 次
for i in 1 2 3; do
  echo "=== repo sync 第 $i 次尝试 ==="
  repo sync -j4 2>&1 | tee "repo_sync_${i}.log"

  # 检查是否有失败
  if grep -q "error: Cannot fetch\|fatal: Couldn't find\|error: .* failed" "repo_sync_${i}.log"; then
    echo "第 $i 次 sync 有失败项"
    if [ $i -lt 3 ]; then
      echo "10秒后自动重试..."
      sleep 10
    else
      echo "=== 3次重试后仍有以下仓库失败 ==="
      grep -E "error:|fatal:" "repo_sync_${i}.log" | sort -u
      echo ""
      echo "请决定: 忽略继续 / 手动修复 / 放弃"
    fi
  else
    echo "repo sync 成功"
    break
  fi
done
```

### 阶段 4：创建索引

代码拉取成功后，在当前项目工作目录和（如果适用）Bug 工作区创建索引和 junction。

> **Junction 命名规则**：使用 `repo_name`（repo_path 最后一段），例如 `edk2`、`kernel`，**不是**完整 repo_path（如 `bsp/bootloader/edk2`）。

1. **更新 CODE_INDEX.md**（项目根目录，不存在则创建）：

```markdown
# Code Index

> 生成时间: 2026-08-11 15:30:00
> 生成工具: code-puller skill

| 仓库 | 分支 | 本地路径 | Gerrit 路径 |
|------|------|---------|-------------|
| edk2 | sprdroid15_vnd_main | F:\05_Code\sprdroid15_vnd_main\edk2 | bsp/bootloader/edk2 |
```

2. **创建 Windows Junction — 项目根目录**（可选，对当前正在使用的仓库）：

```powershell
# 在项目根目录下创建 junction
cmd /c mklink /J "edk2" "F:\05_Code\sprdroid15_vnd_main\edk2"
```

Junction 创建后，项目内可以直接 `cd edk2` 访问代码，对 Git Bash 透明。

3. **创建 Windows Junction — Bug 工作区（如果存在）**：

   如果当前对话上下文中有已知的 Bug 工作区路径，也在此目录下创建 junction，使开发者可以直接 `cd` 进入 Bug 工作区访问代码。

   Bug 工作区路径格式：`E:\08_Bug\CQ\_<BugID>_<Platform>_<IssueType>\`

   判定方式（按优先级）：
   - 检查对话上下文中是否有已知的 Bug 工作区路径（如 `E:\08_Bug\CQ\_3507385_UMS9230E_Power\`）
   - 检查当前项目目录是否在 Bug 工作区内（路径包含 `E:\08_Bug\CQ\_`）
   - 如果通过 bug-core 联动进入，从 bug-core 的上下文提取 Bug 工作区路径

   ```powershell
   # 在 Bug 工作区下创建 junction
   cmd /c mklink /J "E:\08_Bug\CQ\_<BugID>_<Platform>_<IssueType>\<repo_name>" "F:\05_Code\<branch>\<repo_name>"
   ```

   示例：`cmd /c mklink /J "E:\08_Bug\CQ\_3507385_UMS9230E_Power\edk2" "F:\05_Code\sprdroid15_vnd_main\edk2"`

4. **更新 Bug 工作区的 `材料索引.md`（如果存在）**：

   如果 Bug 工作区存在 `材料索引.md` 文件，读取其内容，找到代码文件路径相关章节，在其中追加 junction 路径说明，方便开发者直接在 Bug 工作区中通过 junction 访问代码。

   ```markdown
   ## 代码文件路径

   - 代码位置：`F:\05_Code\<branch>\<repo_name>`
   - Bug 工作区 junction：`<repo_name>\` （在 Bug 工作区下可直接 `cd <repo_name>` 访问）
   - Gerrit 路径：`<repo_path>`
   ```

   注意：追加时不要删除 `材料索引.md` 中已有的其他内容。

## 诊断知识库

已知环境问题按优先级排列，每次诊断先检查这些。详见 `references/known_issues.md`。

## 关键文件

| 文件 | 作用 |
|------|------|
| `SKILL.md` | 本文件，完整工作流 |
| `references/known_issues.md` | 已知环境问题清单（可积累，Tier 1 快速命中） |
| `references/gerrit_servers.md` | Gerrit 服务器配置（地址、端口、认证方式） |
| `references/branch_guide.md` | 平台→软件版本→分支的查询指引 |
| `scripts/create_shortcut.py` | 创建代码目录快捷方式到当前项目 |