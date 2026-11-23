# TD.4.10.6 — Sink Alternate Mode Test

> **Case ID**: TD.4.10.6
> **来源**: USB Type-C Functional Test Specification 2023-02-23, Section 4.36
> **生成时间**: 2026-09-23
> **知识库**: Case SPCSS01702428 自学习生成

---

## 测试目的

验证作为 Sink 的 PUT (Product Under Test) 支持 Alternate Modes。测试执行 Sink-initiated (UFP-initiated) 和 Source-initiated (DFP-initiated) Alternate Mode discovery 流程：Discover SVIDs → Enter Mode → DP Status/Configure via Structured VDMs。

## 测试角色

- DUT: Sink (UFP), 需支持 Alternate Mode
- Tester: Source (DFP) + CVS (Compliance Verification System)

## 前置条件 (Applicability)

| 条件 | 要求 | SANTIAGOA_0921 实际值 |
|------|------|----------------------|
| `USB_PD_Support` | YES | ✅ YES |
| `Type_C_State_Machine` | ≠ SRC | ✅ DRP |
| `Type_C_Is_Alt_Mode_Controller` | YES | ❌ **NO** |

> ⚠️ **Applicability Conflict**: SANTIAGOA VIF declares `Type_C_Is_Alt_Mode_Controller=NO`, meaning the DUT is NOT an Alt Mode controller. Per the spec, TD.4.10.6 should NOT be applicable. However, the Lecroy v8.1.3 applicability check only validates `USB_PD_Support=YES` and `Type_C_State_Machine != SRC` before proceeding to the procedure, deferring the Alt Mode controller check to the VIF validation within the procedure itself.

## 测试步骤

### Phase A: Bring-Up (Steps 1-3)

| Step | 操作 | 说明 |
|------|------|------|
| 1 | Startup method for Sink tests | CVS follows Sink startup: connect CC lines, apply VBUS/Rp |
| 2 | PD Contract establishment | CVS (Source) and DUT negotiate PD Explicit Contract |
| 3 | Cable Detection + Cable Orientation | TC_CableDetection → TC_CableOrientation (Preliminary) |

### Phase B: VIF Validation (关键步骤 — 本次失败点)

| Step | 操作 | VIF 字段要求 | SANTIAGOA 实际值 |
|------|------|-------------|-----------------|
| 4 | `Type_C_Is_Alt_Mode_Adapter` 检查 | YES | ❌ **NO** |
| 5 | `Modal_Operation_Supported_SOP` 检查 | YES | ❌ **NO** |
| 6 | `Attempts_Discov_SOP` 检查 | YES (to determine Sink-initiated direction) | ✅ YES |

### Phase C: Alt Mode Discovery (Steps 7-27 — 未执行)

| Step | 操作 | 说明 |
|------|------|------|
| 7 | Send Discover SVIDs | Tester sends to DUT |
| 8 | Verify Discover SVIDs ACK | DUT must respond with GoodCRC |
| 9-10 | Wait for SVIDs / Verify VDM response | DUT returns Discover SVIDs (Structured VDM) |
| 11 | Send Discover Modes (per SVID) | Tester queries supported modes |
| 12-13 | Verify Discover Modes ACK + response | DUT must respond |
| 14 | Send Enter Mode | Tester enters the first supported mode |
| 15 | Verify Enter Mode ACK | DUT must respond with GoodCRC |
| 16-19 | DP Status + DP Configure | For DisplayPort Alt Mode |
| 20-22 | Electrical constraints check | Signal quality assessment |
| 23-24 | Exit Mode | Tester exits the mode |
| 25-26 | Disconnect | PD Hard Reset and disconnect |
| 27 | Re-check Startup | Repeat startup + PD contract |

## 判定标准

