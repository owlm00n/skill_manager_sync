# Phase 4: Log 深度分析

**Case ID:** TEST.PD.PROT.SRC.13  
**Bug ID:** 3523346  
**分析日期:** 2026-09-10  
**状态:** ✅ 完成

---

## 1. 结论

### 1.1 核心发现

| # | 发现 | 置信度 |
|:--:|------|:------:|
| 1 | **SC27XX PHY 层 PS_RDY TX 失败（int sts=0x40）在所有三份 log 中均出现** — 包括 PASS 的 Aug 24/27 | 🔴 确认 |
| 2 | **ERROR_RECOVERY → PORT_RESET 内部转换时间在所有三份 log 中完全一致（~2.6-2.8ms）** | 🔴 确认 |
| 3 | **Aug 21→Aug 24 的修复不在 kernel 驱动层** — 驱动 cleanup 路径时间完全一致 | 🔴 确认 |
| 4 | **修复最可能在 SC27XX PD Controller 固件层** — 或测试环境/tester 配置变更 | 🟡 高置信 |
| 5 | **Aug 27 Rev3ChkdSrc BU.1 存在 PD 3.0 Sink attach 的 HARD_RESET_SEND 循环** | 🔴 确认 |

### 1.2 一句话总结

> SC27XX PD Controller PHY 在 PR_Swap Rd transition 后发送 PS_RDY 时始终触发 TX 错误（int sts=0x40），kernel 驱动层 cleanup 路径在所有 log 中完全一致（~2.6ms ERROR_RECOVERY → PORT_RESET），Aug 21 FAIL → Aug 24 PASS 的修复不在 kernel 驱动层，最可能位于 SC27XX PD Controller 固件层或测试环境配置变更。

---

## 2. 关键事件时间线

### 2.1 时间戳体系说明

Kernel log 中存在两种时间戳，**必须区分使用**：

| 时间戳类型 | 格式 | 示例 | 含义 | 用于 |
|-----------|------|------|------|------|
| **Kernel 捕获时间** | `[  75.129912]` 行首 | `[  75.129912] IRQ: tx error failed` | 日志行被 printk 捕获的时间（含 log buffer 延迟） | 粗略定位 |
| **内部 sprd_pd_log 时间** | `[   75.129865]` 行内 | `pd irq: int sts = 0x40` | PD Controller 驱动的内部时间戳 | ⚠️ **精确计时** |

> **⚠️ 重要修正**: 上一轮分析摘要中声称 "ERROR_RECOVERY → PORT_RESET 转换时间 Aug 21: 18ms, Aug 24: 3ms, Aug 27: 1ms" 是**基于 kernel 捕获时间戳的错误结论**。实际内部 sprd_pd_log 时间戳显示三者完全一致。

### 2.2 PR_Swap Error Recovery 精确时序对比

#### Aug 21 (FAIL) — 精确时序

```
内部时间戳              事件                                              Kernel捕获时间
─────────────────────────────────────────────────────────────────────────────────────
[ 74.770748]  sc27xx_typec_pr_swap_no_chk_detach, on = 1              [ 74.770748]
[ 74.771072]  pd irq: int sts = 0x10 (RX: PR_Swap 消息接收)            [ 74.771072]
[ 74.806552]  sprd_tcpm_typec_pr_swap_no_chk_detach, cur state:       [ 74.806552]
              PR_SWAP_ACCEPT, on: 1
[ 74.816864]  pd irq: int sts = 0x20 (TX success: Accept 发送)        [ 74.816864]
[ 75.129865]  pd irq: int sts = 0x40 (TX ERROR: PS_RDY 发送失败) ⬅️   [ 75.129912]  ← 相差 47μs
[ 75.131318]  OFF_CC_DEBOUNCED send ps rdy failed                     [ 75.158789]  ← 相差 27.5ms!
[ 75.131321]  state change PR_SWAP_SRC_SNK_SOURCE_OFF_CC_DEBOUNCED    [ 75.162906]  ← 相差 31.6ms!
              -> ERROR_RECOVERY
[ 75.132647]  ERROR_RECOVERY clear power role swap flag               [ 75.175562]
[ 75.132649]  state change ERROR_RECOVERY -> PORT_RESET               [ 75.176757]  ← 相差 44.1ms!
[ 75.136803]  sc27xx_pd_reset clear_tx_id = 0                         [ 75.182949]
[ 75.142308]  sc27xx_typec_err_recover_state_en enter line 764        [ 75.142308]
[ 75.194098]  sc27xx_typec_err_recover_state_disen enter line 779     [ 75.194098]
```

