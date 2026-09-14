# Phase 4: Log 深度分析 — TEST.PD.PROT.SRC3.01

**分析时间**: 2026-08-31
**Case ID**: TEST.PD.PROT.SRC3.01
**数据来源**: `0-kernel.log` (ORIGINAL FAIL, 1,515,520 bytes, 11,345 lines)

---

## 1. 结论

**软件层面行为正常，硬件重试是导致测试失败的根因。**

Kernel log 确认：
- 每个 TX 周期软件仅发起**一次** `PD TX` 操作
- 每次 TX 后硬件 IRQ 报告 `tx error failed`，软件 IRQ 同样报告 `tx error failed`
- TX 完成状态为 `status: 2`（错误，未收到 GoodCRC）
- 软件延迟 150ms（`SPRD_PD_T_SEND_SOURCE_CAP`）后重试，符合 PD 规范
- 无 I2C 通信异常、无 Charger IC 异常、无 BC1.2 干扰

**关键发现**：CC 线上观察到的 4 条消息（1 次发送 + 3 次硬件重试）全部来自同一次软件 TX 操作，但测试仪将其计为 4 条独立消息。软件层面每个周期只有一次 TX 完成事件，间隔由软件 150ms 控制，符合规范。问题出在硬件自动重试机制，而非软件逻辑。

---

## 2. TX 事件时间线

### 2.1 完整 TX 周期表

| 周期 | curr_time1 (ms) | curr_time2 (ms) | Duration (ms) | 延迟 (ms) | int sts | status | CC 极性 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 89507 | 89517 | 10 | 150 | 0x40 | 2 | polarity 0 |
| 2 | 89667 | 89677 | 9 | 150 | 0x40 | 2 | polarity 0 |
| 3 | 90138 | 90147 | 8 | 150 | 0x40 | 2 | polarity 1 |
| 4 | 106804 | 106812 | 8 | 150 | 0x40 | 2 | polarity 0 |
| 5 | 106962 | 106972 | 10 | 150 | 0x40 | 2 | polarity 0 |
| 6 | 107122 | 107131 | 9 | 150 | 0x40 | 2 | polarity 0 |
| 7 | 107281 | 107290 | 9 | 150 | 0x40 | 2 | polarity 0 |
| 8 | 107440 | 107453 | 13 | 150 | 0x40 | 2 | polarity 0 |
| 9 | 107603 | 107612 | 9 | 150 | 0x40 | 2 | polarity 0 |

**观察**：
- 所有 9 个周期：`int sts = 0x40`（bit 6 = TX 完成中断），`status: 2`（TX 错误）
- 所有周期：`header = 0x11a1`（Source Capabilities 消息头），`data[0] = 0x9064`，`data[1] = 0x3601`
- Duration 范围：8-13ms，软件延迟固定 150ms
- 总共 135 条 TX 相关事件

### 2.2 单次 TX 周期事件序列（典型）

```
[时间点 1] handle_src_send_capabilities: curr_time1 = 89507 ms
[时间点 2] PD TX, header: 0x11a1                          ← 软件发起 TX
[时间点 3] sc27xx-typec-pd: IRQ: tx error failed           ← 硬件 IRQ 报告错误
[时间点 4] pd irq: tx error failed                          ← 软件 IRQ 报告错误
[时间点 5] int sts = 0x40                                   ← TX 完成中断
[时间点 6] PD TX complete, status: 2                        ← TX 完成，status:2
[时间点 7] handle_src_send_capabilities: curr_time2 = 89517 ms
[时间点 8] duration = 10 ms
[时间点 9] pending state change SRC_SEND_CAPABILITIES → SRC_SEND_CAPABILITIES @ 150 ms
```

**来源**: `extract_tx_events.py` 输出，原始文件 `0-kernel.log`

---

## 3. CC 状态转换时间线

### 3.1 Burst 1: 首次连接（2 TX 周期）

| 时间 (s) | 行号 | 事件 | 说明 |
|------|:---:|------|------|
| 89.268 | L9805 | `typec in or out, pd attached = 1` | 测试仪连接 CC 线 |
| 89.279 | L9817 | `DRP state 5, event 1` | CC 检测到连接 |
| 89.328 | L9862 | `TOGGLING → SRC_ATTACH_WAIT` | 状态机转换 |
| 89.330 | L9863 | `SRC_ATTACH_WAIT → SRC_ATTACHED` | 确认 Source 连接 |
| 89.371 | L9883 | `pending SRC_ATTACHED → SRC_STARTUP @ 100 ms` | 延迟 100ms 启动 |
| 89.420 | L9884 | `SRC_ATTACHED → SRC_STARTUP` | 启动 PD 通信 |
| 89.507 | — | **TX 周期 1** 开始 (curr_time1=89507) | 发送 Source Capabilities |
| 89.667 | — | **TX 周期 2** 开始 (curr_time1=89667) | 150ms 后重试 |
| 89.704 | L9928 | `sc27xx_disconnect_set_status_use_pdhubc2c` | 测试仪断开 CC 线 |
| 89.712 | L9941 | `USB disconnect, device number 1` | USB 断开 |
| 89.729 | L9964 | `disconnect, use_pdhub_c2c = 1` | PD 断开 |
| 89.743 | L9970 | `DRP state 0, event 2` | 回到 DRP 初始状态 |
| 89.761 | L9985 | `CC1: 2→0, CC2: 0→0 [SRC_SEND_CAPABILITIES, disconnected]` | 断开时正在发送 |
| 89.761 | L9986 | `SRC_SEND_CAPABILITIES → SRC_UNATTACHED` | 状态回到未连接 |

