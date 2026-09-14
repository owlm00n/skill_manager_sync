# Process-Failure Analysis — Bug 3523391 TEST.PD.PROT.SNK.12

**分析时间**: 2026-09-11
**分析对象**: 上一轮 6-Phase PD 认证分析（2026-09-09 产出），用户确认为错误
**分析目的**: 剖析 5 个用户识别的错误点的根因流程失败，并提出 `SKILL.md` 级别的预防措施

---

## 总览

| # | 用户识别的错误点 | 流程失败根因（一句话） | 涉及 Skill 阶段 |
|---|----------------|----------------------|----------------|
| 1 | Trace 文件存在却被标记缺失 | Phase 1 附件识别只看文件后缀，未做"HTML 报告→同级 trace 文件夹"关联推断 | Phase 1 |
| 2 | 所有来源标注缺少全路径 | Skill 从未要求全绝对路径标注，核心原则仅说"可回溯到证据" | 全局核心原则 + 所有 Phase |
| 3 | 失败点定位 (Phase 2 §2.3) 完全编造 | Skill 未强制"Lecroy 报告让你查 trace → 必须先读 trace 再下结论"，允许从 kernel log 反推一个报告里不存在的失败步骤 | Phase 2 + Phase 3 |
| 4 | Comment #27 列出却被忽略 | Phase 1 收集了评论但未将最新客户方向性评论 FLAG 为"引导方向"，Phase 2/3/4 无交叉校验关卡 | Phase 1 + 2/3/4 |
| 5 | (由其他 agent 负责) | — | — |

---

## Point 1 — Trace 文件存在却被标记缺失

### (a) 上一轮分析做了什么

Phase 1 产物 `C:\Users\xianjun.zeng\.claude\skills\pd_auth_analyse\data\cases\3523391_TEST.PD.PROT.SNK.12\01_test_case_info\01_test_case_info.md` 第 117-126 行的"可用/缺失材料汇总"表将 `.usb` trace 标记为"❌ 缺失"：

| 类别 | 状态 | 说明 |
|------|:----:|------|
| Lecroy Trace (.usb) | ❌ 缺失 | 无二进制 trace 文件，无法做协议层精确时序分析 |

Phase 3 产物 `C:\Users\xianjun.zeng\.claude\skills\pd_auth_analyse\data\cases\3523391_TEST.PD.PROT.SNK.12\03_trace_analysis\03_trace_analysis.md` 第 5 行随即声明：

> ⚠️ **注意**: 无 Lecroy 二进制 `.usb` trace 文件，本分析基于 Lecroy HTML 报告和 Kernel Log 中记录的 PD 消息序列进行协议层面分析。

### (b) 为什么这是错的

用户确认以下文件**实际存在**（用户原话："trace文件明明存在...通常有html的lecroy报告，在同级目录就会有trace的文件夹，里面就是trace"）：

