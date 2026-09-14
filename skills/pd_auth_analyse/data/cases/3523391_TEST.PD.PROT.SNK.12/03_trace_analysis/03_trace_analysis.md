# Phase 3: Trace 深度分析 — TEST.PD.PROT.SNK.12

**分析时间**: 2026-09-09

> ⚠️ **注意**: 无 Lecroy 二进制 `.usb` trace 文件，本分析基于 Lecroy HTML 报告和 Kernel Log 中记录的 PD 消息序列进行协议层面分析。

---

## 3.1 结论

**协议层异常**: DUT 在 PR_Swap Sink→Source 转换过程中，tPSSourceOffTimer (835ms) 超时。DUT 发送 Accept 后进入 Sink Off 状态，但未能完成 CC 线角色切换（Rd→Rp）并发送 PS_RDY，导致 Tester 侧判定测试场景中止。

**根因方向**: SC27xx PMIC 的 CC 检测在 PR_Swap 期间被 `sc27xx_typec_pr_swap_no_chk_detach(on=1)` 禁用，导致 sprd_tcpm 状态机无法检测到 CC 线状态变化，无法从 PR_SWAP_SNK_SRC_SINK_OFF 转换到下一个状态。

---

## 3.2 关键事件序列（协议层重建）

> **来源**: Kernel Log PD 消息记录 + PD 3.1 规范状态机定义

| 时间 (相对) | 时间 (绝对) | 方向 | 消息/事件 | 备注 |
|:-----------:|------------|:----:|----------|------|
| T0 | 88.232 | DUT 内部 | CC 中断 irq=78 | 触发 `pr_swap_no_chk_detach on=1` |
| T0+30ms | 88.262 | Tester→DUT | **PR_Swap** (header 0x76a, Rev 2.0) | PD 3.0 模式，使用 Rev 2.0 消息格式 |
| T0+30ms | 88.262 | DUT 内部 | SNK_READY → **PR_SWAP_ACCEPT** | 状态机接受 PR_Swap |
| T0+42ms | 88.274 | DUT→Tester | **Accept** (header 0x243) | TX status: 0 (SUCCESS) ✅ |
| T0+48ms | 88.280 | DUT 内部 | PR_SWAP_ACCEPT → **PR_SWAP_START** | 开始角色交换 |
| T0+53ms | 88.285 | DUT 内部 | PR_SWAP_START → **PR_SWAP_SNK_SRC_SINK_OFF** | 关闭 Sink 电源 |
| T0+55ms | 88.287 | DUT 内部 | ⏰ PSSourceOffTimer 启动 | 835ms 超时定时器 |
| T0+72ms | 88.304 | DUT 内部 | `vbus_online: 0` | VBUS 确认关闭 |
| T0+840ms | 89.072 | DUT 内部 | ⏰ **PSSourceOffTimer 超时** | → ERROR_RECOVERY 🔴 |

### 协议层预期序列 vs 实际序列

| 步骤 | 预期 | 实际 | 判定 |
|:----:|------|------|:----:|
| 接收 PR_Swap | ✅ | ✅ 88.262s | OK |
| 发送 Accept | ✅ | ✅ 88.274s, TX status=0 | OK |
| 关闭 Sink VBUS | ✅ | ✅ 88.285s, vbus=0 | OK |
| 检测 VBUS=0 | ✅ | ✅ 88.304s, vbus_online=0 | OK |
| **切换 CC 线 Rd→Rp** | ✅ | ❌ **无日志，未执行** | **FAIL** |
| 开启 Source VBUS | ✅ | ❌ 未执行 | FAIL |
| **发送 PS_RDY** | ✅ | ❌ **未发送** | **FAIL** |

---

## 3.3 Timer 合规检查

| Timer | 规范值 | 测量值 | 判定 | 说明 |
|-------|--------|--------|:----:|------|
| **tPSSourceOff** | 835ms (750-920ms) | **835ms (超时)** | ❌ **FAIL** | 定时器到期触发 ERROR_RECOVERY，未正常停止 |
| tSendSourceCap | — | — | N/A | 未进入 Source 角色 |
| tPSReady | — | — | N/A | PS_RDY 未发送 |

**关键发现**: tPSSourceOffTimer 本身设置正确（835ms），但它是作为安全超时触发，而非正常转换路径。问题在于：**在 835ms 内，状态机没有收到使其从 PR_SWAP_SNK_SRC_SINK_OFF 正常转换的事件。**

---

## 3.4 消息序列合规检查

### PD 3.0 PR_Swap 消息序列

| 检查项 | 预期 | 实际 | 合规 |
|--------|------|------|:----:|
| PR_Swap 消息格式 | PD 3.0 Rev 字段 | header 0x76a (Rev 2.0 格式) | ⚠️ 注1 |
| Accept 消息 | 收到 PR_Swap 后发送 | header 0x243, TX=0 | ✅ |
| Accept 发送时序 | < tSenderResponse (30ms) | 12ms (88.262→88.274) | ✅ |
| PS_RDY 发送 | Source On 后 | 未发送 | ❌ |
| GoodCRC | 每条消息后 | 未在 log 中记录 | N/A |

> **注1**: PD 3.0 测试模式下 Tester 发送 Rev 2.0 格式的 PR_Swap 消息是正常的 — CTS 规范允许使用 Rev 2.0 消息格式进行 PD 3.0 测试。

### Tester 侧观察（根据 Comment #8, #10, #13）

| 时间 | Tester 观察 | 说明 |
|------|-----------|------|
| PR_Swap 发送后 | 收到 Accept ✅ | DUT 正常响应 |
| Accept 后 | **等待 PS_RDY 超时** ❌ | DUT 未发送 PS_RDY |
| 超时后 | 发送 Source_Capabilities | 尝试恢复通信 |
| Source_Cap 后 | **未收到 GoodCRC** ❌ | DUT 已进入 ERROR_RECOVERY，PD 状态机崩溃 |

---

## 3.5 PD 2.0 vs PD 3.0 协议差异分析

| 对比维度 | Rev2Snk (PASS) | Rev3ChkdSnk (FAIL) |
|----------|:---:|:---:|
| PD 协议版本 | PD 2.0 | PD 3.0 |
| PR_Swap 消息 | header 0x566 (Rev 2.0) | header 0x76a (Rev 2.0 格式) |
| Tester 测试模式 | PD 2.0 CTS | PD 3.0 CTS |
| 时序要求 | 较宽松 | 较严格 |
| CC 检测行为 | 可能未触发 `pr_swap_no_chk_detach` | **触发 `pr_swap_no_chk_detach`** |

**关键差异假设**: 在 PD 2.0 测试模式（Rev2Snk）下，Tester 的行为可能不触发 CC 检测中断 (irq=78)，因此 `sc27xx_typec_pr_swap_no_chk_detach` 不会被调用，CC 检测保持正常，sprd_tcpm 状态机能正常完成 PR_Swap 转换。

在 PD 3.0 测试模式（Rev3ChkdSnk）下，Tester 的 CC 线行为可能触发了 CC 检测中断，导致 `pr_swap_no_chk_detach` 被提前调用，CC 检测被禁用，状态机转换失败。

---

*Phase 3 完成 | 2026-09-09*