---
name: pd-auth-analyse
description: PD认证问题分析Skill — 以单个Bug为上下文，串联Bug信息/证据/kernel log/.usb trace/客户代码，输出可落地的修复建议
version: "0.2.0"
tags: [pd, auth, certification, bug-analysis, unisoc, type-c]
triggers:
  - "pd认证"
  - "pd auth"
  - "认证失败"
  - "type-c认证"
  - "cts测试"
  - "pd trace"
  - "sourcecap"
  - "pr_swap"
  - "dr_swap"
  - "分析Bug"
  - "pd_analyse"
  - "bug分析"
---

# PD 认证 Bug 分析工作流

以**单个 Bug 为上下文**，自动串联 Bug 信息 / 证据 / kernel log / .usb trace / 客户代码，输出可落地的修复建议。

> 设计定稿：[`docs/pd_auth_workflow_plan.md`](../../docs/pd_auth_workflow_plan.md)
> 项目总览：[`docs/PROJECT_OVERVIEW.md`](../../docs/PROJECT_OVERVIEW.md)
> 机器可读配置：[`src/config/skill_manifest.json`](../../src/config/skill_manifest.json)

## 触发

- 用户说"分析 Bug <BUG_ID>"、"pd_analyse <BUG_ID>"、"看这个认证失败 Bug"
- 用户粘贴 Bug 描述并要求定位根因 / 出修复建议
- 用户提到 `pd认证` / `cts测试` / `认证失败` 等关键字

## 入口

### 全自动（推荐）

```bash
python -m src.run_pipeline <BUG_ID> [--force] [--step N]
```

- `--force`：强制重跑（忽略 manifest.json 幂等）
- `--step N`：只跑第 N 步（N ∈ 1..7）

### 单步执行

```bash
python -m src.lib.step1_bug_info <BUG_ID> [--force]
python -m src.lib.step2_evidence <BUG_ID> <CASE_PATH> [--force]
python -m src.lib.step3_hypothesis <CASE_PATH> [--force]
python -m src.lib.step4_log_analysis <CASE_PATH> [--force]
python -m src.lib.step5_trace_analysis <CASE_PATH> [--force]
python -m src.lib.step6_code_analysis <CASE_PATH> [--force]
python -m src.lib.step7_fix_suggestion <CASE_PATH> [--force]
```

## 全局约定

### Case 目录

```
data/cases/<BUG_ID>_<TEST_ID>/
├── 00_input/attachments.json
├── 01_bug_info.{json,md}
├── 02_evidence.md
├── 03_hypothesis.md
├── 04_log_analysis.md
├── 05_trace_analysis.md
├── 06_code_analysis.md / 06_code_findings.json
├── 07_fix_suggestion.md
├── SUMMARY.md
└── manifest.json
```

- TEST_ID 未知时先建 `<BUG_ID>_pending/`，Step 1 提取到 TEST_ID 后重命名
- 每步产物同时有 JSON（机器读）和 Markdown（人读）
- 每步产物开头必须有"分析结果结论"区

### 幂等

- 每步执行前读 `manifest.json`，比对输入 hash
- 未变则跳过并提示"复用上次结果，如需重跑加 --force"
- 每步执行后更新 `manifest.json`

### 执行模式

全程自动（不停下等确认），用户做事后确认；不满意就 `--force` 重跑该步。

## 7 步工作流

### Step 1: Bug 信息获取

- **输入**：`BUG_ID`
- **数据源**：`knowledge/bugs/pd_bugs_detail.json` 优先 → bug-core skill 回退
- **产物**：
  - `01_bug_info.json`：标题/状态/时间/描述/评论/附件列表/patch 链接
  - `01_bug_info.md` 结论区：**附件清单（分类）** / **Bug 类型判定** / **提取的 TEST_ID** / **失败现象关键句**
- **早退 gate**：非 PD 认证类 → `manifest.status="early_exit_not_pd_auth"`，停止后续步骤
- **副作用**：提取到 TEST_ID → `<BUG_ID>_pending/` 重命名为 `<BUG_ID>_<TEST_ID>/`

### Step 2: 证据映射

- **输入**：Step 1 附件清单 + bug-workspace 目录（先搜 `~/bug*/<BUG_ID>*/` 及常见盘符，找不到问用户）
- **产物**：
  - `00_input/attachments.json`：绝对路径 + name + type（`.usb` / `kernel_log` / `dmesg` / `patch` / `customer_code`）+ size + hash
  - `02_evidence.md`：证据清单 + **缺口提示**

### Step 3: 根因假设 & 排查地图