- `02_TEST.PD.PROT.SNK.12_Rev3ChkdSnk_FAIL.usb` — Rev3ChkdSnk 失败的 trace
- `01_..._Rev2Snk.usb` — Rev2Snk 通过的 trace
- `pd.sqlite` — 已解码 PD 数据包数据库（可查询）
- `USB_ComplianceTestLog.html` — 逐步测试日志
- `USB_ComplianceSessionLog.html` — 会话日志
- Debug `.inc` / `.ginc` 配置文件（`Debug\` 文件夹）

这些文件与 HTML Lecroy 报告处于同级或兄弟目录。Phase 1 只做了"按文件后缀分类"，没有做"HTML 报告 → 同级目录必有 trace 文件夹"的关联推断，因此把一片丰富的 trace 数据判成了"缺失"。

### (c) 根因流程失败

**失败在 Phase 1（信息收集）的"附件自动识别规则"**。`C:\Users\xianjun.zeng\.claude\skills\pd_auth_analyse\SKILL.md` 第 54-64 行的识别规则表只按"单个文件后缀"分类：

| 特征 | 分类 |
|------|------|
| `.usb` 文件 | Lecroy Trace |
| `*.html` | Lecroy 报告 |
| ... | ... |

规则没有一条说："当发现 Lecroy HTML 报告时，必须主动在其同级/兄弟目录搜索 trace 文件夹（含 `.usb`）以及 `pd.sqlite`、`USB_ComplianceTestLog.html`、`Debug\` 配置文件夹"。因此 Phase 1 把 `.usb` 的存在与否完全交给了"是否碰巧被遍历到"，没有关联推断。

**Skill 层面的缺口**：
1. Phase 1 的附件识别规则是"被动分类"，不是"主动推断"。
2. Phase 3 的 trace 分析入口只区分"有 `.usb` 且有解析 skill"vs"无 `.usb`，读 HTML"，没有中间态："`.usb` 存在但作为二进制无法直接读文本时，应优先查 `pd.sqlite` / `USB_ComplianceTestLog.html` 等已解码/可读同源数据"。
3. Skill 从未定义"trace 不可读为文本 ≠ trace 缺失"这一关键区分。

### (d) 预防复发的具体 Skill 变更

1. 在 Phase 1 "附件自动识别规则"中新增一条**关联推断规则**：当发现 HTML Lecroy 报告/结果文件（如 `Teledyne LeCroy USB Compliance Result*.html`、`USB_ComplianceTestLog.html`、`USB_ComplianceSessionLog.html`）时，必须主动在同级目录和兄弟目录搜索 trace 文件夹（含 `.usb`），以及 `pd.sqlite`、`user data.db`、`USB_ComplianceTestLog.html`、`Debug\` 配置文件夹（`.inc`/`.ginc`）。
2. 在"降级规则"表中新增一行：trace 文件存在但作为二进制不可直接读文本时，**禁止**标记"缺失"，应改为"存在 — 需解码"，并优先查 `pd.sqlite`（可查询的已解码 PD 数据包）、`USB_ComplianceTestLog.html`（逐步时序）等同源可读数据。
3. 在 Phase 3（Trace 深度分析）中明确：trace 数据源优先级为 `pd.sqlite` > `USB_ComplianceTestLog.html` > `.usb`（二进制，需解码器）> Debug 配置；"trace 无法以文本读取"不等于"trace 缺失"。

---

## Point 2 — 所有来源标注缺少全路径

### (a) 上一轮分析做了什么

所有 Phase 产物的来源标注只用了相对路径或裸文件名，例如：

- Phase 2 `C:\...\02_failure_location\02_failure_location.md` 第 100 行：`**来源**: \`0-kernel.log\` lines 11035-11389`
- Phase 3 `C:\...\03_trace_analysis\03_trace_analysis.md` 第 19 行：`> **来源**: Kernel Log PD 消息记录 + PD 3.1 规范状态机定义`
- Phase 4 `C:\...\04_log_analysis\04_log_analysis.md` 第 5 行：`**Log 来源**: \`0-kernel.log\` lines 11030-11389`
- Phase 1 `C:\...\01_test_case_info\01_test_case_info.md` 第 12-18 行的路径列写的是 `Attachements/20260827_155005/...` 这样的相对片段。

用户原话："你所有的来源标注都没有全路径"。

### (b) 为什么这是错的

相对路径/裸文件名无法被另一个 agent 或另一个会话可靠地定位回原始证据文件。尤其在 Windows + 多盘符 + 多层 `Attachements/` 嵌套的环境下，`0-kernel.log` 这个名字可能出现在多个测试轮次的目录里。没有全路径就没有真正的"可回溯"。

### (c) 根因流程失败

**失败在全局核心原则**。`C:\Users\xianjun.zeng\.claude\skills\pd_auth_analyse\SKILL.md` 第 17-23 行的 5 条核心原则中，第 3 条只说"每次分析都能回溯到证据 — log 行号、trace 时间戳、规范条款引用"，**从未要求全绝对路径**。各 Phase 的产物清单（第 91-95、114-120、136-140、155-160 行）也只列字段名，没有强制"来源必须含全路径"。

**Skill 层面的缺口**：核心原则把"行号/时间戳"当成可回溯的全部，忽略了"文件定位"这一更基础的维度。

### (d) 预防复发的具体 Skill 变更

1. 新增**核心原则 #6**：每一个数据点、log 行引用、trace 事件、证据引用都必须包含**完整绝对文件路径**（+ 行号，如适用）。仅相对路径或裸文件名是被禁止的。
2. 在每个 Phase 的产物部分重申此要求。

---

## Point 3 — 失败点定位 (Phase 2 §2.3) 完全编造

### (a) 上一轮分析做了什么

Phase 2 产物 `C:\...\02_failure_location\02_failure_location.md` 第 62-75 行如实引用了 Lecroy 报告：