**内部时间精确计算：**
- TX error → ERROR_RECOVERY: 75.131321 - 75.129865 = **1.456ms**
- ERROR_RECOVERY → PORT_RESET: 75.132649 - 75.131321 = **1.328ms**
- **TX error → PORT_RESET 总计: 75.132649 - 75.129865 = 2.784ms**
- err_recover_state_en → err_recover_state_disen: 75.194098 - 75.142308 = **51.790ms**

#### Aug 24 (FIXED) — 精确时序

```
内部时间戳              事件                                              Kernel捕获时间
─────────────────────────────────────────────────────────────────────────────────────
[ 78.678772]  sc27xx_typec_pr_swap_no_chk_detach, on = 1              [ 78.678772]
[ 78.708015]  sprd_tcpm_typec_pr_swap_no_chk_detach, cur state:       [ 78.708015]
              PR_SWAP_ACCEPT, on: 1
[ 79.037103]  pd irq: int sts = 0x40 (TX ERROR: PS_RDY 发送失败) ⬅️   [ 79.037144]  ← 相差 41μs
[ 79.038444]  OFF_CC_DEBOUNCED send ps rdy failed                     [ 79.059626]  ← 相差 21.2ms
[ 79.038447]  state change PR_SWAP_SRC_SNK_SOURCE_OFF_CC_DEBOUNCED    [ 79.059631]  ← 相差 21.2ms
              -> ERROR_RECOVERY
[ 79.039729]  state change ERROR_RECOVERY -> PORT_RESET               [ 79.062107]  ← 相差 22.4ms
[ 79.048306]  sc27xx_typec_err_recover_state_en enter line 764        [ 79.048306]
[ 79.102826]  sc27xx_typec_err_recover_state_disen enter line 779     [ 79.102826]
```

**内部时间精确计算：**
- TX error → ERROR_RECOVERY: 79.038447 - 79.037103 = **1.344ms**
- ERROR_RECOVERY → PORT_RESET: 79.039729 - 79.038447 = **1.282ms**
- **TX error → PORT_RESET 总计: 79.039729 - 79.037103 = 2.626ms**
- err_recover_state_en → err_recover_state_disen: 79.102826 - 79.048306 = **54.520ms**

#### Aug 27 (FIXED) — 精确时序

```
内部时间戳              事件                                              Kernel捕获时间
─────────────────────────────────────────────────────────────────────────────────────
[114.934236]  sc27xx_typec_pr_swap_no_chk_detach, on = 1              [114.934236]
[114.967423]  sprd_tcpm_typec_pr_swap_no_chk_detach, cur state:       [114.967423]
              PR_SWAP_ACCEPT, on: 1
[115.291300]  pd irq: int sts = 0x40 (TX ERROR: PS_RDY 发送失败) ⬅️   [115.291339]  ← 相差 39μs
[115.292517]  OFF_CC_DEBOUNCED send ps rdy failed                     [115.313913]  ← 相差 21.4ms
[115.292521]  state change PR_SWAP_SRC_SNK_SOURCE_OFF_CC_DEBOUNCED    [115.316131]  ← 相差 23.6ms
              -> ERROR_RECOVERY
[115.293902]  state change ERROR_RECOVERY -> PORT_RESET               [115.318131]  ← 相差 24.2ms
[115.303610]  sc27xx_typec_err_recover_state_en enter line 764        [115.303610]
[115.354106]  sc27xx_typec_err_recover_state_disen enter line 779     [115.354106]
```

**内部时间精确计算：**
- TX error → ERROR_RECOVERY: 115.292521 - 115.291300 = **1.221ms**
- ERROR_RECOVERY → PORT_RESET: 115.293902 - 115.292521 = **1.381ms**
- **TX error → PORT_RESET 总计: 115.293902 - 115.291300 = 2.602ms**
- err_recover_state_en → err_recover_state_disen: 115.354106 - 115.303610 = **50.496ms**

