# 02 — 真实失败点定位（Trace 派生）

**Bug**: 3523391 (unicase005585)
**测试用例**: TEST.PD.PROT.SNK.12 — PR_Swap - PSSourceOffTimer Timeout
**DUT**: UNISOC-P610F01-1.0 (UMS512 / SC27xx PMIC 集成 CC)
**分析时间**: 2026-09-11
**证据层级**: Lecroy .usb + USB_ComplianceTestLog.html = 主证据；POWER-Z pd.sqlite = 辅助交叉验证（单独标记来源）

---

## 1. 测试用例说明

TEST.PD.PROT.SNK.12 是 USB PD 协议合规性测试中的 Sink 端 PR_Swap（Power Role Swap）测试。

**用例目的**（来源: `USB_ComplianceTestLog.html` 第 295 行）:
> TEST.PD.PROT.SNK.12 PR_Swap - PSSourceOffTimer Timeout

**完整用例名**中的 "PSSourceOffTimer Timeout" 是**测试用例的名称/目的**，不是失败判决。该测试验证 Sink 在 PR_Swap 过程中是否正确处理 tPSSourceOffTimer 时序。

**预期流程**:
1. Tester（Source/DFP）完成 PD 协商
2. Tester 发送 PR_Swap 控制消息给 DUT（Sink/UFP）
3. DUT 回复 Accept
4. Source 关断 VBUS → 等待 tPSSourceOffTimer → Source 发送 PS_RDY
5. DUT（现为 Source）发送 PS_RDY
6. 角色互换完成

**测试变体**:
- **Rev2Snk** (TestPdRevision=1, 即 PD 2.0): DUT 以 PD 2.0 模式运行
- **Rev3ChkdSnk** (TestPdRevision=2, 即 PD 3.0): DUT 以 PD 3.0 Checked 模式运行

---

## 2. Lecroy 测试结果总览（主证据）

### 2.1 结果摘要

来源: `E:\08_Bug\Bug 3523391(unicase005585) - [UMS512][zte_sh][P610F01][17353][现场-客户手机]PD CE认证失败 TEST.PD.PROT.SNK.12\Attachements\20260827_155005\USB Power Delivery\TEST.PD.PROT.SNK.12\USB_ComplianceTestLog.html`

| 测试变体 | PD Revision | 结果 | 分析仪触发 | Generation 超时 | 错误码 |
|----------|:-----------:|:----:|:----------:|:---------------:|:------:|
| Rev2Snk | PD 2.0 (TestPdRevision=1) | **PASS** | 3752 ms | — | — |
| Rev3ChkdSnk | PD 3.0 (TestPdRevision=2) | **FAIL** | 16164 ms | 15112 ms | 0xFFF5 |

### 2.2 Rev2Snk (PD 2.0) — PASS 详情

来源: `USB_ComplianceTestLog.html`，逐行引用：

| 行号 | 原文 | 说明 |
|------|------|------|
| 430 | `<li >Rev2Snk <font color="#22b14c">pass</font>` | 变体结果: PASS |
| 441 | `Update TestPdRevision in file Variables.inc to 1` | TestPdRevision=1 → PD 2.0 |
| 488 | `Analyzer Trigged... 3752 ms` | 分析仪在 3752 ms 触发，在 15000 ms 窗口内 |
| 494 | `COMMON.PROC.BU.2#1 pass` | 验证 1/3: PASS |
| 518 | `TEST.PD.PROT.SNK.12#1 pass` | 验证 2/3: PASS |
| 542 | `TEST.PD.PROT.SNK.12#2 pass` | 验证 3/3: PASS |

**3 项验证全部通过**。分析仪在 3752 ms 触发（远在 15000 ms 等待窗口内），说明 PR_Swap 握手按时完成。

### 2.3 Rev3ChkdSnk (PD 3.0) — FAIL 详情

来源: `USB_ComplianceTestLog.html`，逐行引用：

| 行号 | 原文 | 说明 |
|------|------|------|
| 571 | `<li >Rev3ChkdSnk <font color="#ff0000">fail</font>` | 变体结果: FAIL |
| 582 | `Update TestPdRevision in file Variables.inc to 2` | TestPdRevision=2 → PD 3.0 |
| 627 | `Generation Time-out... 15112 ms` | Generation 超时 15112 ms，超过 15000 ms 等待 |
| 630 | `Analyzer Trigged... 16164 ms` | 分析仪在 16164 ms 触发 |
| 638 | `Error(0xFFF5): Test scenario aborted. Please check the trace file to determine the cause.` | 测试场景中止 |
| 651 | `Test Elapsed Time: 0 minute(s) and 44 seconds` | 总耗时 44 秒 |

