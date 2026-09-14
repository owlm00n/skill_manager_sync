# Phase 2: 测试用例说明 & 失败点定位 — TEST.PD.PROT.SRC3.01

**分析时间**: 2026-08-31
**Case ID**: TEST.PD.PROT.SRC3.01
**来源**: USB_PD3_CTS_Q4_2024_OR.pdf Page 148, Bug 3523357 Comment #0

---

## 1. 测试项说明

| 属性 | 值 |
|------|-----|
| **Case ID** | TEST.PD.PROT.SRC3.01 |
| **测试名称** | SourceCapabilityTimer Timeout |
| **测试目的** | 验证 Source UUT 在未收到 GoodCRC 时，SourceCapabilityTimer 超时后重试 Source Capabilities 消息的时序是否符合 PD 规范 |
| **测试角色** | Source (UUT) vs Sink (Tester) |
| **判定标准** | 第 3→4 条 Source Capabilities 消息间隔 ≥ 100.9ms (tReceive min + tTypeCSendSourceCap min) |

## 2. 完整测试步骤序列

| 步骤 | 描述 | 判定 | 本 Case 结果 |
|:---:|------|------|:---:|
| 1 | 测试从断开状态开始 | — | ✅ PASS |
| 2 | Tester 施加 Rd，等待 VBUS present | — | ✅ PASS |
| 3 | Tester 等待 UUT 发送第一条 Source_Capabilities | ≤ tFirstSourceCap max | ✅ PASS |
| 4 | Tester 收到第一条 Source_Capabilities 后，**故意不回复 GoodCRC** | — | ✅ 正常执行 |
| 5a | 测量第 1→2 条 Source_Capabilities 间隔 | ≤ tReceive max + tRetry | ✅ 测试未报告 |
| 5b | 测量第 2→3 条 Source_Capabilities 间隔 | ≤ tReceive max + tRetry | ✅ 测试未报告 |
| **5c** | **测量第 3→4 条 Source_Capabilities 间隔** | **≥ 100.9ms 且 ≤ 201.1ms** | **❌ FAIL** |
| 5d | 测量第 4→5 条 Source_Capabilities 间隔 | ≤ tReceive max + tRetry | 未执行（5c 已失败） |

## 3. 失败步骤定位

### 3.1 失败步骤

**步骤 5c.ii** — 第 3→4 条 Source Capabilities 消息间隔 < 100.9ms

### 3.2 失败类型

**时序违规 (Timing Violation)** — 消息间隔过短

### 3.3 仪器报告原始 FAIL 判定

```
Error(0x0000021D): Source Capabilities message(4) was received before 100.9 ms 
(tReceive min (0.9 ms) + tTypeCSendSourceCap min (100 ms)) from the time the 
last bit of the Source Capabilities message(3) EOP has been received.
```

**来源**: Bug 3523357 Comment #0 (ZTE 肖荣国提交)

### 3.4 测试仪信息

| 属性 | 值 |
|------|-----|
| 型号 | LeCroy Voyager M310e |
| 序列号 | #27506 |
| 软件版本 | Compliance Suite 7.92 Build 1198 |
| VIF | UNISOC P610F01, PD Port Type 4 (Source), PD Spec Revision 3.1 |

## 4. 失败上下文

### 4.1 前序事件

1. UUT (UMS512 P610F01) 作为 Source 连接
2. Tester 模拟 Sink 并施加 Rd
3. UUT 检测到连接，开始发送 Source Capabilities
4. Tester 收到消息 1, 2, 3 后均不回复 GoodCRC
5. UUT 的 SourceCapabilityTimer 超时，触发重试

### 4.2 关键发现

**硬件重试导致消息 4 提前到达**：

- 软件层面：UUT 在 SourceCapabilityTimer 超时后（~150ms）发起第 3 次软件 TX
- 硬件层面：SC27XX PD 控制器在未收到 GoodCRC 时，自动以 ~1-2ms 间隔重传
- 测试仪视角：一次软件 TX 产生的 4 次硬件重传被计为 4 条独立消息
- 消息 3 和消息 4 来自同一次软件 TX 的不同硬件重传，间隔仅 ~1-2ms

### 4.3 时间线

```
软件 TX 周期 #1: 发送 → 硬件重传 4 次 → TX Complete (status:2)
  Tester 看到: 消息 1, 2, 3, 4 (间隔 1-2ms)
                    ↑              ↑
                    消息 3         消息 4
                    间隔 = ~1-2ms << 100.9ms → FAIL
```

### 4.4 后续事件

- 测试失败后，Tester 断开 CC 线
- UUT 进入 SRC_UNATTACHED 状态
- 测试仪重新连接，开始下一轮测试（Burst 模式）

## 5. 三组测试结果对比

| 测试组 | 配置 | 结果 | 失败步骤 |
|------|------|:---:|------|
| ORIGINAL FAIL | `SPRD_PD_T_SEND_SOURCE_CAP = 150ms` | ❌ FAIL | 5c.ii |
| 8-24 FAIL | `SPRD_PD_T_SEND_SOURCE_CAP = 150ms` | ❌ FAIL | 5c.ii |
| AFTER CODE CHANGE FAIL | `SPRD_PD_T_SEND_SOURCE_CAP = 180ms` | ❌ FAIL | 5c.ii |

**结论**: 增加软件延迟（150ms→180ms）**无效**，因为硬件重试间隔（~1-2ms）不受软件参数影响。

---

## 6. 失败根因初步判断

| 置信度 | 根因方向 |
|:---:|------|
| **95%** | SC27XX PD 控制器硬件 TX 自动重试机制（`SC27XX_PD_AUTO_RETRY = BIT(0)`） |
| 5% | 其他未排查的硬件/软件交互问题 |

**判断依据**:
1. 测试仪报告消息 3→4 间隔 < 100.9ms
2. Ke.Wang1 硬件分析（Comment #12）确认 CC 线观察到 5 次软件发送 × 4 次硬件重传 = 20 个包
3. 增加软件延迟 150→180ms 无效（硬件重试间隔不受影响）
4. `enable_tx_auto_retry` 接口已存在，一旦禁用可消除硬件重试

---

*Phase 2 完成 | 产物: `02_failure_location.md` | 下一步: Phase 3 Trace 分析*