### 3.2 Burst 2: 第二次连接（1 TX 周期）

| 时间 (s) | 行号 | 事件 | 说明 |
|------|:---:|------|------|
| 89.903 | L10017 | `typec in or out, pd attached = 1` | 测试仪重新连接 |
| 89.912 | L10027 | `DRP state 5, event 1` | CC 检测 |
| 89.958 | L10057 | `TOGGLING → SRC_ATTACH_WAIT` | 状态机 |
| 89.959 | L10058 | `SRC_ATTACH_WAIT → SRC_ATTACHED` | 确认连接 |
| 90.002 | L10077 | `pending SRC_ATTACHED → SRC_STARTUP @ 100 ms` | 延迟启动 |
| 90.052 | L10084 | `SRC_ATTACHED → SRC_STARTUP` | 极性：polarity 1 |
| 90.138 | — | **TX 周期 3** 开始 (curr_time1=90138) | 发送 Source Capabilities |
| 90.195 | L10133 | `sc27xx_disconnect_set_status_use_pdhubc2c` | 测试仪断开 |
| 90.233 | L10175 | `DRP state 1, event 2` | 回到 DRP |
| 90.246 | L10193 | `CC1: 0→0, CC2: 2→0 [SRC_SEND_CAPABILITIES, polarity 1, disconnected]` | polarity 1 断开 |
| 90.246 | L10194 | `SRC_SEND_CAPABILITIES → SRC_UNATTACHED` | 未连接 |

### 3.3 Burst 3: 第三次连接（6 TX 周期）

| 时间 (s) | 行号 | 事件 | 说明 |
|------|:---:|------|------|
| 106.551 | L10433 | `typec in or out, pd attached = 1` | 测试仪重新连接 |
| 106.564 | L10453 | `DRP state 5, event 1` | CC 检测 |
| 106.608 | L10487 | `TOGGLING → SRC_ATTACH_WAIT` | 状态机 |
| 106.609 | L10488 | `SRC_ATTACH_WAIT → SRC_ATTACHED` | 确认连接 |
| 106.654 | L10511 | `pending SRC_ATTACHED → SRC_STARTUP @ 100 ms` | 延迟启动 |
| 106.718 | L10518 | `SRC_ATTACHED → SRC_STARTUP` | 极性：polarity 0 |
| 106.804 | — | **TX 周期 4** 开始 (curr_time1=106804) | |
| 106.962 | — | **TX 周期 5** 开始 (curr_time1=106962) | |
| 107.122 | — | **TX 周期 6** 开始 (curr_time1=107122) | |
| 107.281 | — | **TX 周期 7** 开始 (curr_time1=107281) | |
| 107.440 | — | **TX 周期 8** 开始 (curr_time1=107440) | |
| 107.603 | — | **TX 周期 9** 开始 (curr_time1=107603) | |
| 107.667 | L10639 | `sc27xx_disconnect_set_status_use_pdhubc2c` | 测试仪断开 |
| 107.682 | L10656 | `USB disconnect, device number 1` | USB 断开 |
| 107.699 | L10671 | `DRP state 0, event 2` | 回到 DRP |
| 107.720 | L10688 | `CC1: 2→0, CC2: 0→0 [SRC_SEND_CAPABILITIES, disconnected]` | 断开时仍在发送 |
| 107.723 | L10692 | `SRC_SEND_CAPABILITIES → SRC_UNATTACHED` | 未连接 |

**来源**: `extract_cc_events.py` 输出，原始文件 `0-kernel.log`

---

## 4. Burst 模式分析

### 4.1 测试仪 Burst 行为

```
Burst 1: Attach → TX×2 → Disconnect  (TX 周期 1-2)
Burst 2: Attach → TX×1 → Disconnect  (TX 周期 3)
Burst 3: Attach → TX×6 → Disconnect  (TX 周期 4-9)
```

**关键观察**：
- Burst 1 和 Burst 2 中，测试仪在仅 1-2 个 TX 周期后迅速断开
- 断开原因：`disconnect SC27XX_ATTACHED_SRC not get vbus ok`（L9984, L10192, L10687）
- Burst 3 中，测试仪保持连接，允许 6 个连续的 TX 周期
- 极性在 Burst 间交替（polarity 0 → polarity 1 → polarity 0）

### 4.2 与 Ke.Wang1 硬件分析的对齐

