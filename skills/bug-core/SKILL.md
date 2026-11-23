---
name: bug-core
description: Bugzilla Bug查询核心 - 多实例Bug信息查询、智能摘要、搜索、离线模式、评论发布、状态修改、分析报告生成、并行材料获取
version: "2.2"
tags: [bugzilla, bug, query, summary, search, commit, status, comment, analysis, material-acquisition, code-acquirer, doc-acquirer]
---

# Bug查询核心

查询Bugzilla Bug信息，生成智能摘要，支持多实例和多模式查询。支持评论发布和状态修改。

## 触发条件

- 用户输入 Bug ID（纯数字5位以上、SPCSS开头、或 `unicase\d+` Unicase 工单号）
- 用户说"查Bug"、"Bug助手"、"Bug查询"、"查一下Bug"
- 用户粘贴Bug页面内容
- 用户上传文件并提及Bug相关关键词

### Unicase 工单号识别

**`unicase\d+` 格式的 ID（如 `unicase015809`）是 Unicase 平台工单号**，不是 Bugzilla Bug ID。

Unicase 工单通过 Bugzilla 的 `alias` 字段与 SPCSS Bug 关联。收到 Unicase 工单号后，执行以下解析流程：

1. 使用 REST API `quicksearch=unicaseXXXXXX` 查找关联的 Bugzilla Bug
2. 或使用 `alias=unicaseXXXXXX` 参数直接搜索
3. 找到关联 Bug 后 → 使用 Bugzilla Bug ID 继续正常流程
4. **工作区命名必须包含两个 ID**：`Bug {bugzilla_id}({unicase_id}) - {title}`
   - 示例：`Bug 3575241(unicase015809) - [UMS9370][longcheer_BU6] HADCI7 voltage read 0`
5. `bug_summary.txt` 中同时记录 Bugzilla ID 和 Unicase ID

**关键特性**：
- Bugzilla REST API 返回的 `alias` 字段包含 Unicase ID（如 `"alias": ["unicase015809"]`）
- Unicase 控制台 URL：`https://isupport.unisoc.com/isupport-unicase/?caseId={数字部分}`
  - 示例：`unicase015809` → `https://isupport.unisoc.com/isupport-unicase/?caseId=15809`

## ⚠️ AI 操作前置规则（必须遵守）

**在执行任何操作前，必须先完成以下检查，违反将导致错误路径或错误实例：**

### 规则 1: Windows 路径禁止用 `python -c` 内联执行，必须写临时脚本

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

每次触发 bug-core 时，按以下顺序执行：

```
□ 1. 涉及 Windows 路径的 Python 操作 → 写入临时脚本文件，禁止 python -c 内联
□ 2. 开始执行实际任务
```

## 工作流程

### 流程1：Bug ID查询（默认）

1. 用户输入Bug ID
2. 调用 REST API 获取Bug信息
3. 如果REST API失败，尝试 web_fetch 获取HTML页面
4. 生成智能摘要展示给用户
5. **（Unisoc实例）自动创建工作区**：
   - ⛔ **文件夹名必须通过运行 `get_bug_folder_name.py` 脚本获取**（精确复刻 `fetch_buginfo_by_API_UI.py` 命名逻辑），禁止 AI 手动拼接
   - 调用 bug-workspace 生成文件夹、.url快捷方式、bug_summary.txt，并生成 rayfile 下载命令
   - **SPCSS Bug**：自动解析 alias 获取 Bugzilla ID → 路由到 `CQ/` 子目录 → 脚本输出 folder_name
   - **内部 Bug（纯数字）**：直接使用 Bug ID → 路由到根目录 → 脚本输出 folder_name
6. 提示用户上传附件或联动分析

### 流程2：手动输入解析

1. 用户粘贴Bug页面内容
2. 调用 parse_bug_from_text() 自动解析提取
3. 展示解析结果，确认后继续

### 流程3：web_fetch降级

当REST API不可用时：
1. 使用web_fetch获取Bug页面HTML
2. LLM从HTML中提取关键信息
3. 或使用 ?ctype=xml 获取结构化XML