```
└─ Rev3ChkdSnk: FAIL
    └─ "Test scenario aborted. Please check the trace file to determine the cause."
```

但紧接着第 78-84 行，分析者凭空发明了一个具体的失败步骤：

| 定位维度 | 结果 |
|----------|------|
| **失败步骤** | **步骤 4→5 转换失败** (PE_PRS_SNK_SRC_Transition_to_off → PE_PRS_SNK_SRC_Assert_Rp) |
| **失败类型** | **tPSSourceOffTimer 超时** (835ms 后触发 ERROR_RECOVERY) |
| **直接表现** | DUT 关闭 VBUS 后，无法完成 CC 线从 Rd→Rp 的切换... |

Phase 2 第 88-99 行还给出了一段"Kernel Log 时间线"作为佐证，标注来源 `0-kernel.log lines 11035-11389`。

### (b) 为什么这是错的

Lecroy 报告的原始判定是一个**通用中止**（Error 0xFFF5, "Test scenario aborted. Please check the trace file to determine the cause."）。报告**明确告诉分析者"请查 trace 文件来确定原因"**。但分析者：

1. 没有读 trace 文件（因为 Point 1 已把 trace 标成"缺失"）。
2. 转而从 kernel log 反推了一个"步骤 4→5, tPSSourceOffTimer 超时"的结论。
3. 把这个从 kernel log 编造的结论当成 Lecroy 报告的失败点写进 Phase 2。

这是一个典型的**级联错误**：Point 1（trace 标缺失）→ Point 3（无法读 trace，被迫从 log 编造失败点）→ 错误根因（Phase 4 把 `pr_swap_no_chk_detach` 提前调用当成根因，置信度还标了 5 星）。

用户原话确认 Lecroy 报告**只**说了通用中止，"步骤 4→5, tPSSourceOffTimer timeout"是编造的。

### (c) 根因流程失败

**失败在 Phase 2 和 Phase 3 的关卡设计**。`C:\Users\xianjun.zeng\.claude\skills\pd_auth_analyse\SKILL.md`：

- Phase 2（第 98-120 行）要求"阅读 Lecroy fail 报告，提取 FAIL 判定信息"并"对照测试步骤序列，定位具体 FAIL 在第几步"。但 Skill **没有规定**："当 Lecroy 报告判定为通用中止并明确要求查 trace 时，禁止在未读 trace 的情况下从 kernel log 反推失败步骤。"
- Phase 3（第 122-140 行）要求"围绕 Phase 2 定位的失败步骤分析 trace"。但 Phase 2 已经给了它一个编造的失败步骤，Phase 3 只能顺着编下去。
- 核心原则 #1（第 18 行）"先理解测试在测什么，再看它哪里失败了"被违反——分析者跳过了"测试到底在哪一步 fail"的证据收集。

**Skill 层面的缺口**：Skill 没有"报告让你查 trace → 必须先查 trace 再下结论"这一硬关卡；也没有"Lecroy 报告的通用中止不得作为具体失败步骤定位的依据"这一约束。

### (d) 预防复发的具体 Skill 变更

1. 在 Phase 2 新增约束：当 Lecroy 报告判定为通用中止（如 "Test scenario aborted. Please check the trace file"）时，**禁止**在未读 trace 的情况下从 kernel log 推断失败步骤；失败步骤定位必须以 trace 证据为准。
2. 通过 Point 1 的 Skill 修复（trace 不再被误标缺失），从源头消除"因为 trace 缺失所以从 log 编造"的诱因。
3. 通过 Point 4 的 Skill 修复（引入客户引导方向交叉校验），Phase 2 的失败步骤结论必须与 Comment #27 的方向对齐——Comment #27 明确说"PD 3.0 第二次 PR_Swap 未收到 PS_RDY"，而编造的"步骤 4→5 CC 线切换失败"与此方向不符，交叉校验关卡会拦住。

---

## Point 4 — Comment #27 列出却被忽略

### (a) 上一轮分析做了什么

Phase 1 产物 `C:\...\01_test_case_info\01_test_case_info.md` 第 88-100 行的"1.6 关键评论汇总"表确实列出了 Comment #27：

| #27 | Yongqing.Wang | 9/8 | PD 2.0 首次 PR_Swap 成功。PD 3.0 第二次 PR_Swap 未收到 PS_RDY。VBUS 时序日志匹配 |

