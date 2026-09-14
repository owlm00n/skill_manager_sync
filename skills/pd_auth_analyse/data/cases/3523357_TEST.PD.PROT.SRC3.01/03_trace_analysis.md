# Phase 3: Trace 深度分析 — TEST.PD.PROT.SRC3.01

**分析时间**: 2026-08-31
**Case ID**: TEST.PD.PROT.SRC3.01
**数据来源**: Bug 3523357 Comment #12 (Ke.Wang1 硬件分析), Bug 描述, Kernel Log TX 事件

> ⚠️ **材料限制**: 无法获取 Lecroy .usb 二进制 trace 文件或 HTML 导出报告。以下分析基于 Ke.Wang1 的硬件分析（Comment #12）、Bug 描述中的错误码、以及 kernel log 中的 TX 事件时序。

---

## 1. 结论

**协议层异常**: SC27XX PD 控制器硬件在未收到 GoodCRC 时，以 ~1-2ms 间隔自动重传 Source Capabilities 消息。测试仪将同一软件 TX 周期的不同硬件重传计为独立消息，导致消息 3→4 间隔仅 ~1-2ms，违反 PD 规范要求的 ≥100.9ms。

**根因方向**: 硬件 TX 自动重试机制（`SC27XX_PD_AUTO_RETRY = BIT(0)`），置信度 95%。

---

## 2. 关键事件序列

### 2.1 软件层面（Kernel Log 视角）

每个 TX 周期只看到一次 TX 完成事件：

```
[时间点 1] handle_src_send_capabilities: curr_time1 = 89507 ms
[时间点 2] PD TX, header: 0x11a1                          ← 软件发起 TX
[时间点 3] sc27xx-typec-pd: IRQ: tx error failed           ← 硬件 IRQ 报告错误
[时间点 4] PD TX complete, status: 2                        ← TX 完成，status:2 = 错误
[时间点 5] int sts = 0x40                                   ← TX 完成中断
[时间点 6] handle_src_send_capabilities: curr_time2 = 89517 ms
[时间点 7] duration = 10 ms
[时间点 8] pending state change SRC_SEND_CAPABILITIES → SRC_SEND_CAPABILITIES @ 150 ms
```

**关键观察**:
- `int sts = 0x40`（bit 6）: TX 完成中断，每个周期出现一次
- `status: 2`: TX 完成但发生错误（未收到 GoodCRC）
- 从软件层面看，每个周期只有**一次** TX 完成事件
- 软件延迟 150ms 后重试

### 2.2 硬件层面（CC Line 视角，测试仪看到）