### 流程4：客户回复模板

当用户需要回复客户（SPCSS Bug）时触发：
- 用户说"回复客户"、"customer reply"、"生成回复"、"用模板回复"

┌──────────────────────────────────────────────────────────────────────┐
│ ⛔ CRITICAL CONSTRAINT — 绝对禁止在用户确认前发送回复                   │
│                                                                      │
│   此规则在上下文压缩后仍需遵守！违反此规则将导致未经审核的回复直接       │
│   发送到 Bugzilla，无法撤回。                                         │
│                                                                      │
│   ✅ 正确流程: 生成预览 → 展示预览给用户 → 用户确认说"发送" → 发送     │
│   ❌ 错误做法: 生成内容后直接调用 post_comment() 或 bug_commit() 发送  │
│                                                                      │
│   代码层已加固: post_comment() 和 bug_commit() 默认 send_mode='preview'│
│   在 preview 模式下只写本地文件，不会实际发送。                         │
│   要实际发送必须显式传 send_mode='live' 或设环境变量                    │
│   BUGZILLA_SEND_MODE=live。                                          │
└──────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────┐
│ ⛔ CRITICAL CONSTRAINT — 生成预览必须调用 prepare_customer_reply()    │
│                                                                      │
│   绝对禁止 AI 手动 Write 回复文件到 config/ 目录。                     │
│                                                                      │
│   ✅ 正确做法:                                                        │
│     from bug_core import prepare_customer_reply                       │
│     result = prepare_customer_reply(bug_id, content, platform,       │
│                                      new_status="needinfo")          │
│     # 函数内部执行: _find_bug_workspace() → ws优先写入 → header元数据  │
│                                                                      │
│   ❌ 错误做法:                                                        │
│     Write("config/reply_SPCXXX_preview.txt", "Dear CUS\n...\nThanks")│
│     # 绕过了 ws 优先逻辑、header 元数据，文件落在错误的共享目录         │
│                                                                      │
│   原因: prepare_customer_reply() 内部封装了 _find_bug_workspace()     │
│   和 _resolve_reply_filepath()，只有通过函数调用才能确保文件写入       │
│   Bug 专属工作区而非共享 config 目录。手写文件会导致跨 Bug 混淆。      │
│                                                                      │
│   此规则同样适用于 post_comment() 和 bug_commit() 的 preview 模式     │
│   —— preview 文件也必须通过函数写入，禁止手动 Write。                  │
└──────────────────────────────────────────────────────────────────────┘

**SPCSS 场景统一格式：`Dear CUS` + 用户内容 + `Thanks`**

**回复风格约束**（去AI味，工程师直述风格）：
- 禁止表格，纯文字段落
- 禁止emoji、加粗、斜体等富文本装饰
- 禁止反问句和问题重述，直接陈述事实
- 禁止填充语（如"我帮你逐一看了"、"先说结论"、"要分两拨来看"）
- 简洁直接，对方是工程师，只讲结论和依据，不铺陈过程

**工作流（5 步）**：

```
Step 1 — 生成回复内容
  AI 根据分析报告生成工程师直述风格的回复草案
         │
         ▼
Step 2 — 读取风格规则
  AI 读取 config/reply_style_rules.md（语义规则文件）
         │
         ▼
Step 3 — LLM 自我风格检查
  AI 用 rules.md 的 R1-R5 语义规则自检生成的内容
  找出所有违规 → 修复 → 再检查 → 直到通过
         │
         ▼
Step 4 — 传入 prepare_customer_reply()
  violations = [{"rule": "R1", "severity": "error", "desc": "..."}, ...]
  prepare_customer_reply(bug_id, content, style_violations=violations)
  函数将违规信息写入预览 header
         │
         ▼
Step 5 — 用户 review 预览文件
  用户确认后说"发送" → send_customer_reply()
```

