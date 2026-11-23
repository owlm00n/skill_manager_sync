# TEST.PD.PROT.ALL.02: Soft Reset and Hard Reset

## 测试目的
验证 UUT 正确使用 Soft Reset 和 Hard Reset 机制。当 Tester 不发送 GoodCRC 响应 UUT 的消息时，UUT 应在 CRCReceiveTimer 超时后按 nRetryCount 次重传消息，然后发送 Soft Reset 重建协议层，再次重传 nRetryCount 次失败后发送 Hard Reset 进行物理层复位。

## 测试配置
- 角色: Source (DUT) / Sink (DUT) / DRP (DUT)
- Tester: 根据 UUT 类型切换角色（Source only / Sink only / Consumer/Provider / Provider/Consumer）
- 设备: Teledyne LeCroy Voyager M310e / USB Compliance Suite

## 测试条件 (Test Conditions)

| Condition Code | Consumer Only | Provider Only | DRP, C/P, P/C | Free Cable | VPD, Captive Cable, Si-Only, eMarker |
|---------------|:---:|:---:|:---:|:---:|:---:|
| Rev2Src | | ✓ | ✓ | | |
| Rev3ChkdSrc | | ✓ | ✓ | | |
| Rev2Snk | ✓ | | ✓ | | |
| Rev3ChkdSnk | ✓ | | ✓ | | |
| Rev2VcMinEnd1 | | | | ✓ | ✓ |
| Rev3VcMinEnd1 | | | | ✓ | ✓ |
| Rev2VcMaxEnd1 | | | | ✓ | ✓ |
| Rev3VcMaxEnd1 | | | | ✓ | ✓ |
| Rev2VcMinEnd2 | | | | ✓ | |
| Rev3VcMinEnd2 | | | | ✓ | |
| Rev2VcMaxEnd2 | | | | ✓ | |
| Rev3VcMaxEnd2 | | | | ✓ | |

## 测试步骤

### Bring-up 阶段

根据 UUT 的 VIF `PD_Port_Type` 字段选择 Bring-up 程序：

| UUT PD_Port_Type | 第一次运行 (Tester→UUT) | 第二次运行 (Tester→UUT) |
|------------------|------------------------|------------------------|
| Consumer Only | Source only → COMMON.PROC.BU.2 | — |
| Consumer/Provider | Source only → COMMON.PROC.BU.2 | Provider/Consumer → COMMON.PROC.BU.7 (DRP bit B29=1b) |
| Provider Only | Sink only → COMMON.PROC.BU.1 | — |
| Provider/Consumer | Consumer/Provider → COMMON.PROC.BU.8 | Sink Only → COMMON.PROC.BU.1 (DRP bit B29=1b) |
| DRP | Source only → COMMON.PROC.BU.2 | Sink only → COMMON.PROC.BU.1 (DRP bit B29=0b) |

> **COMMON.PROC.BU.1 (Bring-up Source UUT)** — 参见下方 "Bring-up 详细步骤"

---

### 第一轮：重传 + Soft Reset 协议恢复

