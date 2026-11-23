# TEST.PD.EPR.SRC3.01 — EPR Entry Process, UUT as VCONN Source

**Case ID**: TEST.PD.EPR.SRC3.01
**规范来源**: USB PD 3.1 CTS Q4 2024 OR, Section 7.1.1, Pages 225-228
**生成时间**: 2026-09-22
**置信度**: 高 (直接从规范 PDF 提取)

---

## 测试目的

Tester 作为 Sink 验证 UUT 作为 VCONN Source 时 EPR 协商（entry → contract → exit）的完整流程。

## 测试条件

- **测试角色**: Provider Only, Provider/Consumer, Consumer/Provider, DRP
- **Rev3ChkdSrc**: ✓
- **Rev3UnchkdSrc**: ✓
- **Tester 行为**: Sink Only，EPR_Mode_Capable bit = 1

---

## 测试步骤

| 步骤 | Check ID | 描述 | 判定标准 | 失败条件 |
|------|----------|------|---------|---------|
| 1 | — | **Bring-up** COMMON.PROC.BU.1 (Provider Only/DRP/P/C) 或 BU.7 (C/P) | SPR 契约建立 | BU.1 失败则测试停止 |
| 2 | **#13** | Tester 发送 EPR_Get_Source_Cap | Provider Only + EPR=No → Not_Supported; DRP/C/P/P/C + EPR=No+Snk=No → Not_Supported; 非Provider Only + EPR=No+Snk=Yes → Reject; EPR=Yes → EPR_Source_Capabilities | 响应不匹配 → FAIL |
| 3 | — | Tester 发送 EPR_Mode(Enter), Action=0x01, Data=140W | — | — |
| 4 | **#2** | 检查 UUT 对 EPR_Mode(Enter) 响应 | **EPR=Yes**: EPR_Mode(Action=0x02 Enter_Acknowledged, Data=0); **EPR=No**: Not_Supported, **测试停止** | EPR=Yes 且非 Enter_Acknowledged → FAIL; EPR=No 且非 Not_Supported → FAIL |
| 5 | **#5** | **仅在 EPR=Yes 时执行**: 检查 EPR_Mode(Enter_Succeeded, Action=0x03) 在 tEnterEPR 内 | ≤ tEnterEPR (从 EPR_Mode(Enter) 的 GoodCRC 起) | 超时 → FAIL, 测试停止 |
| 6a | **#3** | **仅在 Captive_Cable=No 且 EPR=Yes 时**: 检查 UUT 未发送 VCONN_Swap | 未发送 VCONN_Swap | 发送了 VCONN_Swap → FAIL |
| 6b | **#4** | **仅在 Captive_Cable=No 且 EPR=Yes 时**: 检查 UUT 未发送 SOP' Discover Identity | 未发送 SOP' Discover Identity | 发送了 → FAIL |
| 7 | **#6** | **仅在 EPR=Yes 时**: 检查 EPR_Source_Capabilities 在 tFirstSourceCap 内 | ≤ tFirstSourceCap (从 EPR_Mode(Enter_Succeeded) 的 GoodCRC 起) | 超时 → FAIL |
| 8 | **#10** | **仅在 EPR=Yes 时**: 建立 EPR 契约 (COMMON.PROC.PD3.2) | EPR_Request → Accept → PS_RDY | 契约失败 → FAIL |
| 9 | **#7** | **仅在 EPR=Yes 时**: Tester 发送 EPR_Request (Object Position=1, 100mA) → 检查 Accept/Reject/Wait | Accept/Reject/Wait 其一 | 无响应 → FAIL |
| 10 | **#8** | **仅在 EPR=Yes 时**: 检查 PS_RDY 在 EPR 模式 tSrcTransReq 内 | ≤ EPR tSrcTransReq | 超时 → FAIL |
| 11 | — | Tester 等待 100ms → 发送 EPR_Mode(Exit, Action=0x05) | — | — |
| 12 | **#9** | 检查 SPR Source_Capabilities 在 tFirstSourceCap 内 (EPR 退出后) | ≤ tFirstSourceCap (从 EPR_Mode(Exit) 的 GoodCRC 起) | 超时 → FAIL |
| 13 | **#11** | 建立 SPR 契约 (COMMON.PROC.PD.11) | Source_Capabilities → Request → Accept → PS_RDY | 契约失败 → FAIL |
| — | **#12** | Wait Message 重试机制 | 最多 10 次重试 | 超 10 次 → FAIL |

---

## 关键 CTS 规范条款: EPR=No 时的条件表

**步骤 4b (Check #2) 明确指示**:

> "If the VIF field EPR_Supported_As_Src is No, The Tester checks that the UUT responds with Not_Supported Message and **the test stops here**."

当 VIF EPR_Supported_As_Src=No 时:
- DUT 在步骤 4 正确回复 Not_Supported → Check #2 PASS
- **测试应立即停止**，步骤 5-13 (#3/#4/#5/#6/#7/#8/#9/#10/#11) 均不应执行
- 这些未执行步骤应标记为 N/A，而非 FAIL

## 关键时序参数

| 参数 | 符号 | 说明 |
|------|------|------|
| EPR 进入超时 | tEnterEPR | EPR_Mode(Enter) → Enter_Succeeded 最大延迟 |
| 首次 SourceCap | tFirstSourceCap | 连接/EPR 进入后发送首条 SourceCap 的最大延迟 |
| EPR 模式 tSrcTransReq | tSrcTransReq (EPR) | EPR 模式下 Accept → PS_RDY 最大延迟 |

---

## 失败模式

- **工具缺陷 (LeCroy 8.1.3 / Q3 2024 CTS)**: EPR=No 场景下，#6/#7/#8/#10/#11 误报 FAIL — 这些是后 EPR 进入步骤，应在步骤 4b 后标记 N/A。部分检查项 (#3/#4/#5/#9) 正确标记 N/A，说明条件表逻辑实现不完整。
  - **Q4 2024 OR Revision History** 明确记录了: "Q3, 2024: TEST.PD.EPR.SRC3.1 condition table errata fix" — 此 errata fix 正是针对此问题的修复，但 LeCroy 8.1.3 实现的 CTS 版本为 Q2 2025 OR (full) + Q3 2025 RC1 (partial)，**可能未完整合入此 Q3 2024 errata fix**。

---

## 来源

- 官方规范: `USB_PD3_CTS_Q4_2024_OR.pdf`, Section 7.1.1 TEST.PD.EPR.SRC3.1, Pages 225-228
- Errata 记录: Q3 2024 Revision History — "TEST.PD.EPR.SRC3.1 condition table errata fix"
- 实测数据: SPCSS01702390, LeCroy 8.13 Build 1234, Voyager M310e SN:27503
- 客户 VIF: `SANTIAGOA_0921.xml` — EPR_Supported_As_Src=No, EPR_Supported_As_Snk=No