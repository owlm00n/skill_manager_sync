---
name: ylog-helper
description: Ylog 日志生命周期管理 — 从设备拉取、移除、解压、分析 ylog 日志。Ylog 是展锐内部日志系统，二进制格式存储，需解压后才能看到 kernel log/main log 等。触发词：ylog、拉ylog、ylog pull、ylog rm、清除ylog、解压ylog、ylog分析、/data/ylog
version: "1.0"
tags: [ylog, unisoc, log, ap, debug, decompress]
---

# Ylog Helper — 展锐 Ylog 日志管理

管理展锐平台 Ylog 日志的完整生命周期：拉取、移除、解压、分析。

## 触发条件

- 用户说"ylog"、"拉 ylog"、"pull ylog"、"下载 ylog"
- 用户说"清除 ylog"、"删除 ylog"、"ylog rm"
- 用户说"解压 ylog"、"ylog 分析"、"看 ylog"
- 用户说"ylog 里面有什么"、"ylog 怎么看"
- 识别到 `/data/ylog` 路径操作时自动触发
- 用户说"拉取手机日志"且上下文是展锐平台时

## 前置条件

- ADB 已连接（本 Skill 依赖 adb-helper）
- 设备已 root（`adb root` 可执行）
- 目标设备使用展锐平台（Ylog 机制）

## Ylog 是什么

Ylog 是展锐（Unisoc）平台内部日志系统，日志存储在 `/data/ylog/` 目录下。**不同 Android 版本格式不同**：

### 新版本 Android（blackboxlog 格式）

**当前主流格式**。日志以 tar.gz 压缩包存储，解压后直接是纯文本：

```
/data/ylog/ap/blackboxlog/poweron/
├── 0/
│   └── log_0.tar.gz          ← 解压后: kernel.log + android.log
├── 1/
│   └── log_1.tar.gz          ← 每次开机一个目录
└── N/
    └── log_N.tar.gz
```

每个 `log_N.tar.gz` 包含：
- `kernel.log` — 内核日志（纯文本）
- `android.log` — Android 主日志（纯文本）

**不需要 analyzer.py**，直接 `tar -xzf` 或 Python `tarfile` 解压即可。

### 旧版本 Android（.ylog 二进制格式）

旧版本使用 `.ylog` 后缀的二进制文件，需要 `analyzer.py` 解码：

```
/data/ylog/ap/
├── kernel.ylog           ← 二进制格式（magic: 0x2E2E/0x5A5A/0xB5B5）
├── main.ylog
├── radio.ylog
└── analyzer.py           ← 解码工具
```

**Ylog 二进制格式**（旧版）：

```
┌────────────────────────────────┐
│  FileHeader (magic: 0x2E2E)   │
├────────────────────────────────┤
│  BlockHeader (magic: 0x5A5A)  │
│  ├─ zlib compressed data      │
│  ├─ zlib compressed data      │
│  └─ ...                       │
├────────────────────────────────┤
│  BlockHeader (magic: 0x5A5A)  │
│  └─ ...                       │
├────────────────────────────────┤
│  FileTail (magic: 0xB5B5)     │
└────────────────────────────────┘
```

**解码命令**（旧版）：

```bash
python analyzer.py kernel.ylog    # 输出到当前目录
# 或不带参数，自动搜索当前目录 *.ylog 文件
python analyzer.py
```

解码后输出：`android_main.log`, `android_system.log`, `android_radio.log`, `android_events.log`, `android_crash.log`

### 判断版本

拉取后检查 `/data/ylog/ap/` 目录：
- **有 `blackboxlog/poweron/`** → 新版，直接解压 tar.gz
- **有 `*.ylog` 文件** → 旧版，用 `analyzer.py` 解码
- **有 `analyzer.py` 但没有 `.ylog` 文件** → 新版（analyzer.py 是残留文件）

## 功能清单

### 1. Ylog 拉取

从设备拉取 ylog 日志到本地：

**方式一：拉取 AP 日志（推荐，最常用）**

```bash
mkdir -p <output_dir>
adb pull /data/ylog/ap <output_dir>
```

