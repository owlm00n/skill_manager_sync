# Phase 5: 历史 Bug 参照 — TEST.PD.PROT.SRC.13

**分析时间**: 2026-09-10
**Case ID**: TEST.PD.PROT.SRC.13
**Bug ID**: 3523346
**数据来源**: Bugzilla REST API (不可达 — 办公网限制), 同平台历史 Case (3523357, 3523391), pd_auth_analyse 知识库

---

## 1. 知识库状态

| 资源 | 路径 | 状态 |
|------|------|:----:|
| 历史 Bug 模式库 | `knowledge/bugs/top_issue_patterns.md` | ❌ 不存在 |
| 结构化 Bug 知识库 | `knowledge/bugs/auth_knowledge_base.json` | ❌ 不存在 |
| Bug 归档 | `knowledge/bugs/archive/` | ❌ 不存在 |
| 同平台历史 Case | `data/cases/3523357_TEST.PD.PROT.SRC3.01/` | ✅ 已完成分析 |
| 同平台历史 Case | `data/cases/3523391_TEST.PD.PROT.SNK.12/` | ✅ 已完成分析 |

> ⚠️ **数据限制说明**: Bugzilla REST API 在办公网外不可达 (`HTTP 400` 于所有 quicksearch 查询)，无法进行全局历史 Bug 搜索。以下分析基于同平台 (UMS512) 已完成的 Case 和 6 大失败模式框架。

---

## 2. 本 Bug 失败模式分类

| 属性 | 值 |
|------|-----|
| **失败模式** | PD Controller IC (SC27XX) 硬件层行为异常 |
| **子类别** | PR_Swap Rd transition 后 BMC PHY 发送能力下降 → PS_RDY TX 失败 |
| **涉及模块** | SC27XX PD Controller PHY (硬件/固件) + sprd_tcpm (驱动 cleanup 路径) |
| **关键寄存器** | SC27XX PD 中断状态寄存器 — int sts=0x40 (bit 6, TX error) |
| **关键函数** | `sc27xx_typec_err_recover_state_en`, `sprd_tcpm_pr_swap_no_chk_detach`, `sc27xx_pd_reset` |
| **触发条件** | PR_Swap 后 DUT 作为 Sink 执行 Rd transition，发送 PS_RDY 时 GoodCRC 无响应 |
| **平台** | UMS512 (SC27xx PMIC 集成 Type-C + PD Controller) |
| **PD 版本** | PD 3.0 CTS (Lecroy Voyager M310e v7.92 Build 1198) |

---

## 3. 6 大失败模式匹配

| # | 失败模式 | 匹配度 | 说明 |
|:--:|---------|:----:|------|
| 1 | CC 检测与 PD 通信时序配合 | ⭐⭐⭐ | 部分相关 — CC 线 Rd/Rp 切换时序影响 BMC 发送 |
| 2 | PD 协议栈状态机实现缺陷 | ⭐⭐ | 弱相关 — 驱动层 ERROR_RECOVERY 状态机工作正常 |
| **3** | **TCPCI/PD Controller IC 通信异常** | **⭐⭐⭐⭐⭐** | **高度匹配 — SC27XX PHY 层 TX 错误是直接原因** |
| 4 | BC1.2 检测干扰 PD 通信 | ⭐ | 不相关 |
| 5 | VBUS 限流/HIZ 控制异常 | ⭐⭐⭐ | 部分相关 — Rev3ChkdSrc BU.1 的 0x000003A9 与 VBus 有关 |
| 6 | 认证 Patch 适配不完整 | ⭐⭐⭐ | 可能相关 — Aug 21→Aug 24 修复在固件层，可能是 patch 合入 |

### 3.1 主失败模式：模式 3 — PD Controller IC 通信异常

本 Case 是 **模式 3（TCPCI/PD Controller IC 通信异常）的典型变体**：

