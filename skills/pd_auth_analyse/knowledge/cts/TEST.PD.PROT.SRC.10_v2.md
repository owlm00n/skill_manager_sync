# TEST.PD.PROT.SRC.10: PR_Swap – PSSourceOnTimer Timeout

## 测试目的
验证 UUT 作为新 Source 时，PSSourceOnTimer 超时机制是否正确实现。Tester 在 PR_Swap 后故意不发送 PS_RDY Message，强制 UUT 的 PSSourceOnTimer 超时，检查 UUT 是否在规范窗口内执行 USB Type-C Error Recovery。

## 测试配置
- 角色: Source (DUT)，PR_Swap 后变为新 Sink 再变回新 Source
- Tester: Dual-Role Power，初始为 Sink，PR_Swap 后变为新 Source（但不发 PS_RDY）
- Tester 特殊行为: 发送 Sink_Capabilities 时 B27 (Unconstrained Power) = 1b (COMMON.PROC.PD.3)

## 测试条件 (Test Conditions)

| Condition Code | 适用 UUT 类型 |
|---------------|--------------|
| Rev2Src | Provider Only, C/P, P/C, DRP |
| Rev3ChkdSrc | Provider Only, C/P, P/C, DRP |

> 注: Consumer Only 不适用此测试。

## 测试步骤