### 2.3 三份 Log 时序对比总表

| 指标 | Aug 21 (FAIL) | Aug 24 (FIXED) | Aug 27 (FIXED) | 差异 |
|------|:-----------:|:------------:|:------------:|:----:|
| **TX error → ERROR_RECOVERY** | 1.456ms | 1.344ms | 1.221ms | ±0.2ms |
| **ERROR_RECOVERY → PORT_RESET** | 1.328ms | 1.282ms | 1.381ms | ±0.1ms |
| **TX error → PORT_RESET 总计** | **2.784ms** | **2.626ms** | **2.602ms** | ±0.2ms |
| **err_recover 使能时长** | 51.790ms | 54.520ms | 50.496ms | ±4ms |
| **Kernel 捕获延迟 (TX error 行)** | 47μs | 41μs | 39μs | 可忽略 |
| **Kernel 捕获延迟 (PORT_RESET 行)** | 44.1ms | 22.4ms | 24.2ms | ⚠️ 差异大 |

### 2.4 关键洞察

1. **Kernel 捕获时间戳不可靠**：`PORT_RESET` 行的 kernel 捕获延迟在 Aug 21 高达 44.1ms，而 Aug 24/27 仅 22-24ms。这是因为 printk log buffer 在不同时刻的刷新延迟不同，**与 PD 协议行为无关**。

2. **驱动 cleanup 路径完全一致**：TX error → ERROR_RECOVERY → PORT_RESET 的内部转换时间在三份 log 中均为 ~2.6-2.8ms，差异在 ±0.2ms 以内（正常的中断/jiffies 精度抖动）。

3. **err_recover 使能时长一致**：50-55ms，与 Aug 24/27 的 PASS 结果一致。

4. **Aug 21 FAIL 的根因不在 kernel 驱动层**：如果 Aug 21 FAIL 是因为驱动 cleanup 慢了，内部时间戳应该显示明显差异。实际没有。

---

## 3. PHY 层证据：int sts=0x40 (TX Error)

### 3.1 SC27XX PD Controller 中断状态寄存器

| 位 | 值 | 含义 |
|:--:|:--:|------|
| bit 4 | 0x10 | RX 事件（收到消息） |
| bit 5 | 0x20 | TX 成功（消息发送完成） |
| bit 6 | 0x40 | **TX 错误（消息发送失败）** |

### 3.2 所有 PR_Swap 场景的 int sts 序列

#### Aug 21 (FAIL) — 首次 PR_Swap 之前的 TX 错误

```
时间          int sts    事件
────────────────────────────────────────
 55.951983    0x40      第1次 TX error（非 PR_Swap 场景，Source_Cap 发送失败）
 56.456824    0x40      第2次 TX error（Source_Cap 重试失败）
 73.224861    0x30      第1次 BU.1 成功（TX success + RX）
 73.265838    0x20      TX success（Accept）
 73.297843    0x20      TX success（PS_RDY）
 73.403029    0x20      TX success
 73.407099    0x10      RX event
 74.771072    0x10      RX event（PR_Swap 消息）
 74.816864    0x20      TX success（Accept 发送）
 75.129865    0x40      ⬅️ TX ERROR（PS_RDY 发送失败）
```

**Aug 21 特征**: 2 次初始 TX 错误 + 1 次 PR_Swap PS_RDY TX 错误。总共 3 次 TX 错误。

#### Aug 24 (FIXED) — 首次 PR_Swap 之前的 TX 错误

```
时间          int sts    事件
────────────────────────────────────────
 59.336508    0x40      第1次 TX error（非 PR_Swap 场景）
 59.494203    0x40      第2次 TX error（重试失败）
 59.929939    0x40      第3次 TX error（再次重试失败）
 77.168040    0x20      第1次 BU.1 成功（TX success）
 77.172099    0x10      RX event
 79.037103    0x40      ⬅️ TX ERROR（PS_RDY 发送失败）
```

**Aug 24 特征**: 3 次初始 TX 错误（比 Aug 21 多 1 次）+ 1 次 PR_Swap PS_RDY TX 错误。总共 4 次 TX 错误。