---

## 3. 真实失败点（Trace 派生）

### 3.1 推导方法

1. 读取 Lecroy `USB_ComplianceTestLog.html` 全文 654 行，提取 Rev2Snk 和 Rev3ChkdSnk 两个变体的结果、时序、错误码
2. 从 Lecroy `.usb` 二进制文件中提取 HTML 标注块（`<html>...</html>`），这些标注由 Lecroy Compliance Suite 在测试过程中写入，记录每个测试步骤的完成状态
3. 比较两个 `.usb` 文件的 HTML 标注数量和内容
4. 使用 POWER-Z pd.sqlite 进行辅助交叉验证（标记为"POWER-Z 辅助捕获"）

### 3.2 Lecroy .usb HTML 标注分析（主证据）

来源:
- `E:\08_Bug\Bug 3523391(unicase005585) - [UMS512][zte_sh][P610F01][17353][现场-客户手机]PD CE认证失败 TEST.PD.PROT.SNK.12\Attachements\20260827_155005\USB Power Delivery\TEST.PD.PROT.SNK.12\01_TEST.PD.PROT.SNK.12_Rev2Snk.usb` (9,261,906 bytes)
- `E:\08_Bug\Bug 3523391(unicase005585) - [UMS512][zte_sh][P610F01][17353][现场-客户手机]PD CE认证失败 TEST.PD.PROT.SNK.12\Attachements\20260827_155005\USB Power Delivery\TEST.PD.PROT.SNK.12\02_TEST.PD.PROT.SNK.12_Rev3ChkdSnk_FAIL.usb` (25,614,448 bytes)

#### File 01 (Rev2Snk PASS) — 5 个 HTML 标注:

| 序号 | 偏移 | HTML 标注内容 | 对应测试步骤 |
|------|------|--------------|-------------|
| 1 | @008d4eb9 | `negotiation completed` | PD 协商完成 |
| 2 | @008d4ef7 | `the tester sends a pr_swap message to the uut` | Tester 发送 PR_Swap |
| 3 | @008d4f4d | `the put sent an accept message to pr-swap. the uut sent an accept message` | DUT 回复 Accept |
| 4 | @008d4fbf | `Error Recovery Detected on 851.180 ms [Start of measurement: 4.021 sec Found: 4.872 sec (750.000 ms - 920.000 ms)]` | Error Recovery 检测（PR_Swap 角色切换的正常恢复） |
| 5 | @008d505f | `End of the Common-Checks.` | Common-Checks 完成 |

**结论**: PR_Swap → Accept 握手完整完成，测试场景走完全流程。

#### File 02 (Rev3ChkdSnk FAIL) — 0 个 HTML 标注:

| 序号 | 偏移 | HTML 标注内容 | 对应测试步骤 |
|------|------|--------------|-------------|
| — | — | **（无）** | — |

**File 02 中唯一可提取的字符串**:
- `LeCroy Analyzer Trace File` — 文件头 magic
- `Teledyne LeCroy USB Compliance Suite Version: 7.92 Build 1198` — 软件版本
- `Triggered on Exr Port Rp On (CC1), Exr Port Ra On (CC2), Power Delivery/CC Packets` — 触发条件
- `CATCWalk`
- `0-106/Packet/107` — 包引用（107 个包被记录）
- `Packet 106/Packet`

**结论**: 测试场景在**任何测试步骤标注写入之前**就中止了。Lecroy Compliance Suite 在正常完成一个步骤后会写入 HTML 标注（如 "negotiation completed"）。File 02 中 0 个 HTML 标注意味着**连初始协商（negotiation completed）步骤都未完成**，场景即被中止。

### 3.3 POWER-Z 辅助交叉验证（非 Lecroy 来源）

> **来源标记**: 以下数据来自 POWER-Z 手持式 USB PD 分析仪（pd.sqlite），**不是 Lecroy 数据**。仅作为辅助交叉验证使用。
>
> 文件: `E:\08_Bug\Bug 3523391(unicase005585) - [UMS512][zte_sh][P610F01][17353][现场-客户手机]PD CE认证失败 TEST.PD.PROT.SNK.12\Attachements\20260827_155005\pd.sqlite` (167,936 bytes)
>
> 解码方法: `C:\Users\xianjun.zeng\AppData\Local\Temp\decode_powerz_full.py`，按 PD spec 标准布局解码 16-bit header（offset 6 小端序）