| Step | Tester 操作 | DUT 预期响应 | Timer/限值 |
|------|------------|-------------|-----------|
| 1 | 完成 Bring-up（根据 UUT 类型选择 BU.1/BU.2/BU.7/BU.8） | 显式合约已建立 | — |
| 2 | 根据 UUT 类型/角色发送消息（第一次）：<br>• Cable Plug → Discover Identity Command<br>• Source or Sink → Get_Sink_Cap Message | — | — |
| 3 | **检查响应消息**（根据 UUT 类型/角色）：<br>• Cable Plug → **[#1]** 必须回复 Discover Identity ACK<br>• Sink → **[#2]** 必须回复 Sink_Capabilities<br>• Source → **[#3]**：Provider/Consumer 回 Sink_Capabilities；PD2 Provider Only 回 Reject；PD3 Provider Only 回 Not_Supported | 按类型回复对应消息 | — |
| 4 | **不发送 GoodCRC**（触发重传机制） | — | — |
| 5 | **检查重传行为**（根据 UUT 类型/角色）：<br>• Cable Plug → **[#4]** 禁止重传<br>• Sink or Source → **[#5]** 必须以相同 MessageID 重传 (Sink_Capabilities / Not_Supported / Reject)，在 CRCReceiveTimer 超时后 tRetry 内重传，共 nRetryCount 次 | **[#5] FAIL if** UUT 未重传 nRetryCount 次 | tReceive: 0.9-1.1ms<br>tRetry: ≤195µs<br>nRetryCount: 2 |
| 6 | **检查 Soft Reset 行为**（根据 UUT 类型/角色）：<br>• Cable Plug → **[#6]** 禁止发 Soft Reset 或 Hard Reset（等 35ms）<br>• Sink → **[#7]** 必须在 [tReceive min, tReceive max + tSoftReset max] = [0.9ms, 16.1ms] 内发 Soft Reset；Tester 回复 GoodCRC → Accept → Source_Capabilities (5V@100mA) → **[#8]** Sink 回 Request → COMMON.PROC.PD.10 建合约<br>• Source → **[#9]** 必须在 [tReceive min, tReceive max + tSoftReset max] = [0.9ms, 16.1ms] 内发 Soft Reset；Tester 回复 GoodCRC → Accept → **[#10]** Source 回 Source_Capabilities → COMMON.PROC.PD.11 建合约 | **[#9] FAIL if** Soft Reset 未在 [0.9ms, 16.1ms] 内收到<br>Soft Reset 后重建合约 | tSoftReset: ≤15ms<br>Soft Reset 窗口: [0.9ms, 16.1ms] |

---

### 第二轮：再次重传 + Soft Reset → Hard Reset

| Step | Tester 操作 | DUT 预期响应 | Timer/限值 |
|------|------------|-------------|-----------|
| 7 | 根据 UUT 类型/角色发送消息（第二次）：<br>• Cable Plug → Discover Identity Command<br>• Source or Sink → Get_Sink_Cap Message | — | — |
| 8 | **检查响应**（根据 UUT 类型/角色）：<br>• Cable Plug → **[#11]** 必须回 Discover Identity ACK<br>• Sink → **[#12]** 必须回 Sink_Capabilities<br>• Source → **[#13]** 必须回 Sink_Capabilities / Not_Supported / Reject | — | — |
| 9 | **不发送 GoodCRC** | — | — |
| 10 | **检查重传行为**（根据 UUT 类型/角色）：<br>• Cable Plug → **[#14]** 禁止重传<br>• Sink or Source → **[#15]** 必须以相同 MessageID 重传 nRetryCount 次 | **[#15] FAIL if** UUT 未重传 nRetryCount 次 | 同 Step 5 |
| 11 | **检查 Soft Reset + Hard Reset**（根据 UUT 类型/角色）：<br>• Cable Plug → **[#16]** 禁止发 Soft Reset 或 Hard Reset<br>• Sink or Source →<br>&nbsp;&nbsp;i. **[#17]** 必须在 [0.9ms, 16.1ms] 内发 Soft Reset<br>&nbsp;&nbsp;ii. Tester **不发送 GoodCRC** 给 Soft Reset<br>&nbsp;&nbsp;iii. **[#18]** 必须以相同 MessageID 重传 Soft Reset nRetryCount 次<br>&nbsp;&nbsp;iv. **[#19]** 必须在 nRetryCount 次 Soft Reset 重传失败后，tHardReset + tReceive max = 6.1ms 内发送 Hard Reset | **[#17] FAIL if** Soft Reset 未在 [0.9ms, 16.1ms] 内<br>**[#18] FAIL if** 未重传 Soft Reset nRetryCount 次<br>**[#19] FAIL if** 未发 Hard Reset | tHardReset: ≤5ms<br>Hard Reset 窗口: tHardReset + tReceive max = 6.1ms<br>nRetryCount: 2 |

---

### Bring-up 详细步骤: COMMON.PROC.BU.1 (Bring-up Source UUT)

| Step | Tester 操作 | DUT 预期响应 | Timer/限值 |
|------|------------|-------------|-----------|
| BU.1 | 测试从断开状态开始 | — | — |
| BU.2 | Captive_Cable=YES: 施加 Rd；否则 施加 Rd + Ra | — | — |
| BU.3 | — | **[BU.1#1]** VBUS 上电 (vSafe5V) 后 tFirstSourceCap max=250ms 内发送 Source_Capabilities 首 bit | tFirstSourceCap ≤ 250ms |
| BU.4 | 回复 GoodCRC | — | — |
| BU.5 | 发送 Request: 5V@100mA, Object Position=001b, No USB Suspend=1b | — | — |
| BU.6 | — | **[BU.1#2]** UUT 不得重传 Source_Capabilities；必须回复 Accept 或 Wait | — |
| BU.7 | 若 UUT 回 Wait，每 tSinkRequest 重发 Request，最多 10 次 | **[BU.1#4]** 10 次 Wait 后仍 Wait → FAIL | tSinkRequest ≤ 100ms |
| BU.8 | — | **[BU.1#3]** Accept 的 GoodCRC EOP 后 tSrcTransReq 内收到 PS_RDY 首 bit | — |
| BU.9 | 显式合约已建立 | — | — |
| BU.10 | 等待 tCtsAfterLastPoint 再响应 UUT 消息 | — | — |

---

## 判定标准 (Check ID 汇总)

### 适用于 Source UUT 的检查点 (Rev2Src / Rev3ChkdSrc)

| Check ID | 描述 | PASS 条件 |
|----------|------|----------|
| **[TEST.PD.PROT.ALL.2#3]** | Tester 发 Get_Sink_Cap 后 UUT 回复 Sink_Capabilities / Not_Supported / Reject | UUT 回复正确的消息类型 |
| **[TEST.PD.PROT.ALL.2#5]** | Tester 不发 GoodCRC，UUT 以相同 MessageID 重传 nRetryCount 次 | 重传 2 次，间隔 ≤ tRetry |
| **[TEST.PD.PROT.ALL.2#9]** | UUT 在 [0.9ms, 16.1ms] 内发 Soft Reset | Soft Reset 在时间窗口内 |
| **[TEST.PD.PROT.ALL.2#10]** | Soft Reset 后 Accept → UUT 发 Source_Capabilities | 发送 Source_Capabilities |
| **[TEST.PD.PROT.ALL.2#13]** | 第二轮 Get_Sink_Cap 后 UUT 回复正确消息 | 同 #3 |
| **[TEST.PD.PROT.ALL.2#15]** | 第二轮不发 GoodCRC，UUT 重传 nRetryCount 次 | 同 #5 |
| **[TEST.PD.PROT.ALL.2#17]** | UUT 在 [0.9ms, 16.1ms] 内发 Soft Reset | 同 #9 |
| **[TEST.PD.PROT.ALL.2#18]** | Tester 不发 GoodCRC 给 Soft Reset，UUT 重传 Soft Reset nRetryCount 次 | 重传 Soft Reset 2 次 |
| **[TEST.PD.PROT.ALL.2#19]** | nRetryCount 次 Soft Reset 失败后，tHardReset + tReceive max = 6.1ms 内发 Hard Reset | 发送 Hard Reset |

### 错误码（Lecroy 仪表特定）

| Error Code | 含义 | 关联 Check |
|-----------|------|-----------|
| `0x000001F5` | UUT did not retransmit nRetryCount times | [#5], [#15] |
| `0x00000273` | UUT did not send Hard Reset | [#19] |

---

## 常见失败模式

- **UUT 重传失败 (Error 0x000001F5, Checks #5/#15)**: UUT 收到 Get_Sink_Cap 后回复了正确消息（Sink_Capabilities / Not_Supported / Reject），但 Tester 不发 GoodCRC 时，UUT 在 tReceive (0.9-1.1ms) 超时后未能在 tRetry (≤195µs) 内以相同 MessageID 重传 nRetryCount=2 次
  → 通常原因: PD 协议栈的 CRCReceiveTimer 超时处理未触发重传，或重传逻辑在特定 PD 版本模式（Rev2/PD2.0）下的状态机转换不正确
  → 调试方法: 检查 `sprd_tcpm` 协议栈中 CRCReceiveTimer 回调路径的重传触发逻辑，确认 Rev2 (PD_SPEC_REVISION_2) 和 Rev3 (PD_SPEC_REVISION_3) 模式下是否共享同一代码路径

- **UUT 未发送 Hard Reset (Error 0x00000273, Check #19)**: 第二轮 nRetryCount 次 Soft Reset 重传全部失败（Tester 不给 GoodCRC），UUT 应在 tHardReset (≤5ms) + tReceive max (1.1ms) = 6.1ms 内发送 Hard Reset 信号，但实际未发送
  → 通常原因: PD 协议栈在 Soft Reset 重传失败后的 Hard Reset 触发链断裂——可能是状态机在 Rev2 模式下未正确从 "Soft Reset 重传耗尽" 过渡到 "Hard Reset 发起" 状态
  → 调试方法: 检查 `sprd_tcpm` 中 Soft Reset 重传完成后的状态迁移逻辑，确认 nRetryCount 耗尽后是否进入 Hard Reset 触发路径（`pd_send_hard_reset()` 或等效函数调用）

- **Rev2 与 Rev3 行为差异**: Rev2Src 条件 FAIL，Rev3ChkdSrc 条件 PASS（同一 UUT，同一测试逻辑，相同 Check #5/#15/#19）
  → 通常原因: PD SPEC_REVISION 版本号影响协议栈内部行为分支——可能存在 Rev2 专属的状态机精简路径或重传逻辑差异
  → 关键证据: Rev2 使用 PD_SPEC_REVISION=2, Rev3 使用 PD_SPEC_REVISION=3；所有 COMMON.CHECK.PD.* 均 PASS（基础协议通道正常），排除了物理层（I2C/CC/VBUS）问题

---

## 参考 Bug 案例
- **Bug SPCSS01702421**: Rev2Src → TEST.PD.PROT.ALL.2#5 FAIL (0x000001F5), #15 FAIL (0x000001F5), #19 FAIL (0x00000273); Rev3ChkdSrc → 全部 PASS
  - 平台: UMS9230E / LONGCHEER_BU2 / SPRDROID17
  - 引导方向: Lecroy FW 7.9.2→8.1.3 升级暴露，已知 Lecroy 8.0+ 可检测新故障

---

## 来源
- 官方规范: `USB_PD3_CTS_Q4_2024_OR.pdf`, TEST.PD.PROT.ALL.2, Page 99-102
- 官方规范: `USB_PD3_CTS_Q4_2024_OR.pdf`, COMMON.PROC.BU.1, Page 44
- 实测数据: `USB_ComplianceTestLog.html`, Bug SPCSS01702421, 2026-09-22 test session
- Timer 规范: `knowledge/specs/pd_protocol_timers.md` (来源: `USB_PD_R3_2 V1.0 2023-10.pdf`, Section 6.6, Table 6.69/6.71)