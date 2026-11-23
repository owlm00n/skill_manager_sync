# TEST.PD.PROT.ALL.01: Corrupted GoodCRC

## 测试目的
验证 UUT 在收到错误的 GoodCRC 时能正确重传 PD 消息。Tester 检查 UUT 在未收到正确 GoodCRC 的情况下是否会重传 PD 消息（以相同的 MessageID 重传 `nRetryCount` 次），以及当 AMS 被中断时是否正确发送 Soft_Reset。

## 测试配置
- 角色: All UUT types (Consumer Only / Provider Only / DRP / C/P / P/C)
- Tester: 根据 UUT 类型自适应（Source only / Sink only / Provider-Consumer / Consumer-Provider）
- 设备: Lecroy Voyager M310e / USB Compliance Suite
- Bring-up 流程: DRP UUT 运行两次 — 第一次 UUT as Sink (COMMON.PROC.BU.2 或 BU.8)，第二次 UUT as Source (COMMON.PROC.BU.1)

## 测试条件 (Test Conditions)

| Condition Code | Consumer Only | Provider Only | DRP, C/P, P/C |
|---------------|:---:|:---:|:---:|
| Rev2Snk | ✓ | — | ✓ |
| Rev3ChkdSnk | ✓ | — | ✓ |
| Rev2Src | — | ✓ | ✓ |
| Rev3ChkdSrc | — | ✓ | ✓ |

> 注: 对于 DRP UUT，测试运行两次 — 第一次 Tester 作为 Source only 以 BU.2 bring-up (UUT as Sink)，第二次 Tester 作为 Sink only 以 BU.1 bring-up (UUT as Source)。本 case UUT 类型为 DRP (Provider/Consumer, LongCheer SANTIAGOA)。

## 测试步骤

### Phase 1: Bring-up & Initial Response (Steps 1-3)

| Step | Tester 操作 | DUT 预期响应 | Check ID | Timer/限值 |
|------|------------|-------------|----------|-----------|
| 1 | 根据 UUT 类型执行 9 种可能的 bring-up 程序之一 | UUT 进入就绪状态 | — | 取决于具体 BU 流程 |
| 2 | 发送 Get_Sink_Cap Message (Source/Sink UUT) | UUT 回复对应消息 | — | — |
| 3a | — (Cable Plug) | UUT 发送 Discover Identity ACK | **#1** | — |
| 3b | — (Sink UUT) | UUT 发送 Sink_Capabilities Message | **#2** | — |
| 3c | — (Source UUT) | Provider/Consumer 发 Sink_Capabilities；Provider Only PD2 发 Reject；Provider Only PD3 发 Not_Supported | **#3** | — |

### Phase 2: Corrupted CRC GoodCRC — First Retransmission Test (Steps 4-5)

| Step | Tester 操作 | DUT 预期响应 | Check ID | Timer/限值 |
|------|------------|-------------|----------|-----------|
| 4 | 发送 GoodCRC，CRC 错误（4b5b 编码前 flip bit 0） | — | — | — |
| 5a | — (Cable Plug) | UUT **不得**重传 | **#4** | — |
| 5b | — (Sink/Source) | UUT **必须**以相同 MessageID 重传（Sink_Capabilities/Not_Supported/Reject），在 CRCReceiveTimer 超时后的 tRetry 内完成。Tester 回复有效 GoodCRC | **#5** | tRetry (CRCReceiveTimer 超时后) |

### Phase 3: Second Message Exchange (Steps 6-8)

| Step | Tester 操作 | DUT 预期响应 | Check ID | Timer/限值 |
|------|------------|-------------|----------|-----------|
| 6 | 再次发送 Get_Sink_Cap Message | UUT 回复对应消息 | — | — |
| 7a | — (Cable Plug) | UUT 发送 Discover Identity ACK | **#6** | — |
| 7b | — (Sink) | UUT 发送 Sink_Capabilities Message | **#7** | — |
| 7c | — (Source) | UUT 发送 Sink_Capabilities/Not_Supported/Reject | **#8** | — |

### Phase 4: Wrong MessageID GoodCRC — nRetryCount Retransmission Test (Steps 8-10)

| Step | Tester 操作 | DUT 预期响应 | Check ID | Timer/限值 |
|------|------------|-------------|----------|-----------|
| 8 | 发送 GoodCRC，MessageID 错误（接收消息的 MessageID + 1） | — | — | — |
| 9a | — (Cable Plug) | UUT **不得**重传 | **#9** | — |
| 9b | — (Sink/Source) | UUT **必须**以相同 MessageID 重传（Sink_Capabilities/Not_Supported/Reject），在 CRCReceiveTimer 超时后的 tRetry 内 | **#10** | tRetry |
| 10 | (仅 Sink/Source) 重复 Step 8-9，直到 UUT 以相同 MessageID 重传了 `nRetryCount` 次 | — | — | nRetryCount (PD Spec: 2) |