#### Aug 27 (FIXED) — 首次 PR_Swap 之前的 TX 错误

```
时间          int sts    事件
────────────────────────────────────────
 96.235136    0x40      第1次 TX error（非 PR_Swap 场景）
 96.778071    0x40      第2次 TX error（重试失败）
113.423404    0x20      第1次 BU.1 成功（TX success）
113.433215    0x10      RX event
115.291300    0x40      ⬅️ TX ERROR（PS_RDY 发送失败）
```

**Aug 27 特征**: 2 次初始 TX 错误 + 1 次 PR_Swap PS_RDY TX 错误。总共 3 次 TX 错误。

### 3.3 TX 错误模式分析

| 指标 | Aug 21 (FAIL) | Aug 24 (FIXED) | Aug 27 (FIXED) |
|------|:-----------:|:------------:|:------------:|
| 初始 Source_Cap TX 错误数 | 2 | 3 | 2 |
| PR_Swap PS_RDY TX 错误 | **有** | **有** | **有** |
| PS_RDY TX 错误后 PASS？ | ❌ FAIL | ✅ PASS | ✅ PASS |
| 总 TX 错误数 | 3 | 4 | 3 |

**结论**：
- **PS_RDY TX 错误（int sts=0x40）在所有三份 log 中均出现** — 包括 PASS 的 Aug 24 和 Aug 27
- 初始 TX 错误数（2-3 次）与测试结果无关 — Aug 24 有最多 TX 错误（4 次）但仍 PASS
- **PS_RDY TX 失败本身不是 FAIL 的直接原因** — 所有 log 都失败，但只有 Aug 21 FAIL

---

## 4. tCtsErrorRecovery 失效机制分析

### 4.1 已知事实

- **规范要求**: tCtsErrorRecovery ≤ 15ms（从 PS_RDY 发送失败到 Error Recovery 被检测到）
- **Phase 3 Trace 分析**: Lecroy 仪器测到 ~16ms，超限 ~1ms
- **Phase 4 Log 分析**: 驱动内部 TX error → PORT_RESET 仅 2.6-2.8ms

### 4.2 时间预算分解

```
TX error 发生 (int sts=0x40)
    │
    ├─ ~0ms    SC27XX 内部 HW 重试 CRCReceiveTimer (0.9-1.1ms × nRetryCount=2)
    │          实际耗时: ~2.2ms (2次重试)
    │
    ├─ ~1.2-1.5ms  驱动收到中断 → 判定 "send ps rdy failed"
    │               → state change: SOURCE_OFF_CC_DEBOUNCED → ERROR_RECOVERY
    │
    ├─ ~1.3ms  ERROR_RECOVERY → PORT_RESET
    │
    ├─ ~2.6ms  TX error → PORT_RESET（驱动内部总计）
    │
    └─ ?ms     SC27XX 硬件内部处理时间（不被 kernel log 记录）
               ────────────────────────────────────────
               仪器测到的总时间: ~16ms
               驱动内部时间: ~2.6ms
               差值: ~13.4ms（在 SC27XX 硬件内部消耗）
```

### 4.3 硬件内部时间消耗假说

SC27XX PD Controller 在报告 TX error 之前，内部会进行 CRCReceiveTimer 重试：

```
PHY 层尝试发送 PS_RDY:
  ├─ 第1次: 发送 → 等待 GoodCRC → CRCReceiveTimer 超时 (0.9-1.1ms) → 重试
  ├─ 第2次: 发送 → 等待 GoodCRC → CRCReceiveTimer 超时 (0.9-1.1ms) → 重试
  ├─ 第3次: 发送 → 等待 GoodCRC → CRCReceiveTimer 超时 (0.9-1.1ms) → 失败
  └─ 报告 int sts=0x40 → 驱动收到中断
```

**HW 重试时间**: 3 × ~1.1ms = ~3.3ms（CRCReceiveTimer 超时）+ BMC 编码/发送时间

**关键问题**: 这 3.3ms 的 HW 重试时间在 kernel log 中不可见，因为 int sts=0x40 是在所有重试耗尽后才报告给驱动的。

### 4.4 Aug 21 FAIL 的 16ms 来自哪里？

如果驱动内部只有 2.6ms，HW 重试约 3.3ms，合计约 6ms，那么剩余的 ~10ms 在哪里？

