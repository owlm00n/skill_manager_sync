# TEST.PD.PS.SRC.05: Source Hard Reset Test

## 测试目的
作为 Sink-Only，Tester 验证 Source UUT 在收到 Hard Reset 信号后正确响应，VBUS 在 Hard Reset 信号最后一位之后的 tPSHardReset min (25ms) 内保持在当前有效电压范围内，并按规范时序恢复到 vSafe5V。

## 测试配置
- 角色: Source (DUT)
- Tester: Sink-Only
- 模式: PD2 和 PD3

## 测试条件 (Test Conditions)

| Condition Code | 适用 UUT 类型 |
|---------------|--------------|
| Rev2Src | Provider Only, Provider/Consumer, Consumer/Provider, DRP |
| Rev3ChkdSrc | Provider Only, Provider/Consumer, Consumer/Provider, DRP |

## 测试步骤

### Part 1: 从 5V 隐式合约执行 Hard Reset

| Step | Tester 操作 | DUT 预期响应 | Timer/限值 | Check ID |
|------|------------|-------------|-----------|----------|
| 1 | 执行 Bring-up (COMMON.PROC.BU.1 或 COMMON.PROC.BU.7) | UUT 建立显式合约 (5V) | — | — |
| 2 | 发送 Hard Reset 信号 | — | — | — |
| 3a | 检查 VBUS | VBUS 在 Hard Reset 信号最后一位之后 tPSHardReset min (25ms) 内保持在当前有效电压范围内 | tPSHardReset min = 25ms | TEST.PD.PS.SRC.5#1 |
| 3b | 检查 VBUS | VBUS 在 tPSHardReset max 之后的 tSafe0V max 内达到 vSafe0V max | tSafe0V max = 25ms | TEST.PD.PS.SRC.5#2 |
| 3c | 检查 VBUS | VBUS 在达到 vSafe0V 后，延迟 tSrcRecover min~max 后上升到 vSafe0V max 以上 | tSrcRecover min=0.66ms, max=1ms | TEST.PD.PS.SRC.5#3 |
| 3d | 检查 VBUS | VBUS 在上升到 vSafe0V max 以上后 tSrcTurnOn max 内达到 vSafe5V | tSrcTurnOn max = 275ms | TEST.PD.PS.SRC.5#4 |
| 3e | 检查消息 | UUT 在 VBUS 达到 vSafe5V min 后 tFirstSourceCap max 内开始发送 Source_Capabilities | tFirstSourceCap max = 206ms | TEST.PD.PS.SRC.5#5 |
| 4 | 断开连接，等待至少 1s | — | — | — |
| 5 | 如果 UUT 没有 >5V 的 Fixed PDO，测试在此结束 | — | — | — |

### Part 2: 从最高 Fixed PDO 合约执行 Hard Reset (仅当 UUT 有 >5V Fixed PDO 时)

| Step | Tester 操作 | DUT 预期响应 | Timer/限值 | Check ID |
|------|------------|-------------|-----------|----------|
| 6 | 执行 Bring-up，Request 最高 Fixed PDO，建立合约 (不拉电流) | UUT 建立最高电压合约 | — | TEST.PD.PS.SRC.5#6 |
| 7 | 发送 Hard Reset 信号 | — | — | — |
| 8a | 检查 VBUS | VBUS 在 Hard Reset 信号最后一位之后 tPSHardReset min (25ms) 内保持在当前有效电压范围内 | tPSHardReset min = 25ms | TEST.PD.PS.SRC.5#7 |
| 8b | 检查 VBUS | VBUS 在 tPSHardReset max 之后的 tSafe5V max 内达到 vSafe5V max | tSafe5V max = 275ms | TEST.PD.PS.SRC.5#8 |
| 8c | 检查 VBUS | VBUS 在 tPSHardReset max 之后的 tSafe0V max 内达到 vSafe0V max | tSafe0V max = 25ms | TEST.PD.PS.SRC.5#9 |
| 8d | 检查 VBUS | VBUS 在达到 vSafe0V 后，延迟 tSrcRecover min~max 后上升到 vSafe0V max 以上 | tSrcRecover min=0.66ms, max=1ms | TEST.PD.PS.SRC.5#10 |
| 8e | 检查 VBUS | VBUS 在上升到 vSafe0V max 以上后 tSrcTurnOn max 内达到 vSafe5V | tSrcTurnOn max = 275ms | TEST.PD.PS.SRC.5#11 |
| 8f | 检查消息 | UUT 在 VBUS 达到 vSafe5V min 后 tFirstSourceCap max 内开始发送 Source_Capabilities | tFirstSourceCap max = 206ms | TEST.PD.PS.SRC.5#12 |
| 9 | 断开连接 | — | — | — |

## 判定标准

