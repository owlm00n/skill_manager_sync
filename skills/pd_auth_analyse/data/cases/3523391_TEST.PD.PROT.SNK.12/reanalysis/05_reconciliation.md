# 05 — Reconciliation: Bug 3523391 (UMS512 PD CE cert failure, TEST.PD.PROT.SNK.12)

> **Reconciliation agent** — resolves the CONFLICT between Agent 2 (03_trace_analysis.md) and Agent 3 (04_log_analysis.md).
> A prior reconciliation agent STALLED (600s stream watchdog). This document was produced under anti-stall guardrails (temp `.py` scripts, incremental writes, bounded windows).
>
> **Scope**: 5 tasks — (A) kernel event extraction, (B) clock alignment, (C) Rev3ChkdSnk FAIL-run kernel analysis, (D) parser correctness, (E) synthesis.

---

## 0. The Conflict (recap)

| | Agent 2 (03_trace_analysis.md) | Agent 3 (04_log_analysis.md) |
|---|---|---|
| Source | POWER-Z pd.sqlite + Lecroy Voyager HTML | 0-kernel.log |
| Rev3ChkdSnk (PD 3.0) FAIL run | 0 HTML annotations (aborted); DUT sent **0 Accept / 0 PS_RDY / 0 PR_Swap** — completely silent; Tester sent 280 repeated PD3.0 Request + 3 unanswered VCONN_Swap (0x01ad @ 57.728–57.731s) | Found ONE PR_Swap at kernel 88.2s (header 0x76a, line 11040) where DUT sent Accept (0x243) but never PS_RDY → ERROR_RECOVERY |
| Rev2Snk (PD 2.0) PASS run | 1× PS_RDY (0x566, MsgID=2, t=35.761s) | (not analyzed) |

**The contradiction**: a run with an Accept ≠ a run with 0 Accepts. They cannot both be the Rev3ChkdSnk run. One of the two agents analyzed the wrong run window.

---

## A. Kernel Event Extraction (Task A)

**Source command**: `python "C:/Users/xianjun.zeng/AppData/Local/Temp/rc_task_a2.py"` → output `C:\Users\xianjun.zeng\AppData\Local\Temp\rc_out_a.txt` (379 lines, 187 PD-relevant events)
**Original file**: `E:\08_Bug\Bug 3523391(...)\Attachements\20260827_155005\003-0827_050107_poweron\0-kernel.log` (1,826,816 bytes / 13,689 lines)
**Window**: kernel uptime [87.0, 112.0]s. Regex `r'^[0-9A-Fa-f]+\s+<\s*\d+\s*>\s+\[\s*(\d+\.\d+)\s*\]'` (kernel log uses `< 6>` — space inside angle brackets).

### A.1 Rev2Snk PASS run — kernel 87.1–87.8s (full SNK negotiation)

| Line | t (s) | Event |
|---|---|---|
| L10667 | 87.107 | `sc27xx_typec_interrupt enter line 797` — typec attach |
| L10720 | 87.169 | `state change TOGGLING -> SNK_ATTACH_WAIT` |
| L10734 | 87.186 | `state change SNK_ATTACHED -> SNK_STARTUP` |
| L10735 | 87.187 | `state change SNK_STARTUP -> SNK_DISCOVERY` |
| L10740 | 87.193 | `state change SNK_DISCOVERY -> SNK_WAIT_CAPABILITIES` |
| L10761 | 87.298 | **RX Source_Capabilities** `header = 0x1161` (R2, id0, Src/DFP, NDO=1) |
| L10776 | 87.315 | **TX Request** `0x1042` (R2, id1, Snk/UFP, NDO=1) |
| L10793 | 87.334 | **RX Accept** `0x363` (R2, id2, Src/DFP) |
| **L10976** | **87.758** | **RX PS_RDY `header = 0x566` (MsgID=2, R2, Src/DFP)** ← **clock-alignment anchor #1** |
| L10981 | 87.758 | `PD RX, header: 0x566 [1][device]` |
| L10983 | 87.758 | `state change SNK_TRANSITION_SINK -> SNK_READY` ← **Rev2Snk reaches SNK_READY (PASS)** |

### A.2 PR_Swap phase — kernel 88.2–90.0s (immediately after Rev2Snk PASS)

