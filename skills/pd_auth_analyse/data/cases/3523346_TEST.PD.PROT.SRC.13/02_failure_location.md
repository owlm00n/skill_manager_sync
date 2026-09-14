# Phase 2: Test Case & Failure Location — Bug 3523346 / TEST.PD.PROT.SRC.13

> **分析日期**: 2026-09-10
> **Skill 版本**: pd_auth_analyse v3.0
> **数据来源**: 本报告中每个数据小节末尾标注来源命令和原始文件路径

---

## 1. 测试项说明

| 属性 | 值 |
|------|-----|
| **Case ID** | `TEST.PD.PROT.SRC.13` |
| **全称** | PR_Swap – GoodCRC not sent in Response to PS_RDY |
| **测试目的** | 验证 UUT 在 PR_Swap 后成为新 Source，其 PS_RDY 未收到对端 GoodCRC 时，能正确进入 Error Recovery |
| **UUT 角色** | DRP / C/P（PR_Swap 前为 Sink，Swap 后为新 Source） |
| **Sub-tests** | Rev2Src（PD 2.0 模式）、Rev3ChkdSrc（PD 3.0 模式） |
| **判定标准** | 3 个 Check Point，详见 `knowledge/cts/TEST.PD.PROT.SRC.13.md` |

> **来源**: `knowledge/cts/TEST.PD.PROT.SRC.13.md`（Phase 1 产物，基于 USB PD3 CTS Q4 2024 OR Page 147-148 生成）

---

## 2. 完整测试步骤序列与失败位置映射

### 2.1 Rev2Src Sub-test（PD 2.0 模式）

| Step | 描述 | Check Point | Aug 21 | Aug 24 | Aug 27 |
|------|------|:-----------:|:------:|:------:|:------:|
| B.1 | Cable Detection（前处理） | — | ✅ PASS | ✅ PASS | ✅ PASS |
| B.2 | 断开状态启动 | — | — | — | — |
| B.3 | Tester 施加 Rd（VIF Captive_Cable != YES → Rd+Rd） | — | — | — | — |
| **B.4** | **检查 UUT VBUS present (vSafe5V) → Source_Capabilities** | **BU.1#1** | ✅ PASS | ✅ PASS | ✅ PASS |
| **B.5** | **Tester 回复 GoodCRC → 发送 Request 5V@100mA** | — | — | — | — |
| **B.6** | **检查 UUT Accept/Wait** | **BU.1#2** | ✅ PASS | ✅ PASS | ✅ PASS |
| **B.7** | **检查 PS_RDY 收到** | **BU.1#3** | ✅ PASS | ✅ PASS | ✅ PASS |
| **B.8** | **Wait 重试检查** | **BU.1#4** | ✅ PASS | ✅ PASS | ✅ PASS |
| 2 | Tester 发送 PR_Swap | — | — | — | — |
| **3** | **检查 UUT 响应（Accept/Reject/Wait）与 VIF 一致性** | **SRC.13#1** | ✅ PASS | ✅ PASS | ✅ PASS |
| 4 | Tester 降流 ≤ iSwapStandby (tSrcTransition min) | — | — | — | — |
| 5a | 检查 UUT VBUS→vSafe0V 后发 PS_RDY | SRC.13#2a | ✅ PASS | ✅ PASS | ✅ PASS |
| 5b | 检查 PS_RDY 在 tSrcTrans max + tSrcSwapStdby max 内 | SRC.13#2b | ✅ PASS | ✅ PASS | ✅ PASS |
| 6 | Tester **不回复 GoodCRC** + 施加 Rp 替代 Rd | — | — | — | — |
| 7a | UUT CRCReceiveTimer 超时 → 重试 PS_RDY (nRetryCount=2) | — | — | — | — |
| **7b** | **检查 Error Recovery 在 tCtsErrorRecovery(15ms) 内** | **SRC.13#3** | ❌ **FAIL** | ✅ PASS | ✅ PASS |

> **来源**: Lecroy `USB_ComplianceTestLog.html` Aug 21（Python 脚本提取，`C:/Users/xianjun.zeng/AppData/Local/Temp/extract_detailed_html.py`）

