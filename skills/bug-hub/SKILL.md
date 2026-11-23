---
name: bug-hub
description: Bugzilla Assistant 统一编排入口 — 链式调度子技能（bug-core/bug-workspace/pd_auth_analyse/log-analyzer/protocol-parser/keyword-vault/code-generator）完成端到端 Bug 分析。Unified orchestration entry for end-to-end bug analysis via chained sub-skills. Web Dashboard at port 8777.
version: "1.1"
tags: [dashboard, hub, bugzilla, web-ui, orchestration, routing]
---

# Bug Hub — 统一编排入口 / Unified Orchestration Hub

Bugzilla Assistant 核心编排器，负责链式调度子技能完成端到端 Bug 分析。同时提供 Web Dashboard（端口 8777）作为浏览器端人工操作入口。

Unified orchestrator for end-to-end bug analysis via chained sub-skills. Dual entry: conversational `/bug-hub` (AI-driven) + Web Dashboard (http://127.0.0.1:8777).

---

## 触发条件 / Activation Triggers

以下情况激活本 Skill：

- 用户输入 `/bug-hub Bug XXXXXX`（如 `/bug-hub Bug 3523391分析`）
- 用户输入 `/bug-hub unicaseXXXXXX`（如 `/bug-hub unicase015809`）— Unicase 工单号，自动解析为 Bugzilla Bug
- 用户说 **"分析Bug"**、**"Bug分析"**、**"启动Bug分析流程"**、**"端到端分析"**、**"全流程分析"**
- 用户需要对单个 Bug 做完整分析（查询 + 附件下载 + 日志分析 + 协议解析 + 报告生成）
- 用户提到 **"Bug Hub"**、**"bughub"**、**"bugzilla分析"**
- 用户需要通过 Dashboard 查看/操作 Bug 相关模块

Activation keywords in English:
- `analyze bug` / `bug analysis` / `end-to-end analysis` / `full flow analysis` / `Bug XXXXX`

---

## 子技能路由表 / Sub-skill Routing Table

**规则：bug-core 返回 Bug 信息后，必须检查 Bug title/summary 是否命中下表关键字。命中则必须调用对应 Skill。**

**Rule: After bug-core returns bug info, MUST check if the bug title/summary matches any keyword in this table. If matched, MUST invoke the corresponding Skill.**

| 触发条件（Bug 标题/评论含关键字） | 调用子技能 | 说明 |
|------|------|------|
| PD认证 / cts测试 / 认证失败 / lecroy / typec fail / Type-C / USB PD / TEST.PD.\* / CERTIFICATION FAIL / PD protocol / PD auth | **pd_auth_analyse** | 6-Phase PD 领域深度分析（优先级最高，检测到则强制执行） |
| Bug ID（5位以上数字、SPCSS开头、或 `unicase\d+` Unicase工单号） | **bug-core** | Bug 信息查询、智能摘要、评论提取。Unicase ID 自动通过 alias/quicksearch 解析为 Bugzilla ID |
| 下载附件 / 创建工作区 / UNC路径 / rayfile / 附件解压 | **bug-workspace** | 工作区创建 + 附件下载 + 解压 |
| 日志分析 / kernel log / dmesg / logcat / 搜索日志 / 日志错误 | **log-analyzer** | 日志深度分析、关键字搜索 |
| 协议解析 / trace / Lecroy / .usb / PD trace / PD协议 | **protocol-parser** | PD 协议解析、.usb 文件解码 |
| 关键字管理 / keyword / 添加关键词 | **keyword-vault** | 关键字库管理、模式维护 |
| 代码生成 / code gen / 生成脚本 / 生成代码 | **code-generator** | 代码/脚本生成 |

> **路由优先级：** pd_auth_analyse > bug-core > bug-workspace > log-analyzer/protocol-parser > keyword-vault/code-generator
>
> 多关键字命中时，按优先级顺序依次调度。

---

## 强制编排规则 / Mandatory Orchestration Rules

1. **入口规则 / Entry Rule**：所有 Bug 分析必须先经过 **bug-core** 查询，不得跳过。bug-core 负责获取 Bug 基本信息、评论、引导方向，为后续分析提供上下文。
2. **关键字检查 / Keyword Check**：bug-core 返回 Bug 信息后，**必须**检查 Bug title/summary/comments 是否命中路由表关键字，命中则必须调用对应 Skill。
3. **PD 认证强制路由 / PD Auth Mandatory Routing**：如果命中 PD 认证相关关键字（PD认证 / cts测试 / 认证失败 / lecroy / typec fail / Type-C / USB PD / TEST.PD.\*），必须在 bug-workspace 下载附件后，调用 **Skill: pd_auth_analyse** 进行 6-Phase 深度分析。**不得在 /bug-hub 主会话中绕开 pd_auth_analyse 直接分析。**
4. **不得跳过 / No Skipping**：不得跳过子技能直接用主会话上下文做分析。每个子技能有独立的领域知识、规则和产物标准，跳过会导致分析不完整。
5. **Compaction 后保持 / Persist After Compaction**：上下文压缩后以上规则**仍需遵守**。不得因上下文压缩丢失流程约束而发送未经审核的输出（参见 SPCSS01696773 事故教训：Compaction 后 Pending Tasks 触发错误行为）。
6. **Baseline Bootloader 验证 / Bootloader Verification**：bug-core 返回 Bug 信息后、进入代码分析前，**必须**通过 `platform/manifest` 确定正确的 bootloader 类型。

   判定流程（按优先级）：
   a) 从 `cf_base_on_ver` 提取 VND 分支名（如 `SPRDROID15_VND_MAIN` → `sprdroid15_vnd_main`）
   b) 查 `CODE_INDEX.md` → 已有条目直接给出 Gerrit 路径
   c) `git archive` 提取 manifest（~2-3s，零 clone，**唯一权威来源**）：
      ```
      git archive --remote=ssh://xianjun.zeng@gerrit.unisoc.com:29418/platform/manifest \
          <vnd_branch> bsp/bootloader/default.xml | tar xO
      ```
   d) 解析 XML → 判定 `<project name="bsp/bootloader/...">`：
      - 只有 `bsp/bootloader/lk` → **LK** bootloader
      - 只有 `bsp/bootloader/edk2` → **EDK2** bootloader
      - 两者都有 → **两者都需分析**（部分基线多 bootloader 共存）

   **⛔ 禁止从 `cf_base_on_ver` 的 Android 版本号直接推测 bootloader 类型。**
   **必须通过 manifest 验证后才可写 "分支 → LK" 或 "分支 → EDK2" 结论。**

   涉及以下 Component 的 Bug **必须执行此检查**：
   Power / PMIC / Charger / Sleep / LDO / Deep Sleep / Light Sleep / DVFS

   检查结果必须明确输出：`VND分支: xxx → manifest验证: LK/EDK2/共存 → 代码路径: xxx`

   **如果 CODE_INDEX 缺少对应 bootloader 条目 → 调用 code-puller 拉取后再继续分析。**
   **违反本规则的教训**: Bug 3616041(unicase026305) — 从 cf_base_on_ver 推测 Android 16→LK，实际检查 manifest 发现 sprdroid15_vnd_main 用 EDK2（非 LK），sprdroid16_vnd_main_tv 是 LK+EDK2 共存。旧启发式在三组实验中全部失败。