**假说 1: SC27XX 固件等待时间（最可能）**
- Aug 21 固件在处理 PR_Swap Rd transition 后，可能在 BMC PHY 重新初始化（CC 线从 Rp 切换到 Rd 后的 BMC 驱动能力恢复）上有额外延迟
- Aug 24/27 固件可能优化了这个等待时间

**假说 2: 测试环境差异**
- Aug 21 和 Aug 24/27 可能使用了不同的 Lecroy 仪器配置或不同版本的 tester 脚本
- 仪器对 tCtsErrorRecovery 的测量起点可能不同

**假说 3: CC 线电气状态恢复**
- PR_Swap 后 Rd transition 完成，但 BMC 发送电路需要稳定时间
- Aug 21 固件可能在这个阶段有额外的 debounce 等待

---

## 5. Rev3ChkdSrc BU.1 分析

### 5.1 Aug 21 Log — 无 Rev3ChkdSrc 证据

Aug 21 kernel log 在 PR_Swap Error Recovery 后没有 Rev3ChkdSrc（PD 3.0 Sink 模式）的初始化日志。Log 在此之后结束或进入其他测试。

### 5.2 Aug 24 Log — 无 Rev3ChkdSrc 证据

Aug 24 kernel log 在 PR_Swap session 之后（~149.8s）只有 audio 相关事件，没有 PD 3.0 Sink attach 日志。

**可能原因**:
- Aug 24 只测试了 Rev2Src（PD 2.0 模式），Rev3ChkdSrc 未执行
- 或 Rev3ChkdSrc 在另一次上电中测试，对应 log 未包含在当前文件中

### 5.3 Aug 27 Log — Rev3ChkdSrc BU.1 证据

```
时间             事件
────────────────────────────────────────────────────────────────
[213.167704]  sc27xx_pd_reset clear_tx_id = 1       ← PD 3.0 Sink session 开始
[213.226442]  sc27xx_pd_reset clear_tx_id = 0
[213.517895]  charger-manager: retry_cnt = 5         ← 充电管理重试
[213.527654]  sprd-fgu: retry_cnt = 23               ← 电量计重试
[213.548267]  charger-manager: retry_cnt = 5
[213.642710]  sc27xx_pd_send_hardreset: send hard reset  ← 第1次 Hard Reset
[213.649766]  sc27xx_typec_pr_swap_no_chk_detach, on = 0
[213.649814]  sprd_tcpm_typec_pr_swap_no_chk_detach, cur state: HARD_RESET_START, on: 0
[216.046598]  sc27xx_pd_send_hardreset: send hard reset  ← 第2次 Hard Reset
[216.081873]  sprd_tcpm_typec_pr_swap_no_chk_detach, cur state: HARD_RESET_START, on: 0
[218.447184]  sc27xx_typec_pr_swap_no_chk_detach, on = 0
[218.449911]  sprd_tcpm_typec_pr_swap_no_chk_detach, cur state: SNK_READY, on: 0
```

### 5.4 Rev3ChkdSrc 失败模式分析

**观察到的行为**:
1. PD 3.0 Sink attach 后，`clear_tx_id = 1` → `clear_tx_id = 0`（正常初始化）
2. 随后进入 `HARD_RESET_SEND` → `HARD_RESET_START` 循环
3. 两次 Hard Reset 发送（间隔 2.4s），之后进入 `SNK_READY`
4. 没有看到 Source_Cap 接收、Request 发送、PS_RDY 接收等正常 PD 通信

**失败原因推断**:
- PD 3.0 Sink 模式下，DUT 尝试与 tester 建立 PD 通信，但通信失败
- 可能的原因：PD 3.0 模式下 VBus 初始化失败（Phase 3 提到 `0x000003A9`: VBus not present）
- DUT 判断通信失败后发送 Hard Reset 尝试恢复，但恢复后仍无法建立 PD 通信
- 最终进入 SNK_READY（纯 Type-C Sink 模式，无 PD 通信）

**与 Phase 3 结论一致**: Phase 3 分析指出 "PD 3.0 mode VBus init likely fails due to PD 2.0-only VIF"

---

## 6. 回答 Phase 3 未解问题

