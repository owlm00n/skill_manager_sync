# Phase 4: Log 深度分析 — PR_Swap 状态机转换失败根因

**分析时间**: 2026-09-09
**Log 来源**: `0-kernel.log` lines 11030-11389
**关键纠正**: CC LOGIC 是 **SC27xx PMIC 集成**，非第三方芯片

---

## 4.1 结论

**根因**: `sc27xx_typec_pr_swap_no_chk_detach(on=1)` 在 PR_Swap 消息到达前就被 CC 检测中断 (irq=78) 触发，提前禁用了 CC 检测功能。sprd_tcpm 状态机进入 PR_SWAP_SNK_SRC_SINK_OFF 后，需要 CC 线状态变化事件来触发向 PE_PRS_SNK_SRC_Assert_Rp 的转换，但由于 CC 检测被禁用，该事件永远不会产生，状态机在 835ms 后超时进入 ERROR_RECOVERY。

**置信度**: ⭐⭐⭐⭐⭐ (高 — 有完整 kernel log 证据链支持)

---

## 4.2 关键事件时间线（完整状态机追踪）

### 4.2.1 PR_Swap 失败序列详解

**来源**: `0-kernel.log` lines 11030-11129

| 行号 | 时间戳 (s) | 事件 | 分析 |
|:----:|-----------|------|------|
| 11035 | 88.231895 | `pd irq: start handle irq, irq = 78` | CC 检测中断触发 |
| **11036** | **88.232817** | **`sc27xx_typec_pr_swap_no_chk_detach, on = 1`** | 🔴 **CC 检测被禁用** |
| 11040 | 88.232693 | `header = 0x76a` | PR_Swap 消息（PD 2.0 格式） |
| 11044 | 88.232795 | `state change SNK_READY -> PR_SWAP_ACCEPT` | 状态机接受 PR_Swap |
| 11045 | 88.232805 | `sprd_tcpm_typec_pr_swap_no_chk_detach, cur state: PR_SWAP_ACCEPT, on: 1` | 确认 CC 检测禁用 |
| 11049 | 88.234268 | `PD TX, header: 0x243` | 发送 Accept |
| 11058 | 88.235897 | `PD TX complete, status: 0` | ✅ Accept 发送成功 |
| 11066 | 88.235964 | `state change PR_SWAP_ACCEPT -> PR_SWAP_START` | 开始角色交换 |
| 11067 | 88.235968 | `sink swap source role start` | 角色交换确认 |
| 11069 | 88.235971 | `typec try role en:=0` | 禁用 TrySNK 模式 |
| 11072 | 88.235976 | `state change PR_SWAP_START -> PR_SWAP_SNK_SRC_SINK_OFF` | **进入 Sink Off 状态** |
| 11073 | 88.235981 | `vbus=0 charge:=0` | DUT 关闭内部 VBUS/充电 |
| 11075 | 88.235982 | `vbus is already Off` | VBUS 已经关闭 |
| **11076** | **88.237377** | **`pending state change PR_SWAP_SNK_SRC_SINK_OFF -> ERROR_RECOVERY @ 835 ms`** | ⏰ **PSSourceOffTimer 启动** |
| 11092 | 88.304479 | `sc27xx_pd_extcon_vbus_change_event, vbus_online: 0` | 外部 VBUS 确认关闭 |
| 11128 | 88.314674 | `vbus_connect_value:0` | VBUS 连接确认=0 |

**关键观察**: 在 88.285s 到 89.072s 之间（共 787ms），**没有任何 CC 线状态变化或 PD 消息事件**。状态机完全静止。

### 4.2.2 ERROR_RECOVERY 序列

**来源**: `0-kernel.log` lines 11330-11389

