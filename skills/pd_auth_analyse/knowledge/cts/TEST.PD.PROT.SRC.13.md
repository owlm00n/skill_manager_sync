# TEST.PD.PROT.SRC.13: PR_Swap – GoodCRC not sent in Response to PS_RDY

> **规范来源**: USB PD3 CTS Q4 2024 OR, Page 147-148
> **ECN 状态**: 未检查 ECN 修改

---

## Description（原文）

As a new Source, the Tester intentionally does not reply GoodCRC Message to the PS_RDY Message after a PR_Swap in order to force the UUT to do an Error Recovery and verifies it is correctly implemented.

**译文**: Tester 作为新 Source，在 PR_Swap 后故意不回复 PS_RDY Message 的 GoodCRC，以强制 UUT 执行 Error Recovery，验证 UUT 是否正确实现了 Error Recovery。

---

## Test Specific Tester Behavior（原文）

- The Tester is a Dual-Role Power, initially a Sink.
- The Tester sends Sink_Capabilities setting B27 (Unconstrained Power) to 1b — COMMON.PROC.PD.3

---

## Test Conditions（原文）

| 条件 | Consumer Only | Provider Only, C/P, P/C, DRP |
|------|:---:|:---:|
| Rev2Src | | ✓ |
| Rev3ChkdSrc | | ✓ |

---

## Test Procedures（原文逐条）

### Step 1: Bring-up

There are 2 possible bring-up procedures:

- **a.** The UUT has VIF field PD_Port_Type set to Consumer/Provider → the Tester runs bring-up procedure with the UUT as a Source **COMMON.PROC.BU.7**
- **b.** The UUT has VIF field PD_Port_Type set to anything else → the Tester runs bring-up procedure with the UUT as a Source **COMMON.PROC.BU.1**

<details>
<summary>COMMON.PROC.BU.1 Bring-up Source UUT（展开）</summary>