### 2.2 Rev3ChkdSrc Sub-test（PD 3.0 模式）

| Step | 描述 | Check Point | Aug 21 | Aug 24 | Aug 27 |
|------|------|:-----------:|:------:|:------:|:------:|
| B.1 | Cable Detection（前处理） | — | ✅ PASS | ✅ PASS | ✅ PASS |
| **B.4** | **检查 UUT VBUS present → Source_Capabilities** | **BU.1#1** | ❌ **FAIL** | ❌ **FAIL** | ❌ **FAIL** |
| B.5-B.8 | BU.1#2~#4（Bring-up 后续步骤） | — | n/a ⛔ | n/a ⛔ | n/a ⛔ |
| 2-7 | 主测试（PR_Swap → Error Recovery） | — | 未执行 ⛔ | 未执行 ⛔ | 未执行 ⛔ |

> **来源**: Lecroy `USB_ComplianceTestLog.html` Aug 21/24/27

---

## 3. 失败步骤详细分析

### 3.1 Rev2Src — SRC.13#3 FAIL（仅 Aug 21，已修复）

**失败点**: Step 7b — Error Recovery 未在 tCtsErrorRecovery(15ms) 内检测到

**错误信息（原文）**:
```
Error(0x00000381): USB Type-C Error Recovery was not detected within 15ms 
after the last bit of the EOP of the last retried PS_RDY Message.
```

**前置条件（全部通过）**:
- ✅ BU.1 Bring-up 完整通过（BU.1#1~#4 全部 PASS）→ UUT 可作为 Source 正常建立显式契约
- ✅ SRC.13#1 通过 → PR_Swap Accept，VIF 字段 PD_Port_Type C/P 一致
- ✅ SRC.13#2 通过 → UUT 正确驱动 VBus→vSafe0V，PS_RDY 在时间窗口内发送

**失败机制分析**:

```
正常流程:
  UUT 发送 PS_RDY → CRCReceiveTimer(0.9~1.1ms) 超时未收到 GoodCRC
  → 重试 PS_RDY #1 → 再次超时 → 重试 PS_RDY #2 (nRetryCount=2) → 再次超时
  → 检测 CC 线为 Rp (Tester 已在 Step 6 切换) → 触发 Error Recovery
  → tCtsErrorRecovery(15ms) 窗口内 Tester 检测到 Error Recovery

UUT 失败场景 (Aug 21):
  UUT 发送 PS_RDY → CRCReceiveTimer 超时 → PS_RDY 重试 ×2 → 重试耗尽
  → Error Recovery 触发延迟过大 或 根本没有触发
  → Tester 在 tCtsErrorRecovery(15ms) 内未检测到 Error Recovery
  → SRC.13#3 FAIL
```

**关键 timer 时间线（估算）**:
| 事件 | 时间基准 | 累计时间 |
|------|---------|---------|
| UUT PS_RDY EOP | t0 | 0ms |
| CRCReceiveTimer 超时 #1 | t0 + 0.9~1.1ms | ~1ms |
| PS_RDY 重试 #1 完成 | t0 + 1.0~1.2ms | ~1.2ms |
| CRCReceiveTimer 超时 #2 | t0 + 1.9~2.3ms | ~2.2ms |
| PS_RDY 重试 #2 完成 | t0 + 2.0~2.4ms | ~2.4ms |
| CRCReceiveTimer 超时 #3 | t0 + 2.9~3.5ms | ~3.3ms |
| Error Recovery 最晚开始 | — | ~3.3ms |
| **Tester 判定截止** | **t0 + 15ms** | **15ms** |

UUT 需要在约 3.3ms 到 15ms 之间（窗口 ~11.7ms）检测到 CC 线状态变化并触发 Error Recovery。

> **来源**: 时间估算基于 SRC.13.md 中 Timer 规范（`knowledge/specs/pd_protocol_timers.md`）

### 3.2 Rev3ChkdSrc — BU.1#1 FAIL（所有三次测试，持续失败）

**失败点**: Step B.4 — "The UUT did not present VBus"

**错误信息（原文）**:
```
Error(0x000003A9): The UUT did not present VBus.
```