| Line | t (s) | Event |
|---|---|---|
| L11038 | 88.236 | `vbus is already Off` |
| **L11040** | **88.258** | **RX PR_Swap** `header = 0x76a` (parser=DR_Swap / **spec=PR_Swap**, MsgID=3, R2, Src/DFP) ← **THE CONFLICTED PR_Swap** |
| L11043 | 88.261 | `PD RX, header: 0x76a [1][device]` |
| L11044 | 88.263 | `state change SNK_READY -> PR_SWAP_ACCEPT` |
| L11049 | 88.265 | **TX Accept** `0x243` (MsgID=1, Snk/UFP) |
| L11066 | 88.276 | `state change PR_SWAP_ACCEPT -> PR_SWAP_START` |
| L11072 | 88.286 | `state change PR_SWAP_START -> PR_SWAP_SNK_SRC_SINK_OFF` (vbus=0 charge=0, "vbus is already Off") |
| L11076 | 88.288 | `pending state change PR_SWAP_SNK_SRC_SINK_OFF -> ERROR_RECOVERY @ 835 ms` |
| L11337 | 89.073 | `state change PR_SWAP_SNK_SRC_SINK_OFF -> ERROR_RECOVERY [delayed 835 ms]` ← tPSSourceOffTimer 835ms expiry |
| L11357 | 89.xxx | `state change -> PORT_RESET` |
| L11403 | 90.022 | `state change PORT_RESET_WAIT_OFF -> SNK_UNATTACHED [delayed 835 ms]` |
| L11404 | 90.024 | `Start toggling` |
| L11405 | 90.025 | `state change SNK_UNATTACHED -> TOGGLING` |

**Observation**: the PR_Swap at kernel 88.2s occurred **after** Rev2Snk had already reached SNK_READY (at 87.758s). Per USB PD, a PR_Swap received while in SNK_READY is normal (Tester-initiated role swap at the end of the test). The swap FAILED (tPSSourceOffTimer 835ms → ERROR_RECOVERY), but the overall Rev2Snk test still PASSED because SNK_READY had been reached.

### A.3 Rev3ChkdSnk FAIL run — kernel 101.8s+

| Line | t (s) | Event |
|---|---|---|
| **L11722** | **101.833** | `sc27xx_typec_interrupt enter line 797` — Rev3ChkdSnk attach detected |
| **L11723** | **101.834** | **`typec has already connected!`** ← **SMOKING GUN** (stale state) |
| L11724 | 101.835 | `now works as DRP and is in 2 state, event 1` |
| L11725 | 101.857 | `vbus_change_event, vbus_online: 0, ... Power Role: Sink` |
| L11728 | 101.864 | `vbus_change_event, vbus_online: 1` |
| L11730 | 101.867 | `typec connect, not vbusonly` |
| L11878 | 109.775 | `vbus_change_event, vbus_online: 0` ← VCONN_Swap window (clock-aligned) |
| L11895 | 110.919 | `vbus_change_event, vbus_online: 1` |

**Critical**: in the ENTIRE [101.8, 112.0]s window, there are **ZERO** `header = 0x` lines, **ZERO** `PD RX` / `PD TX` lines, **ZERO** state-machine transitions to `SNK_WAIT_CAPABILITIES` / `SNK_NEGOTIATE_CAPABILITIES` / `SNK_READY`. Only `typec attach` + `vbus_change_event` toggling + charging-subsystem (bq2560x) activity. See Section C for the broader-window confirmation.

---

## B. Clock Alignment (Task B)

**Method**: match `(header_hex, MsgID)` pairs that appear in BOTH the POWER-Z capture (Agent 2) and the kernel log. These are independent clocks; a matching pair gives the offset.

### B.1 Anchor #1 — PS_RDY 0x566

| Source | t (s) | header | MsgID | Rev | Role |
|---|---|---|---|---|---|
| POWER-Z (Agent 2, §3.1) | 35.761 | 0x566 | 2 | R2 | Src/DFP |
| Kernel L10976 (this report §A.1) | 87.758 | 0x566 | 2 | R2 | Src/DFP |
| **Offset** | **+51.997 s** | | | | |

### B.2 Anchor #2 — PR_Swap 0x76a

| Source | t (s) | header | MsgID | Rev | Role |
|---|---|---|---|---|---|
| POWER-Z (Agent 2, §3.2) | 36.263 | 0x076a | 3 | R2 | Src/DFP |
| Kernel L11040 (this report §A.2) | 88.258 | 0x76a | 3 | R2 | Src/DFP |
| **Offset** | **+51.994 s** | | | | |

### B.3 Alignment verdict

Both independent anchors give **offset ≈ +52.0 s** (Δ = 3 ms — within clock jitter). **Alignment CONFIRMED.**

