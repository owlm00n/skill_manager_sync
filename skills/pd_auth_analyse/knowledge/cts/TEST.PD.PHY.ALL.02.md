# TEST.PD.PHY.ALL.02: Transmitter Eye Diagram

## 测试目的
验证 UUT 在 BIST Carrier Mode 下发送的 CC 线数据满足 USB PD 2.0 规范的眼图模板（Eye Diagram Mask）要求。

## 测试配置
- 角色: Sink (DUT) — 本案例: Rev3ChkdSnk
- Tester: Source (Rp 4.7kΩ → 3.3V, 容性负载 ~400pF) / BIST 发起者
- 设备: Teledyne LeCroy Voyager M310e / USB Compliance Suite

## 测试条件 (Test Conditions)

| Condition Code | 适用 UUT 类型 |
|---------------|--------------|
| Rev3ChkdSrc | Provider Only |
| Rev3ChkdSnk | Consumer Only, DRP, Consumer/Provider |
| CabFlippedSrc | Cable |
| CabFlippedSnk | Cable |
| Rev3 VcMinEnd1~VcMaxEnd2 | VPD, Captive Cable, Si-Only, eMarker |

> 本案例适用: **Rev3ChkdSnk** (Consumer Only / DRP / Consumer/Provider)

## Tester 行为

| UUT 角色 | Tester 端接 | 容性负载 |
|----------|-----------|---------|
| **Sink** (本案例) | Rp 4.7kΩ → 3.3V | ~400pF |
| Source | Rd 5.1kΩ → GND | ~400pF |

## 测试步骤

