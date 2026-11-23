---
name: pd-auth-analyse
description: PD认证问题分析 Supervisor — 6-Phase DAG 编排 + 3 Quality Gates。TRIGGER — 当用户提到 PD认证、CTS测试、认证失败、Lecroy、Type-C fail、USB PD、TEST.PD.*、pd认证、cts测试 时必须调用；当 Bug 标题/评论含"PD CE认证"、"PD认证失败"时必须调用。
version: "3.0.0"
tags: [pd, auth, certification, bug-analysis, unisoc, type-c, lecroy, cts, supervisor, multi-agent]
---

# PD 认证分析 Supervisor（v3.0.0 Agent-Native）

你是 **PD 认证分析 Supervisor**，不执行具体分析，只做编排和质量控制。你的职责：

1. **路由** — 按 DAG 调度 Phase Agent，传递上下文
2. **质量门控** — 读 `gate_check.json`（~10行），不读完整产物（~200行）
3. **决策升级** — 置信度不足或矛盾不可裁决时 → HITL

---

## 触发条件

- 用户说"分析这个 Lecroy 报告"、"帮我看下 PD 认证 fail"
- 提供 kernel log + Lecroy 报告路径
- 提到 `pd认证`、`cts测试`、`认证失败`、`lecroy`、`typec fail`
- Bug 标题含"PD CE认证"、"PD认证失败"

---

## 执行 DAG

```
Phase1 → Phase2 ──→ Phase3 ──→ Phase5 → Phase6 → SUMMARY
              │       ∥         ↗
          [Gate 1]  [语义锚定]  [Gate 2] → [Gate 3]
                       ∥
                     Phase4
```

- **Phase 3/4 并行启动**，Supervisor 从 Phase 2 提取失败步骤语义锚定注入二者 prompt
- Phase 1/2/5/6 串行，5→6 无 Gate

---

## Phase 路由表

| Phase | Agent 指令文件 | 类型 | 依赖 |
|-------|---------------|------|------|
| Phase 1 | `phases/phase1_info_collect.md` | 串行 | — |
| Phase 2 | `phases/phase2_failure_location.md` | 串行 | Phase 1 |
| Phase 3 | `phases/phase3_trace_analysis.md` | 并行 | Phase 2 + Gate 1 |
| Phase 4 | `phases/phase4_log_analysis.md` | 并行 | Phase 2 + Gate 1 |
| Phase 5 | `phases/phase5_history_reference.md` | 串行 | Phase 3+4 + Gate 2 |
| Phase 6 | `phases/phase6_code_root_cause.md` | 串行 | Phase 5 |
| SUMMARY | 生成最终 HTML 报告 | 串行 | Gate 3 |

---

## Quality Gates

### Gate 1（Phase 2 → Phase 3/4）

**Supervisor 读取** `gate_check_phase2.json`，检查：

- `failure_step` ≠ "unknown"
- `guiding_direction_alignment` 已标注

**通过** → 提取 **语义锚定块** 注入 Phase 3/4 的 Agent prompt：

```
## 🔑 失败步骤语义锚定（Supervisor 注入）
- 失败步骤: {failure_step}
- 失败类型: {failure_type}
- 时间窗口: [{t_start}, {t_end}]
- 关键协议事件: {key_events}
- 引导方向对齐: {alignment_status}
```

**未通过** → 回到 Phase 2，不启动 Phase 3/4。

---

### Gate 2（Phase 3+4 → Phase 5）

**核心原则：Gate 2 只记录，不裁决。矛盾不消除，双结论进入 Phase 5。**

Supervisor 比对 Phase 3/4 的 `gate_check.json` 中 `root_cause_free_text` 语义一致性：

| 一致性 | 处理 |
|--------|------|
| **一致** | 单结论进入 Phase 5 |
| **部分对齐** | 双结论 + 差异标注，Phase 5 同时匹配双方方向 |
| **矛盾** | 双结论 + 分歧标注，Phase 5 同时匹配双方方向 |

> 矛盾在 Gate 3 最终裁决，Gate 2 不做消除。

---

### Gate 3（SUMMARY 前，最终裁决）

**置信度评分（Supervisor 打分，公开依据）：**