```
kernel_t = POWER-Z_t + 52.0 s
```

### B.4 Attribution of the 88.2 s / 0x76a PR_Swap

- POWER-Z Rev2Snk PR_Swap @ 36.263 s → kernel = 36.263 + 52.0 = **88.263 s** ≈ kernel L11040 @ 88.258 s. ✓
- POWER-Z Rev3ChkdSnk window = 49.984–65.133 s → kernel = **101.98–117.13 s**.
- POWER-Z Rev3ChkdSnk VCONN_Swap @ 57.728 s → kernel = 57.728 + 52.0 = **109.728 s** ≈ kernel L11878 @ 109.775 s (`vbus_change_event, vbus_online: 0`). ✓

**VERDICT**: The kernel 88.2 s / 0x76a PR_Swap belongs to the **Rev2Snk PASS run** (it is the end-of-test role swap the Tester sends after Rev2Snk reaches SNK_READY). It does **NOT** belong to the Rev3ChkdSnk FAIL run. **Agent 3 analyzed the wrong window.** The real Rev3ChkdSnk FAIL run in the kernel log is at **≈102–117 s**, not 88 s.

---

## C. Rev3ChkdSnk FAIL-run kernel analysis (Task C)

**Source command**: `python "C:/Users/xianjun.zeng/AppData/Local/Temp/rc_task_c.py"` → output `C:\Users\xianjun.zeng\AppData\Local\Temp\rc_out_c.txt` (366 lines, 181 events in [90.0, 120.0]s with broader keyword filter)
**Original file**: same 0-kernel.log as §A.

### C.1 The gap between Rev2Snk and Rev3ChkdSnk (kernel 90.0–101.8 s)

After Rev2Snk's PR_Swap failure → ERROR_RECOVERY → PORT_RESET → `Start toggling` → `SNK_UNATTACHED -> TOGGLING` (L11403–11405 @ 90.02 s), the DUT sits in TOGGLING for ~11 seconds. During this gap (90.76–101.07 s) the log shows ONLY charging-subsystem polling:
- `bq2560x:check vbus:132 < 4700, report aicl status` (VBUS below PD threshold)
- `bq25601: stop charge` repeated every ~1 s
- `CHG_STAT: NOT CHARGING`

**No PD RX/TX, no state machine transitions.** DUT is in TOGGLING, waiting for a new attach.

### C.2 Rev3ChkdSnk attach — the SMOKING GUN (kernel 101.83 s)

```
L11722 t=101.832574  sc27xx_typec_interrupt enter line 797
L11723 t=101.834187  typec has already connected!          ← STALE STATE
L11724 t=101.835396  now works as DRP and is in 2 state, event 1
L11725 t=101.857311  sc27xx_pd_extcon_vbus_change_event, vbus_online: 0, can_communication: 1, Power Role: Sink, in_hard_reset: 0
L11726 t=101.861138  vbus_connect_value:1
L11728 t=101.863515  vbus_change_event, vbus_online: 1
L11730 t=101.867158  typec connect, not vbusonly
```

The message **`typec has already connected!`** at L11723 is the root-cause indicator. When the Tester re-attaches for the Rev3ChkdSnk (PD 3.0) run, the `sc27xx-typec` driver's internal "connected" flag is **still set** from the prior Rev2Snk run (which ended in TOGGLING but never cleanly cleared the typec-attach state). As a result, the driver treats the new attach as a no-op duplicate and **does not re-initialize the PD engine**.

### C.3 What the PD stack did while Tester sent 280 Requests + 3 VCONN_Swaps

Across the **entire** Rev3ChkdSnk window (kernel 101.8–120.0 s, ≈18 s), the broader-filter extraction (rc_out_c.txt) shows:

| Category | Count in [101.8, 120.0] s |
|---|---|
| `PD RX` / `PD TX` lines | **0** |
| `header = 0x` / `header:` occurrences | **0** |
| `state change ... -> SNK_WAIT_CAPABILITIES` | **0** |
| `state change ... -> SNK_NEGOTIATE_CAPABILITIES` | **0** |
| `state change ... -> SNK_READY` | **0** |
| `Accept` / `Request` / `PS_RDY` / `PR_Swap` TX/RX | **0** |
| `vbus_change_event` toggles | 4 (vbus_online 0→1→0→1) |
| `typec connect, not vbusonly` | 2 (L11730 @ 101.867, L11897 @ 110.922) |
| charging subsystem (bq2560x start/stop charge, FGU) | many |