Ke.Wang1 (Comment #12) 的硬件分析：

```
测试仪在 CC 线上观察到:
  - 5 次软件发送（Source Capabilities 消息）
  - 每次软件发送产生 4 次硬件重传（包括首次发送）
  - 总共 20 个数据包 (5 × 4)
  - 前 14 个包丢失（UUT 处于 VBUS OFF 状态）
```

**单次软件 TX 在 CC 线上的表现**:

```
软件 TX Start
  → [Msg 1]  ─1-2ms→  [Msg 2]  ─1-2ms→  [Msg 3]  ─1-2ms→  [Msg 4]
       ↑                   ↑                   ↑                   ↑
    首次发送            硬件重试 #1         硬件重试 #2         硬件重试 #3
                                                                      │
                                                              TX Complete
                                                              (status:2)
```

### 2.3 测试仪视角（消息编号）

```
测试仪收到的消息序列（CC 线）:
  软件 TX 周期 #1: [Msg 1]─1ms─[Msg 2]─1ms─[Msg 3]─1ms─[Msg 4]
  软件 TX 周期 #2: [Msg 5]─1ms─[Msg 6]─1ms─[Msg 7]─1ms─[Msg 8]
  ...

  测试仪将消息编号为:
    消息 1, 2, 3, 4 来自 TX 周期 #1
    消息 5, 6, 7, 8 来自 TX 周期 #2
    ...

  步骤 5c 检查: 消息 3 → 消息 4 间隔 = ~1-2ms
  要求: ≥ 100.9ms
  结果: FAIL ❌
```

---

## 3. Timer 合规检查

| 参数 | 测量值 | 规范要求 | 判定 |
|------|------|------|:---:|
| 消息 3→4 间隔（硬件重试） | ~1-2ms | ≥ 100.9ms (tReceive min + tTypeCSendSourceCap min) | ❌ **FAIL** |
| 消息 3→4 间隔（软件延迟） | 150ms (T_SEND_SOURCE_CAP) | ≤ 201.1ms (tReceive max + tTypeCSendSourceCap max) | ✅ PASS |
| 单次 TX Duration | ~9-10ms | — | ✅ 正常 |
| 软件周期间隔 | ~150ms | — | ✅ 符合配置 |

**分析**: 软件层面的时序是正确的（150ms 延迟），但硬件重试在 1-2ms 内产生额外的 CC 线消息，测试仪将这些消息计为独立消息，导致消息 3→4 间隔远小于 100.9ms。

---

## 4. 消息序列合规检查

### 4.1 SourceCapabilityTimer 超时重试序列

**期望行为（符合 PD 规范）**:
```
Source                          Sink (Tester)
  |                                    |
  |--- Source_Capabilities (1) ------->|  ← 发送
  |   (Tester 不回复 GoodCRC)          |
  |                                    |
  |   ... SourceCapabilityTimer 超时 ...|
  |   ... 等待 tTypeCSendSourceCap ... |
  |                                    |
  |--- Source_Capabilities (2) ------->|  ← 150ms 后重试
  |   (Tester 不回复 GoodCRC)          |
  |                                    |
  |   ... SourceCapabilityTimer 超时 ...|
  |   ... 等待 tTypeCSendSourceCap ... |
  |                                    |
  |--- Source_Capabilities (3) ------->|  ← 150ms 后重试
  |   (Tester 不回复 GoodCRC)          |
  |                                    |
  |   ... SourceCapabilityTimer 超时 ...|
  |   ... 等待 tTypeCSendSourceCap ... |
  |                                    |
  |--- Source_Capabilities (4) ------->|  ← 150ms 后重试
```

**实际行为（硬件重试干扰）**:
```
Source (SC27XX HW)                Sink (Tester)
  |                                    |
  |--- Source_Capabilities (1) ------->|  ← 软件 TX #1
  |--- Source_Capabilities (2) ------->|  ← 硬件重试 #1 (~1ms)
  |--- Source_Capabilities (3) ------->|  ← 硬件重试 #2 (~1ms)
  |--- Source_Capabilities (4) ------->|  ← 硬件重试 #3 (~1ms)
  |                                    |
  |   ... 150ms 软件延迟 ...           |
  |                                    |
  |--- Source_Capabilities (5) ------->|  ← 软件 TX #2
  |--- Source_Capabilities (6) ------->|  ← 硬件重试 #1 (~1ms)
  |--- Source_Capabilities (7) ------->|  ← 硬件重试 #2 (~1ms)
  |--- Source_Capabilities (8) ------->|  ← 硬件重试 #3 (~1ms)
```

### 4.2 合规判定

| 检查项 | 期望 | 实际 | 判定 |
|------|------|------|:---:|
| 消息 3→4 间隔 ≥ 100.9ms | 软件延迟 150ms | 硬件重试 ~1ms | ❌ |
| 消息内容一致 | 相同 Source_Capabilities | 相同（同一软件 TX） | ✅ |
| 消息格式正确 | 有效 PD 消息 | 有效 | ✅ |
| GoodCRC 处理 | 不回复 | 测试仪不回复 | ✅ |

**结论**: 消息序列本身合法，但消息间隔因硬件重试而严重缩短，违反步骤 5c.ii 的时序要求。

---

## 5. 增加软件延迟无效的原因

```
修改前: SPRD_PD_T_SEND_SOURCE_CAP = 150ms
修改后: SPRD_PD_T_SEND_SOURCE_CAP = 180ms

CC 线表现:
  修改前: [Msg1,2,3,4] ─150ms─ [Msg5,6,7,8] ─150ms─ [Msg9,10,11,12]
  修改后: [Msg1,2,3,4] ─180ms─ [Msg5,6,7,8] ─180ms─ [Msg9,10,11,12]
              ↑ 同一周期内消息间隔仍为 ~1ms

  测试仪检查的是同一周期内消息 3→4 的间隔，软件延迟只影响不同周期间隔。
  增加软件延迟无法解决硬件重试导致的 1-2ms 间隔问题。
```

---

## 6. 修复验证预期

修复后（禁用 `enable_tx_auto_retry`），CC 线表现：

```
修复后:
  [Msg1] ─150ms─ [Msg2] ─150ms─ [Msg3] ─150ms─ [Msg4] ─150ms─ [Msg5]
     ↑              ↑              ↑              ↑
  软件 TX #1    软件 TX #2    软件 TX #3    软件 TX #4
  间隔 = 150ms  间隔 = 150ms  间隔 = 150ms

  步骤 5c 检查: 消息 3→4 间隔 = 150ms
  要求: ≥ 100.9ms 且 ≤ 201.1ms
  结果: PASS ✅
```

---

*Phase 3 完成 | 产物: `03_trace_analysis.md` | 下一步: Phase 4 Log 分析*

> ⚠️ **置信度说明**: 由于缺少 Lecroy .usb 二进制 trace 文件，CC 线消息间隔的精确值（~1-2ms）来自 Ke.Wang1 的硬件分析报告，而非直接测量。建议在修复后获取 Lecroy .usb 文件验证实际效果。