### Phase 5: Interrupted AMS Test (Steps 11-17)

> 以下测试验证 UUT 端口在收到 incoming message 时是否正确丢弃 outgoing message（PRL_Tx_Discard_Message 状态，参见 PD Spec Figure 6-61）。

| Step | Tester 操作 | DUT 预期响应 | Check ID | Timer/限值 |
|------|------------|-------------|----------|-----------|
| 11 | (Cable Plug 结束) | — | — | — |
| 12 | 发送 Get_Sink_Cap Message（新一轮 AMS 开始） | — | — | — |
| 13 | 等待 Sink_Capabilities/Not_Supported/Reject Message | UUT 发送响应消息 | — | — |
| 14 | 发送 GoodCRC，CRC 错误（4b5b 编码前 flip bit 0） | — | — | — |
| 15 | 发送 Get_Source_Cap Message，**在错误 GoodCRC 发送后 35μs**（tRetry 超时前） | — | — | 35μs (< tRetry) |
| 16 | — (Sink/Source) | UUT **不得**在收到 Get_Source_Cap 后以相同 MessageID 重传。Tester 等待 25ms 检查是否重传 | **#11** | 25ms 等待窗口 |
| 17 | — (Sink/Source) | UUT **必须**发送 Soft_Reset Message（AMS 被中断时的预期行为） | **#12** | — |

## 判定标准

- [ ] **Check #5**: UUT 在收到 CRC 错误的 GoodCRC 后，在 CRCReceiveTimer + tRetry 内以相同 MessageID 重传
- [ ] **Check #10**: UUT 在收到 MessageID 错误的 GoodCRC 后，以相同 MessageID 重传 `nRetryCount` 次
- [ ] **Check #11**: UUT 在收到 Get_Source_Cap（中断 AMS）后不得重传
- [ ] **Check #12**: UUT 在 AMS 被中断后发送 Soft_Reset Message

## 唯一检查点 (Check ID) 汇总

| Check ID | 适用 UUT | 判定 |
|----------|---------|------|
| **TEST.PD.PROT.ALL.1#1** | Cable Plug | 是否发送 Discover Identity ACK |
| **TEST.PD.PROT.ALL.1#2** | Sink | 是否发送 Sink_Capabilities |
| **TEST.PD.PROT.ALL.1#3** | Source | Provider/Consumer 发 Sink_Capabilities；Provider Only PD2 发 Reject；Provider Only PD3 发 Not_Supported |
| **TEST.PD.PROT.ALL.1#4** | Cable Plug | 不得重传（CRC 错误 GoodCRC） |
| **TEST.PD.PROT.ALL.1#5** | Sink/Source | 必须以相同 MessageID 重传（CRC 错误 GoodCRC），tRetry 内 |
| **TEST.PD.PROT.ALL.1#6** | Cable Plug | 是否发送 Discover Identity ACK（第二轮） |
| **TEST.PD.PROT.ALL.1#7** | Sink | 是否发送 Sink_Capabilities（第二轮） |
| **TEST.PD.PROT.ALL.1#8** | Source | 是否发送 Sink_Capabilities/Not_Supported/Reject（第二轮） |
| **TEST.PD.PROT.ALL.1#9** | Cable Plug | 不得重传（MessageID 错误 GoodCRC） |
| **TEST.PD.PROT.ALL.1#10** | Sink/Source | 必须以相同 MessageID 重传 `nRetryCount` 次（MessageID 错误 GoodCRC） |
| **TEST.PD.PROT.ALL.1#11** | Sink/Source | 收到 Get_Source_Cap 后不得重传（25ms 等待窗口） |
| **TEST.PD.PROT.ALL.1#12** | Sink/Source | 必须发送 Soft_Reset（AMS 被中断） |

## 关键 Timer 数值