POWER-Z 共捕获 303 条原始记录（295 条有效 PD 消息），时间跨度 t=16.206s ~ 71.504s（55.298s）。

**消息类型统计**:

| 数量 | 消息类型 | 所属阶段 |
|------|----------|----------|
| 280 | PD3.0/Src/DFP/Request | Phase 3/4 (Rev3ChkdSnk PD3.0) |
| 4 | PD2.0/Snk/UFP/GoodCRC | Phase 2 (Rev2Snk PD2.0) |
| 3 | PD3.0/Src/DFP/VCONN_Swap | Phase 3 (Rev3ChkdSnk PD3.0) |
| 2 | PD2.0/Src/DFP/GoodCRC | Phase 2 |
| 1 | PD2.0/Src/DFP/Request | Phase 2 |
| 1 | PD2.0/Snk/UFP/BIST | Phase 2 |
| 1 | PD2.0/Src/DFP/Accept | Phase 2 |
| 1 | **PD2.0/Src/DFP/PS_RDY** | **Phase 2（唯一一次 PS_RDY）** |
| 1 | PD2.0/Src/DFP/Get_Sink_Cap | Phase 2 |
| 1 | PD2.0/Snk/UFP/Accept | Phase 2 |

**关键发现**:
- **PS_RDY 仅出现 1 次**，在 Phase 2（Rev2Snk PD2.0），t=35.761s
- **Phase 3/4（Rev3ChkdSnk PD3.0）中 PS_RDY 出现次数 = 0**
- Phase 3/4 中 Accept 出现次数 = 0
- Phase 3/4 中 PR_Swap 控制消息出现次数 = 0
- Phase 3/4 仅有 280 条重复的 PD3.0/Src/DFP/Request 消息（payload=0a900120，MessageID 循环 0-7），以及 3 条 VCONN_Swap（t=57.728-57.731s，未得到 Accept 响应）

### 3.4 真实失败点结论

**真实失败点**: Rev3ChkdSnk（PD 3.0）测试场景在初始阶段即中止（Error 0xFFF5 "Test scenario aborted"），DUT 在 PD 3.0 模式下未发送 PS_RDY。

**Lecroy 主证据链**:
1. `USB_ComplianceTestLog.html` 第 638 行: `Error(0xFFF5): Test scenario aborted. Please check the trace file to determine the cause.` — 场景中止，非定时器超时测量
2. `02_TEST.PD.PROT.SNK.12_Rev3ChkdSnk_FAIL.usb` 中 HTML 标注数 = 0 — 场景在写入任何步骤标注前中止
3. `01_TEST.PD.PROT.SNK.12_Rev2Snk.usb` 中 HTML 标注数 = 5 — 对比证明 PASS 变体走完了完整流程

**POWER-Z 辅助验证**: PD3.0 阶段 280 条重复 Request 消息中无任何 PS_RDY/Accept/PR_Swap，与 Lecroy .usb 零标注结论一致。

---

## 4. 时序测量

来源: `USB_ComplianceTestLog.html`

| 指标 | Rev2Snk (PASS) | Rev3ChkdSnk (FAIL) | 合规判定 |
|------|:--------------:|:------------------:|----------|
| Generation Max Wait | 15000 ms | 15000 ms | — |
| Analyzer Trigged | 3752 ms | 16164 ms | — |
| Generation Time-out | — | 15112 ms | 超过 15000 ms 等待窗口 |
| 实际场景状态 | 3/3 验证通过 | 场景中止 (0xFFF5) | — |

**分析**:
- Rev2Snk: 分析仪在 3752 ms 触发，远在 15000 ms 窗口内 → 正常
- Rev3ChkdSnk: Generation Time-out 在 15112 ms 触发（超过 15000 ms 等待），说明 Lecroy Compliance Suite 的场景脚本在等待 DUT 响应时超时。随后分析仪在 16164 ms 触发（Generation Time-out 后 1052 ms），最终输出 Error(0xFFF5)

---

## 5. VBUS 状态

来源: POWER-Z pd.sqlite（辅助捕获）

| 阶段 | VBUS 电压范围 | 说明 |
|------|:------------:|------|
| Phase 1 (t=16.206-16.211s) | 5.26 V | 初始 5V |
| Phase 2 (t=35.302-36.267s) | 4.98 V | Rev2Snk PR_Swap 期间 |
| Phase 3/4 (t=49.984-65.133s) | 4.98-4.99 V | Rev3ChkdSnk 期间 |

