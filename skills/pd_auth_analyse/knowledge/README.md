# PD 认证知识库

本目录是本项目的核心知识库，包含 PD 协议规范、CTS 测试流程、Bug 失败模式和方法论。

---

## 目录结构

| 目录 | 内容 | 入口 |
|------|------|------|
| `specs/` | PD 协议规范 + CTS 测试规范 PDF | [`specs/README.md`](specs/README.md) |
| `cts/` | CTS 测试流程文件 + 生成规则 | [`cts/README.md`](cts/README.md) |
| `bugs/` | Bug 失败模式与根因模式 | `bugs/top_issue_patterns.md` |
| `methodology/` | 排查方法论 | `methodology/troubleshooting_workflow.md` |

---

## ⚠️ CTS 流程生成规则

> 生成任何 CTS 测试流程文件前，**必须阅读**:
> 1. [`cts/README.md`](cts/README.md) — 6 条生成规则
> 2. [`cts/CTS_GENERATION_LESSONS.md`](cts/CTS_GENERATION_LESSONS.md) — SNK.14 错误教训

**核心原则**: CTS 规范 PDF (`specs/USB_PD3_CTS_Q4_2024_OR.pdf`) 是唯一权威来源，禁止从 Bug 数据推断测试规范。

---

## 快速入口

| 任务 | 入口 |
|------|------|
| 生成 CTS 流程文件 | → `cts/README.md` |
| 了解生成教训 | → `cts/CTS_GENERATION_LESSONS.md` |
| 查 Timer 限值 | → `specs/pd_protocol_timers.md` |
| 查消息序列 | → `specs/pd_message_sequences.md` |
| 查失败模式 | → `bugs/top_issue_patterns.md` |
| 查排查流程 | → `methodology/troubleshooting_workflow.md` |