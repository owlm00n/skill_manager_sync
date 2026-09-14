---
name: bug-workspace
description: Bug工作区创建 & 附件下载 & 坐标 — 自动生成文件夹、.url快捷方式、Bug Z模板、路径历史、快速打开、UNC优先下载附件（rayfile FTP fallback）、结构化评论解析、日志目录列表
version: "3.0"
tags: [bugzilla, workspace, unc, download, shortcut, orchestration, material-acquisition, log-directory, structured-parsing]
---

# Bug工作区

根据Bug信息自动创建工作区——生成文件夹、.url 快捷方式、Bug 摘要文件、Bug Z 模板复制、路径历史管理、快速打开，并通过 **UNC 优先下载**（rayfile FTP fallback）完成附件下载。**v3.0 已合并 bug-logs 全部功能**（结构化评论解析、日志目录列表、附件下载）。

> **bug-logs 已废弃**：所有功能已合并到 bug-workspace，请直接使用 bug-workspace。

## 触发条件

- 用户说"创建工作区"、"下载附件"、"生成下载命令"
- 用户说"给Bug XXX创建工作区"、"下载Bug XXX的日志"
- 用户说"列出日志目录"、"查看日志文件"、"Bug的log在哪"
- 用户查询 unisoc Bug 后需要下载日志附件
- 使用 MCP `bug_workspace` 工具

## ⚠️ AI 操作前置规则（必须遵守）

**在执行任何操作前，必须先完成以下检查，违反将导致错误路径或错误实例：**

### 规则 1: 搜索工作区前先读配置

**禁止硬编码搜索路径。** 查找现有工作区时，必须从配置文件读取 `default_workspace`：

```
1. 读取 config/bugzilla_instances.json → 获取 default_workspace（如 "E:\\08_Bug"）
2. 读取 config/paths.json → 获取所有历史路径
3. 从 default_workspace 开始搜索，而非从当前工作目录或猜测路径
```

**搜索策略**：
- 一级目录（如 `E:\08_Bug`）→ 用 `bash ls` 逐层搜，**不要用 Glob**
- 二级及以下 → 用 Glob 精确匹配
- 搜索范围必须覆盖 `default_workspace` + `paths.json` 中所有路径

### 规则 2: instance 参数必须查配置，禁止猜测

**调用任何需要 `instance` 参数的函数前，必须先读 `config/bugzilla_instances.json`：**

```
1. 读取 config/bugzilla_instances.json
2. 确认目标实例在可用列表中（如 kernel, mozilla, gnome, unisoc, local）
3. 使用确切的实例名，不凭记忆猜测
```

**错误示例**：`instance='shanghai'`（凭记忆猜测，实际不存在）
**正确示例**：先读 `bugzilla_instances.json`，确认后使用 `instance='unisoc'`

### 规则 3: 大目录搜索用 bash，不用 Glob

**Glob 在大目录下性能差且可能遗漏。** 搜索策略分级：

| 目录级别 | 工具 | 示例 |
|---------|------|------|
| 一级（如 `E:\08_Bug`） | `bash ls` | `ls -d "E:\08_Bug\CQ\"*BugID*` |
| 二级及以下 | Glob | `Glob(workspace_path, "*BugID*")` |

### 规则 4: Windows 路径禁止用 `python -c` 内联执行，必须写临时脚本

