# TEST.PD.PROT.SRC.10: PR_Swap – PSSourceOnTimer Timeout

> **规范来源**: USB PD3 CTS Q4 2024 OR, Page 144-145
> **ECN 状态**: 无 ECN 修改（已验证全部 5 份 ECN 均不涉及本测试项）

---

## Description（原文）

As a new Source, the Tester intentionally does not send a PS_RDY Message after a PR_Swap in order to force a PSSourceOnTimer timeout on the UUT and verifies it is correctly implemented.

**译文**: Tester 作为新 Source，在 PR_Swap 后故意不发送 PS_RDY Message，以强制 UUT 的 PSSourceOnTimer 超时，验证 UUT 是否正确实现了该 Timer。

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

### Step 3: 检查 UUT 响应 — [TEST.PD.PROT.SRC.10#1]

The Tester checks the response:

- **a.** If the UUT responds with a **Wait** Message → the Tester resends PR_Swap every tPRSwapWait + tCtsWait for 10 times. Once the Tester has resent PR_Swap for 10 times, **the check fails, and the test ends here**.
- **b.** If the UUT responds with **Reject** or **Not_Supported** → check that the VIF field PD_Port_Type is set to "Provider only" or VIF field Accepts_PR_Swap_As_Src is set to No. **The test ends here.**
- **c.** The check fails if the UUT responds with an **Accept** Message and the VIF field PD_Port_Type is not set to either "Provider/Consumer", "Consumer/Provider", or "DRP". **The test ends here.**

### Step 4: Tester 降低电流

The Tester draws no more than iSwapStandby within tSrcTransition min after it has sent the last GoodCRC.

### Step 5: 检查 UUT PS_RDY — [TEST.PD.PROT.SRC.10#2]

The Tester checks the response:

- **a.** The check fails if the UUT does not send a PS_RDY Message after the UUT driving VBUS voltage to vSafe0V.
- **b.** The check fails if the UUT does not send PS_RDY within **tSrcTransition max + tSrcSwapStdby max** after the last bit of GoodCRC was sent in response to the received Accept.

### Step 6: Tester 施加 vSafe5V 但不发 PS_RDY

The Tester presents vSafe5V on VBUS but **does not send a PS_RDY Message**, in order to force a PSSourceOnTimer timeout on the UUT.

### Step 7: 检查 UUT Error Recovery — [TEST.PD.PROT.SRC.10#3]

A USB Type-C Error Recovery is expected from the UUT. The Tester checks the response:

- **a.** The check fails if a USB Type-C Error Recovery is detected **before tPSSourceOn min** after the time the last bit of the EOP of the GoodCRC Message corresponding to the received PS_RDY Message.
- **b.** The check fails if a USB Type-C Error Recovery is **not detected within tPSSourceOn max** after the last bit of the EOP of the GoodCRC Message corresponding to the received PS_RDY Message.

---

## Check Points 汇总

| Check ID | 原文描述 | 判定 |
|----------|---------|------|
| TEST.PD.PROT.SRC.10#1 | UUT 对 PR_Swap 的响应是否合规（Wait/Reject/Accept 与 VIF 一致性） | FAIL → 测试结束 |
| TEST.PD.PROT.SRC.10#2a | UUT 驱动 VBUS→vSafe0V 后是否发送 PS_RDY | FAIL |
| TEST.PD.PROT.SRC.10#2b | PS_RDY 是否在 tSrcTransition max + tSrcSwapStdby max 内 | FAIL |
| TEST.PD.PROT.SRC.10#3a | Error Recovery 不得早于 tPSSourceOn min | FAIL（过早） |
| TEST.PD.PROT.SRC.10#3b | Error Recovery 必须在 tPSSourceOn max 内出现 | FAIL（过晚/缺失） |

---

## 关键 Timer（辅助参考，来源: USB PD R3.1 Spec）

> ⚠️ 以下数值来自 PD 规范，非 CTS 文档原文。CTS 仅引用 timer 名称。

| Timer | Min | Max | 含义 |
|-------|-----|-----|------|
| tSrcTransition | 100ms | 275ms | Source VBUS 转换时间 |
| tSrcSwapStdby | — | 100ms | PR_Swap 后旧 Source 进入 standby |
| tPSSourceOn | 250ms | 480ms | 新 Source 使 VBUS 达 vSafe5V 的窗口 |
| tPRSwapWait | — | — | PR_Swap Wait 后重试间隔基数 |
| tFirstSourceCap | — | 100ms | 首次 SourceCap 发送上限 |
| tSrcTransReq | — | 275ms | Accept 后到 PS_RDY 的上限 |

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
        Tester 施加 vSafe5V, 不发 PS_RDY ← 故意触发超时
                │
                ▼
        等待 UUT Error Recovery
        [CHECK #3: tPSSourceOn min ≤ 时间 ≤ tPSSourceOn max]
                │
                ├── 过早 → FAIL #3a
                ├── 过晚/缺失 → FAIL #3b
                └── 窗口内 → PASS
```

---

## 常见失败模式（辅助分析，非规范内容）

> ⚠️ 以下内容基于历史 case 经验，非 CTS 规范原文。

- **CHECK #2 FAIL (PS_RDY 超时)**: UUT 作为新 Sink 未及时完成 Vbus 放电
  → 可能原因: Vbus 放电电路响应慢、驱动延迟

- **CHECK #3a FAIL (Error Recovery 过早)**: UUT 的 PSSourceOnTimer 设置过短
  → 可能原因: 驱动中 tPSSourceOn 参数配置错误

- **CHECK #3b FAIL (Error Recovery 未触发)**: UUT 未正确实现 PSSourceOnTimer 超时处理
  → 可能原因: 状态机未正确启动 Timer、Timer 超时回调未触发 Error Recovery
  → 代码关注: tcpm_set_state 中 PE_SNK_STARTUP 的超时处理逻辑