```
SC27XX PD Controller PHY 层
    │
    ├─ 正常状态: int sts=0x20 (TX success) — 消息发送后收到 GoodCRC
    │
    └─ 异常状态: int sts=0x40 (TX error)  — CRCReceiveTimer 重试耗尽后无 GoodCRC
         │
         └─ PR_Swap Rd transition 后始终触发
```

**与经典模式 3 的区别**：
- 经典模式 3 通常是 I2C 通信超时/Alert 未响应
- 本 Case 是 SC27XX PHY 层 (BMC 编码器) 的 TX 失败，I2C 通信本身正常
- 属于模式 3 的 **PHY 层子类**，而非 TCPCI 通信子类

### 3.2 次要模式：模式 1 — CC 检测与 PD 通信时序配合

PR_Swap Rd transition 涉及 CC 线从 Rp 切换到 Rd，这个电气转换的时间窗口可能影响 BMC 发送：
- Aug 21: 延迟较大 (~16ms 总量，仪器超限)
- Aug 24/27: 延迟减小 (~15ms 总量，刚好不超限)

### 3.3 次要模式：模式 5 — VBUS 限流/HIZ 控制异常

Rev3ChkdSrc BU.1 的 `0x000003A9` (VBus not present) 涉及 PD 3.0 Sink 模式下的 VBus 使能问题，可能与 bq2560x OTG 或 charger IC 配置有关。

---

## 4. 同平台历史 Case 参照

### 4.1 Case 1: Bug 3523357 — TEST.PD.PROT.SRC3.01 (UMS512)

| 属性 | 值 |
|------|-----|
| **Bug ID** | 3523357 (unicase005573) |
| **平台** | UMS512 (与当前 Bug 完全相同) |
| **客户** | ZTE P610F01 (与当前 Bug 相同) |
| **测试项** | TEST.PD.PROT.SRC3.01 — SourceCapabilityTimer Timeout |
| **失败现象** | SC27XX 硬件自动重试 Source Capabilities，导致消息计数超标 |
| **根因** | SC27XX PD 控制器 `enable_tx_auto_retry` 功能在发送 Source Capabilities 时自动重试，仪器统计到 5-10 条消息而非预期的 3 条 |
| **修复方案** | 在 6 个状态点禁用 `enable_tx_auto_retry` (SRC_READY, SRC_SEND_CAPABILITIES, HARD_RESET_SEND 等) |
| **状态** | ✅ FIXED |

**与当前 Case 的关联**：

| 维度 | Bug 3523357 (SRC3.01) | Bug 3523346 (SRC.13) | 关联性 |
|------|----------------------|---------------------|:----:|
| SC27XX 硬件自动行为 | TX 自动重试 | TX 错误 (int sts=0x40) | 🟡 同根 |
| 涉及模块 | SC27XX PD Controller | SC27XX PD Controller | ✅ 相同 |
| 修复层级 | 固件 register 配置 | 固件层 (推断) | 🟡 可能相关 |
| CRCReceiveTimer | 涉及 (重试计时) | 涉及 (重试后失败) | ✅ 相同机制 |

**关键洞察**: Bug 3523357 证明了 **SC27XX PD Controller 存在不应有的硬件自动行为**（`enable_tx_auto_retry`），这些行为会干扰 PD 协议时序。Bug 3523346 中的 TX 错误 (int sts=0x40) 可能也受相同的硬件自动行为影响 — 硬件在发送 PS_RDY 后自动重试，但 tester 不回复 GoodCRC（符合测试要求），导致 CRCReceiveTimer 耗尽后报告 TX 错误。

**适用性评估**: 🟡 部分适用。禁用 TX 自动重试**不能**解决 PS_RDY TX 失败的根本问题（tester 故意不回复 GoodCRC），但可以减少硬件内部的重试时间，从而缩短 tCtsErrorRecovery 总时间。

### 4.2 Case 2: Bug 3523391 — TEST.PD.PROT.SNK.12 (UMS512)