### 6.1 问题 #3: Aug 21→Aug 24 的修复 patch 具体改了什么？

**答案**: 修复**不在 kernel 驱动层**。

**证据**:
1. ERROR_RECOVERY → PORT_RESET 内部转换时间三份 log 完全一致（~2.6-2.8ms）
2. err_recover_state_en → err_recover_state_disen 时长一致（~50-55ms）
3. 驱动调用链 `sc27xx_typec_err_recover_state_en` → `sc27xx_typec_pr_swap_no_chk_detach` → `sc27xx_pd_reset` 的执行顺序和时机完全一致
4. PS_RDY TX 错误（int sts=0x40）在所有 log 中均出现

**修复位置推断**:
- **SC27XX PD Controller 固件**（最可能）: 可能优化了 PR_Swap Rd transition 后 BMC PHY 的初始化时序
- **测试环境配置**: Aug 24/27 可能使用了不同的 tester 配置或 Lecroy 仪器设置
- **非 kernel 驱动层**: 如果 kernel 驱动有 patch，cleanup 时序应该有可观测的变化

### 6.2 问题 #4: Aug 24/27 kernel log 中是否有 Rev3ChkdSrc BU.1 的初始化日志？

**答案**:
- **Aug 24**: ❌ 未发现 Rev3ChkdSrc PD 3.0 Sink attach 日志
- **Aug 27**: ✅ 发现 PD 3.0 Sink attach 日志（~213s），但存在 HARD_RESET_SEND 循环

**详见 §5.2-5.3**

### 6.3 问题 #5: PD 3.0 模式下 bq2560x OTG enable 是否被正确调用？

**答案**: 从当前 tcpci 中断级别的 log 提取中，未捕获到 bq2560x OTG 相关日志。

**需要进一步检查**: 需要在 Aug 27 完整 kernel log 中搜索 `bq2560x.*OTG` 和 `bq2560x.*enable` 来确认。从现有数据看，PD 3.0 Sink 模式下 VBus 可能未被正确使能，导致 tester 报 `0x000003A9`（VBus not present）。

### 6.4 问题 #1: SC27XX int sts=0x40 的精确含义

**答案**: int sts=0x40 = bit 6 = TX 错误。表示 SC27XX PD Controller PHY 层在尝试发送消息时失败。在当前场景中，是发送 PS_RDY 消息时，PHY 层在 CRCReceiveTimer 重试耗尽后仍未收到 GoodCRC 响应，报告 TX 失败。

**内部重试推断**: nRetryCount=2（Phase 3 从 trace 中确认），CRCReceiveTimer=0.9-1.1ms，总 HW 重试时间约 2.7-3.3ms。这部分时间在 kernel log 中不可见。

### 6.5 问题 #2: sc27xx_pd_reset(clear_tx_id=0) 的影响

**答案**: `sc27xx_pd_reset(clear_tx_id=0)` 在 ERROR_RECOVERY → PORT_RESET 之后被调用，作用是清除 PD Controller 的 TX 状态寄存器，为下一次 PD 通信做准备。这是标准的 cleanup 操作，在所有三份 log 中行为一致。

### 6.6 问题 #6: PR_Swap Rd transition 后 CC 线电气状态

**答案**: 从 kernel log 层面无法直接观测 CC 线电气状态。但从 SC27XX PHY 始终报告 TX 错误（int sts=0x40）来看，**BMC 发送电路在 PR_Swap Rd transition 后确实存在问题**。这可能是：
- CC 线从 Rp 切换到 Rd 后，BMC 驱动的偏置电压需要稳定时间
- SC27XX 内部的 BMC 发送器在角色切换后需要重新校准

**注意**: 这个问题在所有 log 中都存在（PASS 和 FAIL 一样），所以不是 FAIL 的根因，而是 SC27XX 硬件的一个已知行为特征。

---

## 7. Aug 27 多次 Session 失败分析

### 7.1 失败 Session 序列

Aug 27 log 中，在成功的 PR_Swap session 之前，有两次失败的 session：

```
Session 1: 初始 TX error (96.2s) → TX error (96.8s) → 没有后续 BU.1 成功记录
Session 2: BU.1 成功 (113.4s) → PR_Swap → PS_RDY TX error → PASS
Session 3: PD 3.0 Sink attach (213.2s) → HARD_RESET_SEND 循环 → SNK_READY
```