┌──────────────────────────────────────────────────────────────────────┐
│ ⛔ CRITICAL CONSTRAINT — AI 生成回复后必须 LLM 自检                    │
│                                                                      │
│   在调用 prepare_customer_reply() 前，AI 必须：                        │
│   1. 读取 config/reply_style_rules.md                                  │
│   2. 逐条对照 R1-R5 语义规则自检生成的内容                              │
│   3. 发现违规 → 修复内容 → 重新自检 → 直到零 error                     │
│   4. 将 violations 列表传入 prepare_customer_reply()                   │
│                                                                      │
│   禁止跳过此步骤直接调用 prepare_customer_reply()。                    │
│   风格检查不再由 Python 正则实现，而是由 LLM 语义理解完成。             │
│                                                                      │
│   用户反馈收集在 config/reply_style_feedback.md（自由书写，自然语言）   │
│   用户说"提炼反馈"时，AI 读取 feedback.md → 更新 rules.md。            │
└──────────────────────────────────────────────────────────────────────┘

```python
# Step 1-3: AI 生成内容 + 读取 rules.md + 自检（LLM 执行）
# Step 4: 传入 violations 调用函数

from bug_core import prepare_customer_reply, send_customer_reply

violations = [
    # 示例：AI 自检发现的问题（无违规时传空列表）
    # {"rule": "R1", "severity": "error", "desc": ""分析完成" — 填充语，删掉"}
]

result = prepare_customer_reply(
    bug_id="SPCSS01690575",
    content="样机不支持PD协议过不了认证，这个是前提，提供了vif，测试也过不了",
    platform="UMS512",
    style_violations=violations,  # LLM 自检结果
)
# 文件写入工作区，header 含 StyleCheck PASS/FAIL

# Step 5: 用户 review/修改文件后，确认发送
result = send_customer_reply(
    bug_id="SPCSS01690575",
    new_status="needinfo",
    instance="unisoc",
    use_combined=True,
)
# 从 preview.txt 读取已修改内容，调用 bug_commit 提交
```

┌──────────────────────────────────────────────────────────────────────┐
│ ⛔ CRITICAL CONSTRAINT — 用户说"发送"后必须先消歧，禁止直接发送        │
│                                                                      │
│   背景: 2026-11-02 Bug 3604164 — 用户说"已经修改发送"，LLM 误以为     │
│   用户确认"已发送"并跳过了发送步骤。实际上客户回复从未发送到Bugzilla。 │
│                                                                      │
│   规则: 当用户说包含"发送"的任何话时（如"发送吧"/"发送了"/"已发送"/   │
│   "修改发送"/"已经修改发送"），禁止直接从字面推断用户意图，必须执行    │
│   以下消歧流程：                                                      │
│                                                                      │
│   Step 1 — 调用 Bugzilla API 检查最新评论：                           │
│     GET /rest/bug/{bug_id}/comment → 检查最新评论是否包含回复内容      │
│                                                                      │
│   Step 2 — 根据检查结果分支：                                         │
│     • 已有匹配评论 → 提示"Bugzilla 上已有新评论(Comment #N)，无需重复发送"│
│     • 没有新评论   → 询问用户"Bugzilla 上尚未看到新评论，是否现在发送？"│
│                                                                      │
│   ❌ 禁止行为:                                                        │
│     • 禁止从"已经修改发送"推断"用户说已发送，跳过"                      │
│     • 禁止从"发送了"推断"不需要我再发送"                               │
│     • 禁止不经 API 验证就直接决定发或不发                              │
│                                                                      │
│   关键原则: 用户说"发送"后，唯一的信息源是 Bugzilla API，不是用户措辞  │
└──────────────────────────────────────────────────────────────────────┘

### 回复前自检清单

**每次生成 Bugzilla 回复后，在调用 post_comment() 或 bug_commit() 之前，必须先完成以下自检：**