**检查逻辑** (BU.1#1):
> The check fails if the first bit of a Source_Capabilities Message is not received 
> from the UUT within tFirstSourceCap max (250ms) after VBUS present (vSafe5V).

**具体含义**:
- Tester 在 CC 线上施加 Rd（模拟 Sink），等待 UUT 作为 Source 上电 VBus 并发送 Source_Capabilities
- BU.1#1 失败有两个可能的直接原因:
  1. UUT **根本没有上电 VBus**（vSafe5V 未出现）→ 0x000003A9 描述指向此原因
  2. UUT 上电了 VBus 但在 tFirstSourceCap(250ms) 内未发送 Source_Capabilities → 错误码描述不精确时也可能是此原因

**与 Rev2Src 的对比**:

| 维度 | Rev2Src | Rev3ChkdSrc |
|------|---------|-------------|
| BU.1#1 结果 | ✅ PASS | ❌ FAIL |
| PD 规范版本 | PD 2.0 | PD 3.0 |
| 失败次数 | 0/3 | **3/3** |
| 修复状态 | Aug 24 起 PASS | **持续失败** |

> **关键区别**: 同一个 UUT、同一根线缆、同一台 Tester，仅仅是 PD 规范版本不同（Rev2 vs Rev3Chkd），BU.1#1 的结果就完全不同。说明问题不是硬件层面的 VBus 上电能力，而是 **PD 3.0 模式下的初始化流程差异** 导致 VBus 未被正确上电。

**后续影响**:
- BU.1#1 fail 后，BU.1#2/3/4 标记为 "n/a"（未执行）
- 主测试（SRC.13#1~#3）完全未执行
- Rev3ChkdSrc 测试在 Bring-up 阶段即终止

> **来源**: Lecroy `USB_ComplianceTestLog.html` Aug 21/24/27 — BU.1#1 fail 序列（`C:/Users/xianjun.zeng/AppData/Local/Temp/extract_detailed_html.py`）

---

## 4. VIF 字段提取（来自 Lecroy 报告）

从 Aug 21 HTML 报告中提取的关键 VIF 字段：

| VIF 字段 | 值 | 对本次测试的影响 |
|----------|-----|-----------------|
| `PD_Specification_Revision` | **2** | UUT 声明支持 PD 2.0，但 CTS 要求同时测试 Rev2Src 和 Rev3ChkdSrc |
| `PD_Port_Type` | (C/P 或 DRP) | 走 BU.1 Bring-up（非 BU.7），说明不是 Consumer/Provider |
| `Accepts_PR_Swap_As_Src` | **YES** | PR_Swap 接受作为 Source → SRC.13#1 检查通过 |
| `Accepts_PR_Swap_As_Snk` | **YES** | 支持作为 Sink 接受 PR_Swap |
| `Requests_PR_Swap_As_Src` | **YES** | 支持作为 Source 发起 PR_Swap |
| `Requests_PR_Swap_As_Snk` | **YES** | 支持作为 Sink 发起 PR_Swap |
| `PD_Power_As_Source` | **5000** | 作为 Source 提供 5V/5A |

> **来源**: Lecroy `USB_ComplianceTestLog.html` Aug 21 — VIF 字段解析（`C:/Users/xianjun.zeng/AppData/Local/Temp/extract_detailed_html.py`）

---

## 5. 测试执行详细时间线（Aug 21）

### 5.1 Rev2Src 执行序列

```
[Preliminary] Cable Detection → PASSED
[PD Link Init] Power Delivery Link initialization on Voyager #27506
[BU.1#1] PASS — VBus present, Source_Capabilities received ✓
[BU.1#2] PASS — Accept received for 5V@100mA Request ✓
[BU.1#3] PASS — PS_RDY received within tSrcTransReq ✓
[BU.1#4] PASS — No Wait message (N/A) ✓
[SRC.13#1] PASS — PR_Swap Accept, VIF Port_Type consistent ✓
[SRC.13#2] PASS — PS_RDY sent after vSafe0V, within time window ✓
[Step 6] Tester: no GoodCRC + apply Rp instead of Rd
[SRC.13#3] FAIL — Error Recovery NOT detected within 15ms after last retried PS_RDY EOP ✗
  → Error(0x00000381)
  → Trace saved: 01_TEST.PD.PROT.SRC.13_Rev2Src_FAIL.usb
```

### 5.2 Rev3ChkdSrc 执行序列

```
[PD Link Init] Power Delivery Link initialization on Voyager #27506
  → ConditionID = "Rev3ChkdSrc"
[BU.1#1] FAIL — VBus NOT present within tFirstSourceCap(250ms) ✗
  → Error(0x000003A9): The UUT did not present VBus
[BU.1#2] n/a — skipped (BU.1#1 fail)
[BU.1#3] n/a — skipped
[BU.1#4] n/a — skipped
[SRC.13#1~#3] NOT EXECUTED — test terminated at bring-up
  → Trace saved: 02_TEST.PD.PROT.SRC.13_Rev3ChkdSrc_FAIL.usb
```

> **来源**: Lecroy `USB_ComplianceTestLog.html` Aug 21 — 逐 Check Point 执行序列（`C:/Users/xianjun.zeng/AppData/Local/Temp/extract_detailed_html.py`）

---

## 6. Rev2Src vs Rev3ChkdSrc 失败模式总结

| 维度 | Rev2Src | Rev3ChkdSrc |
|------|---------|-------------|
| **失败 Check Point** | SRC.13#3 | COMMON.PROC.BU.1#1 |
| **失败阶段** | 主测试 Step 7（最后一步） | Bring-up Step 3（第一步） |
| **错误码** | 0x00000381 | 0x000003A9 |
| **错误描述** | Error Recovery 未在 15ms 内检测到 | UUT 未上电 VBus |
| **测试覆盖** | 完整执行了所有 preceding steps | 主测试完全未执行 |
| **Aug 21 结果** | ❌ FAIL | ❌ FAIL |
| **Aug 24 结果** | ✅ PASS（已修复） | ❌ FAIL（持续） |
| **Aug 27 结果** | ✅ PASS（已修复） | ❌ FAIL（持续） |
| **根因方向** | PR_Swap 后 Error Recovery fallback 逻辑缺失 | PD 3.0 模式 VBus 初始化失败 |
| **优先级** | ✅ 已解决 | 🔴 当前核心问题 |

---

## 7. 分析方向建议

### Rev3ChkdSrc BU.1#1（当前待解决问题）

**关键观察**:
1. **同 UUT Rev2Src BU.1#1 PASS** → UUT 硬件有能力上电 VBus 并发送 Source_Capabilities
2. **PD 3.0 模式差异** — 可能原因：
   - a) PD 3.0 模式下 CC line 检测/DRP 行为不同（如 Rp 值、去抖时间）
   - b) TCPCI Register 配置在 PD 3.0 模式下有差异
   - c) Unisoc PD 驱动仅在 PD 2.0 模式下正确初始化了 VBus，PD 3.0 模式未正确处理