**Session 1 失败原因**: 两次 Source_Cap TX 错误后未能建立 PD 通信。可能与 "not get vbus ok" 相关（Phase 3 摘要中提到）。

### 7.2 多 Session 失败的影响

- 认证测试中，如果 DUT 在建立 PD 通信前多次失败，可能影响 tester 对 DUT 的初始状态判断
- 但 Session 2 最终 PASS，说明 DUT 在多次尝试后能够成功通过 PR_Swap 测试

---

## 8. 最终根因判断

### 8.1 根因链路

```
SC27XX PD Controller PHY 层缺陷
    │
    ├─ PR_Swap Rd transition 后 BMC PHY 发送能力下降
    │   └─ 发送 PS_RDY 时始终触发 TX 错误 (int sts=0x40)
    │
    ├─ HW 内部 CRCReceiveTimer 重试耗尽 (~3ms)
    │   └─ 报告 TX 错误给驱动
    │
    ├─ 驱动 cleanup 路径 (~2.6ms, 固定)
    │   └─ ERROR_RECOVERY → PORT_RESET
    │
    └─ 总时间: HW(~3ms) + 驱动(~2.6ms) + 固件等待(?ms)
        │
        ├─ Aug 21: ~16ms → 超 tCtsErrorRecovery=15ms → FAIL
        └─ Aug 24/27: ~15ms → 不超限 → PASS
```

### 8.2 Aug 21 FAIL 的额外时间来源

驱动内部时间固定为 ~2.6ms，HW 重试约 ~3ms，合计 ~5.6ms。剩余 ~10ms 最可能来自：

1. **SC27XX 固件在 PR_Swap Rd transition 后的 BMC PHY 初始化等待**（Aug 21 固件版本可能有更长的等待时间）
2. **CC 线电气状态稳定等待**（从 Rp 驱动切换到 Rd 终端后，BMC 发送器需要重新建立偏置）

### 8.3 置信度评估

| 结论 | 置信度 | 依据 |
|------|:------:|------|
| PS_RDY TX 错误在所有 log 中出现 | 🔴 99% | 三份 log 的 int sts=0x40 记录 |
| 驱动 cleanup 路径一致 | 🔴 99% | 内部时间戳精确对比 |
| 修复在固件层 | 🟡 80% | 排除法：驱动层无差异 |
| 精确的额外时间来源 | 🟡 60% | 需要 SC27XX 固件源码确认 |

---

## 9. Phase 4 产物检查

| 产物 | 路径 | 状态 |
|------|------|:----:|
| Log 深度分析报告 | `04_log_analysis.md` | ✅ 当前文件 |
| 三份 Log 时序对比 | §2.2-2.3 | ✅ |
| PHY 层 int sts 分析 | §3 | ✅ |
| tCtsErrorRecovery 时间预算 | §4 | ✅ |
| Rev3ChkdSrc BU.1 分析 | §5 | ✅ |
| Phase 3 问题回答 | §6 | ✅ |
| 最终根因判断 | §8 | ✅ |

---

## 10. 未解问题（带入 Phase 5）

| # | 问题 | 优先级 |
|:--:|------|:------:|
| 1 | SC27XX PD Controller 固件在 Aug 21 和 Aug 24 之间的版本差异？ | 🔴 高 |
| 2 | 历史上是否有类似的 SC27XX TX 错误导致认证失败的案例？ | 🔴 高 |
| 3 | Aug 27 Rev3ChkdSrc 中 bq2560x OTG enable 是否被调用？ | 🟡 中 |
| 4 | PD 3.0 VIF 配置是否限制了 Rev3ChkdSrc 测试？ | 🟡 中 |

---

> **Phase 4 完成，进入 Phase 5（历史 Bug 参照）**

---

*分析工具: pd_auth_analyse v3.0 Phase 4*  
*数据来源: Aug 21/24/27 kernel log (0-kernel.log), tcpci 中断提取脚本 (find_tcpci.py)*  
*内部时间戳: sprd_pd_log 行内时间戳（格式: `[   XX.XXXXXX]`）*