```
┌─────────────────────────────────────────────────┐
│  回复前自检清单 (SEND-SAFETY CHECKLIST)          │
│                                                 │
│  ☐ 我是否已经将回复内容写入本地预览文件？          │
│  ☐ 我是否已经向用户展示了预览内容？               │
│  ☐ 意图分类（二级判定，必须执行）：                │
│     Tier 1 — 识别用户措辞属于哪个类别：             │
│       🔴 声明类（NOT a send command）：              │
│          "已经发送了" / "修改发送了" / "已发送"       │
│          "发过了" / "已经发了" / "发送了"            │
│          → STOP: 先查 Bugzilla API 确认是否真的已发送 │
│          → 若未发送：提示用户"尚未发送，是否需要发送？"│
│       🟢 指令类（IS a send command）：               │
│          "发送吧" / "确认发送" / "可以发了"           │
│          "发出去" / "提交吧" / "send it"             │
│          → 可以继续发送流程                          │
│     Tier 2 — 不确定时默认保守：                      │
│       无法明确判定 → 查 API → 问用户确认 → 不直接发送 │
│                                                 │
│  ⛔ 如果以上任一答案为"否"：                      │
│     → 只生成预览，不发送                         │
│     → 绝对不要传 send_mode='live'                │
│                                                 │
│  ✅ 仅当三项全部为"是"时，才可发送                │
└─────────────────────────────────────────────────┘
```

> **背景**: 2026-08-31 SPCSS01696773 事件 — 上下文压缩导致 Skill 流程约束丢失，Harness Summary 中 "Pending Tasks: Reply to customer" 触发 LLM Recency Bias，AI 直接调用 post_comment() 发送了未经审核的回复。此自检清单作为最后一道防线，在每次回复前强制检查。

### 流程5：Bug修改（commit + 改状态）

当用户需要回复Bug、贴patch、改状态时触发：
- 用户说"commit"、"回复"、"改状态"、"贴patch"、"评论"
- 用户输入 `/bug-core` 指令并附带 `--commit` 参数

**重要：默认行为已改为组合模式（`use_combined=True`），评论会合并到状态变更的 comment 中，只产生一条评论，不会产生两条冗余评论。**

操作流程：
1. 收集评论内容（用户输入 + patch文件路径）
2. 调用 `bug_commit(bug_id, comment_text, new_status, instance)` 一键完成
3. 展示操作结果（new_status, URL）

```bash
# CLI 一键提交（旧行为，use_combined=False）
python bug_core.py SPCSS01676377 unisoc --commit --status needinfo \
  --comment "dear cus\n试试下面的代码" --patch "E:\path\to\patch"

# 发评论 + 改状态（注意：--commit 必改状态，不传 --status 默认 needinfo）
python bug_core.py 3453091 unisoc --commit --status needinfo --comment "已修复，请验证"

# 仅发评论（不改状态，推荐用于进度同步类评论）
python bug_core.py 3453091 unisoc --comment-only --comment "进度同步：已提交Gerrit评审"

# 通过 Python API（默认合并评论，仅一条 comment）
from bug_core import bug_commit, post_comment
result = bug_commit("SPCSS01676377", "dear cus\n测试看看", "needinfo", instance="unisoc")
# 只发评论不改状态：
result = post_comment("3453091", "进度同步内容", instance="unisoc")
# 如需旧行为（两条评论）：
result = bug_commit("SPCSS01676377", "测试", "needinfo", instance="unisoc", use_combined=False)
```

> ⚠️ **陷阱提醒**：`--commit` / `bug_commit()` 是“发评论+改状态”固定组合，`--status` 默认 `needinfo`。
> 只想发评论请用 `--comment-only` / `post_comment()`，否则会把 Bug 误改为 Need_Info。
> 中文评论内容避免用 PowerShell `Get-Content` 读 UTF-8 文件（默认 GBK 解码会乱码），应用 Python `open(encoding='utf-8')` 读取。

**参数说明：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `use_combined` | `True` | 合并模式：评论放入状态变更 comment（推荐） |
| `use_combined` | `False` | 旧模式：先 post comment 再 update status（两条评论） |

### 流程6：分析报告生成 + 并行材料获取 (v2.2)

**Unisoc SPCSS Bug 分析完成后，同时启动两个后台 Agent 并行获取代码和文档。**

当 Bug 分析报告生成、识别出"还需要获取"的材料清单后，**不等用户手动操作**，按材料类型拆分为两组，同时启动两个 Agent 并行获取：