**`python -c "..."` 在 Git Bash 下处理 Windows 路径（含 `\` 反斜杠）时，shell 转义会反复破坏路径字符串，导致 exit 127 或 No such file or directory。**

| 做法 | 结果 | 示例 |
|------|:----:|------|
| `python -c "..."` 含 Windows 路径 | ❌ 失败 | `python -c "open('E:\\08_Bug\\...')"` |
| 写临时 `.py` 文件再执行 | ✅ 可靠 | `python "C:/Users/.../Temp/script.py"` |

**规则**：
- **任何需要操作 Windows 路径（含 `\\` 或 `\`）的 Python 代码，必须用 Write 工具写入临时脚本文件（`C:/Users/xianjun.zeng/AppData/Local/Temp/xxx.py`），再用 Bash 执行该脚本文件。**
- 唯一例外：纯计算/字符串操作，完全不涉及文件系统路径的 `python -c` 可以接受。
- 临时脚本路径使用正斜杠（`C:/Users/...`），避免反斜杠。

**失败模式识别**：
- 看到 `exit 127` + `No such file or directory` + 路径中反斜杠消失 → 立即切换到临时脚本方式，不要重试内联写法。

### 执行检查清单

每次触发 bug-workspace 时，按以下顺序执行：

```
□ 1. 读取 config/bugzilla_instances.json — 获取 default_workspace 和可用实例列表
□ 2. 读取 config/paths.json — 获取历史路径
□ 3. 从 default_workspace 开始搜索现有工作区（bash ls，不用 Glob）
□ 4. 确认 instance 参数在 bugzilla_instances.json 中存在
□ 5. 涉及 Windows 路径的 Python 操作 → 写入临时脚本文件，禁止 python -c 内联
□ 6. 开始执行实际任务
```

## 工作流程

1. **读取配置** — `config/bugzilla_instances.json`（获取 default_workspace + 实例列表）+ `config/paths.json`（历史路径）
2. **搜索现有工作区** — 从 `default_workspace` 开始，用 `bash ls` 逐层搜索
3. 获取 Bug 信息（跨 Skill 调用 bug-core）
4. 根据 Bug ID + Summary 生成文件夹名: `Bug [BugID][Summary]`
5. 在指定路径创建文件夹
6. 复制 Bug Z 模板（若存在）
7. 创建 .url 快捷方式（链接到 Bug 页面）
8. 生成 bug_summary.txt（所有 Bug 字段摘要）
9. **UNC 优先下载附件**（从 Comment #0 提取 UNC 路径 → `shutil.copytree`/`copy_missing`）
10. **rayfile FTP fallback**（UNC 不可达时自动降级到 rayfile 下载）
11. 自动解压 Attachements 下的 ZIP 附件（mobilelog/kernel_log 等）
12. **分析报告生成后，主动获取"还需获取"的材料**（查询历史Bug、读取规格书、搜索平台文档）

```
用户: 给 Bug 219041 创建工作区并下载附件
AI:
  1. 读取 bugzilla_instances.json → default_workspace = "E:\08_Bug", instance = "unisoc"
  2. 读取 paths.json → 历史路径列表
  3. bash ls "E:\08_Bug" 搜索现有工作区
  4. 获取 Bug 219041 信息
  5. 生成文件夹: E:\08_Bug\Bug 219041 - USB enumeration timeout
  6. 复制 Bug Z 模板
  7. 创建快捷方式: Bug_219041.url
  8. 生成摘要: bug_summary.txt
  9. UNC 下载附件（Comment #0 提取 UNC 路径 → 直接复制）
  10. 自动解压 ZIP
  11. 生成分析报告，识别"还需获取"的材料清单
  12. 主动尝试获取材料（查询历史Bug、读取规格书、搜索平台文档）
  13. ✅ 工作区创建完成！
```

## 核心功能

### 文件夹命名

格式: `Bug [BugID][Summary]`
- 自动清除非法文件名字符（`<>:"/\|?*`）
- 超长名称自动截断（保留头尾）

### 附件下载 (v3.0 重写 — UNC 优先 + rayfile fallback)

**下载模式** (`download_mode`):

| 模式 | 说明 |
|------|------|
| `"incremental"` | **默认** — 仅下载新增/变更文件（`copy_missing`），跳过已存在 |
| `"full"` | 完整覆盖 — 清空目标目录后重新下载（`shutil.copytree dirs_exist_ok=True`） |
| `"skip"` | 跳过下载 — 仅创建文件夹结构，不下载任何附件 |

**下载策略** (`detect_attachment_type` + `download_bug_attachments`):