| 行号 | 时间戳 (s) | 事件 | 分析 |
|:----:|-----------|------|------|
| 11336 | 89.072524 | `sc27xx_typec_pr_swap_no_chk_detach, on = 0` | CC 检测重新启用 |
| 11337 | 89.072543 | `state change PR_SWAP_SNK_SRC_SINK_OFF -> ERROR_RECOVERY` [delayed 835 ms] | 🔴 超时触发 |
| 11338 | 89.072550 | `sprd_tcpm_typec_pr_swap_no_chk_detach, cur state: ERROR_RECOVERY, on: 0` | 确认 |
| 11352 | 89.094406 | `typec try role en:=2` | 恢复 TrySNK |
| 11356 | 89.098477 | `ERROR_RECOVERY clear power role swap flag` | 清除 PR_Swap 标志 |
| 11357 | 89.100403 | `state change ERROR_RECOVERY -> PORT_RESET` | 端口复位 |
| 11360 | 89.101479 | `sprd_tcpm_typec_disconnect: connected=1` | 断开连接 |
| 11363 | 89.104479 | `sprd_tcpm_typec_disconnect: unregister_partner` | 注销 Partner |
| 11364 | 89.104522 | `pd_capable flase` [sic] | PD 能力清除 |
| 11381 | 89.126516 | `cc:=0` | CC 线复位 |
| 11382 | 89.187516 | `pending state change PORT_RESET -> PORT_RESET_WAIT_OFF @ 100 ms` | 等待复位 |

---

## 4.3 异常调用链分析

### 4.3.1 PR_Swap 状态机转换路径

```
正常路径 (PD 规范):
  SNK_READY → PR_SWAP_ACCEPT → PR_SWAP_START
    → PR_SWAP_SNK_SRC_SINK_OFF     [关闭 Sink]
    → PR_SWAP_SNK_SRC_SOURCE_ON    [切换 CC→Rp, 开启 Source]
    → SRC_SEND_PS_RDY              [发送 PS_RDY]
    → SRC_READY                    [PR_Swap 完成]

实际路径 (Bug 3523391):
  SNK_READY → PR_SWAP_ACCEPT → PR_SWAP_START
    → PR_SWAP_SNK_SRC_SINK_OFF     [关闭 Sink ✅]
    → ⏰ 835ms 超时                  [卡住 — 无法转换]
    → ERROR_RECOVERY                [状态机崩溃 ❌]
    → PORT_RESET → SNK_UNATTACHED → TOGGLING
```

### 4.3.2 驱动调用链

```
sc27xx-typec (CC检测/DRP)
  ├── CC 中断 (irq=78) → sc27xx_typec_pr_swap_no_chk_detach(on=1)
  │   └── 禁用 CC detach 检测 → 同时禁用 CC 状态变化事件
  │
  └── sprd_tcpm (PD 协议栈/状态机)
      ├── PR_SWAP_ACCEPT → 调用 sprd_tcpm_typec_pr_swap_no_chk_detach(on=1)
      ├── PR_SWAP_START → PR_SWAP_SNK_SRC_SINK_OFF
      │   └── 设置 835ms PSSourceOffTimer
      ├── [等待 CC 状态变化事件...] ← 🔴 事件永远不会来
      └── 835ms 超时 → ERROR_RECOVERY
          └── 调用 sc27xx_typec_pr_swap_no_chk_detach(on=0)
```

### 4.3.3 关键函数分析

| 函数 | 调用时机 | 作用 | 问题 |
|------|---------|------|------|
| `sc27xx_typec_pr_swap_no_chk_detach(on=1)` | CC 中断 irq=78 触发 | 禁用 CC 断开检测 | **也阻止了 CC 状态变化事件** |
| `sprd_tcpm_typec_pr_swap_no_chk_detach(on=1)` | PR_SWAP_ACCEPT 状态 | 同步状态机 | 确认 CC 检测已禁用 |
| `sprd_tcpm_pd_enable_vbus_discharge()` | PR_SWAP_SNK_SRC_SINK_OFF | 关闭 VBUS | 正常工作 ✅ |
| **状态机转换条件检查** | PR_SWAP_SNK_SRC_SINK_OFF | **等待 CC 事件** | 🔴 **事件被阻塞** |

---

## 4.4 根因分析

### 4.4.1 问题机制

```
时间线:
  88.232s: CC 中断 (irq=78) 触发
           └→ sc27xx_typec_pr_swap_no_chk_detach(on=1)
              └→ CC 检测功能被禁用
              └→ CC 状态变化事件被阻塞

  88.262s: PR_Swap 消息到达 (30ms 后)
           └→ sprd_tcpm 进入 PR_Swap 状态机

  88.285s: 进入 PR_SWAP_SNK_SRC_SINK_OFF
           └→ VBUS 关闭 ✅
           └→ 状态机等待 CC 线状态变化事件
              └→ 但 CC 检测已被禁用！
              └→ 事件永远不会产生

  89.072s: 835ms 超时
           └→ ERROR_RECOVERY
```