The **only** PD-adjacent events are `vbus_change_event` toggles. Notably:
- L11878 @ **109.775 s** `vbus_change_event, vbus_online: 0` — this is clock-aligned to POWER-Z VCONN_Swap @ 57.728 s (57.728 + 52.0 = 109.728 s). The VCONN_Swap causes a VBUS dip the typec driver detects — but because the PD engine was never started, **no PD message is sent or received**.
- L11895 @ 110.919 s `vbus_change_event, vbus_online: 1` — VBUS returns.

### C.4 Why the PD 3.0 stack does not process the Tester's messages

The `sc27xx-typec` driver sees the stale `typec has already connected!` state and **never calls the PD-engine re-init path** (`sprd_tcpm_snk_attach` / `sc27xx_pd_reset` / `SNK_STARTUP` sequence seen at kernel 87.13–87.19 s during the healthy Rev2Snk attach). Compare:

| Step | Rev2Snk attach (L10667–10740) | Rev3ChkdSnk attach (L11722–11730) |
|---|---|---|
| typec interrupt | ✓ enter line 797 | ✓ enter line 797 |
| "already connected" check | (not printed — fresh) | **"typec has already connected!"** ← blocks re-init |
| `pd attached = 1` | ✓ | ✗ (absent) |
| `pd := on` | ✓ (L10699) | ✗ |
| `sc27xx_pd_reset` / `rx_flush` | ✓ | ✗ |
| `state change TOGGLING -> SNK_ATTACH_WAIT` | ✓ | ✗ |
| `state change -> SNK_WAIT_CAPABILITIES` | ✓ | ✗ |
| RX Source_Capabilities | ✓ (0x1161) | ✗ |