Part 1 (5V 合约) — 唯一检查点:
- **[TEST.PD.PS.SRC.5#1]**: VBUS stays within present valid voltage range for tPSHardReset min (25ms) after last bit of Hard Reset Signal.
- **[TEST.PD.PS.SRC.5#2]**: VBUS reaches vSafe0V max within tSafe0v max of tPSHardReset max.
- **[TEST.PD.PS.SRC.5#3]**: VBUS rises above vSafe0V max after a delay of between tSrcRecover min and tSrcRecover max after reaching vSafe0V.
- **[TEST.PD.PS.SRC.5#4]**: VBUS reaches vSafe5V within tSrcTurnOn max after rising above vSafe0v max.
- **[TEST.PD.PS.SRC.5#5]**: UUT starts sending a Source Capabilities message within tFirstSourceCap max of VBUS reaching vSafe5v min.

Part 2 (最高电压合约) — 仅当 UUT 有 >5V Fixed PDO 时:
- **[TEST.PD.PS.SRC.5#6]** 至 **[TEST.PD.PS.SRC.5#12]**: 同 Part 1 的检查逻辑，但在最高 Fixed PDO 电压下执行。

## 关键参数

| 参数 | 值 | 来源 |
|------|-----|------|
| tPSHardReset min | 25ms | USB PD R3.1 Spec |
| tPSHardReset max | 35ms | USB PD R3.1 Spec |
| tSafe0V max | 25ms | USB PD R3.1 Spec |
| tSrcRecover min | 0.66ms | USB PD R3.1 Spec |
| tSrcRecover max | 1ms | USB PD R3.1 Spec |
| tSrcTurnOn max | 275ms | USB PD R3.1 Spec |
| tFirstSourceCap max | 206ms | USB PD R3.1 Spec |
| vSrcValid (5V PDO) | 4.75V ~ 5.5V | USB PD R3.1 Spec, +/-5% |

## 常见失败模式

- **TEST.PD.PS.SRC.5#1 Fail — VBUS 在 Hard Reset 后 25ms 内跌出有效电压范围**: 最典型的失败模式。
  → 通常原因: UUT (Source) 在收到 Hard Reset 信号后过快地放电 VBUS，导致在 tPSHardReset min 要求的 25ms 窗口内 VBUS 已经低于 vSrcValid min (4.75V for 5V PDO)。
  → 常见于电池供电设备，VBUS 输出电容不足或 charger IC 在 Hard Reset 时主动放电 VBUS。
  → 调试方法: 用 Lecroy 分析 .usb trace 文件提取 Hard Reset 事件前后的 VBUS 电压波形，测量 VBUS 从 Hard Reset 最后一位开始到跌出 vSrcValid 范围的时间。

- **TEST.PD.PS.SRC.5#1 Fail — 仅第1次迭代失败，后续迭代通过**: 
  → 通常原因: 首次 Hard Reset 时 VBUS 电容初始电荷状态不同（充电未稳定），或者 charger IC 的上电初始化路径中有延迟导致 VBUS 在第一个 Hard Reset 时响应不一致。
  → 调试方法: 对比第1次和第2次迭代的 VBUS 波形，观察初始 VBUS 电压是否不同；检查 charger IC 在第一次建立合约后的寄存器状态。

- **TEST.PD.PS.SRC.5#3 Fail — VBUS 恢复时序异常 (tSrcRecover)**:
  → 通常原因: charger IC 在 vSafe0V 阶段的放电/恢复逻辑不符合 tSrcRecover min~max 窗口要求。

- **Steps 6-12 N/A**: UUT 没有 >5V 的 Fixed PDO（如仅支持 5V/1.5A 的手机充电器），Part 2 不适用。

## 参考 Bug 案例
- **Bug SPCSS01702402**: TEST.PD.PS.SRC.5#1 Fail — VBUS does not stay within valid voltage range for tPSHardReset min (25ms) after last bit of Hard Reset signal. Error 0x0000008F. UMS9230E + LongCheer SANTIAGOA + upm6910 charger IC. FW: M310e7.92. 仅第1次迭代失败（Rev2Src 和 Rev3ChkdSrc 均如此），41/41 Common Checks 全部通过。1个 Source PDO (5V/1.5A)，电池供电，VIF 声明 "No Power Interruption Possible"。

---

## 来源
- 官方规范: `USB PD3 CTS Q4 2024 OR.pdf`, Section 6.1.1 — TEST.PD.PS.SRC.5 Source Hard Reset Test, Page 212-213
- Timer 规范: `USB PD R3.1 Specification` — tPSHardReset, tSafe0V, tSrcRecover, tSrcTurnOn, tFirstSourceCap, vSrcValid values
- 实测数据: Bug SPCSS01702402, Lecroy Compliance Test Log (`USB_ComplianceTestLog.html`, lines 350-994), Lecroy Result HTML