```
用户: 分析 Bug SPCSS01696773
AI:
  1. 获取 Bug 信息 + 评论
  2. 创建工作区 + 下载附件
  3. 生成分析报告（含"还需获取"清单）
  4. 🚀 并行启动两个异步 Agent:
     ├── Agent 1: "获取UMS312-内核DCDC驱动代码" (code-acquirer)
     │   → 调用 code-puller 拉 kernel/linux 源码
     │   → 写入 {report}.code.md
     └── Agent 2: "获取UMS312-DVFS配置和平台文档" (doc-acquirer)
         → 调用 isupport-downloader 搜 DCC 文档
         → 读取附件 PDF 规格书
         → 写入 {report}.docs.md
  5. ✅ 报告已生成，代码和文档后台并行获取中...
  6. 两个 Agent 都完成后，合并 .code.md + .docs.md → 主报告
```

**Agent 启动参数**：

```python
# bug-core 分析报告生成后，解析"还需要获取"清单，按类型拆分后并行启动

# Agent 1: 代码获取
Agent(
    subagent_type="code-acquirer",
    description="获取{platform}-{代码材料描述}",
    prompt=f"""
    输入参数：
    - bug_id: {bug_id}
    - report_path: {report_path}
    - workspace_path: {workspace_path}
    - platform: {platform}
    - base_on_version: {base_on_version}

    请读取报告中的"还需要获取"清单，只获取代码类材料（kernel/edk2/源码），
    调用 code-puller Skill，结果写入 {report_path}.code.md。
    """,
    run_in_background=True
)

# Agent 2: 文档获取（与 Agent 1 同时启动）
Agent(
    subagent_type="doc-acquirer",
    description="获取{platform}-{文档材料描述}",
    prompt=f"""
    输入参数：
    - bug_id: {bug_id}
    - report_path: {report_path}
    - workspace_path: {workspace_path}
    - platform: {platform}
    - base_on_version: {base_on_version}

    请读取报告中的"还需要获取"清单，只获取文档类材料（配置/手册/规格书），
    调用 isupport-downloader Skill 和读取 PDF，结果写入 {report_path}.docs.md。
    """,
    run_in_background=True
)
```

**Agent 命名规则**：
- 代码 Agent：`获取{平台}-{代码描述}`，如 `获取UMS312-内核DCDC驱动代码`
- 文档 Agent：`获取{平台}-{文档描述}`，如 `获取UMS312-DVFS配置和平台文档`

**材料分组逻辑**：

| 材料特征 | 分配给 | 调用 Skill |
|---------|:-----:|-----------|
| 包含"代码/驱动/kernel/源码/edk2/bootloader" | `code-acquirer` | `code-puller` |
| 包含"文档/DVFS/OPP/配置/手册/规格书/datasheet" | `doc-acquirer` | `isupport-downloader` + Read PDF |
| 历史 Bug 引用 | bug-core 自己处理 | REST API |

**合并机制**：
- 两个 Agent 各自写入独立文件（`{report}.code.md` / `{report}.docs.md`），避免写冲突
- 用户可随时查看已完成的独立结果
- 两个都完成后，bug-core 自动将内容合并到主报告（标准化命名: `{bug_id}_{type}_{keyword}__{YYYYMMDD}.md`，由 `common.report_utils.generate_report_filename_from_bug()` 生成，bug_core 做向后兼容封装）

**设计原则**：
- **并行不阻塞**：代码和文档同时获取，总耗时 = max(代码耗时, 文档耗时)
- **独立写文件**：各自写独立文件，零冲突
- **命名透明**：Agent 会话名体现具体任务，方便在任务列表中跟踪
- **失败不中断**：任一 Agent 失败不影响另一个，也不影响主报告

### 流程7：风格规则迭代（feedback → 提炼 → rules）

**当用户指出回复风格问题时，通过此流程将反馈编码为规则。**