| Timer | 值 | 来源 |
|-------|-----|------|
| `tRetry` | PD3.1 Spec Section 6.6.5.3, tRetry = 195μs (min) ~ 225μs (max) | `knowledge/specs/pd_protocol_timers.md` (辅助参考，非 CTS 原文) |
| `CRCReceiveTimer` | PD3.1 Spec Section 6.6.5.1, CRCReceiveTimer = 195μs (min) ~ 1.0ms (max) | `knowledge/specs/pd_protocol_timers.md` (辅助参考，非 CTS 原文) |
| `nRetryCount` | PD3.1 Spec Section 6.6.5.3, nRetryCount = 2 | `knowledge/specs/pd_protocol_timers.md` (辅助参考，非 CTS 原文) |
| 中断 AMS 延迟 | 35μs (CTS spec 明确定义) | CTS PDF Page 99 |
| 重传等待窗口 | 25ms (CTS spec 明确定义，Check #11) | CTS PDF Page 99 |

## Bring-up 流程引用

本测试使用两个 bring-up 流程（DRP UUT 运行两次）：

### COMMON.PROC.BU.8 — Bring-up Provider-Consumer as Sink UUT (18 steps)
- **来源**: CTS PDF Page 50-51
- **适用**: UUT 作为 Sink 角色（Rev2Snk / Rev3ChkdSnk）
- 关键步骤: Rd+Ra → UUT 发 Source_Capabilities (#1) → Tester 发 Request → Accept/Wait (#2/#9) → PS_RDY (#3) → PR_Swap → PS_RDY (#6) → 新合约 (#7) → VCONN_Swap (#8)

### COMMON.PROC.BU.1 — Bring-up UUT as Source
- **来源**: CTS PDF (UUT as Source bring-up standard procedure)
- **适用**: UUT 作为 Source 角色（Rev2Src / Rev3ChkdSrc）
- 关键步骤: Rp → 检测连接 → VCONN + vSafe5V → 等 50ms → 发 Source_Capabilities → Request → Accept → PS_RDY

## 常见失败模式

- **Check #10 FAIL: UUT 未重传 nRetryCount 次 (Error 0x000001F5)**
  → 通常原因: PD 协议栈重传计数器逻辑缺陷 — CRCReceiveTimer 超时后重传逻辑未正确递增 MessageID 重传计数器，或重传被其他协议事件（如收到新消息）提前终止
  → 调试方法: 在 `sprd_tcpm` 驱动的 PRL_Tx_Layer 状态机中插入重传计数 log，确认 `nRetryCount` 是否达到 2 次才放弃

- **Check #11 FAIL: 收到 Get_Source_Cap 后仍发送了消息 (Error 0x0000050F)**
  → 通常原因: PD 协议栈未正确实现 PRL_Tx_Discard_Message 状态（Figure 6-61），当收到 incoming message 时未停止 outgoing message 的 retry timer 和重传
  → 调试方法: 检查 PRL 层状态机中 PRL_Tx_Discard_Message 入口条件是否覆盖 "收到 Get_Source_Cap 时 CRCReceiveTimer 仍在运行" 的场景

- **间歇性 pass/fail (Rev2Src FAIL, Rev3ChkdSrc PASS)**
  → 通常原因: 首次 bring-up 后协议栈状态未完全稳定、timer 精度受系统负载影响、或重传计数在特定时序窗口下异常清零
  → 定位方法: 对比 Rev2Src 和 Rev3ChkdSrc 的 Lecroy trace，重点比较: (1) 第一次 corrupted CRC GoodCRC 后 UUT 的 retry 时序; (2) MessageID 递增模式; (3) 中断 AMS 时 UUT 是否已进入 PRL_Tx_Discard_Message

## 参考 Bug 案例
- **SPCSS01702417 (Bug 3564897)**: TEST.PD.PROT.ALL.01 Corrupted GoodCRC FAIL — UMS9230E / LONGCHEER_BU2 / UPM6910 charger。Rev2Src phase Check #10 FAIL (Error 0x000001F5: 未重传 nRetryCount 次) + Check #11 FAIL (Error 0x0000050F: 收到 Get_Source_Cap 后仍发送消息)。Rev3ChkdSrc 全部 PASS — 间歇性问题。

---

## 来源
- 官方规范: `knowledge/cts/USB_PD3_CTS_Q4_2024_OR.pdf`, Section 5.1.1, Page 96-99
- Bring-up 流程: `knowledge/cts/USB_PD3_CTS_Q4_2024_OR.pdf`, COMMON.PROC.BU.8 (Page 50-51), COMMON.PROC.BU.1
- 实测数据: Bug 3564897 (SPCSS01702417), Lecroy Compliance Test Log `USB_ComplianceTestLog.html`
- Timer 规范: `knowledge/specs/pd_protocol_timers.md` (辅助参考, tRetry/CRCReceiveTimer/nRetryCount, 非 CTS 原文)