3. **VIF PD_Spec_Revision = 2** — UUT 声明的是 PD 2.0，但 CTS 仍要求以 PD 3.0 模式运行 Rev3ChkdSrc 测试
4. **BU.1 走的是 Source UUT bring-up** — Tester 施加 Rd，期望 UUT 作为 Source 上电

**Phase 3/4 需确认**:
- Rev3ChkdSrc trace 中 CC line 实际状态（UUT 是否正确检测到 Rd？是否尝试上电 VBus？）
- Kernel log 中 PD 3.0 模式切换相关的日志（`sprd_tcpm`、`tcpci` module）

### Rev2Src SRC.13#3（已修复但值得理解）

**修复窗口**: Aug 21 → Aug 24（3 天）
- 如有修复 patch，应查看具体改了什么（PR_Swap 后的 Error Recovery 链路）
- 确认修复是否也可能帮助 Rev3ChkdSrc

---

## 8. Phase 2 产物检查

| 产物 | 路径 | 状态 |
|------|------|:----:|
| 测试流程 CTS 文件 | `knowledge/cts/TEST.PD.PROT.SRC.13.md` | ✅ Phase 1 已生成 |
| 失败点定位报告 | `02_failure_location.md` | ✅ 当前文件 |

---

> **Phase 2 完成，进入 Phase 3（Trace 深度分析）**