Because the PD engine never enters `SNK_WAIT_CAPABILITIES`, the Tester's Source_Capabilities, its 280 repeated PD3.0 Requests, and its 3 VCONN_Swaps are **never received/processed by the DUT PD stack**. The Tester's messages go unanswered (matching Agent 2's observation of 0 DUT responses), and VBUS merely toggles as a side-effect of the VCONN_Swap's electrical effect on VBUS.

**This RESOLVES Agent 2's open question** ("why doesn't the PD 3.0 stack process the Tester's messages?"): the typec driver's stale "already connected" state prevented PD-stack re-initialization at the Rev3ChkdSnk attach.

---

## D. Parser Correctness (Task D)

**Source file**: `C:\Users\xianjun.zeng\.claude\skills\protocol-parser\parsers\pd_parser.py` (877 lines)

### D.1 The bug

The `PD_MESSAGE_TYPES` dict (lines 127–144) mislabels USB PD Control message types from `0x9` onward — **off-by-one versus the USB PD spec (both R2.0 and R3.0)**.

| msg_type | pd_parser.py line | parser label | USB PD spec (R2.0 & R3.0) | correct? |
|---|---|---|---|---|
| 0x8 | L136 | Get_Sink_Cap | Get_Sink_Cap | ✓ |
| 0x9 | **L137** | Sink_Capabilities | **DR_Swap** | ✗ WRONG |
| 0xA | **L138** | DR_Swap | **PR_Swap** | ✗ WRONG ← key error |
| 0xB | **L139** | PR_Swap | **VCONN_Swap** | ✗ WRONG |
| 0xC | **L140** | VCONN_Swap | **Wait** | ✗ WRONG |
| 0xD | **L141** | Wait | **Soft_Reset** | ✗ WRONG |
| 0xE | **L142** | Soft_Reset | **Data_Reset** | ✗ WRONG |

The dict appears to follow the USB PD R1.0 / early-draft ordering where `0x9 = Sink_Capabilities` (a Data message). In PD R2.0 and R3.0, `Sink_Capabilities` is a **Data** message with `msg_type = 0x8` is `Get_Sink_Cap` (Control) — and the Control-message numbering from 0x9 onward is `DR_Swap, PR_Swap, VCONN_Swap, Wait, Soft_Reset, Data_Reset`.

### D.2 What is NOT buggy

- The `decode_pd_header` function (lines 180–217) bit-level decoding is **CORRECT** per spec: bit15=Extended, bits14-12=NumDataObjects, bits11-9=MsgID, bit8=PowerRole, bits7-6=SpecRevision, bit5=DataRole, bit4=reserved, bits3-0=MessageType (L196 `msg_type_code = val & 0xF`). Only the `PD_MESSAGE_TYPES` *lookup table* is wrong.
- The separate `PD_COMMANDS` dict (lines 89–122) uses a **different** 2-digit hex scheme — these are SPRD hardware custom codes (e.g. `0A: PS_RDY`, `0C: DR_SWAP`, `0D: PR_SWAP`), a custom hardware mapping, NOT the PD R3.0 spec message-type encoding. Not necessarily buggy, just a different namespace.

### D.3 Impact on this Bug

Agent 3 used the parser's label for `0x76a` → bits[3:0] = 0xA → parser said "DR_Swap", but per spec 0xA = **PR_Swap**. The DUT kernel log itself (L11044) shows `state change SNK_READY -> PR_SWAP_ACCEPT` — i.e. the **DUT firmware correctly identified 0x76a as PR_Swap** (firmware uses its own table, not pd_parser.py). Agent 3, trusting the parser, proposed "Candidate A: DUT misinterprets DR_Swap as PR_Swap". That candidate is **INVALIDATED**: per spec 0x76a IS PR_Swap; the DUT correctly entered PR_SWAP_ACCEPT. The parser mislabel is a **tooling bug, separate from the cert-failure root cause**.

### D.4 Recommended parser fix (for the tooling bug, not the cert bug)

```diff
--- a/pd_parser.py
+++ b/pd_parser.py
@@ -134,9 +134,9 @@ PD_MESSAGE_TYPES = {
     0x7: "Get_Source_Cap",
     0x8: "Get_Sink_Cap",
-    0x9: "Sink_Capabilities",
-    0xA: "DR_Swap",
-    0xB: "PR_Swap",
-    0xC: "VCONN_Swap",
-    0xD: "Wait",
-    0xE: "Soft_Reset",
+    0x9: "DR_Swap",
+    0xA: "PR_Swap",
+    0xB: "VCONN_Swap",
+    0xC: "Wait",
+    0xD: "Soft_Reset",
+    0xE: "Data_Reset",
     0xF: "Vendor_Defined",
 }
```
(Note: `Sink_Capabilities` is a Data message, not Control; it belongs in the Data-message-type table, keyed by the Data msg_type numbering, not here.)

---

## E. Final Reconciled Root Cause (Task E)

### E.1 Conflict resolution

The Agent 2 vs Agent 3 conflict is **RESOLVED**. The two agents were looking at **two different runs**:

- **Agent 3's kernel 88.2 s PR_Swap (0x76a)** is part of the **Rev2Snk PASS run**. Clock alignment (offset +52.0 s, two independent anchors: 0x566/MsgID=2 and 0x76a/MsgID=3) maps kernel 88.258 s → POWER-Z 36.263 s, which is inside the Rev2Snk window (POWER-Z 35.7–36.3 s). Agent 3 analyzed the **wrong window** — he mistook the end-of-Rev2Snk PR_Swap for the Rev3ChkdSnk FAIL run.
- **Agent 2's Rev3ChkdSnk FAIL run** (POWER-Z 49.98–65.13 s) maps to kernel **101.98–117.13 s**. In that kernel window the DUT PD stack is **completely silent** (0 PD RX/TX, 0 state transitions to negotiation) — exactly matching Agent 2's observation of 0 DUT responses.

Both agents were individually correct about what they observed; they disagreed only because each thought his run was the Rev3ChkdSnk run. Agent 2 was right; Agent 3's run was Rev2Snk.

### E.2 The Rev2Snk PR_Swap at 88.2 s

The PR_Swap the Tester sent at the end of Rev2Snk **did fail** (tPSSourceOffTimer 835 ms expired → ERROR_RECOVERY @ 89.073 s → PORT_RESET → TOGGLING @ 90.025 s). This matches the Lecroy HTML annotation "Error Recovery Detected on 851.180 ms" cited by Agent 2. However, the overall Rev2Snk test was still marked **PASS** by Lecroy because the DUT had already reached SNK_READY (the Common-Checks pass criterion) at kernel 87.758 s. The PR_Swap failure is a secondary issue, not the cert-failure root cause.

(The PR_Swap failure mechanism: the DUT, as Sink entering PR_Swap, must turn off its VBUS sink and wait for the new Source to supply VBUS. At L11038/L11072 the kernel reports "vbus is already Off" — VBUS was already 0 before the swap. The `PR_SWAP_SNK_SRC_SINK_OFF` state then waited the full `tPSSourceOffTimer` (835 ms) without advancing to `SRC_TRANSITION`, then ERROR_RECOVERY. This is consistent with the Tester not driving VBUS as the new Source within the timer window, OR the DUT's sink-off detection failing because VBUS was already 0 — a separate issue worth a follow-up, but not the cause of the Rev3ChkdSnk FAIL.)

### E.3 The real Rev3ChkdSnk FAIL root cause

**Root cause (HIGH confidence)**: The `sc27xx-typec` driver retained a stale "connected" state from the prior Rev2Snk run (which ended in TOGGLING after its PR_Swap ERROR_RECOVERY/PORT_RESET). When the Tester re-attached for the Rev3ChkdSnk (PD 3.0) run at kernel 101.833 s, the typec interrupt fired (L11722), but the driver printed **`typec has already connected!`** (L11723) and **did not re-initialize the PD engine**. Specifically, it skipped:
- `pd attached = 1` / `pd := on`
- `sc27xx_pd_reset` / `sc27xx_pd_rx_flush`
- the `TOGGLING -> SNK_ATTACH_WAIT -> SNK_STARTUP -> SNK_DISCOVERY -> SNK_WAIT_CAPABILITIES` state-machine sequence

Consequently the PD engine never entered `SNK_WAIT_CAPABILITIES` and never received the Tester's `Source_Capabilities`. The Tester's subsequent 280 repeated PD3.0 Requests (MsgID cycling 0–7, ~150 ms apart) and 3 VCONN_Swaps (0x01ad @ POWER-Z 57.728–57.731 s ↔ kernel 109.73 s) all went **unanswered** by the DUT. The VCONN_Swap's electrical effect on VBUS was detected by the typec hardware as `vbus_change_event` toggles (L11878 @ 109.775 s, L11895 @ 110.919 s), but no PD message was ever sent or received. Lecroy recorded 0 HTML annotations for this run and marked it FAIL.

### E.4 Confidence

**HIGH.** Three independent lines of evidence converge:
1. **Clock alignment** with two independent `(header, MsgID)` anchors (0x566/id2, 0x76a/id3) both give offset +52.0 s (Δ 3 ms). This unambiguously places kernel 88.2 s in the Rev2Snk run and the Rev3ChkdSnk FAIL run at kernel 102–117 s.
2. **Rev3ChkdSnk FAIL-run kernel evidence** (rc_out_c.txt, broader filter, 18 s window): zero PD RX/TX, zero negotiation state transitions — directly matches Agent 2's "0 DUT responses".
3. **Smoking gun** `typec has already connected!` at L11723 (t=101.834 s) is a direct, mechanistic explanation for why the PD stack was never re-initialized: the typec driver's stale "connected" flag short-circuited the attach handler. The contrast with the healthy Rev2Snk attach (which ran the full `pd := on` → `sc27xx_pd_reset` → `SNK_WAIT_CAPABILITIES` sequence at L10699–10740) is definitive.

### E.5 Recommended next steps (for the cert failure — separate from the parser bug)

1. **Primary fix (driver)**: in `sc27xx-typec`, when the PORT_RESET/ERROR_RECOVERY/TOGGLING path tears down a connection, explicitly clear the internal "typec connected" flag so that the next `sc27xx_typec_interrupt` for a fresh attach runs the full re-init path instead of bailing out with "already connected". Equivalently, treat `TOGGLING -> SNK_ATTACH_WAIT` as the authoritative attach signal and force-reinit the PD engine regardless of the stale flag.
2. **Secondary investigation**: why the Rev2Snk PR_Swap failed (tPSSourceOffTimer expiry when "vbus is already Off"). This is a real defect but did not fail the cert (Rev2Snk still PASSed). Worth a follow-up bug but not the cert root cause.
3. **Tooling fix**: apply the pd_parser.py diff in §D.4 so future analyses do not mislabel PR_Swap as DR_Swap.

---

## Appendix: artifacts produced by this reconciliation

| Artifact | Path | Size |
|---|---|---|
| Task A extraction script | `C:\Users\xianjun.zeng\AppData\Local\Temp\rc_task_a2.py` | 122 lines |
| Task A output | `C:\Users\xianjun.zeng\AppData\Local\Temp\rc_out_a.txt` | 379 lines / 187 events |
| Task C extraction script | `C:\Users\xianjun.zeng\AppData\Local\Temp\rc_task_c.py` | 118 lines |
| Task C output | `C:\Users\xianjun.zeng\AppData\Local\Temp\rc_out_c.txt` | 366 lines / 181 events |
| This report | `...\reanalysis\05_reconciliation.md` | (see byte size in final return) |