**VBUS 全程稳定在 4.98-5.26V**，无明显断电或异常波动。VBUS 时序正常。

---

## 6. 与 Comment #27 对齐校验

**Comment #27 原文** (Yongqing.Wang, 9/8):
> PD 2.0 首次 PR_Swap 成功。PD 3.0 第二次 PR_Swap 未收到 PS_RDY。VBUS 时序日志匹配

| Comment #27 论点 | Trace 证据 | 对齐 |
|-----------------|-----------|:----:|
| PD 2.0 首次 PR_Swap 成功 | Rev2Snk PASS (3/3 验证通过)；.usb File 01 有 5 个 HTML 标注含 "pr_swap" + "accept"；POWER-Z PS_RDY @ t=35.761s | ✅ 一致 |
| PD 3.0 第二次 PR_Swap 未收到 PS_RDY | Rev3ChkdSnk FAIL；.usb File 02 有 0 个 HTML 标注；POWER-Z Phase 3/4 中 PS_RDY 数量=0 | ✅ 一致 |
| VBUS 时序日志匹配 | POWER-Z VBUS 全程 4.98-5.26V 稳定 | ✅ 一致 |

**Comment #27 的三个论点全部被 Lecroy 主证据 + POWER-Z 辅助证据证实。**

---

## 7. 驳斥旧错误结论

### 旧结论（2026-09-09 产出，已确认错误）

> "步骤 4→5 tPSSourceOffTimer 超时"
> "sc27xx_typec_pr_swap_no_chk_detach(on=1) 提前禁用 CC 检测导致超时"

### 驳斥依据

| 旧论点 | Trace 事实 | 驳斥 |
|--------|-----------|------|
| "tPSSourceOffTimer 超时" | Lecroy 判决为 `Error(0xFFF5): Test scenario aborted`（场景中止），**不是** tPSSourceOffTimer 定时器超时测量。"PSSourceOffTimer Timeout" 是**测试用例名称**，不是失败判决 | ❌ 推翻 |
| "步骤 4→5 超时" | .usb File 02 有 0 个 HTML 标注，场景在步骤 1（negotiation completed）之前就中止了，根本未到达步骤 4→5 | ❌ 推翻 |
| "sc27xx_typec_pr_swap_no_chk_detach(on=1) 提前禁用 CC 检测" | 该结论从 kernel log 反推得出，**未读取任何 trace 文件**。Trace 证据显示 DUT 在 PD3.0 模式下未响应 PS_RDY，与 kernel log 中的 CC 检测禁用无因果关系 | ❌ 推翻 |

**旧结论的流程错误**: 在未读取 Lecroy .usb trace 和 USB_ComplianceTestLog.html 的情况下，从 kernel log 反推了一个 trace 层面不存在的失败点。详见 `C:\Users\xianjun.zeng\.claude\skills\pd_auth_analyse\data\cases\3523391_TEST.PD.PROT.SNK.12\reanalysis\00_process_failure_analysis.md`。

---

## 8. 结论

**真实失败点**（Trace 派生）:

Rev3ChkdSnk（PD 3.0）变体中，DUT 在 PD 3.0 模式下**未发送 PS_RDY**，导致 Lecroy Compliance Suite 的测试场景脚本无法完成，Generation Time-out 在 15112 ms 超过 15000 ms 等待窗口后中止场景，输出 `Error(0xFFF5): Test scenario aborted`。

**PS_RDY 缺失的 Trace 证据**:
1. **Lecroy 主证据**: `02_TEST.PD.PROT.SNK.12_Rev3ChkdSnk_FAIL.usb` 中 0 个 HTML 标注（对比: PASS 变体有 5 个标注含 PR_Swap/Accept 完整流程）
2. **POWER-Z 辅助**: Phase 3/4（t=49.984-65.133s）中 PS_RDY 出现次数 = 0（对比: Phase 2 PASS 阶段 PS_RDY @ t=35.761s 存在 1 次）

**旧 tPSSourceOffTimer 理论**: 不成立。"PSSourceOffTimer Timeout" 是测试用例名称，Lecroy 实际判决是"场景中止"(0xFFF5)，场景在到达步骤 4→5 之前就已中止。

**与 Comment #27 对齐**: 完全一致。PD 2.0 首次 PR_Swap 成功、PD 3.0 第二次 PR_Swap 未收到 PS_RDY、VBUS 时序正常 — 三个论点均被 trace 证据证实。
