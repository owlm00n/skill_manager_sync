# Known Issues — SSH 诊断知识库

> 按优先级排列。每次诊断先检查这些，命中则直接输出结论，跳过后续诊断。
> 新发现的问题追加到文件末尾，标注发现日期和触发条件。

---

## 1. MobaXterm SSH 路径冲突

- **发现日期**: 2026-08-11
- **触发条件**: Shell 为 Git Bash（`/usr/bin/bash`），且 `~/.ssh` 解析到 MobaXterm 路径
- **影响范围**: 所有使用 Git Bash 的 SSH 操作

### 问题描述

MobaXterm 自带的 Cygwin/MSYS SSH 环境会在 Git Bash 中覆盖 Windows 原生 SSH 配置路径：

```
Git Bash 中的 ~/.ssh → /c/Users/XIANJU~1.ZEN/DOCUME~1/MOBAXT~1/home/.ssh/
Windows 实际路径     → C:\Users\xianjun.zeng\.ssh\
```

两套路径下的 SSH key 不同，导致：
- 用户在 Gerrit 注册的是 Windows 路径下的公钥
- Git Bash 实际发送的是 MobaXterm 路径下的 key
- 结果：`Permission denied (publickey)` — 指纹不匹配

### 检测方法

```bash
ls -la ~/.ssh/
```

如果输出路径包含 `MOBAXT~1` 或 `DOCUME~1`，即命中此问题。

### 解决方案

**方案 A（推荐）**：在 Gerrit 注册 MobaXterm 路径下的公钥
```bash
cat ~/.ssh/id_rsa.pub
# 复制输出，添加到 https://gerrit.unisoc.com/gerrit/settings/#SSHKeys
```

**方案 B**：强制 Git Bash 使用 Windows 原生 SSH
```bash
# 在 ~/.bashrc 或 ~/.profile 中设置
export HOME="/c/Users/xianjun.zeng"
```

**方案 C**：配置 `~/.ssh/config` 显式指定 key 路径
```
Host gerrit.unisoc.com
    HostName gerrit.unisoc.com
    Port 29418
    User xianjun.zeng
    IdentityFile C:/Users/xianjun.zeng/.ssh/id_rsa
```

### 验证

```bash
ssh -T -p 29418 xianjun.zeng@gerrit.unisoc.com
# 预期输出: "gerrit: " 开头的欢迎信息
```

---

## 2. Windows 保留文件名 `aux` 导致 git checkout 失败

- **发现日期**: 2026-08-12
- **触发条件**: 拉取 Linux kernel 仓库，树中包含 `arch/arm64/boot/dts/sprd/aux/` 目录
- **影响范围**: 所有 Windows 系统上的 kernel 仓库 checkout

### 问题描述

Windows 将 `aux`、`con`、`prn`、`nul` 等列为保留设备名，不允许创建同名文件或目录。Linux kernel 的 `arch/arm64/boot/dts/sprd/aux/` 目录在 Windows 上无法创建，导致 `git clone` / `git checkout` 失败：

```
fatal: cannot create directory at 'arch/arm64/boot/dts/sprd/aux': Invalid argument
```

### 检测方法

```bash
git ls-tree -r HEAD --name-only | grep '/aux/'
# 如果输出非空，即命中此问题
```

### 解决方案

方案：从 git 索引中移除 `aux` 目录后再 checkout

```bash
# 1. 将完整树读入索引
git read-tree HEAD

# 2. 从索引中移除 aux 目录
git rm --cached -r "arch/arm64/boot/dts/sprd/aux"

# 3. 强制 checkout（跳过已移除的 aux）
git checkout-index -a -f
```

### 注意

- `aux` 目录中的文件不会被 checkout，但 `.git` 中仍保留完整历史
- 如需这些文件，在 WSL/Linux 环境上操作
- 当前发现仅 `arch/arm64/boot/dts/sprd/aux/screen_onoff_check.dtsi` 一个文件受影响

---

## 3. Gerrit SshCommandInterceptor 权限拦截

- **发现日期**: 2026-08-12
- **触发条件**: 尝试拉取未授权的 Gerrit 仓库（如 `code/android/bsp/kernel5.4/kernel5.4`）
- **影响范围**: 无权限的仓库拉取操作

### 问题描述

Gerrit 服务端插件 `SshCommandInterceptor` 会拦截未授权用户的 git 操作：

```
Connection closed by remote host.
```

### 解决方案

1. 检查 Gerrit 仓库的实际路径（通过 `ssh -p 29418 user@gerrit.unisoc.com gerrit ls-projects | grep -i kernel`）
2. 尝试替代仓库路径（如 `kernel/common` 替代 `code/android/bsp/kernel5.4/kernel5.4`）
3. 如果仍然被拦截，联系 Gerrit 管理员开通权限

### 已知可用的仓库路径

| 仓库类型 | 可用路径 | 说明 |
|---------|---------|------|
| Kernel | `kernel/common` | ✅ 可拉取（推荐） |
| Kernel 5.4 | `code/android/bsp/kernel5.4/kernel5.4` | ❌ 被拦截 |
| Kernel 5.15 | `bsp/kernel/kernel5.15` | ❌ 被拦截 |
| Kernel (his) | `his_unisoc/kernel` | ❌ 被拦截 |