Ke.Wang1 (Comment #12) 报告：
> 5 次软件发送，每次产生 4 次硬件重传，共 20 个包，前 14 个包丢失

对齐分析：
- Burst 1 + Burst 2 的 TX 周期 1-3：共 3 次软件发送，但 VBUS 未就绪，包丢失
- Burst 3 的 TX 周期 4-9：共 6 次软件发送，前几个周期可能仍丢失部分包
- Ke.Wang1 观察到的 5 次软件发送 = 6 次中的 5 次（或包含部分有效发送）

---

## 5. 关键日志发现

### 5.1 `int sts = 0x40` 含义

`0x40` = bit 6，即 TX 完成中断标志。每个 TX 周期均出现一次，证明：
- 硬件 TX 确实完成了（发送了数据包）
- 但 `status: 2` 表示未收到 GoodCRC（测试仪故意不回复）

### 5.2 `tx error failed` 双重触发

每个周期中，`tx error failed` 出现两次：
1. **硬件 IRQ**：`sc27xx-typec-pd: IRQ: tx error failed` — PD 控制器硬件中断
2. **软件 IRQ**：`pd irq: tx error failed` — 软件层面处理中断

这证明硬件和软件层面都正确感知到 TX 错误（未收到 GoodCRC），触发重试逻辑。

### 5.3 `disconnect SC27XX_ATTACHED_SRC not get vbus ok`

该日志在每次断开时出现，说明：
- 测试仪在 Source 连接状态下断开 CC 线
- VBUS 未达到有效电平（测试仪可能未拉高 VBUS）
- 这是测试仪 Burst 模式的正常行为，不是 UUT 故障

### 5.4 极性交替

| Burst | 极性 | 说明 |
|:---:|:---:|------|
| 1 | polarity 0 | CC1 连接 |
| 2 | polarity 1 | CC2 连接（测试仪翻转） |
| 3 | polarity 0 | CC1 连接（再次翻转） |

测试仪每次重新连接时可能翻转 CC 极性，这是测试仪的标准行为。

---

## 6. 驱动调用链分析

### 6.1 正常调用链

```
sc27xx-typec (CC 检测/DRP)
  → sprd_tcpm (PD 协议栈/状态机)
    → handle_src_send_capabilities()  ← 软件发起 TX
      → sprd_tcpm_pd_transmit()       ← 构造 PD 消息
        → tcpci_transmit()             ← 通过 I2C 发送到 PD Controller
          → SC27XX PD Controller       ← 硬件发送
            → TX 完成中断 (int sts=0x40)
              → sprd_tcpm_pd_irq()     ← 软件处理中断
                → pending state change @ 150ms
```

### 6.2 异常路径（本 Case）

```
handle_src_send_capabilities()
  → sprd_tcpm_pd_transmit()
    → tcpci_transmit()
      → SC27XX PD Controller
        → [硬件自动重试]  ← 问题点！
          → 发送 #1 → 等待 ~1ms → 未收到 GoodCRC
          → 发送 #2 → 等待 ~1ms → 未收到 GoodCRC
          → 发送 #3 → 等待 ~1ms → 未收到 GoodCRC
          → 发送 #4 → 等待 ~1ms → 未收到 GoodCRC
        → TX 完成中断 (int sts=0x40, status=2)
```

**关键**：软件层面只看到一次 TX 完成事件，但硬件在 CC 线上产生了 4 条消息。

---

## 7. 时间线对齐：Log ↔ Trace

| 层面 | 周期 1 开始 | 周期 2 开始 | 消息 3→4 间隔 |
|------|:---:|:---:|:---:|
| **软件 Log** | 89507ms | 89667ms | 150ms（周期间延迟） |
| **硬件 Trace (CC 线)** | Msg 1,2,3,4 @ ~1ms 间隔 | Msg 5,6,7,8 @ ~1ms 间隔 | 消息 3→4 = ~1-2ms |

**结论**：软件层面行为正确（150ms 延迟），但硬件重试在 CC 线上产生额外消息，测试仪将这些消息计为独立消息，导致消息 3→4 间隔仅 ~1-2ms，远小于 100.9ms。

---

## 8. 无异常模块确认

| 模块 | 检查项 | 结果 |
|------|------|:---:|
| I2C 通信 | `tcpci_transmit`、`tcpci_read`、`tcpci_write` | ✅ 无异常 |
| Charger IC | `sgm41512`、`set_voltage`、`set_vinlimit` | ✅ 无相关日志 |
| BC1.2 检测 | `sprd-bc1p2`、`bc1p2_detect`、`vbos_ok_work` | ✅ 无干扰 |
| VBUS 控制 | `musb_gadget_vbus_draw` | ✅ 无异常 |

---

*Phase 4 完成 | 产物: `04_log_analysis.md` | 下一步: Phase 5 历史 Bug 参照*

> **数据来源声明**：
> - TX 事件：`extract_tx_events.py` 脚本输出，原始文件 `E:\08_Bug\CQ\Bug 3523357...\0-kernel.log`
> - CC 事件：`extract_cc_events.py` 脚本输出，原始文件同上
> - 行号对应原始 kernel log 文件行号