```
用户在 reply_style_feedback.md 写自然语言反馈
  （例："不要在回复里说'帮贵司分析'，直接说结论"）
         │
         ▼
用户说"提炼反馈"
         │
         ▼
AI 执行：
  1. 读取 config/reply_style_feedback.md
  2. 提取需新增/修改的规则
  3. 更新 config/reply_style_rules.md（保持语义描述格式，不写正则）
  4. 在 feedback.md 对应条目末尾标注 [已提炼: YYYY-MM-DD]
```

**文件关系**：

| 文件 | 维护者 | 格式 | 用途 |
|------|:-----:|------|------|
| `config/reply_style_feedback.md` | 用户 | 自由文本，按日期分段 | 用户观察到的风格问题 |
| `config/reply_style_rules.md` | AI | 结构化语义规则 + Good/Bad 对照 | LLM 自检参考 |

**关键原则**：
- 用户只写自然语言，不写正则
- AI 负责将反馈提炼为语义规则描述
- rules.md 中的规则是给 LLM 看的，不是给正则引擎看的
- 提炼后必须在 feedback.md 标注 `[已提炼]`，避免重复处理

通过 `config/bugzilla_instances.json` 中的 `status_map` 字段，统一使用简短状态名：

| 简短名 | 通用Bugzilla | Unisoc |
|--------|-------------|--------|
| `needinfo` | NEEDINFO | Need_Info |
| `assigned` | ASSIGNED | Assigned |
| `resolved` | RESOLVED | Resolved |
| `closed` | CLOSED | Closed |
| `reopened` | REOPENED | Reopened |

Unisoc 专用状态（完整流转：NEW→Assigned→Root-Caused→Code-Committed→Fixed→TobeVerified→Closed）：

| 简短名 | Unisoc 实际状态名 |
|--------|----------------|
| `rootcause` / `rootcaused` | Root-Caused（注意不是 Root_Cause/Root-Cause） |
| `codecommitted` | Code-Committed |
| `fixed` | Fixed |
| `tobeverified` | TobeVerified |
| `reopen` | ReOpen |
| `wontfix` | WONTFIX |
| `duplicated` | Duplicated |
| `invalided` | Invalided |

查询合法状态名与流转图：`GET /rest/field/bug/bug_status?api_key=xxx`（返回各状态的 `can_change_to` 列表）。

### 状态转换必填字段（Hard Gate）

**以下状态转换时，必须通过 `custom_fields` 参数提供对应的自定义字段，否则 `update_bug_status()` 拒绝执行：**

| 状态 | 必填字段 | Bugzilla 字段标签 |
|------|---------|------------------|
| **Root-Caused** | `cf_root_cause` | [1.Root Cause] |
| | `cf_resolution` | [2.Resolution] |
| | `cf_testing_suggestion` | [3.Testing Suggestion] |
| | `cf_impact_customer` | [4.Impact for customer] |
| **Fixed** | 无强制要求 | — |
| **Code-Committed** | 无强制要求 | — |
| **Need_Info** | 无强制要求 | — |

> ⚠️ **Hard Gate 机制**：`update_bug_status()` 在发送 PUT 请求前检查 `status_required_fields` 配置。
> 如果目标状态有必填字段但 `custom_fields` 缺失或为空，直接返回 error dict，API 调用不执行。
> 此检查在代码层实现，AI 无法绕过。

**使用示例**：

```python
# ❌ 错误 — Root-Caused 状态缺少必填字段
bug_commit("SPCSS01702402", "root cause analysis", "rootcaused")

# ✅ 正确 — 提供完整的 cf_* 字段
bug_commit("SPCSS01702402", "root cause analysis", "rootcaused",
           custom_fields={
               "cf_root_cause": "upm6910 charger IC cold-start timing...",
               "cf_resolution": "Increase delay from 30ms to 35ms...",
               "cf_testing_suggestion": "Re-test with Lecroy 8.4.1...",
               "cf_impact_customer": "Low — timer value change only"
           })
```

### 三层防御机制

