# TEST.PD.PROT.SRC3.01 — SourceCapabilityTimer Timeout

**Case ID**: TEST.PD.PROT.SRC3.01
**规范来源**: USB PD 3.1 CTS Q4 2024 OR, Page 148
**生成时间**: 2026-08-31
**置信度**: 高 (直接从规范 PDF 提取)

---

## 测试目的

测试 Source UUT 的 SourceCapabilityTimer 是否正确实现。Tester 故意不回复 GoodCRC 以触发 SourceCapabilityTimer 超时，验证 UUT 的 Source Capabilities 消息重试间隔是否符合 PD 规范时序要求。

## 测试条件

- **测试角色**: Consumer Only, C/P, Provider Only, DRP, P/C
- **Rev3ChkdSrc**: ✓
- **Tester 行为**: 不模拟 Cable（不回复 GoodCRC）
- **初始状态**: 断开连接

## 测试步骤

| 步骤 | 描述 | 判定标准 | 失败条件 |
|------|------|---------|---------|
| 1 | 测试从断开状态开始 | — | — |
| 2 | Tester 施加 Rd，等待 VBUS present | — | — |
| 3 | 等待 UUT 发送第一条 Source_Capabilities | tFirstSourceCap max 内收到 | 超过 tFirstSourceCap max 未收到第一条 Source_Capabilities → **FAIL [TEST.PD.PROT.SRC3.1#1]** |
| 4 | Tester 收到第一条 Source_Capabilities 后，**故意不回复 GoodCRC**，等待下一条 Source_Capabilities | — | 整个测试过程中 Tester 不回复 GoodCRC |
| 5a | 测量第 1 条 → 第 2 条 Source_Capabilities 的间隔 | ≤ tReceive max + tRetry | 超出范围 → **FAIL [TEST.PD.PROT.SRC3.1#2]** |
| 5b | 测量第 2 条 → 第 3 条 Source_Capabilities 的间隔 | ≤ tReceive max + tRetry | 超出范围 → **FAIL [TEST.PD.PROT.SRC3.1#2]** |
| 5c | 测量第 3 条 → 第 4 条 Source_Capabilities 的间隔 | **≥ 100.9ms 且 ≤ 201.1ms** | (i) > 201.1ms → **FAIL** (ii) < 100.9ms → **FAIL** |
| 5d | 测量第 4 条 → 第 5 条 Source_Capabilities 的间隔 | ≤ tReceive max + tRetry | 超出范围 → **FAIL [TEST.PD.PROT.SRC3.1#2]** |

## 关键时序参数

| 参数 | 符号 | 最小值 | 最大值 | 说明 |
|------|------|:---:|:---:|------|
| 接收处理时间 | tReceive | 0.9ms | 1.1ms | 接收方处理消息的时间 |
| Source 发送 SourceCap 间隔 | tTypeCSendSourceCap | 100ms | 200ms | Source 发送 Source Capabilities 的最小间隔 |
| 重试时间 | tRetry | — | — | SourceCapabilityTimer 超时后重试 |
| 首次发送 SourceCap 超时 | tFirstSourceCap | — | tFirstSourceCap max | 连接后首次发送 SourceCap 的最大延迟 |

### 步骤 5c 关键判定

```
步骤 5c 是唯一要求 ≥100.9ms 的步骤，也是本 Case 的失败点：
  - 最小间隔: tReceive min (0.9ms) + tTypeCSendSourceCap min (100ms) = 100.9ms
  - 最大间隔: tReceive max (1.1ms) + tTypeCSendSourceCap max (200ms) = 201.1ms
```

## 测试关键点

1. **Tester 不回复 GoodCRC** — 这是测试的核心机制，迫使 UUT 的 SourceCapabilityTimer 超时并重试
2. **步骤 5c 是最严格的检查** — 仅在第 3→4 条消息之间要求 ≥100.9ms 的最小间隔，其他步骤只需要 ≤上限
3. **硬件重试机制会导致 FAIL** — 如果 PD 控制器硬件在未收到 GoodCRC 时自动重传（1-2ms 间隔），将违反步骤 5c 的 100.9ms 最小间隔要求

## 失败模式

- **常见失败 [TEST.PD.PROT.SRC3.1#1]**: UUT 连接后未在 tFirstSourceCap max 内发送 Source_Capabilities
- **常见失败 [TEST.PD.PROT.SRC3.1#2]**: 第 3→4 条消息间隔 < 100.9ms（硬件 auto-retry 导致）
- **常见失败**: 第 3→4 条消息间隔 > 201.1ms（软件延迟配置过大）

---

*由 pd_auth_analyse Phase 2 自动生成 | 来源: USB_PD3_CTS_Q4_2024_OR.pdf Page 148-149*