---

## 标准编排流程 / Standard Orchestration Flow

```
用户输入: /bug-hub Bug XXXXXX 分析
  或:     /bug-hub unicaseXXXXXX (Unicase工单号)
                │
                ▼
Phase 0 ─── Unicase ID 解析 (如适用)
│   unicase\d+ 格式 → REST API quicksearch/alias 查找 Bugzilla Bug
│   产物: 解析到的 Bugzilla Bug ID
├──────────────────────────────────────────────┤
Phase 1 ─── Skill: bug-core
│   查询 Bug 基本信息、解析评论
│   提取引导方向、UNC 路径、Gerrit 链接
│   产物: Bug 信息摘要表（含 cf_base_on_ver）
│   ⚠️ 完成后检查路由表关键字 ────────────────┐
├──────────────────────────────────────────────┤
Phase 1.5 ─── Baseline Bootloader 验证 (强制)
│   从 cf_base_on_ver 提取 VND 分支名
│   CODE_INDEX 查缓存 → git archive 从 platform/manifest 提取
│   bsp/bootloader/default.xml 解析 → LK / EDK2 / 共存 判定
│   涉及 Power/PMIC/Sleep/LDO 的 Bug 必须执行
│   ⛔ 禁止从 Android 版本号直接推测 bootloader
│   产物: Bootloader 类型 + 代码路径
├──────────────────────────────────────────────┤
Phase 2 ─── Skill: bug-workspace               │
│   创建工作区、下载附件、解压                   │
│   产物: 工作区 + 附件文件                     │
├──────────────────────────────────────────────┤
│                                              ▼
│   ┌─ 命中 PD 认证关键字? ──────────────────────────────┐
│   │  YES → Skill: pd_auth_analyse (6-Phase 深度分析)    │
│   │         Phase 1-6: 信息收集→失败定位→Trace→Log→     │
│   │         历史参照→代码根因→SUMMARY.html              │
│   │  NO  → 主会话继续并行分析 ─────────────────────────┤
│   └────────────────────────────────────────────────────│
│                                              │
├──────────────────────────────────────────────┤
Phase 3 ─── 并行 Agent 分析 (主会话调度)        │
│   ├── Agent A: log-analyzer (kernel log)      │
│   ├── Agent B: protocol-parser (trace)        │
│   └── Agent C: code-acquirer (源码获取, 可选) │
├──────────────────────────────────────────────┤
Phase 4 ─── 综合报告生成 (AI 主会话)
│   合并各子技能/Agent 产物
│   生成分析报告到工作区
│   ⚠️ 报告文件名必须使用标准化格式:
│      {topic}_{type}_{keyword}__{YYYYMMDD}.md
│      示例: 3556390_analysis_efuse__20260916.md
│      Bug 场景: common.report_utils.generate_report_filename_from_bug()
│      通用场景: common.report_utils.generate_report_filename(topic, type, keyword)
│   type 枚举: analysis | harness | patch_eval | summary | ...
│   keyword 必填: 会话相关的简短关键词
```