| 属性 | 值 |
|------|-----|
| **Bug ID** | 3523391 |
| **平台** | UMS512 (与当前 Bug 完全相同) |
| **测试项** | TEST.PD.PROT.SNK.12 — PR_Swap Sink→Source |
| **失败现象** | PR_Swap 状态机阻塞，tPSSourceOffTimer 超时 835ms |
| **根因** | `sc27xx_typec_pr_swap_no_chk_detach(on=1)` 在 PR_Swap 消息之前 30ms 被调用，过早禁用 CC 检测 |
| **状态** | ✅ 分析完成 |

**与当前 Case 的关联**：

| 维度 | Bug 3523391 (SNK.12) | Bug 3523346 (SRC.13) | 关联性 |
|------|---------------------|---------------------|:----:|
| 测试类型 | PR_Swap Sink→Source | PR_Swap Source→Sink | 🟡 相反方向 |
| 失败点 | PR_Swap 启动阶段 | PR_Swap PS_RDY 发送阶段 | 🟡 不同阶段 |
| 涉及函数 | `sc27xx_typec_pr_swap_no_chk_detach` | 同一函数 (PR_Swap detach 逻辑) | ✅ 相同调用链 |
| SC27XX 问题 | CC 检测时序 | PHY TX 能力 | 🟡 不同层面 |

**关键洞察**: Bug 3523391 证明了 **`sc27xx_typec_pr_swap_no_chk_detach` 函数的调用时序对 PR_Swap 稳定性至关重要**。当前 SRC.13 Case 中，`sc27xx_typec_pr_swap_no_chk_detach(on=1)` 在 PS_RDY TX 之前 ~500ms 被调用（正常），但后续的 BMC PHY 恢复可能不充分。

### 4.3 Case 3: Bug 2743733 — TEST.PD.PROT.SRC3.01 (UMS9230) [来自 3523357 Phase 5]

| 属性 | 值 |
|------|-----|
| **Bug ID** | 2743733 (SPCSS01386106) |
| **平台** | UMS9230 (同系列平台) |
| **测试项** | TEST.PD.PROT.SRC3.01 |
| **相同点** | 使用相同的 SC27XX PD 控制器 |

### 4.4 局限性说明

以下信息的缺失限制了历史参照的完整性：
- ❌ **全局 Bugzilla 搜索不可用** — 无法查找其他平台的 SRC.13 案例
- ❌ **知识库未建立** — `top_issue_patterns.md` 和 `auth_knowledge_base.json` 均不存在
- ❌ **无 SC27XX 固件 changelog** — 无法确认 Aug 21→Aug 24 的固件变更内容

---

## 5. 失败模式演进分析

### 5.1 Aug 21 → Aug 24: 修复的性质

从 Phase 4 的 log 分析结论来看：

| 观察 | Aug 21 (FAIL) | Aug 24 (FIXED) | Aug 27 (FIXED) |
|------|:-----------:|:------------:|:------------:|
| PS_RDY TX 错误 | ✅ 有 | ✅ 有 | ✅ 有 |
| ERROR_RECOVERY → PORT_RESET | 2.784ms | 2.626ms | 2.602ms |
| 驱动 cleanup 路径 | 完全一致 | 完全一致 | 完全一致 |
| 测试结果 | ❌ FAIL | ✅ PASS | ✅ PASS |

**修复不在 kernel 驱动层** — 最可能在 SC27XX 固件层。

**可能修复方向**：
1. **BMC PHY 初始化优化**: 固件在 PR_Swap Rd transition 后更快地初始化 BMC 发送器
2. **CC 线电气稳定等待**: 减少 Rp→Rd 切换后的 debounce 等待时间
3. **CRCReceiveTimer 优化**: 减少内部重试次数或缩短 timer 值
4. **中断响应优化**: 固件更快地报告 TX 错误给驱动

