# Branch Guide — 平台分支查询指引

## 从 Bug 数据获取分支信息（最重要）

### 优先使用 `cf_base_on_ver`

**SPCSS Bugzilla 的 `cf_base_on_ver` 自定义字段就是客户使用的分支名！**

在联动 bug-core 时，直接从 Bug 摘要中提取 `Base On Version` 字段：

```
bug-core 输出示例:
  Base On Version: SPRDROID13_VND_MAIN_W25.25.5_P1
  Fix On Version: SPRDROID13_VND_MAIN_W25.25.5_P1
  Branch To Merge: SPRDROID13_VND_MAIN_W25.25.5_P1
```

**执行顺序**：
1. 先调用 bug-core 获取 Bug 完整信息
2. 从结果中提取 `base_on_ver` 字段
3. 用 `base_on_ver` 的值作为目标分支名
4. 如果 `base_on_ver` 为空，再按下面的规则推导

### 分支名格式

展锐平台分支命名遵循以下模式：

```
sprdroid<version>_<type>_<branch>[_<suffix>]
```

| 组成部分 | 说明 | 示例 |
|---------|------|------|
| `sprdroid` | 固定前缀（大小写不敏感） | `SPRDROID` / `sprdroid` |
| `<version>` | Android 版本号 | `13`, `15`, `16`, `17` |
| `<type>` | 分支类型 | `VND` (Vendor), `SYS` (System) |
| `<branch>` | 具体分支名 | `MAIN`, `DEV` |
| `[_<suffix>]` | 可选后缀 | `_W25.25.5_P1`, `_bringup_l8p` |

### 常见分支一览

| 软件版本 | 分支名 | 说明 |
|---------|--------|------|
| SPRDROID13_VND | `SPRDROID13_VND_MAIN_W25.25.5_P1` | Android 13 Vendor 主线 |
| SPRDROID15_VND | `sprdroid15_vnd_main` | Android 14 Vendor 主线 |
| SPRDROID16_SYS | `SPRDROID16_SYS_MAIN` | Android 15 System 主线 |
| SPRDROID15_SYS | `sprdroid15_sys_main` | Android 14 System 主线 |
| SPRDROID17_VND | `sprdroid17_vnd_dev_bringup_l8p` | Android 16 Vendor bringup |

## Android → sprdroid 版本映射

**关键映射表**：

| Android 版本 | sprdroid 版本 | 说明 |
|-------------|--------------|------|
| Android 12 | `sprdroid12` | |
| Android 13 | `sprdroid13` | |
| Android 14 | `sprdroid15` | ⚠️ 跳过了 14 |
| Android 15 | `sprdroid16` | |
| Android 16 | `sprdroid17` | |

> ⚠️ **注意**：Android 14 对应 sprdroid15，Android 15 对应 sprdroid16，以此类推。
> sprdroid 版本号 = Android 版本号 + 1（从 Android 14 开始）

## Bringup 分支命名规则

Bringup 分支用于新芯片的初始调试阶段，命名格式：

```
sprdroid<version>_<type>_dev_bringup_<chip_code>
```

示例：
- `sprdroid17_vnd_dev_bringup_l8p` — Android 16 Vendor bringup (chip: l8p)

## Chip Code → 平台映射

| Chip Code | 平台代号 | 芯片型号 | PMIC |
|-----------|---------|---------|------|
| `l8p` | — | — | — |
| `l8` | — | — | — |

> ⚠️ **注意**：chip code 与平台/芯片的对应关系需从实际项目中确认，不要猜测。此表持续补充。

## 从 Bugzilla 推导分支

Bug 描述中可能包含软件版本号，格式如：

```
软件版本: SPRDROID16_SYS_MAIN
SW Version: sprdroid15_vnd_main
```

### 推导规则（优先级从高到低）

1. **从 `cf_base_on_ver` 字段获取**（最准确）：直接使用 Bug 的 `Base On Version` 值
2. **从 Bug 描述文本中搜索** `SPRDROID` 或 `sprdroid` 关键字
3. **从 Bug 平台字段推导**：Platform 字段（如 `UMS9230E, Android 16`）→ 映射到 sprdroid 版本
4. **查远程分支列表**：`git ls-remote --heads` 列出所有分支，按版本号过滤

### 不确定时的处理

如果从 Bug 描述中无法确定分支：
1. 先用 `git ls-remote --heads` 列出远程所有分支
2. 按版本号过滤，展示候选分支
3. 让用户选择

## 查询远程分支

```bash
# 列出 repo 的所有分支
git ls-remote --heads ssh://xianjun.zeng@gerrit.unisoc.com:29418/<repo_path>

# 示例输出：
# 1a2b3c4d... refs/heads/sprdroid15_vnd_main
# 5e6f7g8h... refs/heads/SPRDROID16_SYS_MAIN
# 9i0j1k2l... refs/heads/SPRDROID13_VND_MAIN_W25.25.5_P1
# 1m2n3o4p... refs/heads/sprdroid17_vnd_dev_bringup_l8p
```

## 分支与目录映射

拉取后的本地目录结构：

```
F:\05_Code\
├── SPRDROID13_VND_MAIN_W25.25.5_P1\
│   ├── kernel\
│   ├── edk2\
│   └── ...
├── sprdroid15_vnd_main\
│   ├── edk2\
│   └── ...
├── sprdroid17_vnd_dev_bringup_l8p\
│   ├── edk2\
│   └── ...
```

同一仓库的不同分支在不同目录下，互不干扰。