1. **UNC 优先**：从 Comment #0 提取系统生成的 UNC 路径（`\\server\share\path...`）
   - 正则：`\\\\[\w.-]+(?:\\[^\s\[\]()]+)+`（不硬编码 IP/服务器名）
   - 辅助信号：Comment #0 是否含 "unisupport" 关键词
2. **rayfile fallback**：UNC 不可达时自动降级到 rayfile FTP 下载
3. **结构化字段 fallback**：Comment #0 含 `[14.Logpath]` 结构化字段时提取 UNC 路径

**UNC 路径提取**（`_extract_unc_from_comment0`）：
- 仅从 Comment #0 提取（系统生成）
- 通用 UNC 正则，不依赖特定 IP 地址
- "unisupport" 关键词作为辅助确认信号

### rayfile 下载命令（v2.0 已修正，v3.0 保留为 fallback）

生成完整的 rayfile-c_cmd.exe 命令（匹配原工具精确参数）：
```
rayfile-c_cmd.exe -a unitrans.unisoc.com -p 2443 -ssl -u ctd01 -w <password> -o download -d "<local_dir>" -s "<ftp_path>" -space_id 2 -gr 31240 -file-update append
```

### 结构化评论解析 (merged from bug-logs)

`parse_unisoc_structured_fields()` — 解析 unisoc Bugzilla Comment #0 的 19 字段模板格式：

```
[1.Severity]:Major
[14.Logpath]:
  LogName:
  LogPath:\\shnas02\TestLogs\PSST\...
  Log Servers:
    External:\\shnas02\TestLogs
    Internal:\\logserver\TestData
    FTP:ftp://unitrans.unisoc.com/TestLogs/...
[15.Logtype]:Default
[16.Occur Time]:2026-05-15 10:30
[19.Version Path]:SPRDROID...
```

**提取字段**: 7 个头部字段 + 19 个编号字段 + LogPath/LogName/LogServers/LogType/OccurTime/VersionPath

### 日志目录列表 (merged from bug-logs)

`list_log_directory()` — 双通道（UNC + FTP）列出日志目录内容：

| 通道 | 适用场景 | 技术 |
|------|---------|------|
| **UNC** | Windows 办公网，直接访问 `\\server\share` | `os.scandir()` |
| **FTP** | UNC 不可达时 fallback | `ftplib.FTP_TLS` |

### 组合查询 (merged from bug-logs)

`fetch_bug_with_logs()` — 一次调用完成：Bug 信息获取 → 结构化解析 → 日志目录列表。

### 智能附件类型检测 (v3.0 重写)

`detect_attachment_type()` — 三级检测：

| 优先级 | 类型 | 检测依据 | 下载方式 |
|:---:|------|---------|---------|
| **1** | **unc** | Comment #0 含 unisupport UNC 路径（系统生成） | `shutil.copytree` / `copy_missing` |
| **2** | **unc** | Comment #0 含 `[14.Logpath]` + 有效 UNC 路径 | `shutil.copytree` / `copy_missing` |
| **3** | **rayfile** | Comment #0 含 "下载附件:" FTP 路径 | `rayfile-c_cmd.exe` 子进程 |
| **—** | **none** | 无上述格式 | 返回错误信息 |

### 附件下载函数 (v3.0)

| 函数 | 说明 |
|------|------|
| `download_from_unc_path(unc_path, dest_dir, mode)` | **v3.0 重写** — full=`shutil.copytree`, incremental=`copy_missing` |
| `download_from_rayfile(ftp_path, dest_dir, instance_config)` | 通过 rayfile-c_cmd.exe 从 FTP 下载 |
| `download_bug_attachments(bug_id, dest_dir, instance, download_mode, normalize_action)` | **统一入口**：检测→创建目录→UNC下载→rayfile fallback→规范化 |
| `normalize_downloaded_folder(attachment_folder, bug_id, action)` | 规范化目录结构（off/move/copy_new） |
| `copy_missing(src, dst)` | 递归复制，仅复制目标不存在的文件 |