1. The test starts in a disconnected state.
2. If VIF field Captive_Cable = YES, the Tester applies Rd. Otherwise, the Tester applies Rd and Ra.
3. **[COMMON.PROC.BU.1#1]** The check fails if the first bit of a Source_Capabilities Message is not received from the UUT within tFirstSourceCap max after VBUS present (vSafe5V).
4. The Tester responds with a GoodCRC.
5. The Tester sends a Request Message for 5V at 100mA (B30…B28=001b, B24=1b, B19…10=100mA, B9…0=100mA).
6. **[COMMON.PROC.BU.1#2]** The check fails if: (a) The UUT retries the Source_Capabilities Message; (b) The UUT does not respond with an Accept or Wait Message. Test stops upon failure.
7. If UUT responds with Wait, the Tester resends Request every tSinkRequest for 10 times or until Accept received. **[COMMON.PROC.BU.1#4]** The check fails if Wait after 10 retries.
8. **[COMMON.PROC.BU.1#3]** The check fails if PS_RDY not received within tSrcTransReq from the last bit of GoodCRC EOP corresponding to Accept.
9. An explicit contract is now established.
10. The Tester waits tCtsAfterLastPoint to respond to messages from the UUT.

</details>

<details>
<summary>COMMON.PROC.BU.7 Bring-up Consumer-Provider as Source UUT（展开）</summary>

1. The test starts in a disconnected state.
2. The Tester applies Rp.
3. If the UUT attachment is detected, the Tester applies VCONN (if Ra is detected) and vSafe5V on VBUS.
4. The Tester waits for 50 ms.
5. The Tester transmits Source_Capabilities Message with single PDO: 5V/100mA (B29=1b, B27=1b).
6. Repeat Step-5 if no GoodCRC received. Delay of tTypeCSendSourceCap (min to max). Repeated at least 50 times.
7. **[COMMON.PROC.BU.7#1]** The check fails if the UUT does not respond with a Request Message.
8. The Tester responds with an Accept Message.
9. The Tester sends PS_RDY at tSrcTransReq max after GoodCRC EOP corresponding to Accept.
10. An explicit contract is now established.

</details>

### Step 2: Tester 发送 PR_Swap

The Tester sends a PR_Swap Message.

### Step 3: 检查 UUT 响应 — [TEST.PD.PROT.SRC.13#1]

The Tester checks the response:

- **a.** If the UUT responds with a **Wait** Message → the Tester resends PR_Swap every tPRSwapWait + tCtsWait for 10 times. Once the Tester has resent PR_Swap for 10 times, **the check fails, and the test ends here**.
- **b.** If the UUT responds with **Reject** or **Not_Supported** → check that the VIF field PD_Port_Type is set to "Provider only" or VIF field Accepts_PR_Swap_As_Src is set to No. **The test ends here.**
- **c.** The check fails if the UUT responds with an **Accept** Message and the VIF field PD_Port_Type is not set to either "Provider/Consumer", "Consumer/Provider", or "DRP". **The test ends here.**

### Step 4: Tester 降低电流

The Tester draws no more than iSwapStandby within tSrcTransition min after it has sent the last GoodCRC.

### Step 5: 检查 UUT PS_RDY — [TEST.PD.PROT.SRC.13#2]

The Tester checks the response:

- **a.** The check fails if the UUT does not send a PS_RDY Message after the UUT driving VBUS voltage to vSafe0V.
- **b.** The check fails if the UUT does not send PS_RDY within **tSrcTransition max + tSrcSwapStdby max** after the last bit of GoodCRC was sent in response to the received Accept.

### Step 6: Tester 不回复 GoodCRC，施加 Rp 替代 Rd

Upon receiving the PS_RDY Message from the UUT, the Tester:

- **a.** Intentionally **does not send a GoodCRC Message** in response to the PS_RDY Message.
- **b.** **Applies Rp** instead of Rd on the CC line.
- **c.** Does not send any further messages.

> **与 SRC.10 的关键区别**: SRC.10 中 Tester 施加 vSafe5V 但不发 PS_RDY（触发 PSSourceOnTimer 超时）；SRC.13 中 Tester 不回复 GoodCRC + 施加 Rp（触发 CRCReceiveTimer 超时 → 重试 PS_RDY → Error Recovery）。

### Step 7: 检查 UUT Error Recovery — [TEST.PD.PROT.SRC.13#3]

A USB Type-C Error Recovery is expected from the UUT. The check fails if a USB Type-C Error Recovery is **not detected within tCtsErrorRecovery** after the last bit of the EOP of the last retried PS_RDY Message.

> **说明**: UUT 发送 PS_RDY 后未收到 GoodCRC，CRCReceiveTimer 超时后重新发送 PS_RDY（nRetryCount=2）。在最后一次重试的 PS_RDY 仍然未收到 GoodCRC 后，UUT 应检测到通信失败并进入 Error Recovery。Tester 检查的是从"最后一次重试的 PS_RDY 的 EOP 最后一位"算起，tCtsErrorRecovery 内是否检测到 Error Recovery。

---

## Check Points 汇总

| Check ID | 原文描述 | 判定 |
|----------|---------|------|
| TEST.PD.PROT.SRC.13#1 | UUT 对 PR_Swap 的响应是否合规（Wait/Reject/Accept 与 VIF 一致性） | FAIL → 测试结束 |
| TEST.PD.PROT.SRC.13#2a | UUT 驱动 VBUS→vSafe0V 后是否发送 PS_RDY | FAIL |
| TEST.PD.PROT.SRC.13#2b | PS_RDY 是否在 tSrcTransition max + tSrcSwapStdby max 内 | FAIL |
| TEST.PD.PROT.SRC.13#3 | Error Recovery 是否在 tCtsErrorRecovery 内被检测到（从最后一次重试的 PS_RDY EOP 算起） | FAIL（过晚/缺失） |

---

## 关键 Timer（辅助参考，来源: USB PD R3.1 Spec）

> ⚠️ 以下数值来自 PD 规范，非 CTS 文档原文。CTS 仅引用 timer 名称。

| Timer | Min | Max | 含义 |
|-------|-----|-----|------|
| tSrcTransition | 100ms | 275ms | Source VBUS 转换时间 |
| tSrcSwapStdby | — | 100ms | PR_Swap 后旧 Source 进入 standby |
| tCtsErrorRecovery | — | 15ms | CTS 定义的 Error Recovery 检测窗口（从最后一次重试的 PS_RDY EOP 算起） |
| tReceive (CRCReceiveTimer) | 0.9ms | 1.1ms | Message 丢失检测超时（SRC.13 中 UUT 用此检测 PS_RDY 未收到 GoodCRC） |
| tPRSwapWait | — | 100ms | PR_Swap Wait 后重试间隔基数 |
| tFirstSourceCap | — | 250ms | 首次 SourceCap 发送上限 |
| tSrcTransReq | — | 275ms | Accept 后到 PS_RDY 的上限 |
| nRetryCount | — | 2 | Message 重试次数（PS_RDY 重试 2 次） |

> **tCtsErrorRecovery 说明**: 这是 CTS 测试脚本定义的专用 timer，值为 15ms。它不是 PD 规范中的标准 timer，而是 CTS 测试仪用于判定 Error Recovery 是否及时出现的检测窗口。来源: Lecroy 测试报告错误信息 `Error(0x00000381): USB Type-C Error Recovery was not detected within 15ms after the last bit of the EOP of the last retried PS_RDY Message.`

---

## 测试逻辑流程图

```
Bring-up (BU.1 或 BU.7)
    │
    ▼
Tester 发送 PR_Swap
    │
    ├── UUT: Wait ──→ 重试×10 ──→ 仍Wait? ──→ FAIL #1, END
    ├── UUT: Reject/Not_Supported ──→ 检查VIF ──→ END
    └── UUT: Accept ──→ 检查VIF Port_Type
                │
                ▼
        Tester 降流 ≤ iSwapStandby (tSrcTransition min)
                │
                ▼
        UUT 驱动 VBUS→vSafe0V, 发送 PS_RDY
        [CHECK #2: 时间 ≤ tSrcTransition max + tSrcSwapStdby max]
                │
                ▼
        Tester 不回复 GoodCRC, 施加 Rp 替代 Rd ← 故意触发 CRCReceiveTimer 超时
                │
                ▼
        UUT: CRCReceiveTimer 超时 → 重试 PS_RDY (nRetryCount=2)
                │
                ├── 最后一次重试 PS_RDY 后仍无 GoodCRC
                │
                ▼
        UUT 应检测到 CC 线 Rp（Tester 已切换）→ 触发 Error Recovery
        [CHECK #3: Error Recovery 在 tCtsErrorRecovery(15ms) 内]
                │
                ├── 未检测到/过晚 → FAIL #3
                └── 检测到 → PASS
```

---

## 常见失败模式（辅助分析，非规范内容）

> ⚠️ 以下内容基于历史 case 经验，非 CTS 规范原文。

- **CHECK #3 FAIL (Error Recovery 未在 15ms 内检测到)**:
  → 通常原因: UUT 在 PS_RDY 重试耗尽后未正确进入 Error Recovery，或 Error Recovery 触发延迟过大
  → 代码关注: `sprd_tcpm.c` 中 PE_SRC_SEND_SOFT_RESET / Error Recovery 状态处理逻辑，CRCReceiveTimer 超时后的重试和 fallback 路径

- **COMMON.PROC.BU.1#1 FAIL (VBus 未检测到)**:
  → 通常原因: UUT 在 PD 3.0 模式 (Rev3ChkdSrc) 下初始化 VBus 失败，可能与 PD 3.0 特有的协议初始化流程相关
  → 代码关注: `sc27xx_typec.c` 中 VBus 上电时序、PD 3.0 模式切换逻辑

---

## 与 SRC.10 的关键差异

| 方面 | SRC.10 | SRC.13 |
|------|--------|--------|
| 测试目的 | 验证 PSSourceOnTimer 超时 → Error Recovery | 验证 CRCReceiveTimer 超时 → Error Recovery |
| Tester 触发方式 | 不发 PS_RDY | 不回复 PS_RDY 的 GoodCRC + 施加 Rp |
| UUT 触发路径 | PSSourceOnTimer 超时 | CRCReceiveTimer 超时 → PS_RDY 重试耗尽 → CC 线 Rp 检测 |
| 判定窗口 | tPSSourceOn min~max (250~480ms) | tCtsErrorRecovery (15ms) |
| Check Points | 5 个 | 3 个 |

---

## 来源

- 官方规范: `USB PD3 CTS Q4 2024 OR.pdf`, TEST.PD.PROT.SRC.13, Page 147-148
- 实测数据: Bug 3523346, TEST-PD-PROT-SRC-13 (Aug 21), TEST.PD.PROT.SRC.13-8-24 (Aug 24), TEST.PD.PROT.SRC.13--8-27 (Aug 27)
- Timer 规范: `knowledge/specs/pd_protocol_timers.md`
- 模板参考: `knowledge/cts/TEST.PD.PROT.SRC.10.md`