| 层 | 类型 | 作用 |
|---|------|------|
| **A. Workflow Gate** | CC Workflow 运行时 | AI 必须调用 `bugzilla-commit` workflow，custom_fields 缺失时 workflow 拒绝执行 |
| **B. Code Gate** | `update_bug_status()` | 发送 PUT 前检查 `status_required_fields`，缺失返回 error dict |
| **C. Knowledge** | SKILL.md 本文档 | AI 参考，告知每个状态需要哪些字段 |

> ⚠️ **机制优先**：Layer A+B 是 Hard Gate，代码/运行时强制，AI 无法绕过。
> Layer C 是辅助知识，帮助 AI 在调用 workflow 前准备好正确的 custom_fields。

**AI 执行流程**：
```
准备 root cause 内容 + cf_* 字段
    → 调用 Workflow("bugzilla-commit", {bug_id, target_status, custom_fields, comment_text})
        → Workflow Phase 1: 校验 custom_fields
        → Workflow Phase 2: prepare_customer_reply() 生成预览
            → 用户 review/修改 .txt 文件
        → Workflow Phase 3: send_customer_reply() 发送
```

## 实例切换

| 关键词 | Bugzilla实例 | URL |
|--------|------------|-----|
| unisoc | Unisoc内网 | bugzilla.unisoc.com（办公网） |
| local | 本地模拟数据 | sample_bugs.json |

## 离线模式

通过 `--offline` 参数或 `instance=local` 启用离线模式，无需网络连接即可查询模拟Bug数据。

```bash
# 列出所有本地Bug
python bug_core.py --list

# 查询指定Bug（离线模式）
python bug_core.py BUG-20261 local

# 全局启用离线
python bug_core.py BUG-20262 --offline
```

环境变量 `OFFLINE_MODE=1` 全局生效。

## 搜索功能

```python
from bug_core import search_bugs

# 按关键词搜索
results = search_bugs("pd")  # 搜索含"pd"的Bug

# 按严重度筛选
results = search_bugs(severity="critical")

# 同时使用
results = search_bugs("pd", severity="critical")
```

## MCP Server 工具

统一的 MCP Server 提供 8 个工具（位于 mcp-server/server.py）：

| 工具 | 功能 | 依赖模块 |
|------|------|---------|
| `bug_info` | 获取Bug详细信息 | bug-core |
| `bug_comments` | 获取Bug评论列表 | bug-core |
| `bugs_search` | 搜索Bug（quicksearch） | bug-core |
| `bug_comment_add` | 发布评论 | bug-core |
| `bug_status_update` | 更新状态 | bug-core |
| `bug_workspace` | 创建工作区 | bug-workspace |
| `bug_logs` | 日志目录列表 | bug-logs |
| `generate_reply` | 生成客户回复模板 | bug-core 模板系统 |

- **bug-logs**: 日志目录列表 + unisoc 结构化评论解析
- **bug-workspace**: 工作区创建 + rayfile 下载命令 + 快捷方式
- **bug-hub**: 统一 dashboard，集成所有 bug-assistant 功能（含回复模板入口）
- **code-acquirer**: 代码材料获取 Agent，调用 code-puller 拉取内核/edk2 源码 (v2.2)
- **doc-acquirer**: 文档材料获取 Agent，调用 isupport-downloader 搜索下载文档 (v2.2)
- **material-acquirer**: 通用材料获取 Agent（保留兼容，新流程优先使用 code-acquirer + doc-acquirer 并行）

## 代码位置

| 文件 | 说明 |
|------|------|
| `bug_core.py` | 核心模块（~450行，含模板生成 ~180行） |
| `get_bug_folder_name.py` | **文件夹命名脚本** — 精确复刻 `fetch_buginfo_by_API_UI.py` 逻辑，AI 必须运行此脚本获取规范文件夹名 |
| `mcp-server/server.py` | 统一 MCP Server（+1 tool: generate_reply） |
| `config/bugzilla_instances.json` | 实例配置 |
| `config/customer_reply_templates.json` | 客户回复模板配置 |
| `data/sample_bugs.json` | 离线模拟数据 |
| `tests/test_core.py` | 核心测试套件 |