### Bug Z 模板复制

`copy_bug_z_template()` — 若 `{base_path}/Bug Z` 目录存在，使用 `shutil.copytree` 复制到工作区。冲突时自动合并（`dirs_exist_ok=True`）。

### 路径历史管理

| 函数 | 说明 |
|------|------|
| `load_workspace_paths()` | 从 `config/paths.json` 加载路径历史（17 个默认路径） |
| `save_workspace_paths(paths)` | 保存路径历史，自动去重保持顺序 |
| `open_workspace_path(path)` | `os.startfile()` 在资源管理器中打开工作区 |

### 快捷方式

创建 Windows .url 文件（`[InternetShortcut]` 格式）：
```ini
[InternetShortcut]
URL=https://bugzilla.unisoc.com/bugzilla/show_bug.cgi?id=219041
IconFile=https://bugzilla.unisoc.com/bugzilla/show_bug.cgi?id=219041
IconIndex=0
```
- 路径 >200 字符自动简化为 `Bug.url`

### 编排下载 (v3.0 重写)

`generate_workspace_with_download()` — 完整工作流编排：
1. 创建工作区文件夹
2. 复制 Bug Z 模板
3. 创建 .url 快捷方式 + bug_summary.txt
4. **UNC 优先下载附件**（Comment #0 提取 UNC 路径）
5. **rayfile FTP fallback**（UNC 不可达时）
6. 自动解压 ZIP 附件
7. 规范化文件夹结构
8. 生成分析报告
9. 返回完整结果

### ZIP 自动解压

`extract_zip_attachments()` — 下载完成后自动扫描 Attachements 目录下所有 `.zip` 文件，就地解压到 `stem/` 子目录：
- 幂等：若目标目录已存在则跳过
- 保留原 ZIP 文件（可选删除）
- 返回 `{"extracted": [...], "skipped": [...], "errors": [...]}`

### 主动材料获取 (v2.2)

分析报告生成后，识别出"还需获取"的材料清单时，**必须主动尝试获取**，而非仅列出清单等待用户操作。

**获取渠道和策略：**

| 材料类型 | 获取方式 | 工具/API |
|----------|----------|----------|
| 历史相关 Bug | Bugzilla REST API 查询 | `GET /rest/bug/{id}` 或搜索 `GET /rest/bug?product=...&summary=...` |
| 规格书/数据手册 | 读取已下载的 PDF 附件 | PyPDF2/pdfplumber 提取文本 |
| 平台文档 | Bugzilla 搜索同产品/同组件 Bug | `GET /rest/bug?product=SPCSS_{platform}&component=...` |
| 参考代码 | 代码仓库搜索 | Grep/git 搜索相关驱动代码 |
| Bug 评论中的引用 | 查询被引用的 Bug ID | 逐条检查评论中提到的 Bug 号 |

**标准流程：**

1. **分析报告列出"还需获取"清单** → 按优先级排序（🔴高 → 🟡中 → 🟢低）
2. **逐项尝试获取**：
   - 历史 Bug：直接调用 REST API（`GET /rest/bug/{id}`），获取 summary/status/resolution/analysis_solution 和评论
   - 规格书 PDF：使用 PyPDF2 提取关键参数（如 FB 引脚分压公式、Vref 电压值）
   - 平台文档：搜索同产品 Bug 列表，按关键词筛选（如 "DCDC"、"VDDCPU"、"外置"）
   - 代码搜索：在相关仓库路径搜索驱动文件
3. **记录获取结果**：
   - 成功获取 → 提取关键信息，更新分析报告
   - 获取失败 → 记录失败原因（超时/无权限/格式不支持），标记为"待用户提供"
4. **汇总发现**：将获取到的关键信息写入分析报告"技术分析"章节