- **输入**：Step 1 结论 + `knowledge/bugs/top_issue_patterns.md` + `knowledge/specs/*.md`
- **外部依赖**：调用 `keyword-vault` skill
  - 位置：`C:\Users\xianjun.zeng\.skills-manager\skills\keyword-vault\`
  - 调用：
    - `python keyword_vault.py export -o data/cases/<case>/00_input/vault_kw.json`
    - `python keyword_vault.py search "<失败现象关键句>"`
- **产物**：`03_hypothesis.md` — top-3 候选根因，每条含：
  - 置信度 / 支持证据 / Log 搜索关键字 / 代码定位函数名

### Step 4: Log 分析

- **输入**：`attachments.json` 中 type=kernel_log/dmesg 的所有文件 + Step 3 关键字集合
- **外部依赖**：调用 `log-analyzer` skill
  - 位置：`C:\Users\xianjun.zeng\.skills-manager\skills\log-analyzer\`
  - 调用：
    - `python log_analyzer.py <logfile> --role pd_engineer --json`
    - `python log_analyzer.py <logfile> --deep`
    - `python log_viewer_v2.py <logfile> --vault-json 00_input/vault_kw.json --role pd_engineer`
- **产物**：`04_log_analysis.md` — 关键事件时间线（时间戳 + 行号 + 原文 + 命中关键字 + 归属候选根因）

### Step 5: Trace 分析

- **输入**：`attachments.json` 中 `.usb` 文件 + Step 3 关注消息类型
- **外部依赖**：调用 `protocol-parser` skill
  - 位置：`C:\Users\xianjun.zeng\.skills-manager\skills\protocol-parser\`
  - 调用：
    - `python smart_extractor.py <logfile>` → JSON（含置信度）
    - `python protocol_combiner.py <logfile>` → 力科风格 HTML
- **处理**：先按 `docs/ref/usb_trace_parsing_report.md` 尝试二进制解析，失败提示"请用 Lecroy 导出为文本后重试"
- **产物**：`05_trace_analysis.md`
  - 复用 Protocol Parser 报告格式
  - 附合规检查点（对照 `knowledge/specs/pd_message_sequences.md`）
  - 按事件序列对齐 Step 4 log 时间线

### Step 6: 代码 & Patch 匹配

- **输入**：Step 3 函数名列表 + Step 1 patch/gerrit 链接 + `attachments.json` 中 type=customer_code + 参考代码根目录
- **参考代码根目录**：`F:\05_Code\UNISOC\SPRDLINUX6.6_KERNEL_MAIN_W26.12.4_codeonly\idh.code\kernel6.6\unisoc\drivers\`
  - 搜索子目录: `unisoc_platform/sprd_charger/`, `unisoc_platform/usb/typec/`, `usb/typec/`
  - 函数搜索策略: 精确匹配优先 → 模糊 token 回退（如 `sgm41512_set_vinlimit` → token `sgm41512` + `vinlimit`）
- **处理**：定位函数 → 客户代码 vs 参考代码 diff → 验证已合 patch 是否在客户代码中
- **产物**：
  - `06_code_analysis.md`（人读）：相关代码定位 / 现状 vs 期望对比 / 客户 diff 情况
  - `06_code_findings.json`（机器读，供 Step 7）

### Step 7: 综合修复建议

- **输入**：Step 3 ~ Step 6 全部产物
- **产物**：
  - `07_fix_suggestion.md`：最终根因结论（含置信度）+ 代码级 diff 建议 + 参数调优建议 + 复测验证步骤
  - `SUMMARY.md`：Bugzilla-friendly 精华版
- **后处理**：调用 `python keyword_vault.py learn "<最终根因描述文本>" -d <最匹配方向>` 回写自学习

## 外部 skill 调用链

| Step | Skill | 位置 | 调用方式 |
|------|------|------|----------|
| 3 | keyword-vault | `C:\Users\xianjun.zeng\.skills-manager\skills\keyword-vault\` | `keyword_vault.py export / search / learn / new-direction` |
| 4 | log-analyzer | `C:\Users\xianjun.zeng\.skills-manager\skills\log-analyzer\` | `log_analyzer.py <log> --role pd_engineer --json [--deep]` |
| 5 | protocol-parser | `C:\Users\xianjun.zeng\.skills-manager\skills\protocol-parser\` | `smart_extractor.py <log>` 或 `protocol_combiner.py <log>` |

## 知识库依赖

- `knowledge/bugs/pd_bugs_detail.json`
- `knowledge/bugs/top_issue_patterns.md`
- `knowledge/bugs/troubleshooting_workflow.md`
- `knowledge/specs/pd_protocol_timers.md`
- `knowledge/specs/pd_message_sequences.md`
- `knowledge/specs/pd_state_machines.md`
- `docs/ref/usb_trace_parsing_report.md`
- `docs/ref/usb_trace_reading_methodology.md`

## 自学习

统一通过 `keyword-vault` 的 `learn` / `new-direction` 命令回写。`log-analyzer` 无独立持久化库，其关键字数据由 keyword-vault 提供。

触发时机：每次 Step 7 完成后，由本 skill 自动调用。