| Check ID | 描述 |
|----------|------|
| `Type_C_Is_Alt_Mode_Controller` | DUT declares as Alt Mode Controller in VIF (applicability) — **FAIL** |
| `Type_C_Is_Alt_Mode_Adapter` | DUT declares as Alt Mode Adapter in VIF (Step 4) — **FAIL** |
| `Modal_Operation_Supported_SOP` | DUT supports Modal Operations on SOP (Step 5) — **FAIL** |
| `SVID_Fixed_SOP` | DUT declares at least 1 valid SVID (Step 6) — **FAIL (0xFF)** |
| Discover SVIDs ACK | DUT sends GoodCRC (Step 8) — NOT REACHED |
| Discover SVIDs response | DUT returns SVIDs via Structured VDM (Step 10) — NOT REACHED |
| Enter Mode ACK | DUT accepts Enter Mode (Step 15) — NOT REACHED |
| Exit Mode ACK | DUT accepts Exit Mode (Step 24) — NOT REACHED |

## 关键 VIF 字段

| VIF 字段 | 要求 | SANTIAGOA 实际值 | 影响 |
|----------|------|-----------------|------|
| `Modal_Operation_Supported_SOP` | YES | **NO** | IsReadyToRun() 判定无法执行 Modal Operations |
| `SVID_Fixed_SOP` | 有效 SVID (如 0xFF01=DP) | **0xFF** (未声明) | IsReadyToRun() 无法确定测试哪个 Alt Mode |
| `Num_SVIDs_Min_SOP` | ≥1 | **0xFF** (未声明) | 同上 |
| `Num_SVIDs_Max_SOP` | ≥1 | **0xFF** (未声明) | 同上 |
| `Modal_Operation_Supported` | YES | **0xFF** (未声明) | 通用 Modal Operation 支持标记 |
| `Type_C_Is_Alt_Mode_Adapter` | YES | **NO** | Step 4 检查失败 |

## IsReadyToRun() 失败逻辑

Lecroy v8.1.3 `IsReadyToRun()` 在 Step 4-6 VIF 验证阶段评估以下条件：

1. `Type_C_Is_Alt_Mode_Adapter` → NO → **第一个失败**
2. `Modal_Operation_Supported_SOP` → NO → **第二个失败**
3. `SVID_Fixed_SOP` → 0xFF (未声明) → **无法确定测试 SVID**

当上述任一条件不满足时，`IsReadyToRun()` 返回 0，测试中止，显示：
```
"Unable to detect the necessary parameters for testing."
```

## 常见失败模式

| 模式 | 现象 | 根因方向 |
|------|------|---------|
| **VIF 未声明 Alt Mode 支持** | IsReadyToRun=0, SVID_Fixed_SOP=0xFF | DUT 不支持 Alt Mode (USB 2.0 only device)，VIF 正确反映了硬件能力 |
| **Modal_Operation_Supported=NO** | IsReadyToRun=0 | VIF 声明不支持 Modal Operations — DUT 不支持 VDM Enter/Exit Mode |
| **Lecroy 固件兼容性变化** | v7.9.2 通过，v8.1.3 失败 | v8.1.3 可能加强了 VIF 前置检查逻辑 → 参见 Case SPCSS01702428 |
| DUT PD 栈不响应 Discover SVIDs | Steps 7-10 超时 | PD 固件缺少 Alt Mode 支持代码 |
| 线缆方向错误 | "wrong orientation" error | 线缆在 Exerciser 侧方向不匹配 |

## 已知 Bug 参考

| Bug ID | 平台 | 现象 | 根因 |
|--------|------|------|------|
| SPCSS01702428 | UMS9230E / LONGCHEER_BU2 | Lecroy v8.1.3 IsReadyToRun=0, VIF Modal_Operation_Supported_SOP=NO | 分析中 — 本 Case |

---

## 来源

- 官方规范: `USB Type C Functional Test Specification 2023 02 23(1).pdf`, Section 4.36 (TD.4.10.6), pp.134-140
  - 提取来源: Tool result `bk68f83b8.txt`, Lines 895-1015, 240-243, 374-376
- 仪表报告: `USB_ComplianceTestLog.html` (TD.4.10.6), Lines 429-497 — VIF extraction + IsReadyToRun=0
- VIF 字段: `SANTIAGOA_0921.xml` (TD.4.10.6) — 完整 VIF dump
- Bug 案例: SPCSS01702428 (Bug 3565036)

*知识库文件 | 自学习生成 2026-09-23 | Case: SPCSS01702428*