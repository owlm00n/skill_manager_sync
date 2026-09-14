# PD 认证失败 Bug 分析 — Agent 任务描述

## 一、任务背景

你是一个 PD/USB-C 认证问题分析专家。现在有一个 PD 认证测试失败的 Bug，需要你帮忙分析。

**重要约束**：
- **不要直接分析根因**，先收集证据
- 先搞清楚"需要什么证据"，再去"找证据"
- 最后输出证据汇总报告，不要全量列举，要总结

## 二、Bug 基本信息

| 字段 | 值 |
|------|-----|
| Bug ID | 3476234 (SPCSS01684954) |
| 摘要 | [UMS9230H][HUAQIN_BD2][PD2577F][16849] TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail |
| 平台 | UMS9230H |
| 客户 | 华勤 BD2（vivo 项目 PD2577F） |
| 严重级别 | 1-Critical |
| 测试项 | TEST.PD.PS.SNK.01 |
| Workspace 路径 | `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\` |

## 三、可用资源

### 3.1 Workspace 附件

Workspace 中包含 507 个附件文件，类型分布如下：

| 类型 | 数量 | 说明 |
|------|------|------|
| `.usb` | 32 | Lecroy trace 文件（PD 协议交互记录） |
| `kernel_log` | 12 | 内核日志 |
| `dmesg` | 10 | dmesg 日志 |
| `generic_log` | 20 | 通用日志（如 kernel.log） |
| `mobile_log_zip` | 4 | 手机端日志压缩包 |
| `patch` | 2 | 修复 patch 文件（.diff） |
| `unknown` | 423 | 其他文件（Android settings、cryptfs 等） |

**关键路径**：
- 附件根目录：`<workspace>\Attachements\`
- Patch 文件：`<workspace>\Attachements\13f31c6.diff`
- Trace 文件：`<workspace>\Attachements\...\TEST.PD.PS.SNK.1\Repeat_*\*.usb`
- Kernel log：`<workspace>\Attachements\...\mobilelog\APLog_*\kernel_log_*`

### 3.2 知识库

项目知识库位于：`D:\06_Project\pd_auth_analyse\knowledge\`

包含：
- `specs/pd_state_machines.md` — PD 协议状态机规范
- `specs/pd_protocol_timers.md` — PD 协议关键 Timer 参数
- `specs/pd_message_sequences.md` — PD 消息序列规范
- `bugs/top_issue_patterns.md` — 常见失败模式

### 3.3 参考代码

UNISOC 主线代码位于：
`F:\05_Code\UNISOC\SPRDLINUX6.6_KERNEL_MAIN_W26.12.4_codeonly\idh.code\kernel6.6\unisoc\drivers\unisoc_platform\sprd_charger\power_delivery\sprd_tcpm.c`

## 四、你的任务

### 阶段 1：理解测试项

1. 搞清楚 **TEST.PD.PS.SNK.01** 这个测试到底测什么
2. 这个测试的通过/失败判定标准是什么
3. 如果测试失败，可能是什么原因导致的（列举可能性）

### 阶段 2：确定需要什么证据

基于你对测试项的理解，回答：
1. 要分析这个测试为什么失败，需要哪些类型的证据？
2. 每类证据应该从哪里获取？
3. 优先级排序：哪些证据最关键？

### 阶段 3：检索证据

按照阶段 2 确定的证据清单，输出证据链，分为几类的证据，命中的具体信息，使用了什么工具，生成了什么产物
### 阶段 4：输出证据汇总报告

格式要求：
```markdown
# Bug 3476234 — 证据收集报告

## 一、测试项背景
（简要说明测试项测什么、判定标准）

## 二、需要什么证据
（基于测试项特点，列出需要的证据类型和获取方式）

## 三、证据检索结果
（逐项列出找到的证据，每项包含：来源、关键发现、证据结论）

## 四、证据汇总
（表格形式总结所有证据）

## 五、待确认事项
（还有哪些证据没找到或需要进一步确认）
```

## 五、注意事项

1. **不要直接跳到根因分析**，先把证据收集完整
2. **不要全量列举文件**，要总结关键发现

## 六、输出文件

将证据汇总报告写入：
`D:\06_Project\pd_auth_analyse\data\cases\3476234_TEST.PD.PS.SNK.01\01_manual\evidence_summary_v2.md`