| Step | Tester 操作 | DUT 预期响应 | 判定/限值 |
|------|------------|-------------|-----------|
| **1** | Bring-up 流程: UUT VIF `PD_Port_Type` 为 Consumer Only/DRP/Consumer+Provider → 执行 **COMMON.PROC.BU.2** (Tester as Source, UUT as Sink) | 正常完成 Bring-up | — |
| **2** | 发送 BIST Request，指定 **"BIST Carrier Mode"**。UUT 为 Sink 时，**不遵循正常 Rp Collision Avoidance**，维持 Rp 4.7kΩ → 3.3V | UUT 进入 BIST Carrier Mode，持续发送 BIST Carrier 数据 | — |
| **3** | 对 BIST 比特流的总电压摆幅创建 **≥100 bin** 的直方图 | — | bin 数 ≥ 100 |
| **4** | 查找 Y5TX (0.5625V) 到最大值之间计数最高的 bin → bin 中间电压为 **"high level"** | — | — |
| **5** | 查找 Y5TX (0.5625V) 到最小值之间计数最高的 bin → bin 中间电压为 **"low level"** | — | — |
| **6** | **mid-level** = (high level + low level) / 2 | — | — |
| **7** | 使用 mid-level 确定 **1 UI**: 定位 "0" bit 上升沿 → 数 32 bits → 定位下一个 "0" bit 上升沿 → 1 UI = 时间差 / 32 | — | 1 UI = 参考比特长度 |
| **8** | 以 mid-level 作为眼图的初始 **crossing level** | — | — |
| **9** | 生成 Eye Diagram，使用 **2640 bits** 叠加到 TX-Mask 上（参考 USB PD 2.0 Spec Figure 5-22, 5-23）。每个 bit 的首尾 crossing 分别距 0.5 UI | 信号不违反 TX-Mask | **FAIL if signals violate TX-Mask** |
| **10** | 若 Step 9 失败，依次调整 crossing level（±10/20/30/40/50mV），**每次调整后重跑 Step 9**:<br>a. mid-level + 10mV → Step 9<br>b. mid-level − 10mV → Step 9<br>c. mid-level + 20mV → Step 9<br>d. mid-level − 20mV → Step 9<br>e. mid-level + 30mV → Step 9<br>f. mid-level − 30mV → Step 9<br>g. mid-level + 40mV → Step 9<br>h. mid-level − 40mV → Step 9<br>i. mid-level + 50mV → Step 9<br>j. mid-level − 50mV → Step 9 | — | 任一次 crossing level 的 Step 9 通过即停止，不再继续后续 crossing level |
| **11** | — | — | **[TEST.PD.PHY.ALL.2 #1]**: FAIL if Eye Diagram check **fails in Step 9 AND all 11 crossing levels in Step 10** (mid-level, ±10/20/30/40/50mV) |
| **12** | — | — | **[TEST.PD.PHY.ALL.2 #2]**: FAIL if rise/fall time check fails:<br>• 10% Level = low + (high−low)×10%<br>• 90% Level = low + (high−low)×90%<br>• 对 2640 bits 中每个上升沿测 10%→90% trise，取平均值 ≥ tRise<br>• 对 2640 bits 中每个下降沿测 90%→10% tfall，取平均值 ≥ tFall |
| **13** | 若 UUT 为非 captive cable 端口，翻转测试插头在 UUT 端，**在另一 CC 连接上重复测试** | — | — |

## 判定标准

- [ ] **[TEST.PD.PHY.ALL.2 #1]**: Eye Diagram mask 在初始 crossing level 或任一补偿 crossing level 下通过 — **本案例 FAIL**
- [ ] **[TEST.PD.PHY.ALL.2 #2]**: Rise/fall time 满足 tRise / tFall 限值 — **本案例 PASS**

## 唯一检查点 (Check ID)

| Check ID | 描述 | 判定逻辑 |
|----------|------|---------|
| **TEST.PD.PHY.ALL.2 #1** | Eye Diagram Mask Check | Step 9 在 mid-level **及** Step 10 所有 11 个 crossing level 下均违反 TX-Mask → FAIL |
| **TEST.PD.PHY.ALL.2 #2** | Rise/Fall Time Check | 平均 trise < tRise 或平均 tfall < tFall → FAIL |

## 关键参数

| 参数 | 值 | 来源 |
|------|-----|------|
| BIST bit 数 | 2640 bits | CTS Spec Step 9a |
| 直方图 bin 数 | ≥ 100 | CTS Spec Step 3 |
| Y5TX 电压阈值 | 0.5625V | CTS Spec Step 4/5 |
| Crossing level 范围 | mid-level ± 0~50mV, 10mV 步进 (11 个值) | CTS Spec Step 10 |
| Tester Rp (Sink UUT) | 4.7kΩ → 3.3V | CTS Spec Tester Behavior |
| Tester 容性负载 | ~400pF | CTS Spec Tester Behavior |
| Eye Mask 参考 | USB PD 2.0 Figure 5-22, 5-23 | CTS Spec Step 9 |

## 常见失败模式

### TEST.PD.PHY.ALL.2 #1: 眼图 Mask 违规

- **ibus 电流 → CC 线噪声耦合**: 当 VBUS 上有充电电流（ibus > 0）时，CC 线受电磁干扰影响，信号质量下降，导致眼图参数不达标
  → 通常原因: CC 线与 VBUS 线物理布局接近，大电流通过时产生耦合噪声；或 PCB layout 中 CC 线阻抗匹配不佳，BIST Carrier 信号质量本身处于临界状态
  → 验证方法: ibus=0 (HIZ模式) 测试 — 若眼图 PASS，确认干扰源为充电电流
  → 调试方法: 检查 CC 线 PCB 走线阻抗、参考层完整性、与 VBUS 线间距

- **CC 线驱动能力不足**: SC27XX PD Controller BIST Carrier 输出驱动强度不足以在 400pF 负载下保持信号完整性
  → 通常原因: PD Controller 的 CC 引脚驱动配置（如 slew rate、drive strength 寄存器）可能不适配特定 PCB layout

- **crossing level 全范围失败**: 11 个 crossing level 均无法通过，说明信号偏差严重，非 crossing level 微调可解决
  → 通常原因: 信号质量根本性问题（噪声耦合、阻抗不匹配），而非 crossing level 选择偏差

## 参考 Bug 案例

- **Bug 3537686 (SPCSS01699865)**: UMS9360/HUAQIN_BD2, TEST.PD.PHY.ALL.2#1 FAIL (3/3 runs), #2 PASS。ibus=0 (HIZ) → PASS，限流 500mA (实际 460+mA) → 仍 FAIL。 → 方向: 平台限流策略 + HW CC 线信号质量
- **Bug 3557090 (SPCSS01701718)**: Request CQ，客户要求增加 CC 眼图测试检测 SW 代码。 → 方向: Kai.Ke 主张使用现有平台限流策略，无需额外 SW
- 历史 5 Bug (3381744, 3284418, 3194887, 3072947, 2920617): 均 TEST.PD.PHY.ALL.2 FAIL，均通过平台现有策略解决，未添加额外 SW

---

## 来源
- 官方规范: `USB_PD3_CTS_Q4_2024_OR.pdf`, TEST.PD.PHY.ALL.2 Transmitter Eye Diagram, Page 80-82
- 实测数据: Lecroy Report `Teledyne LeCroy USB Compliance Result__Communication-Co.,-Ltd.-VP2601-0000.html`, 2026-09-08, 3/3 FAIL
- 项目经验: Bug 3537686 Comment #21-28 (Kai.Ke guiding direction); Bug 3557090 Comment #3-4
- Timer 规范: N/A (PHY 测试，不涉及协议 Timer)