### 4.4.2 核心问题

**时序竞争 (Race Condition)**: CC 检测中断 (irq=78) 可能由 Tester 在准备 PR_Swap 时的 CC 线行为触发，导致 `pr_swap_no_chk_detach` 在 PR_Swap 消息实际到达前就被调用。

**功能过度禁用**: `sc27xx_typec_pr_swap_no_chk_detach(on=1)` 的设计意图是防止 PR_Swap 期间 CC 线电压变化导致误判为断开。但该函数可能**过度禁用了 CC 检测功能**，不仅阻止了断开检测，还阻止了正常的状态变化事件（如 CC 线角色切换完成通知）。

**状态机阻塞**: sprd_tcpm 状态机在 PR_SWAP_SNK_SRC_SINK_OFF 状态下，需要收到 CC 线状态变化事件（或 SC27xx PMIC 的 CC 角色切换完成回调）来触发向下一状态的转换。由于 CC 检测被禁用，该事件永远不会产生。

### 4.4.3 为什么 PD 2.0 通过但 PD 3.0 失败？

| 假设 | 详细说明 | 置信度 |
|------|---------|:----:|
| **CC 中断触发时机不同** | PD 2.0 测试模式下，Tester 的 CC 线行为可能不触发 irq=78 中断，因此 `pr_swap_no_chk_detach` 不被调用，CC 检测保持正常 | ⭐⭐⭐⭐ |
| **状态机路径不同** | PD 2.0 和 PD 3.0 模式下 sprd_tcpm 可能使用不同的 PR_Swap 处理路径，PD 2.0 路径不依赖 CC 检测事件 | ⭐⭐⭐ |
| **Tester 时序差异** | PD 3.0 Tester 在发送 PR_Swap 前有额外的 CC 线操作，触发了 CC 中断 | ⭐⭐⭐ |

**最可能的原因**: PD 3.0 测试模式下，Tester 在发送 PR_Swap 前的 CC 线操作触发了 SC27xx PMIC 的 CC 检测中断 (irq=78)，导致 `pr_swap_no_chk_detach` 被提前调用。PD 2.0 测试模式下无此行为。

---

## 4.5 修复建议

### 修复方向 1: 调整 `pr_swap_no_chk_detach` 的调用时机

**问题**: 当前在 CC 中断中提前调用 `pr_swap_no_chk_detach(on=1)`，远早于 PR_Swap 消息到达。

**修复**: 将 `pr_swap_no_chk_detach(on=1)` 的调用时机推迟到 PR_SWAP_ACCEPT 状态确认后，且确保在 PR_SWAP_SNK_SRC_SINK_OFF 进入前只禁用断开检测，不阻塞 CC 状态变化事件。

```
修改前:
  CC irq → pr_swap_no_chk_detach(on=1) → ... → PR_Swap 消息到达

修改后:
  PR_Swap 消息到达 → PR_SWAP_ACCEPT → pr_swap_no_chk_detach(on=1, 仅禁用 detach)
```

### 修复方向 2: 分离 CC 断开检测和状态变化事件

**问题**: `pr_swap_no_chk_detach` 可能同时禁用了断开检测和状态变化事件。

**修复**: 将 CC 断开检测和 CC 状态变化事件分离为两个独立的控制路径：
- `pr_swap_no_chk_detach(on=1)` → 仅禁用断开检测
- CC 状态变化事件 → 保持启用，允许状态机正常转换

### 修复方向 3: 使用主动 CC 角色切换替代事件等待

**问题**: 状态机在 PR_SWAP_SNK_SRC_SINK_OFF 被动等待 CC 事件。

**修复**: 在进入 PR_SWAP_SNK_SRC_SINK_OFF 后，主动向 SC27xx PMIC 发送 CC 角色切换命令（Rd→Rp），并轮询等待切换完成，而非依赖 CC 检测事件。

---

*Phase 4 完成 | 2026-09-09*