但 Phase 2/3/4 的产物中**没有一处**引用 Comment #27 或以其为分析方向。Phase 2 定位"步骤 4→5 CC 线切换失败"，Phase 3 声称"CC 检测被禁用导致状态机卡死"，Phase 4 给出"tPSSourceOffTimer 超时"——全部偏离 Comment #27 给出的方向（第二次 PR_Swap 未收到 PS_RDY）。

用户原话："1.6 关键评论汇总，的最后转入给我的comment，是关键参考方向，但是你直接忽略了"。

### (b) 为什么这是错的

Comment #27 是客户/现场工程师给出的**最新、最权威的方向性指引**（9/8 日期，是所有评论中最新的）。它明确指出：

1. PD 2.0 **首次** PR_Swap 成功
2. PD 3.0 **第二次** PR_Swap 失败
3. 失败表现是**未收到 PS_RDY**
4. VBUS 时序日志匹配（即 VBUS 行为正常）

上一轮分析不仅忽略了"第二次"这个关键限定（它的失败点定位完全没有区分第几次 PR_Swap），还把方向带偏到 CC 线检测/`pr_swap_no_chk_detach` 上。收集了却不使用，等于没收集。

### (c) 根因流程失败

**失败在 Phase 1 的评论处理以及 Phase 2/3/4 缺乏引导方向交叉校验**。`C:\Users\xianjun.zeng\.claude\skills\pd_auth_analyse\SKILL.md`：

- Phase 1（第 78-95 行）的动作里只有"如有 Bug ID 且环境有 bug 查询 skill → 自动拉取 Bug 信息和附件"，没有"提取并 FLAG 最新客户方向性评论为引导方向"这一步。
- Phase 1 产物清单（第 91-95 行）没有"关键引导方向"字段。
- Phase 2/3/4 的产物清单没有"结论与引导方向的对齐/矛盾说明"字段。
- 整个 Skill 没有任何关卡强制要求"后续分析必须以客户最新方向性评论为框架并交叉校验"。

**Skill 层面的缺口**：Skill 把 Bug 评论当成"背景信息"而不是"分析方向指令"。收集即终点，没有向下游传递。

### (d) 预防复发的具体 Skill 变更

1. 在 Phase 1 新增一步：提取并 FLAG 最新（编号最大的）客户/现场工程师评论为"🔑 关键引导方向 (guiding direction)"，在 Phase 1 产物中新增对应字段。
2. 在 Phase 2/3/4 各自新增一个交叉校验关卡：该 Phase 的结论必须显式说明与引导方向对齐还是矛盾，矛盾时必须给出解释。

---

## Point 5 — 按 Comment #27 重新分析（由其他 agent 处理）

本 Point 的重新分析工作由其他 agent 负责，不属于本流程失败分析的范畴。此处仅记录 Comment #27 的方向作为上下文：

> #27 Yongqing.Wang 9/8: PD 2.0 首次 PR_Swap 成功。PD 3.0 第二次 PR_Swap 未收到 PS_RDY。VBUS 时序日志匹配

方向要点：
- 区分"首次"vs"第二次"PR_Swap
- 失败表现聚焦"未收到 PS_RDY"
- VBUS 时序正常（排除 VBUS 异常方向）

这一方向与上一轮 Phase 2/3/4 的结论（CC 线检测禁用、tPSSourceOffTimer 超时、步骤 4→5 失败）**直接矛盾**，正是 Point 4（忽略引导方向）所导致的。

---

## 级联关系总结

```
Point 1 (trace 误标缺失)
   └→ Point 3 (无法读 trace → 从 kernel log 编造失败步骤)
        └→ Phase 4 错误根因 (pr_swap_no_chk_detach 提前调用，5 星置信)
             └→ 完全偏离真实方向 (Point 5: 第二次 PR_Swap 未收到 PS_RDY)

Point 2 (无全路径) — 独立缺陷，加剧可回溯性丧失

Point 4 (忽略 Comment #27) — 独立缺陷，本可在 Phase 2 交叉校验关卡拦住 Point 3 的编造
```

Point 1 是根，Point 3 是级联后果，Point 4 是本可防止级联却失效的关卡，Point 2 是贯穿全程的可回溯性缺陷。

---

*Process-Failure Analysis 完成 | 2026-09-11*