---

## Web Dashboard / Web 仪表盘

访问地址：**http://127.0.0.1:8777/**

Auto-started on Claude session start alongside CC Hub.

### Dashboard 模块 / Dashboard Modules

| 模块 | 功能 |
|------|------|
| bug-core | Bug 查询/搜索界面 |
| bug-workspace | 工作区创建/管理 |
| log-analyzer | 日志分析器 |
| protocol-parser | PD 协议解析器 |
| keyword-vault | 关键字库管理 |
| code-generator | 代码生成器 |

> **注意：** Dashboard 为浏览器端人工操作入口，模块独立，无自动化编排能力。完整端到端分析请使用 `/bug-hub` 会话内流程。

### 客户回复模板入口 / Customer Reply Template Entry

Dashboard 中集成了 `generate_reply` MCP 工具，用于生成客户回复：
- 按场景/关键词自动匹配模板
- 统一格式：`Dear CUS` + 内容 + `Thanks`
- 当前模板：UMS512 PD/Charge IC 场景

---

## 对比：/bug-hub 会话 vs Web Dashboard

| 维度 | `/bug-hub` 会话 | Web Dashboard |
|------|:--------------:|:-------------:|
| 交互方式 | AI 主动编排 | 用户手动点击 |
| 自动化 | 全自动端到端 | 需人工操作每一步 |
| 灵活性 | 低（固定流程） | 高（任意顺序） |
| PD 认证支持 | 自动路由到 pd_auth_analyse | 手动切换模块 |
| 适用场景 | 批量分析、快速分析 | 单步调试、单模块使用 |
| 底层代码 | 同一套 Python 模块 | 同一套 Python 模块 |

---

## 与会话压缩 / Compaction Resilience

上下文压缩是本流程的关键风险。单次 Bug 端到端分析可能触发 4-5 次 compaction。

**压缩后恢复策略：**
1. 压缩后立即检查当前 Phase 进度，确认已完成和待执行的步骤
2. 重新确认 Bug ID 和 Case 目录路径（这些不会被压缩）
3. 重新检查路由表关键字（防止压缩后丢失 PD 认证判定）
4. **绝不**在压缩后发送未经审核的输出（参见 SPCSS01696773 教训）