**对历史参照的影响**：如果修复在固件层，则无法从 kernel 代码/driver log 中查看到修复内容。这降低了历史参照对"如何修复"的指导价值，但增强了"根因在 SC27XX 硬件"的判断置信度。

### 5.2 Rev3ChkdSrc BU.1: 持续性失败

Rev3ChkdSrc BU.1 (PD 3.0 模式) 在所有三份 log 中均失败：
- **Aug 21**: log 未覆盖 Rev3ChkdSrc 阶段
- **Aug 24**: 无 Rev3ChkdSrc PD 3.0 Sink attach 日志（可能未测试或另次上电）
- **Aug 27**: PD 3.0 Sink attach 后 HARD_RESET_SEND 循环，最终进入 SNK_READY

**可能根因**：PD 3.0 模式下 VBus 初始化失败 — Tester 报 `0x000003A9` (VBus not present)。可能与 VIF 配置（仅 PD 2.0 模式）或 charger IC (bq2560x) OTG 配置有关。

---

## 6. 失败模式匹配总结

### 6.1 本 Case 的独特之处

| 特征 | 说明 |
|------|------|
| **PHY 层 TX 错误在 PASS 中也存在** | 这是 SC27XX 的已知行为特征，不是 Bug，而是硬件限制 |
| **tCtsErrorRecovery 仅超限 ~1ms** | 这是一个**边际失败**，对固件/环境的微小变化高度敏感 |
| **修复在固件层** | 与 kernel 代码无关，无法通过代码审查定位 |
| **双模式失败** | Rev2Src (已修复) + Rev3ChkdSrc (持续失败) 两个独立问题 |

### 6.2 在 6 大模式中的位置

```
模式 1: CC 检测与 PD 通信时序配合    ← 次要因素 (CC 线状态切换)
模式 2: PD 协议栈状态机实现缺陷       ← 不相关
模式 3: TCPCI/PD Controller IC 异常  ← 🔴 主模式 (SC27XX PHY TX 错误)
模式 4: BC1.2 检测干扰               ← 不相关
模式 5: VBUS 限流/HIZ 控制异常       ← 次要因素 (Rev3ChkdSrc VBus)
模式 6: 认证 Patch 适配不完整        ← 次要因素 (固件 patch 合入)
```

**新增子模式建议**: 模式 3 应扩展子类 — **`PHY 层 TX 错误 (int sts=0x40)`**，覆盖 SC27XX PD Controller BMC PHY 在角色切换后的发送失败场景。此子模式特征：
- 触发条件：PR_Swap / DR_Swap 后的角色转换
- 表现：int sts=0x40，PS_RDY / Accept 等消息发送失败
- 位置：SC27XX 硬件/固件层，非 kernel 驱动
- 影响：tCtsErrorRecovery / tPSSourceOn / tPSSourceOff 等 timer 超标

---

## 7. 适用性评估

### 7.1 Bug 3523357 修复方案对本 Case 的适用性

| 修复手段 | 适用性 | 评估 |
|---------|:----:|------|
| 禁用 `enable_tx_auto_retry` | 🟡 部分 | 可减少 HW 重试时间，但不解决 tester 不回 GoodCRC 的问题 |
| 修改 `SC27XX_PD_CFG1` 寄存器 | 🟡 未知 | 需确认固件版本中是否有相关配置位 |
| 增加软件 delay (150→180ms) | ❌ 不适用 | Bug 3523357 已证明软件 delay 对硬件自动行为无效 |

### 7.2 推荐方案优先级

| 优先级 | 方案 | 依据 |
|:------:|------|------|
| 🔴 P0 | **获取 SC27XX 固件 changelog**，确认 Aug 21→Aug 24 的固件变更 | 修复已存在但不可见 |
| 🔴 P0 | **更新 SC27XX 固件**到与 Aug 24/27 相同的版本 | 已知 PASS 的固件版本 |
| 🟡 P1 | **检查 Rev3ChkdSrc VIF 配置**，确认是否支持 PD 3.0 Sink 模式 | 持续性失败需独立修复 |
| 🟡 P1 | **检查 bq2560x OTG 配置**在 PD 3.0 Sink 模式下 | 可能解决 error 0x000003A9 |
| 🟢 P2 | 评估禁用 TX 自动重试对 tCtsErrorRecovery 的改善量 | 边际优化 |