对应脚本：`F:\CMD\ylog_pull.bat`

**方式二：拉取全部 ylog**

```bash
adb pull /data/ylog <output_dir>
```

对应脚本：`F:\CMD\data_pull - 副本.bat`

**方式三：拉取特定文件**

```bash
adb pull /data/ylog/ap/kernel.log <output_dir>
```

**拉取注意事项**：
- `/data/ylog/ap/` 目录可能很大（数百 MB），确保本地有足够空间
- 拉取前可先用 `adb shell ls -la /data/ylog/ap/` 查看文件大小
- 拉取过程可能较慢，使用 USB 连接比 WiFi 快

### 2. Ylog 清除

清除设备上的 ylog 日志（通常在复现问题前清除旧日志）：

```bash
adb root
adb shell rm -rf /data/ylog/ap/*
```

对应脚本：`F:\CMD\ylog_rm.bat`

**清除注意事项**：
- 需要 root 权限
- 清除后重启设备或不重启均可，取决于测试流程
- 清除后复现问题时，新日志会更干净，便于分析

### 3. Ylog 解压

Ylog 日志为二进制格式，需要使用 `analyzer.py` 解压：

**analyzer.py 获取方式**：
- 通常附带在 ylog 压缩包中
- 或从展锐内部获取

**解压命令**：

```bash
python analyzer.py <input.log> <output_dir>
```

**解压后输出**：
- `kernel.log` → 解压后的文本格式内核日志
- `main.log` → 解压后的主日志
- 其他 `.log` 文件同理

### 4. Ylog 分析流程

拉取后的完整分析流程：

```
1. adb pull /data/ylog/ap → 拉取到本地
2. python analyzer.py kernel.log kernel_decoded/ → 解压
3. 查看解压后的文本日志 → 可配合 log-analyzer Skill 分析
```

**与其他 Skill 联动**：
- 拉取完成后，自动提示用户是否调用 `log-analyzer` 分析解压后的日志
- 如果用户提到"分析 ylog 中的 kernel log"，自动触发分析链路

## 工作流程

### 标准问题复现流程

```
1. 清除旧日志:  ylog_rm → adb shell rm -rf /data/ylog/ap/*
2. 复现问题:    操作设备触发 Bug
3. 拉取日志:    ylog_pull → adb pull /data/ylog/ap <bug_workspace>
4. 解压日志:    python analyzer.py kernel.log 解压/
5. 分析日志:    → 调用 log-analyzer Skill
```

### 典型对话示例

```
用户: 帮我把手机上的 ylog 拉下来看看
AI:
  1. adb root → 获取 root 权限
  2. adb shell ls -la /data/ylog/ap/ → 查看文件列表
  3. adb pull /data/ylog/ap D:\ylog\20260827\ → 拉取日志
  4. 提示: "日志已拉取到 D:\ylog\20260827\，需要解压吗？"
```

## 与其他 Skill 的关系

```
adb-helper (前置依赖)
    │
    ▼
ylog-helper (本 Skill)
    ├── adb pull /data/ylog/ap → 拉取日志
    ├── adb shell rm -rf /data/ylog/ap/* → 清除日志
    ├── python analyzer.py → 解压日志
    │
    └──→ log-analyzer (下游)
         解压后的文本日志交给 log-analyzer 分析
```

## 已知经验

1. **Ylog 不是文本格式**：不要直接用文本编辑器打开 `.log` 文件，会看到乱码
2. **analyzer.py 版本**：不同展锐平台的 analyzer.py 版本可能不同，确保使用正确的版本
3. **日志大小**：`/data/ylog/ap/` 通常 100-500MB，拉取需要时间和空间
4. **kernel log 优先级**：分析问题时，kernel.log 通常是最重要的日志文件
5. **清除后等待**：清除日志后建议等待 3-5 秒再复现问题，确保缓冲区已清空

## 注意事项

1. **空间检查**：拉取前检查本地磁盘空间是否足够
2. **权限**：清除 ylog 需要 root 权限
3. **时间戳**：拉取日志时注意记录复现问题的时间点，便于后续定位
4. **备份**：重要日志在清除前先备份