---
name: isupport-downloader
description: isupport DCC文档下载 - 通过文档ID或关键词从isupport.unisoc.com检索并下载PDF/文档，支持批量下载和过滤
version: "2.0"
tags: [isupport, dcc, document, download, unisoc]
---

# isupport DCC 文档下载

从 isupport.unisoc.com 的 DCC（Document Control Center）检索并下载文档。

## 触发条件

- 用户说"下载文档"、"下载isupport文档"、"isupport下载"
- 用户提供文档ID（如"下载ID 105142"）
- 用户提供文档名称关键词（如"搜索UMS512相关文档"）
- 用户说"isupport文档查询"、"DCC下载"

## 前置条件

文档工具位于 `D:\06_Project\isupport_down\`，需要先检查依赖和认证状态。

## 文件组织

### 固定目录结构

所有文档和FAQ保存到工具根目录下的固定目录，无需手动指定 `--dir`：

```
D:\06_Project\isupport_down\
├── docs/                          ← 文档下载目录
│   └── {typename}/                ← 文档类型（中文，如 "配置指南"、"器件规格说明书"）
│       └── {chip}/                ← 芯片平台（取第一个芯片名，null→"未分类"）
│           └── filename.pdf
├── faq/                           ← FAQ保存目录
│   └── {cate1}/                   ← FAQ一级分类（如 "01-BSP-PMU"）
│       └── FAQ{number}_{title}.md
├── .download_index.json           ← 全局下载索引（去重检测）
└── src/
```

### 下载索引 (.download_index.json)

工具根目录下的 `.download_index.json` 追踪所有已下载的文件：
- **文档去重**：按 `fileid` 检测，避免重复下载
- **FAQ去重**：按 `number` 检测，避免重复保存
- 搜索结果显示 `[已下载]` 标记
- 使用 `--force` 强制重新下载/保存

## 工作流程

### 流程1：按文档ID下载（精确）

1. 用户指定文档ID，如"下载文档ID 105142"
2. 调用下载命令（自动保存到 `docs/{typename}/{chip}/`）：
   ```bash
   cd D:\06_Project\isupport_down
   python src/main.py download --id <文件ID>
   ```
3. 如果已下载，工具会提示 `[SKIP]`，使用 `--force` 强制重新下载
4. 如果认证失效（token过期>72h），先执行 `python src/main.py login` 重新登录
5. 验证下载的文件是否为有效PDF（检查文件头 `%PDF-`）
6. **完成后自动执行流程5（下载后索引更新）**

### 流程2：按关键词搜索并下载

1. 用户提供搜索关键词，如"搜索并下载UMS512相关文档"
2. 调用搜索命令（先查看结果，已下载项显示 `[已下载]`）：
   ```bash
   cd D:\06_Project\isupport_down
   python src/main.py search "<关键词>" --max 20 --chip <芯片型号>
   ```
3. 展示搜索结果（文件名、大小、芯片、作者、关键词标签、已下载标记）
4. 确认后调用下载命令（自动保存到 `docs/{typename}/{chip}/`）：
   ```bash
   python src/main.py get "<关键词>" --max 5
   ```
5. 使用 `--force` 覆盖已下载的文件
6. **完成后自动执行流程5（下载后索引更新）**

### 流程3：按条件批量下载

1. 用户指定多个过滤条件：关键词、芯片平台、Android版本
2. 先搜索预览结果：
   ```bash
   python src/main.py search "<关键词>" --chip UMS512 --android-version "Android 17 (X)"
   ```
3. 使用 `--downloaded` 只显示已下载，`--not-downloaded` 只显示未下载
4. 确认搜索结果后执行批量下载
5. **完成后自动执行流程5（下载后索引更新）**

### 流程4：FAQ搜索与保存

1. 搜索FAQ：
   ```bash
   cd D:\06_Project\isupport_down
   python src/main.py faq search "<关键词>" --max 20
   python src/main.py faq search --number FAQ202479985        # 按FAQ编号精确匹配
   python src/main.py faq search "<关键词>" --downloaded      # 只显示已保存的FAQ
   python src/main.py faq search "<关键词>" --not-downloaded  # 只显示未保存的FAQ
   ```
2. 查看FAQ详情（自动保存到 `faq/{cate1}/FAQ{number}_{title}.md`）：
   ```bash
   python src/main.py faq get --number FAQ202479985
   python src/main.py faq get --id 12345
   python src/main.py faq get --number FAQ202479985 --force   # 覆盖已保存的文件
   python src/main.py faq get --number FAQ202479985 --no-save # 只查看，不保存
   ```
3. 浏览FAQ分类树：
   ```bash
   python src/main.py faq tree
   ```

### 流程5：认证刷新

1. 如token过期（提示认证失败），打开浏览器完成SSO登录：
   ```bash
   cd D:\06_Project\isupport_down
   python src/main.py login
   ```
2. 登录后token保存72小时，后续命令无需再次登录

### 流程6：下载后索引更新

> **触发时机**：流程1/2/3 下载完成后自动执行。当下载到 Bug workspace 目录时，通过 Windows Junction 将 isupport 下载缓存映射到 workspace 中，实现与 code-puller 一致的索引方式。**Junction 是主要机制，文本索引是次要的。**

1. **确定 workspace 目录**：如果下载目标目录是某个 Bug workspace 的子目录（如 `workspace/SPCSS01694583/`），则 `workspace` 根目录即为索引根；否则取下载目标目录自身。

2. **确定 isupport 下载缓存目录**：下载工具的实际输出目录，即 `docs/{typename}/{chip}/` 下的对应路径。

3. **创建 Windows Junction**（PRIMARY mechanism，替代旧的"复制文件 + 更新文本索引"方式）：

   **检查现有 Reference_Docs**：
   - 如果 `Reference_Docs` 已经是一个 Junction 且指向正确的目标目录 → 跳过，无需操作
   - 如果 `Reference_Docs` 已经是一个 Junction 但指向错误目录 → 删除旧 Junction，重新创建
   - 如果 `Reference_Docs` 是一个物理目录（非 Junction）：
     - 目录为空 → 直接删除，然后创建 Junction
     - 目录非空 → 警告用户目录中有文件，让用户确认后再删除并创建 Junction

   **创建 Junction 命令**：
   ```powershell
   cmd /c mklink /J "<workspace>/Reference_Docs" "D:\06_Project\isupport_down\docs\配置指南\UMS512"
   ```

   - Junction 名称：`Reference_Docs`
   - 目标：isupport 下载缓存目录（该 Bug 的实际下载路径）
   - 创建后，`cd Reference_Docs` 即可直接访问所有下载的文档，所有文件修改双向同步
   - 删除 Junction 不会影响源文件（源文件仍在 isupport 下载缓存中）
   - 对 Git Bash 透明，无需额外配置

4. **更新 材料索引.md**（SECONDARY mechanism，仅供参考）：

   如果 workspace 根目录下存在 `材料索引.md`，更新其"参考文档"部分，标明 `Reference_Docs/` 是一个 Junction 而非物理目录：

   **索引文件格式**：
   ```markdown
   # 材料索引

   > 生成时间: 2026-08-13 10:30:00
   > 生成工具: isupport-downloader skill

   ## 参考文档 (Reference_Docs/)

   > Reference_Docs/ 是一个 Windows Junction（目录符号链接），指向 isupport 下载缓存目录。
   > Junction 目标: `D:\06_Project\isupport_down\docs\配置指南\UMS512`
   > 所有文件修改双向同步，删除 Junction 不会影响源文件。

   | 文档ID | 文档名称 | 平台 | 大小 | 下载时间 | 本地路径 |
   |--------|---------|------|------|---------|---------|
   | 105142 | UMS512 Hardware Design Guide V1.2.pdf | UMS512 | 3.2MB | 2026-08-13 10:30 | Reference_Docs/105142_UMS512_Hardware_Design_Guide_V1.2.pdf |
   | 108901 | UMS512_PCB_Layout_Guide.pdf | UMS512 | 1.8MB | 2026-08-13 10:32 | Reference_Docs/108901_UMS512_PCB_Layout_Guide.pdf |
   ```

   **更新逻辑**：
   - 解析已有表格，按文档ID去重：如果同一文档ID已存在，更新其条目（名称、大小、下载时间）；否则追加新行
   - 更新文件头部的 `生成时间` 为当前时间
   - 如果 `材料索引.md` 不存在，不强制创建（Junction 是主要机制，文本索引是次要的）

5. **输出结果**：
   - 告知用户 Junction 已创建：`Reference_Docs/` → `<isupport 缓存目录>`
   - 如果 Junction 已存在且指向正确，告知用户无需操作
   - 如果更新了 `材料索引.md`，列出新增/更新的文档数量

## 命令速查

### 文档命令

| 命令 | 用途 |
|------|------|
| `python src/main.py login` | 打开浏览器完成SSO登录 |
| `python src/main.py search "关键词" --max 20` | 搜索文档 |
| `python src/main.py search "关键词" --chip UMS512` | 按芯片过滤搜索 |
| `python src/main.py search "关键词" --downloaded` | 只显示已下载的文档 |
| `python src/main.py search "关键词" --not-downloaded` | 只显示未下载的文档 |
| `python src/main.py download --id 105142` | 按ID下载（自动保存到docs/） |
| `python src/main.py download --id 105142 --force` | 强制重新下载 |
| `python src/main.py get "关键词" --max 5` | 搜索+下载 |
| `python src/main.py get "关键词" --max 5 --force` | 搜索+强制下载 |
| `python src/main.py rename <目录>` | 批量重命名 document_{id}.pdf |

### FAQ命令

| 命令 | 用途 |
|------|------|
| `python src/main.py faq search "关键词"` | 搜索FAQ |
| `python src/main.py faq search --number FAQ202479985` | 按FAQ编号精确搜索 |
| `python src/main.py faq search "关键词" --downloaded` | 只显示已保存的FAQ |
| `python src/main.py faq search "关键词" --not-downloaded` | 只显示未保存的FAQ |
| `python src/main.py faq get --number FAQ202479985` | 查看FAQ详情并自动保存 |
| `python src/main.py faq get --number FAQ202479985 --force` | 强制重新保存 |
| `python src/main.py faq get --id 12345` | 按ID查看FAQ详情 |
| `python src/main.py faq tree` | 列出FAQ产品分类 |

## 输出

- **文档**：自动保存到 `docs/{typename}/{chip}/` 目录结构，按文档类型和芯片平台分类
- **FAQ**：自动保存到 `faq/{cate1}/FAQ{number}_{title}.md`，Markdown格式
- **下载索引**：`.download_index.json` 追踪所有下载记录，支持去重和 `[已下载]` 标记
- **主要机制**：通过 Windows Junction 将 `Reference_Docs/` 映射到 isupport 下载缓存目录（位于 workspace 根目录下），文件实际保存在 `D:\06_Project\isupport_down\docs\` 中，无需复制
- **次要机制**：下载完成后自动更新 workspace 下的 `材料索引.md`（如已存在），包含文档ID、名称、平台、大小、下载时间、本地路径；如不存在则不强制创建
- 文件名为搜索API返回的原始文件名（含中文）
- 返回下载结果：文件名、大小、路径
- 如需要，可展示文件列表和完整性校验（PDF文件头验证）

## Workspace 目录结构（下载到 Bug workspace 时）

```
<workspace>/[SPCSS01694583] Bug Summary.../
├── Bug Z/                        ← Bug Z 模板（可选）
│   └── ...
├── Attachements/                 ← 下载的日志附件（bug-logs）
│   ├── modem_log.zip
│   └── syslog.txt
├── Reference_Docs/               ← [Junction] → isupport 下载缓存（本 skill）
│   ├── 105142_UMS512_Hardware_Design_Guide_V1.2.pdf
│   └── 108901_UMS512_PCB_Layout_Guide.pdf
├── 材料索引.md                   ← 材料索引（自动维护，次要机制）
├── Bug_XXXXXX.url                ← Bugzilla 快捷方式
└── bug_summary.txt               ← Bug 摘要文件
```

> **说明**：`Reference_Docs/` 是一个 Windows Junction（目录符号链接），指向 `D:\06_Project\isupport_down\docs\{typename}\{chip}`。文件实际保存在 isupport 下载缓存中，无需复制到 workspace。删除 Junction 不会影响源文件。`材料索引.md` 记录所有下载材料的索引，作为 Junction 的补充参考。

## 注意事项

- 工具依赖 Python 3.8+，Playwright 1.40+，requests 2.28+
- 首次使用需执行 `login` 完成SSO认证
- Token有效期72小时，过期后需重新登录
- 中文文件名在浏览器Content-Disposition Header中有编码问题，工具已从API直接获取正确文件名
- 支持的文件类型：PDF（主要）、Excel、Word等（通过同一个previewFile端点）
- FAQ文件保存为Markdown格式，包含问题、回答、元数据等结构化内容
- 使用 `--force` 可强制重新下载/保存已存在的文件