### 7.3 置信度评估

| 结论 | 置信度 | 依据 |
|------|:------:|------|
| 与 Bug 3523357 共享 SC27XX 硬件根因 | 🟡 75% | 同平台、同芯片、同 PHY 层问题 |
| 修复在固件层 | 🟡 80% | 排除法：驱动层无差异 |
| Rev3ChkdSrc VBus 问题独立于 SRC.13 | 🟡 70% | 不同错误码、不同测试模式 |
| 知识库缺失影响分析完整性 | 🔴 95% | 无法交叉引用历史 SRC.13 案例 |

---

## 8. 知识库贡献建议

本 Case 分析完成后，建议将以下信息写入知识库：

### 8.1 新知识条目

| 条目 | 内容 | 路径建议 |
|------|------|---------|
| Bug 3523346 索引 | 本 Case 摘要 + 结论 + 修复方向 | `knowledge/bugs/3523346.md` |
| SC27XX PHY TX 错误子模式 | int sts=0x40 的场景、表现、修复方向 | `knowledge/bugs/top_issue_patterns.md` → 模式 3 子类 |
| SC27XX 时间戳使用指南 | kernel 捕获 vs sprd_pd_log 内部时间 | `knowledge/methodology/sc27xx_timestamp_guide.md` |
| SRC.13 测试补充说明 | 修复建议 — SC27XX 固件更新优先于 kernel 驱动修改 | `knowledge/cts/TEST.PD.PROT.SRC.13.md` |

### 8.2 结构化知识库条目模板

```json
{
  "bug_id": "3523346",
  "case_id": "TEST.PD.PROT.SRC.13",
  "platform": "UMS512",
  "failure_pattern": "mode3_phy_tx_error",
  "root_cause_layer": "firmware",
  "key_register": "int_sts=0x40",
  "key_function": "sc27xx_typec_err_recover_state_en",
  "fix_type": "firmware_update",
  "related_bugs": ["3523357", "3523391"],
  "keywords": ["PR_Swap", "PS_RDY", "TX error", "CRCReceiveTimer", "Error Recovery"],
  "confidence": 0.80
}
```

---

## 9. 未解问题（带入 Phase 6 / SUMMARY）

| # | 问题 | 优先级 |
|:--:|------|:------:|
| 1 | SC27XX 固件 Aug 21→Aug 24 的具体变更内容是什么？ | 🔴 高 |
| 2 | 其他平台 (UMS9230/UMS9620) 是否有 SRC.13 测试通过的固件版本？ | 🔴 高 |
| 3 | Rev3ChkdSrc BU.1 VBus 失败是否需要独立的修复方案？ | 🟡 中 |
| 4 | SC27XX `enable_tx_auto_retry` 禁用是否能缩短 tCtsErrorRecovery 时间？ | 🟡 中 |

---

> **Phase 5 完成 | ⚠️ 知识库为空，Bugzilla 搜索不可达 | 下一步: Phase 6 代码级根因 (blocked — 无内核源码)**

---

*分析工具: pd_auth_analyse v3.0 Phase 5*
*数据来源:*
- *同平台历史 Case: `data/cases/3523357_TEST.PD.PROT.SRC3.01/05_history_reference.md`*
- *同平台历史 Case: `data/cases/3523391_TEST.PD.PROT.SNK.12/05_history_reference/05_history_reference.md`*
- *Bugzilla REST API: 不可达 (办公网限制，所有 quicksearch 返回 HTTP 400)*
- *6 大失败模式: pd_auth_analyse Skill 定义*