**重要原则：**
- **先尝试再报告**：不要只列出"还需获取"就结束，必须逐一尝试
- **失败要记录**：获取失败不是错误，但要记录原因，方便用户补充
- **历史 Bug 最有价值**：同类平台的类似问题往往已有结论，优先查询
- **跨平台参考**：UMS512/UMS9230 等平台的 DCDC 相关 Bug 也可能有参考价值

### Bug 摘要文件

生成 `bug_summary.txt`，包含完整的 Bug 字段信息（ID/Severity/Status/Product/Assignee/Attachment等）。

## MCP Server 工具

### bug_workspace

**基础模式（仅创建文件夹）**：
```json
{
  "tool": "bug_workspace",
  "args": {
    "bug_id": 219041,
    "bugzilla_url": "https://bugzilla.unisoc.com/bugzilla",
    "base_path": "E:\\08_Bug"
  }
}
```

**下载模式（v3.0 — UNC 优先 + rayfile fallback）**：
```json
{
  "tool": "bug_workspace",
  "args": {
    "bug_id": 219041,
    "bugzilla_url": "https://bugzilla.unisoc.com/bugzilla",
    "base_path": "E:\\08_Bug",
    "download_mode": "incremental",
    "normalize": "copy_new",
    "copy_bug_z": true
  }
}
```

**参数说明**：
| 参数 | 类型 | 默认 | 说明 |
|------|------|:---:|------|
| `download_mode` | str | `"incremental"` | 下载模式：`"full"` 完整覆盖 / `"incremental"` 增量下载 / `"skip"` 跳过 |
| `normalize` | str | `"copy_new"` | 规范化模式：off / move / copy_new |
| `copy_bug_z` | bool | `true` | 是否复制 Bug Z 模板 |

> **v3.0 变更**：`download` + `refresh` 参数已替换为 `download_mode`。

返回：
```json
{
  "success": true,
  "folder": {
    "folder_name": "Bug 219041 - USB enumeration timeout on XHCI",
    "folder_path": "E:\\08_Bug\\Bug 219041 - USB enumeration timeout on XHCI\\",
    "created": true,
    "shortcut_file": "E:\\08_Bug\\Bug 219041 - USB enumeration timeout on XHCI\\Bug_219041.url",
    "summary_file": "E:\\08_Bug\\Bug 219041 - USB enumeration timeout on XHCI\\bug_summary.txt"
  },
  "download": {
    "success": true,
    "attachment_type": "unc",
    "files_copied": 45
  },
  "bug_z_copied": true,
  "analysis_report": "E:\\08_Bug\\...\\SPCSS01698559_platform_issue.md",
  "errors": []
}
```

### bug_logs (已废弃 ⚠️)

> **bug_logs MCP 工具已废弃**。所有功能已合并到 `bug_workspace` 工具中。
> 请使用 `bug_workspace` 替代，支持 `download_mode` 参数进行 UNC 优先下载。

## 工作区目录结构

```
E:\08_Bug\Bug 219041 - USB enumeration timeout on XHCI\
├── Bug Z/                        ← Bug Z 模板（可选）
│   ├── template.txt
│   └── SubFolder/
├── Attachements/                 ← 下载的附件
│   ├── modem_log.zip
│   └── syslog.txt
├── Bug_219041.url                ← Bugzilla 快捷方式
├── bug_summary.txt               ← Bug 摘要文件
└── SPCSS01698559_platform_issue.md  ← 分析报告
```

## 相关 Skill

- **bug-core**: Bug 查询核心（提供 Bug 信息和 `format_bug_summary()`）
- ~~**bug-logs**~~: **已废弃** — 所有功能已合并到 bug-workspace

## 代码位置

| 文件 | 说明 |
|------|------|
| `bug_workspace.py` | 工作区核心+编排模块（含 UNC 下载+结构化解析+日志目录，~1100行） |
| `config/bugzilla_instances.json` | 实例配置（含 default_workspace/FTP凭证/API key） |
| `config/paths.json` | 工作区路径历史（17 个默认路径） |
| `tests/test_workspace.py` | 工作区测试套件 |