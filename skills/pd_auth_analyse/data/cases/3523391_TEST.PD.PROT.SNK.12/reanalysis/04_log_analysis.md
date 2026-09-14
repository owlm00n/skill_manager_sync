# Bug 3523391 (TEST.PD.PROT.SNK.12) — Kernel Log Re-Analysis per Comment #27

> **Re-analysis directive (Comment #27, Yongqing.Wang 9/8)**:
> "PD 2.0 首次 PR_Swap 成功。PD 3.0 第二次 PR_Swap 未收到 PS_RDY。VBUS 时序日志匹配"
>
> **Primary source log (all line citations below)**:
> `E:\08_Bug\Bug 3523391(unicase005585) - [UMS512][zte_sh][P610F01][17353][现场-客户手机]PD CE认证失败 TEST.PD.PROT.SNK.12\Attachements\20260827_155005\003-0827_050107_poweron\0-kernel.log`
>
> **Decoder**: `C:\Users\xianjun.zeng\.claude\skills\protocol-parser\parsers\pd_parser.py` (decode_pd_header, lines 180-216; PD_MESSAGE_TYPES dict lines 127-144; SPEC_REV dict line 177). Verification script: `C:/Users/xianjun.zeng/AppData/Local/Temp/decode_headers_3523391.py`.
>
> **CC controller**: SC27xx PMIC integrated (sprd_tcpm / sc27xx-typec / sc27xx-typec-pd drivers) — NOT third-party.

---

## 0. Conclusion (Executive Summary)

1. **Only ONE PR_Swap execution exists in this log** — at 88.2s (header 0x76a), which FAILS. The state machine stalls at `PR_SWAP_SNK_SRC_SINK_OFF` for 835 ms (tPSSourceOffTimer), then falls into `ERROR_RECOVERY` → `PORT_RESET` → `SNK_UNATTACHED` → `TOGGLING`. The DUT **never sends PS_RDY**.

2. **The 87.7s event (header 0x566) is NOT a PR_Swap execution.** It is the **initial SNK attach completing** with a received PS_RDY (state `SNK_TRANSITION_SINK` → `SNK_READY`). There is no `PR_SWAP_ACCEPT` / `PR_SWAP_START` / `PR_SWAP_SNK_SRC_SINK_OFF` sequence at 87.7s. **This contradicts the customer's "首次 PR_Swap 成功" framing** — see Discrepancy #1 below.

3. **PS_RDY was NOT sent by the DUT** in the failing swap. The only TX was 0x243 (Accept). The state machine stalled before reaching `SRC_TRANSITION` / `SRC_READY` where PS_RDY would be transmitted. This confirms the customer's "未收到 PS_RDY".

4. **VBUS timing is NORMAL** — VBUS is already Off before and throughout the failing swap (no abnormal VBUS transition). This confirms the customer's "VBUS 时序日志匹配" (VBUS is NOT the culprit).

5. **CRITICAL NEW FINDING — header 0x76a decodes to DR_Swap (not PR_Swap) per standard PD.** Per `pd_parser.py` PD_MESSAGE_TYPES (lines 127-144), bits[3:0]=0xA = DR_Swap. The DUT nevertheless enters `PR_SWAP_ACCEPT` after receiving 0x76a. Cross-check: 0x566 bits[3:0]=0x6 = PS_RDY, which MATCHES the log text "ps rdy msg" — proving SPRD hardware uses STANDARD PD msg_type encoding. Therefore 0x76a SHOULD be DR_Swap; the DUT misinterpreting DR_Swap as PR_Swap is a candidate root cause requiring code-level confirmation.

6. **Previous root-cause theory (`sc27xx_typec_pr_swap_no_chk_detach(on=1)` disables CC detection → tPSSourceOffTimer timeout) is REFUTED in its causal claim** but correct in the symptom. See Section 7.

7. **Real root-cause DIRECTION**: Two candidates — (a) DUT misinterprets 0x76a (DR_Swap) as PR_Swap and enters the wrong state machine; (b) the `PR_SWAP_SNK_SRC_SINK_OFF` state fails to advance to `SRC_TRANSITION`/`SRC_READY` and send PS_RDY despite VBUS=0 (the expected trigger) already being satisfied — likely waiting for a VBUS-off falling-edge IRQ that never fires because VBUS was already off before the swap began.

---

## 1. Discrepancies with Customer's Comment #27 Framing

| # | Customer framing | Log ground truth | Impact |
|---|---|---|---|
| 1 | "首次 PR_Swap 成功" (first PR_Swap succeeds) | The 87.7s event is **initial SNK attach** (SNK_TRANSITION_SINK → SNK_READY via received PS_RDY 0x566), NOT a PR_Swap execution. NO `PR_SWAP_ACCEPT`/`PR_SWAP_START`/`PR_SWAP_SNK_SRC_SINK_OFF` state transitions exist at 87.7s. | The "successful PR_Swap" may be in a different log/session not provided here, OR the customer is interpreting the initial-attach PS_RDY as a "successful swap". |
| 2 | "PD 2.0 首次" / "PD 3.0 第二次" | Both 0x566 and 0x76a decode to **spec Rev 2.0** (bits[7:6]=01). Neither carries Rev 3.0 spec bits. (Earlier Source_Capabilities TX at 68s used 0x11a1 = Rev 3.0, but the 87.7s attach used 0x1161 = Rev 2.0.) | The PD 2.0 vs 3.0 distinction is not reflected in the two PR_Swap-relevant header spec bits in THIS log. |
| 3 | "VBUS 时序日志匹配" | CONFIRMED — VBUS is already Off before and during the failing swap; no abnormal VBUS transition. | VBUS is NOT the culprit. Agreed. |

> **Note**: These discrepancies are flagged for transparency. The analysis below treats the log as ground truth. If a "first successful PR_Swap" exists in another log/session, that log should be provided for a true side-by-side comparison.

---

## 2. First Event Timeline (87.7s — Initial SNK Attach / Received PS_RDY)

> **This is NOT a PR_Swap execution.** It is the initial SNK attach completing with a PS_RDY received from the partner. No PR_SWAP_* state transitions occur.

| Line | Timestamp (s) | Event | Notes |
|---|---|---|---|
| L10959 | 87.730229 | `pd irq: delay 500 us` | IRQ processing delay |
| L10960 | 87.734945 | `sc27xx_typec_pr_swap_no_chk_detach, on = 0` | **on=0 = CLEANUP** (NOT entering PR_Swap) |
| L10976 | 87.730851 | `header = 0x566, msg header = 0x566` | RX header = 0x566 |
| L10977 | 87.730867 | `check_message_packages, reg_val = 0x2000, rx fifo data num = 0` | No data objects |
| L10978 | 87.730907 | `first negotiate, ps rdy msg, not rx flush` | **KEY: PS_RDY processed, RX NOT flushed** |
| L10979 | 87.730910 | `pd irq: ps rdy flag, ktime = 87716 ms` | PS_RDY flag set |
| L10980 | 87.730918 | `pd irq: IRQ_HANDLED` | IRQ handled |
| L10981 | 87.730928 | `PD RX, header: 0x566 [1][device]` | PS_RDY received from partner |
| L10982 | 87.734261 | `Setting voltage/current limit 5000 mV 100 mA` | Power limit set |
| L10983 | 87.734264 | `state change SNK_TRANSITION_SINK -> SNK_READY` | **Initial attach completes** (NOT PR_Swap) |
| L10984 | 87.734938 | `pr_swap_no_chk_detach, cur state: SNK_READY, on: 0` | on=0 cleanup at SNK_READY |

**Header 0x566 decode** (per `pd_parser.py` decode_pd_header):
- bits[3:0] = 0x6 → **PS_RDY** (matches PD_MESSAGE_TYPES[0x6])
- bits[7:6] = 01 → Rev 2.0
- bits[8] = 1 → Source role (partner is Source)
- bits[11:9] = 010 → msg_id=2
- Log text "ps rdy msg" (L10978) **MATCHES** standard decode → SPRD uses standard msg_type encoding.

---

## 3. Second Event Timeline (88.2s — PR_Swap FAIL, header 0x76a)

### 3a. RX of 0x76a + entry into PR_Swap state machine

| Line | Timestamp (s) | Event | Notes |
|---|---|---|---|
| L11035 | 88.231803 | `pd irq: start handle irq, irq = 78` | PD IRQ starts |
| L11036 | 88.232817 | `sc27xx_typec_pr_swap_no_chk_detach, on = 1` | **on=1 = entering PR_Swap** (concurrent with 0x76a RX in same IRQ) |
| L11037 | 88.231855 | `pd irq: int sts = 0x10` | IRQ status |
| L11038 | 88.235987 | `vbus is already Off` | **VBUS already off BEFORE swap** |
| L11039 | 88.231882 | `pd irq: delay 500 us` | IRQ delay |
| L11040 | 88.232693 | `header = 0x76a, msg header = 0x76a` | RX header = 0x76a |
| L11041 | 88.232709 | `check_message_packages, reg_val = 0x2000, rx fifo data num = 0` | No data objects |
| L11042 | 88.232751 | `sc27xx_pd_rx_flush:line971: start rx flush` | **KEY: RX FLUSHED** (differs from first event!) |
| L11043 | 88.232788 | `PD RX, header: 0x76a [1][device]` | 0x76a received |
| L11044 | 88.232795 | `state change SNK_READY -> PR_SWAP_ACCEPT` | **Enters PR_SWAP_ACCEPT** |
| L11045 | 88.232805 | `pr_swap_no_chk_detach, cur state: PR_SWAP_ACCEPT, on: 1` | on=1 at PR_SWAP_ACCEPT entry |
| L11047 | 88.232884 | `rx flush done` | RX flush complete |
| L11048 | 88.232894 | `pd irq: IRQ_HANDLED` | IRQ handled |

### 3b. DUT sends Accept (TX 0x243)

| Line | Timestamp (s) | Event | Notes |
|---|---|---|---|
| L11049 | 88.234268 | `PD TX, header: 0x243` | **Accept sent** (only TX in this swap) |
| L11050 | 88.234296 | `tx msg: header = 0x243` | TX header confirm |
| L11051 | 88.234318 | `tx msg: header cfg = 0x243` | TX config |
| L11053 | 88.234338 | `tx msg end` | TX complete |
| L11054 | 88.234342 | `tx_complete_curr_time = 88220 ms` | TX timestamp |
| L11055 | 88.235702 | `pd irq: start handle irq, irq = 78` | Second IRQ (TX complete) |
| L11056 | 88.235733 | `pd irq: int sts = 0x20` | TX-complete status |
| L11058 | 88.235897 | `PD TX complete, status: 0` | TX success |
| L11064 | 88.235935 | `pd irq: IRQ_HANDLED` | IRQ handled |

### 3c. State machine advances then STALLS

| Line | Timestamp (s) | Event | Notes |
|---|---|---|---|
| L11066 | 88.235964 | `state change PR_SWAP_ACCEPT -> PR_SWAP_START` | Advance to START |
| L11067 | 88.235968 | `sink swap source role start` | Sink-to-source swap begins |
| L11069 | 88.235971 | `typec try role en:=0` | Try-role disabled |
| L11070 | 88.235975 | `try source en` | Try-source enabled |
| L11072 | 88.235976 | `state change PR_SWAP_START -> PR_SWAP_SNK_SRC_SINK_OFF` | **Enters SINK_OFF state** |
| L11073 | 88.235981 | `vbus=0 charge:=0` | VBUS already 0 |
| L11075 | 88.235982 | `vbus is already Off` | VBUS already off (repeated) |
| L11076 | 88.237377 | `pending state change PR_SWAP_SNK_SRC_SINK_OFF -> ERROR_RECOVERY @ 835 ms` | **STALL STARTS — tPSSourceOffTimer armed (835ms)** |
| L11080 | 88.304233 | `vbus_change_event, vbus_online: 0, can_communication: 1, Power Role: Sink` | VBUS event: still off, role still Sink |

> **State machine STALLS at `PR_SWAP_SNK_SRC_SINK_OFF`**. It never advances to `SRC_TRANSITION` / `SRC_READY`. It never sends PS_RDY. The 835 ms tPSSourceOffTimer is armed at L11076.

### 3d. Timeout fires → ERROR_RECOVERY → PORT_RESET → TOGGLING (89.07s – 90.02s)

| Line | Timestamp (s) | Event | Notes |
|---|---|---|---|
| L11336 | 89.072524 | `sc27xx_typec_pr_swap_no_chk_detach, on = 0` | on=0 cleanup |
| L11337 | 89.072472 | `state change PR_SWAP_SNK_SRC_SINK_OFF -> ERROR_RECOVERY [delayed 835 ms]` | **TIMEOUT FIRED** |
| L11338 | 89.072511 | `pr_swap_no_chk_detach, cur state: ERROR_RECOVERY, on: 0` | on=0 at ERROR_RECOVERY |
| L11341 | 89.080178 | `pd := off` | PD disabled |
| L11342 | 89.081107 | `vbus is already Off` | VBUS off |
| L11343 | 89.082183 | `charge is already Off` | Charge off |
| L11344 | 89.083195 | `vconn NULL!!!` | VCONN null (warning) |
| L11345 | 89.085050 | `sc27xx_typec_err_recover_state_en enter line 764` | Error recovery enabled |
| L11352 | 89.073896 | `typec try role en:=2` | Try-role set to 2 |
| L11354 | 89.073908 | `clear try source and sink en` | Clear try flags |
| L11356 | 89.073911 | `ERROR_RECOVERY clear power role swap flag` | PR-swap flag cleared |
| L11357 | 89.073913 | `state change ERROR_RECOVERY -> PORT_RESET` | Enter PORT_RESET |
| L11359 | 89.073919 | `sprd_tcpm_reset_port:line3793` | Port reset |
| L11360 | 89.073922 | `sprd_tcpm_typec_disconnect:line3769 connected = 1` | Disconnect (was connected) |
| L11363 | 89.073925 | `sprd_tcpm_typec_disconnect:line3771 unregister_partner` | Partner unregistered |
| L11364 | 89.074964 | `sprd_tcpm_reset_port:line3804 pd_capable flase` | PD not capable |
| L11366 | 89.080004 | `sc27xx_pd_reset:line1008: clear_tx_id = 0` | TX ID cleared |
| L11367 | 89.080010 | `sc27xx_pd_rx_flush:line971: start rx flush` | RX flush |
| L11369 | 89.080054 | `rx flush done` | RX flush done |
| L11370 | 89.080110 | `set rx: on = 0, sts1 = 0x2000` | RX disabled |
| L11372 | 89.080171 | `set rx: pd := off` | RX off |
| L11373 | 89.081100 | `vbus is already Off` | VBUS off |
| L11375 | 89.084110 | `Setting voltage/current limit 0 mV 0 mA` | Limit cleared |
| L11382 | 89.086480 | `pending state change PORT_RESET -> PORT_RESET_WAIT_OFF @ 100 ms` | 100ms timer armed |
| L11385 | 89.186599 | `state change PORT_RESET -> PORT_RESET_WAIT_OFF [delayed 100 ms]` | PORT_RESET_WAIT_OFF |
| L11386 | 89.186632 | `pending state change PORT_RESET_WAIT_OFF -> SNK_UNATTACHED @ 835 ms` | 835ms timer armed |
| L11403 | 90.021719 | `state change PORT_RESET_WAIT_OFF -> SNK_UNATTACHED [delayed 835 ms]` | SNK_UNATTACHED |
| L11404 | 90.021747 | `Start toggling` | Toggling begins |
| L11405 | 90.021749 | `state change SNK_UNATTACHED -> TOGGLING` | **Final state — connection torn down** |

**Header 0x76a decode** (per `pd_parser.py` decode_pd_header):
- bits[3:0] = 0xA → **DR_Swap** per PD_MESSAGE_TYPES[0xA] (standard PD R3.0/R2.0)
- bits[7:6] = 01 → Rev 2.0
- bits[8] = 1 → Source role (partner is Source)
- bits[11:9] = 011 → msg_id=3
- **CONTRADICTION**: DUT enters `PR_SWAP_ACCEPT` (L11044) after receiving 0x76a, but standard decode says DR_Swap. See Section 5.

**Header 0x243 decode** (DUT TX = Accept):
- bits[3:0] = 0x3 → Accept (matches PD_MESSAGE_TYPES[0x3])
- bits[7:6] = 01 → Rev 2.0
- bits[8] = 0 → Sink role (DUT is Sink)
- bits[11:9] = 001 → msg_id=1

---

## 4. Side-by-Side DIFF: First Event vs Second Event

| Dimension | First Event (87.7s) | Second Event (88.2s) | DIFF |
|---|---|---|---|
| **Header** | 0x566 (L10976) | 0x76a (L11040) | Different messages |
| **Standard decode** | PS_RDY (0x6) — MATCHES log | DR_Swap (0xA) — does NOT match log (DUT enters PR_SWAP_ACCEPT) | **0x76a is misinterpreted OR non-standard** |
| **Spec bits** | Rev 2.0 | Rev 2.0 | Same (both Rev 2.0 — customer's "PD 2.0 vs 3.0" not reflected here) |
| **Event nature** | Initial SNK attach (PS_RDY received) | PR_Swap execution (FAILS) | Fundamentally different events |
| **RX flush** | `not rx flush` (L10978) — PS_RDY processed | `start rx flush` (L11042) — RX flushed | **KEY DIFF in RX FIFO handling** |
| **pr_swap_no_chk_detach** | on=0 (L10960, L10984) — cleanup | on=1 (L11036, L11045) — entering PR_Swap | on=1 only at PR_Swap entry (normal) |
| **State transition** | SNK_TRANSITION_SINK → SNK_READY (L10983) | SNK_READY → PR_SWAP_ACCEPT → PR_SWAP_START → PR_SWAP_SNK_SRC_SINK_OFF → STALL (L11044-L11076) | First reaches stable SNK_READY; second stalls |
| **DUT TX** | None (only RX PS_RDY) | 0x243 Accept (L11049) | Second sends Accept then stalls |
| **PS_RDY sent by DUT** | N/A (DUT is Sink receiving PS_RDY) | **NO** — only TX is 0x243 Accept | DUT never sends PS_RDY in failing swap |
| **VBUS** | (not the focus of this event) | Already Off (L11038, L11073, L11075) — normal | VBUS normal, NOT the culprit |
| **Final state** | SNK_READY (stable) | ERROR_RECOVERY → PORT_RESET → TOGGLING (L11337-L11405) | First succeeds; second tears down connection |
| **Timer** | None | tPSSourceOffTimer 835ms (L11076 → L11337) | 835ms timeout fires |

---

## 5. PS_RDY Analysis

### 5.1 Did the DUT send PS_RDY in the failing swap?

**NO.** The only PD TX in the entire failing-swap sequence is header 0x243 = Accept (L11049-L11051). No TX with header 0x__6 (PS_RDY msg_type) appears between L11035 (swap start) and L11337 (timeout). The DUT state machine stalled at `PR_SWAP_SNK_SRC_SINK_OFF` (L11072) and never reached `SRC_TRANSITION` / `SRC_READY`, which is the state where the DUT (now Source) would send PS_RDY.

### 5.2 Was PS_RDY expected?

Per PD spec PR_Swap sequence (DUT was Sink, swapping to Source):
1. Sink receives PR_Swap → sends Accept ✓ (L11049, 0x243)
2. Sink waits for Source to remove VBUS (tSrcSnkToggle) — VBUS already off (L11038)
3. Sink removes VBUS (already off) → transitions to `PR_SWAP_SNK_SRC_SINK_OFF` ✓ (L11072)
4. **Sink should then wait tSrcRecover, then become Source, send Source_Capabilities + PS_RDY** — THIS NEVER HAPPENS

The state machine stalls at step 3. The 835 ms tPSSourceOffTimer (L11076) fires because the state never advances.

### 5.3 Header 0x76a contradiction — DR_Swap vs PR_Swap

**This is the most critical finding.** Per `pd_parser.py` PD_MESSAGE_TYPES dict (lines 127-144), the standard PD R3.0/R2.0 4-bit msg_type encoding is:
- 0x6 = PS_RDY
- 0xA = DR_Swap
- 0xB = PR_Swap

Decoded headers:
- **0x566**: bits[3:0] = 0x6 = PS_RDY. Log text at L10978 says "ps rdy msg". **MATCH** → SPRD hardware uses standard msg_type encoding for 0x566.
- **0x76a**: bits[3:0] = 0xA = **DR_Swap** per standard. But DUT enters `PR_SWAP_ACCEPT` at L11044.

**Logical deduction**:
- If SPRD hardware uses standard encoding (proven by 0x566), then 0x76a = DR_Swap.
- If 0x76a is truly DR_Swap, the DUT entering `PR_SWAP_ACCEPT` (not DR_SWAP_ACCEPT) is a **message-type misinterpretation bug** in the sprd_tcpm RX handler.
- Alternative: 0x76a uses a non-standard/custom SPRD encoding where 0xA = PR_Swap (but this contradicts 0x566 following standard encoding).
- Another alternative: the header value logged (0x76a) is not the raw PD header but a transformed/internal value — however the 0x566 case shows the logged header IS the raw PD header (standard decode matches).

**This requires code-level confirmation** in the sprd_tcpm RX message handler (`tcpm_pd_rx_handler` / `sc27xx_pd_irq` path) to determine how msg_type is extracted from the RX header and mapped to PD_MESSAGE_TYPE.

> **SPRD PD_COMMANDS dict** (`pd_parser.py` lines 89-122) uses custom hex codes ("0A"=PS_RDY, "0D"=PR_SWAP) that do NOT match standard PD. This dict appears to be for a different purpose (hardware register commands, not wire-format msg_type). The wire-format decode should use PD_MESSAGE_TYPES (standard), which is what `decode_pd_header` does.

---

## 6. VBUS Timing Verification

**Customer claim**: "VBUS 时序日志匹配" (VBUS timing logs match — i.e., VBUS is normal).

**Verification**: CONFIRMED. VBUS is already Off before and throughout the failing PR_Swap:

| Line | Timestamp (s) | VBUS indicator | State |
|---|---|---|---|
| L11038 | 88.235987 | `vbus is already Off` | Before PR_SWAP_ACCEPT entry |
| L11073 | 88.235981 | `vbus=0 charge:=0` | At PR_SWAP_SNK_SRC_SINK_OFF entry |
| L11075 | 88.235982 | `vbus is already Off` | Repeated |
| L11080 | 88.304233 | `vbus_change_event, vbus_online: 0` | VBUS event: still off |
| L11342 | 89.081107 | `vbus is already Off` | At ERROR_RECOVERY |
| L11373 | 89.081100 | `vbus is already Off` | At PORT_RESET |

**Finding**: VBUS was already Off BEFORE the PR_Swap began (L11038 at 88.236s, before PR_SWAP_ACCEPT at L11044). There is no VBUS on→off transition during the swap. VBUS behavior is consistent and normal — it is NOT the culprit. The customer's "VBUS 时序日志匹配" is correct.

**However**: The fact that VBUS is ALREADY off before the swap may itself be relevant to the root cause — see Section 8 (the state machine may be waiting for a VBUS-off falling-edge IRQ that never fires because VBUS was already off).

---

## 7. Evaluation of Previous Root-Cause Theory

### Previous theory (verbatim summary)
> `sc27xx_typec_pr_swap_no_chk_detach(on=1)` is called ~30 ms BEFORE PR_Swap, disabling CC detection. This causes the DUT to miss the partner's detach/transition, leading to tPSSourceOffTimer (835 ms) timeout → ERROR_RECOVERY.

### Evaluation

| Claim | Verdict | Evidence |
|---|---|---|
| "on=1 called 30 ms BEFORE PR_Swap" | **REFUTED** | on=1 is at L11036 [88.232817s], 0x76a RX event is at L11040 [88.232693s]. These are CONCURRENT (within ~1 ms, same IRQ context: IRQ start L11035 [88.231803s]). NOT 30 ms before. |
| "on=1 disables CC detection → timeout" | **NOT SUPPORTED** | The timeout (835ms) IS real (L11076 → L11337), but it is caused by the state machine stalling at PR_SWAP_SNK_SRC_SINK_OFF, NOT by CC detection being disabled. VBUS is already off (L11038) — the expected trigger for advancing the state machine is already satisfied, yet it still stalls. |
| "on=1 is abnormal / the root cause" | **REFUTED** | on=1 is a NORMAL part of entering PR_Swap — it is set at PR_SWAP_ACCEPT entry (L11045) and cleared (on=0) at cleanup during ERROR_RECOVERY (L11338). It does NOT appear in the 87.7s event because that event is initial SNK attach, NOT a PR_Swap. The comparison is not apples-to-apples. |
| "tPSSourceOffTimer 835ms timeout → ERROR_RECOVERY" (symptom) | **CONFIRMED** | L11076 arms 835ms timer; L11337 fires it → ERROR_RECOVERY. This is exactly what the log shows. |

**Overall verdict**: The previous theory correctly identifies the SYMPTOM (835ms timeout → ERROR_RECOVERY) but INCORRECTLY attributes the root cause to `on=1` disabling CC detection. The `on=1` call is concurrent with (not before) the PR_Swap entry and is a normal state-machine action. The real question is WHY the state machine stalls at `PR_SWAP_SNK_SRC_SINK_OFF` despite VBUS already being off.

---

## 8. Real Root-Cause DIRECTION

### Candidate A (HIGHEST priority): 0x76a misinterpreted as PR_Swap instead of DR_Swap

**Evidence**:
- 0x76a bits[3:0] = 0xA = DR_Swap per standard PD (PD_MESSAGE_TYPES[0xA]).
- 0x566 bits[3:0] = 0x6 = PS_RDY per standard, and log text "ps rdy msg" CONFIRMS standard encoding is used.
- DUT enters `PR_SWAP_ACCEPT` (L11044) after 0x76a RX — this is the PR_Swap acceptance state, not DR_Swap acceptance.
- If the partner actually sent DR_Swap (not PR_Swap), the DUT entering the PR_Swap state machine is a **message-type decode bug**.

**Impact if true**: The entire PR_Swap sequence is erroneous — the partner requested a Data Role Swap, but the DUT executed a Power Role Swap. The partner would not send PS_RDY (it's not doing a PR_Swap), so the DUT's tPSSourceOffTimer fires and ERROR_RECOVERY triggers.

**Code to check**: sprd_tcpm RX handler — how msg_type is extracted from the RX header and which state transition it triggers. Specifically the function that maps RX msg_type → `tcpm_pd_rx_handler` → state machine entry. Look for whether 0xA is mapped to DR_Swap or PR_Swap.

### Candidate B: PR_SWAP_SNK_SRC_SINK_OFF fails to advance despite VBUS=0

**Evidence**:
- VBUS is already Off before the swap (L11038, 88.236s) and throughout (L11073, L11075, L11080).
- Per PD spec, `PR_SWAP_SNK_SRC_SINK_OFF` should advance after VBUS=0 is confirmed (tSrcSnkToggle / tPSSourceOffTimer is the max wait, but the state should advance EARLY once VBUS=0 is detected).
- The state machine waits the FULL 835 ms (L11076 → L11337) without advancing → suggests it is waiting for an event (VBUS-off falling-edge IRQ?) that NEVER fires because VBUS was already off before the swap began.

**Impact if true**: The state machine has a missing-edge case — when VBUS is already off at PR_Swap entry, the "VBUS went off" event never fires, so the state never advances. This is a logic bug in the `PR_SWAP_SNK_SRC_SINK_OFF` state handler.

**Code to check**: The `PR_SWAP_SNK_SRC_SINK_OFF` state handler in sprd_tcpm — what event/IRQ does it wait for to advance to `SRC_TRANSITION`? Is there a check for "VBUS already off" at state entry that short-circuits the wait?

### Candidate C (lower priority): RX flush difference

**Evidence**:
- First event (87.7s, PS_RDY 0x566): "first negotiate, ps rdy msg, **not rx flush**" (L10978) — PS_RDY processed without flushing RX FIFO.
- Second event (88.2s, 0x76a): "**start rx flush**" (L11042) — RX FIFO flushed before processing 0x76a.

**Impact**: This difference in RX FIFO handling MIGHT cause the 0x76a message to be processed differently (e.g., a stale/corrupted read). However, this is more likely a SYMPTOM of the different message types (PS_RDY in initial negotiate vs PR_Swap/DR_Swap in steady state) rather than a root cause. Worth noting but lower priority.

---

## 9. Summary of Key Findings

| Question | Answer |
|---|---|
| Two PR_Swap events located? | Only ONE PR_Swap execution in this log: 88.2s (header 0x76a, FAIL). The 87.7s event (0x566) is initial SNK attach, NOT a PR_Swap. |
| First PR_Swap (line+time+header) | **N/A in this log** — 87.7s event (L10976, 0x566) is initial SNK attach PS_RDY, not PR_Swap. Customer's "首次 PR_Swap 成功" not found here. |
| Second PR_Swap (line+time+header) | L11040 [88.232693s], header 0x76a. FAILS. |
| Where does the second stop? | `PR_SWAP_SNK_SRC_SINK_OFF` (L11072), stalls 835ms → `ERROR_RECOVERY` (L11337) → `PORT_RESET` → `TOGGLING` (L11405). |
| PS_RDY sent by DUT? | **NO.** Only TX is 0x243 (Accept, L11049). DUT never reaches SRC_READY. |
| VBUS timing normal? | **YES.** VBUS already Off before and during swap (L11038, L11073, L11075). Confirms "VBUS 时序日志匹配". |
| Previous theory holds? | **NO (refuted as root cause).** on=1 is concurrent with PR_Swap entry (not 30ms before), is normal, and doesn't cause the stall. Symptom (835ms timeout) is correct. |
| New root-cause direction? | (A) 0x76a decodes to DR_Swap per standard PD but DUT enters PR_SWAP_ACCEPT — possible msg_type misinterpretation bug. (B) PR_SWAP_SNK_SRC_SINK_OFF fails to advance despite VBUS=0 already satisfied — missing VBUS-off-edge case. |

---

## 10. Source Citations Index

**Primary log**: `E:\08_Bug\Bug 3523391(unicase005585) - [UMS512][zte_sh][P610F01][17353][现场-客户手机]PD CE认证失败 TEST.PD.PROT.SNK.12\Attachements\20260827_155005\003-0827_050107_poweron\0-kernel.log`

**Decoder**: `C:\Users\xianjun.zeng\.claude\skills\protocol-parser\parsers\pd_parser.py` (lines 89-122 PD_COMMANDS; lines 127-144 PD_MESSAGE_TYPES; line 177 SPEC_REV; lines 180-216 decode_pd_header)

**Verification script**: `C:/Users/xianjun.zeng/AppData/Local/Temp/decode_headers_3523391.py`

**Protocol-parser skill**: `C:\Users\xianjun.zeng\.claude\skills\protocol-parser\SKILL.md`

**All log line citations** (by event):
- First event (87.7s, initial SNK attach): L10959, L10960, L10976, L10977, L10978, L10979, L10980, L10981, L10982, L10983, L10984
- Second event RX (88.2s, PR_Swap FAIL): L11035, L11036, L11037, L11038, L11039, L11040, L11041, L11042, L11043, L11044, L11045, L11047, L11048
- Second event TX (Accept): L11049, L11050, L11051, L11053, L11054, L11055, L11056, L11058, L11064
- Second event stall: L11066, L11067, L11069, L11070, L11072, L11073, L11075, L11076, L11080
- Timeout recovery (89.07s): L11336, L11337, L11338, L11341, L11342, L11343, L11344, L11345, L11352, L11354, L11356, L11357, L11359, L11360, L11363, L11364, L11366, L11367, L11369, L11370, L11372, L11373, L11375, L11382, L11385, L11386, L11403, L11404, L11405

---

*Analysis performed per Comment #27 directive. All findings cite full absolute path + line number. No log content fabricated — every line citation verified via Grep/Read against the primary log.*
