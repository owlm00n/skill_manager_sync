# Gerrit 服务器配置

## 主 Gerrit 服务器

| 配置项 | 值 |
|--------|-----|
| 主机名 | `gerrit.unisoc.com` |
| SSH 端口 | `29418` |
| SSH 用户 | `xianjun.zeng` |
| SSH 完整地址 | `ssh://xianjun.zeng@gerrit.unisoc.com:29418/<repo_path>` |
| Web 地址 | `https://gerrit.unisoc.com/gerrit/` |
| SSH Keys 管理 | `https://gerrit.unisoc.com/gerrit/settings/#SSHKeys` |
| IP 地址 | `10.29.57.243` |

## 认证方式

### SSH（推荐）

- 使用 SSH 公钥认证
- 公钥需在 Gerrit 网页 Settings → SSH Keys 中注册
- 注意 MobaXterm 路径冲突问题（见 `known_issues.md`）

### HTTPS（备用）

- 使用 HTTP Basic Auth
- 用户名：`xianjun.zeng`
- 密码：HTTP 密码（在 Gerrit Settings → HTTP Password 中生成）
- 地址格式：`https://gerrit.unisoc.com/gerrit/a/<repo_path>`

## Component → Repo 优先级映射

**当从 Bug Component 确定代码仓库时，按以下优先级拉取：**

| Bug Component | 优先级 1 | 优先级 2 | 说明 |
|--------------|---------|---------|------|
| BSP_Power_Deep/Light/DVFS | `kernel/common` | `bsp/bootloader/edk2` | 功耗/休眠优先查 kernel |
| BSP_PMIC | `kernel/common` | `bsp/bootloader/edk2` | PMIC 驱动优先在 kernel |
| BSP_Charger | `kernel/common` | `bsp/charger` | 充电驱动主要在 kernel |
| BSP_Bootloader | `bsp/bootloader/edk2` | `kernel/common` | 引导程序优先 bootloader |
| BSP_USB | `kernel/common` | `bsp/usb` | USB 驱动主要在 kernel |
| BSP_Kernel | `kernel/common` | — | 仅 kernel |
| System_Framework | `system/framework` | — | 仅 framework |
| Vendor_HAL | `vendor/hal` | — | 仅 HAL |

### 优先级规则

1. **Power/PMIC/Charger/USB 等驱动类组件**：优先 `kernel/linux`，其次 `bsp/bootloader/edk2`
2. **Bootloader 组件**：优先 `bsp/bootloader/edk2`，其次 `kernel/linux`
3. **纯应用层组件**：只拉对应仓库

### 拉取流程

```
1. 从 Bug Component 查上表 → 确定优先级
2. 先拉优先级 1 的仓库（kernel/linux 或 bsp/bootloader/edk2）
3. 如果优先级 1 的仓库中找不到相关代码 → 再拉优先级 2
4. 如果两个仓库都找不到 → 用 gerrit ls-projects 搜索
```

## 常见仓库映射

| 组件/Bug Component | Gerrit 路径 | 说明 |
|-------------------|------------|------|
| BSP_Bootloader | `bsp/bootloader/edk2` | 引导程序（UEFI/EDK2） |
| BSP_Kernel | `kernel/common` | Linux 内核（通用仓库，推荐） |
| BSP_Kernel (5.4) | `code/android/bsp/kernel5.4/kernel5.4` | Linux 内核（kernel 5.4） |
| BSP_Kernel (5.15) | `bsp/kernel/kernel5.15` | Linux 内核（kernel 5.15） |
| BSP_Kernel (his) | `his_unisoc/kernel` | Linux 内核（his_unisoc） |
| BSP_PMIC | `kernel/common` | PMIC 驱动（kernel 侧） |
| BSP_PMIC (edk2) | `bsp/bootloader/edk2` | PMIC 初始化（bootloader 侧） |
| BSP_Charger | `kernel/common` | 充电管理（kernel 侧） |
| BSP_Charger (edk2) | `bsp/bootloader/edk2` | 充电初始化（bootloader 侧） |
| BSP_USB | `kernel/common` | USB 驱动 |
| System_Framework | `system/framework` | 系统框架 |
| Vendor_HAL | `vendor/hal` | HAL 层 |

> 此表持续扩充。从 Bug 的 Component 字段可反查对应仓库路径。

## 项目列表查询

```bash
# 列出所有可见项目
ssh -p 29418 xianjun.zeng@gerrit.unisoc.com gerrit ls-projects

# 搜索特定项目
ssh -p 29418 xianjun.zeng@gerrit.unisoc.com gerrit ls-projects | grep -i "edk2"
ssh -p 29418 xianjun.zeng@gerrit.unisoc.com gerrit ls-projects | grep -i "kernel"
```

## Repo Manifest 信息

| 平台 | Manifest 仓库 | 常用分支 |
|------|-------------|---------|
| Android 13 Vendor | `platform/manifest` | `SPRDROID13_VND_MAIN_W25.25.5_P1` |
| Android 15 Vendor | `platform/manifest` | `sprdroid15_vnd_main` |
| Android 16 System | `platform/manifest` | `SPRDROID16_SYS_MAIN` |
| Android 16 Vendor Bringup | `platform/manifest` | `sprdroid17_vnd_dev_bringup_l8p` |