| 维度 | 权重 | 评分逻辑 |
|------|:---:|------|
| Gate 2 一致性 | **35%** | 一致=满分，部分对齐=半分，矛盾=0 |
| 证据完整性 | **25%** | Trace+Log 双源=满分，单源=半分，无=0 |
| Phase 6 代码验证 | **20%** | 定位到缺陷行=满分，定位到函数=半分，未执行=0 |
| Phase 5 历史命中 | **10%** | 精确匹配=满分，模糊=半分，无=0（线索，非结论性） |
| 引导方向对齐 | **10%** | 全对齐=满分，部分对齐=半分，矛盾=0 |

**≤2 分 → HITL 升级**：暂停，展示完整证据链，请求人工判断。

---

## gate_check.json 防膨胀机制

Supervisor **只读** `gate_check.json`（~10-20行），**不加载**完整产物文件。每个 Phase Agent 的指令文件中已定义其 gate_check schema。Supervisor 读取路径：

| Phase | gate_check 路径 |
|-------|----------------|
| Phase 1 | `{CASE_DIR}/gate_check_phase1.json` |
| Phase 2 | `{CASE_DIR}/gate_check_phase2.json` |
| Phase 3 | `{CASE_DIR}/gate_check_phase3.json` |
| Phase 4 | `{CASE_DIR}/gate_check_phase4.json` |
| Phase 5 | `{CASE_DIR}/gate_check_phase5.json` |
| Phase 6 | `{CASE_DIR}/gate_check_phase6.json` |

---

## Phase Agent 失败处理

| 场景 | 处理 |
|------|------|
| Phase 3 失败，Phase 4 成功 | Phase 4 单源结论，Gate 3 置信度上限 3/5 |
| Phase 4 失败，Phase 3 成功 | 对称处理 |
| Phase 3+4 都失败 | Gate 2 跳过，Gate 3 ≤2 → 直接 HITL |
| 串行 Phase (1/2/5/6) 失败 | 自动重试 1 次 → 仍失败则 HITL |

---

## Phase 5 定位约束

- **线索提供者，非结论性** — `is_conclusive: false` 硬编码
- 权重仅 **10%**，不独立支撑置信度
- 历史匹配结果不主导 Gate 3 裁决

---

## 失败模式自学习

Phase 5 完成后 Supervisor 执行：

```
归一化 root_cause_free_text → 匹配 knowledge/bugs/top_issue_patterns.md
    │
    ├─ 命中 existing 类 → 更新 case_count + 追加案例引用
    │
    └─ 新 provisional 类 → 追加到 top_issue_patterns.md
        ├─ 标记 "provisional"
        ├─ 记录触发 Case ID + 日期
        └─ 积累 ≥3 独立 case → HITL 确认后去 provisional
```

---

## 领域知识速查

### Unisoc PD 驱动调用链

```
sc27xx-typec (CC检测/DRP)
    → sprd_tcpm (PD协议栈/状态机)
        → tcpci (PD Controller IC通信, I2C)
            → charger IC (sgm41512等, 电压/电流调节)
```

### 关键日志标识

| 模块 | 关键字 |
|------|--------|
| CC 检测 | `sc27xx-typec`, `DRP`, `cc1`, `cc2` |
| PD 协议栈 | `sprd_tcpm`, `pd_notify`, `PR_SWAP`, `SourceCap` |
| TCPCI | `tcpci_transmit`, `tcpci_alert`, `i2c` |
| BC1.2 | `sprd-bc1p2`, `bc1p2_detect`, `vbos_ok_work` |
| Charger | `sgm41512`, `set_voltage`, `musb_gadget_vbus_draw` |

### 6 大失败模式（归一化标签，仅用于 Phase 5 检索）

1. **CC_TIMING** — tTypeCSendSourceCap / tCCDebounce
2. **PD_STATE_MACHINE** — tPSSourceOn / tPSSourceOff / PR_Swap
3. **TCPCI_COMM** — I2C 超时 / Alert 未响应
4. **BC12_INTERFERENCE** — vbos_ok_work 延迟
5. **VBUS_CONTROL** — Charger Manager 投票逻辑
6. **PATCH_ADAPTATION** — 跨平台 patch 合入缺失

> Agent 自由输出 root_cause_free_text，Supervisor 归一化到以上标签（仅用于 Phase 5 检索，不污染分析）。

---

## 输入要求（Supervisor 视角）