| Step | Tester 操作 | DUT 预期响应 | Timer/限值 |
|------|------------|-------------|-----------|
| 1a | VIF PD_Port_Type = Consumer/Provider 时，执行 COMMON.PROC.BU.7 bring-up | 建立显式合约 | — |
| 1b | VIF PD_Port_Type 为其他值时，执行 COMMON.PROC.BU.1 bring-up | 建立显式合约 | — |
| 2 | 发送 PR_Swap Message | UUT 回复 Accept/Wait/Reject/Not_Supported | — |
| 3 | 检查 UUT 响应 [TEST.PD.PROT.SRC.10#1] | 见下方检查点说明 | tPRSwapWait + tCtsWait (Wait 重试间隔) |
| 4 | 发送最后 GoodCRC 后降低电流 ≤ iSwapStandby | — | tSrcTransition min |
| 5 | 检查 UUT PS_RDY [TEST.PD.PROT.SRC.10#2] | UUT 驱动 VBUS→vSafe0V 后发送 PS_RDY | tSrcTransition max + tSrcSwapStdby max |
| 6 | 施加 vSafe5V 到 VBUS，**不发送 PS_RDY** | UUT 启动 PSSourceOnTimer | — |
| 7 | 检查 UUT Error Recovery [TEST.PD.PROT.SRC.10#3] | UUT 执行 USB Type-C Error Recovery | tPSSourceOn min ≤ t ≤ tPSSourceOn max |

### Step 3 检查点详细说明 [TEST.PD.PROT.SRC.10#1]
- **a.** UUT 回复 Wait → Tester 每隔 tPRSwapWait + tCtsWait 重发 PR_Swap，最多 10 次。10 次后仍 Wait → FAIL，测试结束
- **b.** UUT 回复 Reject 或 Not_Supported → 检查 VIF PD_Port_Type = "Provider only" 或 Accepts_PR_Swap_As_Src = No。测试结束
- **c.** UUT 回复 Accept 但 VIF PD_Port_Type 不是 "Provider/Consumer"、"Consumer/Provider" 或 "DRP" → FAIL，测试结束

### Step 5 检查点详细说明 [TEST.PD.PROT.SRC.10#2]
- **a.** UUT 驱动 VBUS 至 vSafe0V 后未发送 PS_RDY → FAIL
- **b.** PS_RDY 未在 GoodCRC(Accept) 后 tSrcTransition max + tSrcSwapStdby max 内发出 → FAIL

### Step 7 检查点详细说明 [TEST.PD.PROT.SRC.10#3]
- **a.** Error Recovery 在 PS_RDY 对应 GoodCRC EOP 后 tPSSourceOn min 之前被检测到 → FAIL（过早）
- **b.** Error Recovery 在 PS_RDY 对应 GoodCRC EOP 后 tPSSourceOn max 内未被检测到 → FAIL（过晚/缺失）

## 判定标准
- [ ] UUT 对 PR_Swap 的响应与 VIF 声明一致 (#1)
- [ ] UUT 作为旧 Source 在 tSrcTransition max + tSrcSwapStdby max 内完成 VBUS 放电并发送 PS_RDY (#2)
- [ ] UUT 作为新 Source 在 tPSSourceOn min ~ tPSSourceOn max 窗口内触发 Error Recovery (#3)

## 检查点 (Check ID)
- **[TEST.PD.PROT.SRC.10#1]**: UUT 对 PR_Swap 响应合规性（Wait 重试/Reject 合理性/Accept 与 VIF 一致性）
- **[TEST.PD.PROT.SRC.10#2]**: UUT 作为旧 Source 的 PS_RDY 发送时序
- **[TEST.PD.PROT.SRC.10#3]**: UUT 作为新 Source 的 PSSourceOnTimer 超时 → Error Recovery 时序窗口

## 关联 Timer 数值

> 来源: `knowledge/specs/pd_protocol_timers.md` + USB PD R3.1 Spec Table 6-34，辅助参考，非 CTS 原文。

| Timer | Min | Max | 含义 |
|-------|-----|-----|------|
| tSrcTransition | 100ms | 275ms | Source 端 VBUS 转换时间 |
| tSrcSwapStdby | — | 100ms | PR_Swap 后旧 Source 进入 standby |
| tPSSourceOn | — | 400ms (SPR) / 450ms (EPR) | 新 Source 使 VBUS 达 vSafe5V 的上限 |
| tPRSwapWait | — | — | PR_Swap Wait 后重试间隔基数 |
| tFirstSourceCap | — | 100ms | 首次 SourceCap 发送上限 (BU.1) |
| tSrcTransReq | — | 275ms | Accept 后到 PS_RDY 的上限 (BU.1) |

## Bring-up 引用流程

### COMMON.PROC.BU.1 Bring-up Source UUT
1. 测试从断开状态开始
2. VIF Captive_Cable = YES → 施加 Rd；否则施加 Rd 和 Ra
3. [COMMON.PROC.BU.1#1] tFirstSourceCap max 内未收到 Source_Capabilities → FAIL
4. Tester 回复 GoodCRC
5. Tester 发送 Request (5V/100mA, Object Position=001b)
6. [COMMON.PROC.BU.1#2] UUT 重发 SourceCap 或未回复 Accept/Wait → FAIL
7. UUT 回复 Wait → 每隔 tSinkRequest 重发 Request，最多 10 次 [COMMON.PROC.BU.1#4]
8. [COMMON.PROC.BU.1#3] tSrcTransReq 内未收到 PS_RDY → FAIL
9. 显式合约建立
10. Tester 等待 tCtsAfterLastPoint 后响应 UUT 消息

### COMMON.PROC.BU.7 Bring-up Consumer-Provider as Source UUT
1. 测试从断开状态开始
2. Tester 施加 Rp
3. 检测到 UUT 连接后，施加 VCONN (如检测到 Ra) 和 vSafe5V
4. 等待 50ms
5. Tester 发送 Source_Capabilities (单 PDO: 5V/100mA, B29=1b, B27=1b)
6. 未收到 GoodCRC → 延迟 tTypeCSendSourceCap (min~max) 后重发，至少 50 次
7. [COMMON.PROC.BU.7#1] UUT 未回复 Request → FAIL
8. Tester 回复 Accept
9. VBUS 稳定后，tSrcTransReq max 内发送 PS_RDY
10. 显式合约建立

## 常见失败模式

- **CHECK #3 FAIL — Error Recovery 早于 tPSSourceOn min (Error 0x00000294)**:
  UUT 在 Tester 施加 vSafe5V 后过早触发 Error Recovery
  → 通常原因: UUT 的 PSSourceOnTimer 计时起点错误（如从 Accept 而非从 UUT 自身 PS_RDY 的 GoodCRC 开始计时），或 Timer 值配置小于规范最小值
  → 调试方法: 在 sprd_tcpm 状态机中打印 PE_SNK_STARTUP / PE_SRC_STARTUP 进入时间戳，对比 PS_RDY GoodCRC EOP 时间，确认计时起点

- **CHECK #3 FAIL — Error Recovery 未在 tPSSourceOn max 内触发**:
  UUT 未正确实现 PSSourceOnTimer 超时处理
  → 通常原因: 状态机未启动 PSSourceOnTimer、Timer 超时回调未触发 Error Recovery、或 VBUS 检测逻辑误判 vSafe5V 已就绪而跳过等待
  → 调试方法: 检查 tcpm_set_state 中 PE_SRC_STARTUP 的 timeout 参数是否为 tPSSourceOn max，确认 hrtimer 是否正确启动

- **CHECK #2 FAIL — PS_RDY 超时**:
  UUT 作为旧 Source 未及时完成 VBUS 放电
  → 通常原因: VBUS 放电电路响应慢、charger IC 关断延迟、驱动中 vSafe0V 检测阈值不合理
  → 调试方法: 抓取 VBUS 波形确认放电斜率，检查 sprd_tcpm_set_vbus(0) 调用到实际 VBUS 降至 vSafe0V 的时间差

## 参考 Bug 案例
- **Bug 2912824**: [UMS9230E][SPROCOMM][blade-A56-u] TEST.PD.PROT.SRC.10 PR_Swap - PSSourceOnTimer Timeout — SRC.10#2 PASS, SRC.10#3 FAIL (Error 0x00000294: Error Recovery detected before tPSSourceOn min)。合入修复后 PASS，但引入 TEST.PD.FRS.SNK3.1 新 fail。Resolution: FIXED
- **Bug 2871706**: [UMS9230E][HUAQIN_BD2][SL7509][C3Z] TEST.PD.PROT.SRC.10 PR_Swap - PSSourceOnTimer Timeout。Resolution: NON-REPRODUCE

---

## 来源
- 官方规范: `USB PD3 CTS Q4 2024 OR.pdf`, Section 5 (Protocol Specific Tests), Page 144-145
- 实测数据: `ref/pd_bugs_detail.json`, Bug 2912824, Bug 2871706
- Timer 规范: `knowledge/specs/pd_protocol_timers.md` + USB PD R3.1 Spec Table 6-34
- Bring-up 流程: `USB PD3 CTS Q4 2024 OR.pdf`, Section 3.2, Page 44-48
- ECN 验证: 全部 5 份 ECN 均不涉及本测试项 (2026-07-27 验证)