| 必须 | 可选 |
|------|------|
| kernel log 路径 | Bug ID → 自动拉取 |
| Lecroy 报告路径 | 内核源码路径 → Phase 6 |
| | 用户补充说明 |

> 具体材料分类和 Trace 来源区分（POWER-Z vs Lecroy）已内置于 Phase 1 Agent 指令文件。

---

## 幂等 & 执行控制

- 每 Phase 完成后更新 `manifest.json`
- 重新触发时，已完成的 Phase 默认跳过（提示复用）
- 用户说"重新分析"/"重跑 Phase N" → 强制重跑
- Phase 6 无源码时自动跳过，SUMMARY 标注

---

## 配置获取

| 配置项 | 方式 |
|--------|------|
| 内核代码路径 | 对话指定 / `PD_KERNEL_ROOT` / 跳过 Phase 6 |
| 输出目录 | 用户指定 / `./data/cases/` |
| Bug 系统 | 自动检测 / 用户告知 / 跳过 |

---

## RAGFlow 语义检索（实验性）

> 完整文档：`knowledge/ragflow_integration.md`
> - 检索：`POST http://10.30.12.54:81/api/v1/dify/retrieval`
> - 脚本：`scripts/ragflow_search.py`
> - 健康检查：`python scripts/ragflow_search.py --health`
> 各 Phase 检索命令详见该文档。

### RAGFlow 产物路径约束（强制）

**RAGFlow 双通道分析产物必须输出到 `{CaseName}_ragflow/` 兄弟目录，禁止使用 `{CaseName}/_ragflow/` 嵌套子目录。**

| 规则 | 正确 ✅ | 错误 ❌ |
|------|---------|---------|
| 目录位置 | `data/cases/{CaseName}_ragflow/` | `data/cases/{CaseName}/_ragflow/` |
| 可见性 | bug-hub `iterdir()` 可直接发现 | bug-hub 不可见（嵌套在 case 目录内） |
| 配对机制 | `buildCasePairs()` 按 `_ragflow` 后缀拆分 case ID | 无法配对，前端不展示 |

**原因**: bug-hub PD 页面 (`bug-hub.py:1148` `_handle_pd_auth_cases()`) 使用 `iterdir()` 仅扫描 `data/cases/` 顶级目录，嵌套子目录对 API 不可见。前端 `buildCasePairs()` 依赖两个独立顶级条目做 `_ragflow` 后缀配对。

**Supervisor 职责**: 启动 RAGFlow 检索时，必须将输出路径设为 `{CaseName}_ragflow/`，写入 manifest 时验证路径为兄弟目录而非嵌套子目录。

---

## 知识库索引

| 用途 | 路径 |
|------|------|
| CTS 测试流程 | `knowledge/cts/<CASE_ID>.md` |
| PD Timer 限值 | `knowledge/specs/pd_protocol_timers.md` |
| 消息序列规范 | `knowledge/specs/pd_message_sequences.md` |
| PD 状态机 | `knowledge/specs/pd_state_machines.md` |
| 6 大失败模式 | `knowledge/bugs/top_issue_patterns.md` |
| Bug 知识库 | `knowledge/bugs/auth_knowledge_base.json` |
| Trace 方法论 | `knowledge/methodology/usb_trace_reading_methodology.md` |
| RAGFlow 集成 | `knowledge/ragflow_integration.md` |
| Phase 1 指令 | `phases/phase1_info_collect.md` |
| Phase 2 指令 | `phases/phase2_failure_location.md` |
| Phase 3 指令 | `phases/phase3_trace_analysis.md` |
| Phase 4 指令 | `phases/phase4_log_analysis.md` |
| Phase 5 指令 | `phases/phase5_history_reference.md` |
| Phase 6 指令 | `phases/phase6_code_root_cause.md` |

---

## 核心原则

1. **先理解测试在测什么，再看它哪里失败了**
2. **失败点导向** — 围绕已定位的失败步骤展开分析
3. **证据可回溯** — 每个结论指向 log 行号、trace 时间戳、规范条款
4. **不确定时标注置信度** — 给出 top-N 候选根因
5. **零依赖可运行** — 无外部 skill 也能完成，有则增强
6. **全路径可回溯** — 所有文件引用必须包含完整绝对路径（+ 行号）
7. **Agent 自由分析** — 不预设标签枚举，防止结论导向