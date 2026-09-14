# Phase 6: 代码级根因分析 — TEST.PD.PROT.SRC3.01

**分析时间**: 2026-08-31
**Case ID**: TEST.PD.PROT.SRC3.01
**数据来源**: Bug 3523357 Comment #17 (Xianjun.Zeng), Phase 2-4 分析结论

> ⚠️ **限制说明**: 未提供内核源码路径，以下分析基于 Bug 评论中的修复方案和 Phase 2-4 的分析结论。代码路径和函数名来自 Bug 3523357 Comment #17。

---

## 1. 根因结论

**根因**: SC27XX PD 控制器硬件 TX 自动重试机制 (`SC27XX_PD_AUTO_RETRY = BIT(0)`) 在未收到 GoodCRC 时，以 ~1-2ms 间隔自动重传 Source Capabilities 消息。软件层面每个 TX 周期只有一次发送，但硬件在 CC 线上产生 4 条消息（1 次发送 + 3 次硬件重试）。测试仪将这 4 条消息计为独立的消息 1-4，导致消息 3→4 间隔仅 ~1-2ms，违反 PD 规范要求的 ≥100.9ms。

**置信度**: 95%

---

## 2. 涉及文件

| 文件 | 修改类型 | 说明 |
|------|:---:|------|
| `drivers/usb/typec/tcpm/sc27xx_pd.c` | 修改 | 提供 `enable_tx_auto_retry` 回调实现 |
| `drivers/usb/typec/tcpm/sprd_tcpm.c` | 修改 | 6 个状态点调用 `enable_tx_auto_retry(false)` |
| `drivers/usb/typec/sc27xx_typec.c` | 修改 | Type-C 驱动层适配 |
| `drivers/usb/musb/musb_sprd.c` | 修改 | USB 驱动层适配 |
| `include/linux/usb/sprd_pd.h` | 修改 | 头文件接口声明 |
| DTS 文件 | 修改 | 设备树配置 |

---

## 3. 硬件机制分析

### 3.1 SC27XX_PD_CFG1 寄存器

```
SC27XX_PD_CFG1 寄存器:
  BIT(0): SC27XX_PD_AUTO_RETRY — 硬件 TX 自动重试使能
    0 = 禁用，仅发送一次，由软件控制重试
    1 = 使能，硬件在未收到 GoodCRC 时自动重传（~1-2ms 间隔）
```

### 3.2 硬件自动重试行为

```
软件发起 TX
  → SC27XX PD Controller 发送消息
  → 等待 GoodCRC (tReceive = 0.9-1.1ms)
  → 未收到 GoodCRC
  → [SC27XX_PD_AUTO_RETRY=1] 硬件自动重发 (~1-2ms 后)
  → 等待 GoodCRC
  → 未收到 GoodCRC
  → [SC27XX_PD_AUTO_RETRY=1] 硬件自动重发 (~1-2ms 后)
  → 等待 GoodCRC
  → 未收到 GoodCRC
  → [SC27XX_PD_AUTO_RETRY=1] 硬件自动重发 (~1-2ms 后)
  → TX 完成中断 (int sts=0x40, status=2)
```

**结果**: 一次软件 TX 在 CC 线上产生 4 条消息，间隔仅 ~1-2ms。

### 3.3 为什么仅禁用 `enable_tx_auto_retry` 而非 `check_tx_goodcrc`

- `check_tx_goodcrc`: 控制 GoodCRC 检查逻辑，影响接收路径
- `enable_tx_auto_retry`: 仅控制 TX 侧的硬件自动重试
- 修复是**无条件**的 — 在所有 Source 发送场景下禁用硬件自动重试
- 软件重试机制（`SPRD_PD_T_SEND_SOURCE_CAP = 150ms`）替代硬件自动重试

---

## 4. 修复方案

### 4.1 核心思路

在所有 Source 角色发送 Source Capabilities 的场景下，调用 `enable_tx_auto_retry(false)` 禁用硬件自动重试。

### 4.2 6 个 Fix Point

| # | 位置 | 状态/函数 | 说明 |
|:---:|------|------|------|
| 1 | `sprd_tcpm.c` | `SRC_READY` 状态进入 | 初始发送前禁用硬件重试 |
| 2 | `sprd_tcpm.c` | `SRC_SEND_CAPABILITIES` 状态进入 | 发送 Source Capabilities 前禁用 |
| 3 | `sprd_tcpm.c` | `HARD_RESET_SEND` 状态进入 | Hard Reset 发送前禁用 |
| 4 | `sprd_tcpm.c` | `SRC_SEND_CAPABILITIES` 重试路径 | 150ms 重试前禁用 |
| 5 | `sprd_tcpm.c` | `sprd_hard_reset_state` 函数 | Hard Reset 状态处理 |
| 6 | `sprd_tcpm.c` | `sprd_tcpm_reset_port` 函数 | 端口复位时禁用 |

### 4.3 概念性代码修改

#### sc27xx_pd.c — 回调实现

```c
// 在 sc27xx_pd.c 中实现 enable_tx_auto_retry 回调
static int sc27xx_pd_enable_tx_auto_retry(struct tcpc_dev *tcpc, bool enable)
{
    struct sc27xx_pd *pd = tcpc_to_sc27xx_pd(tcpc);
    unsigned int val = enable ? SC27XX_PD_AUTO_RETRY : 0;

    return regmap_update_bits(pd->regmap, SC27XX_PD_CFG1,
                              SC27XX_PD_AUTO_RETRY, val);
}
```

#### sprd_tcpm.c — 6 个调用点

```c
// Fix point 1: SRC_READY 状态进入
case SRC_READY:
    tcpm_pd_transmit(tcpm, ...); // 或类似函数
    break;

// 修改为:
case SRC_READY:
    if (tcpm->tcpc->enable_tx_auto_retry)
        tcpm->tcpc->enable_tx_auto_retry(tcpm->tcpc, false);
    tcpm_pd_transmit(tcpm, ...);
    break;

// Fix point 2-6: 类似地在其他 5 个位置添加
```

### 4.4 修复后预期行为

```
修复前 (硬件重试):
  [Msg1]─1ms─[Msg2]─1ms─[Msg3]─1ms─[Msg4] ─150ms─ [Msg5]─1ms─[Msg6]─1ms─[Msg7]─1ms─[Msg8]
   ↑ 同一软件 TX，4 次硬件重传                     ↑ 下一个软件 TX

修复后 (仅软件重试):
  [Msg1] ─150ms─ [Msg2] ─150ms─ [Msg3] ─150ms─ [Msg4] ─150ms─ [Msg5]
   ↑ 一次软件 TX，无硬件重试

步骤 5c 检查: 消息 3→4 间隔 = 150ms
要求: ≥ 100.9ms 且 ≤ 201.1ms
结果: PASS ✅
```

---

## 5. 验证方法

### 5.1 复测步骤

1. 合入修复代码，编译烧录
2. 使用 LeCroy Voyager M310e 运行 TEST.PD.PROT.SRC3.01
3. 确认步骤 5c PASS
4. 获取 Lecroy .usb trace 文件，确认 CC 线上消息间隔符合规范

### 5.2 Kernel Log 验证

修复后预期日志变化：
- `int sts = 0x40` 仍然出现（TX 完成中断）
- `status: 2` 仍然出现（测试仪不回复 GoodCRC）
- 但 CC 线上只有 1 条消息/TX 周期（无硬件重试）

### 5.3 回归测试

| 测试项 | 说明 |
|------|------|
| TEST.PD.PROT.SRC3.01 | 原失败测试项 |
| TEST.PD.PROT.SRC3.02 | SenderResponseTimer Timeout（相关） |
| COMMON.CHECK.PD.3 | GoodCRC 检查 |
| 充电兼容性 | 确认禁用硬件重试不影响正常充电协商 |

---

*Phase 6 完成 | 产物: `06_code_root_cause.md` | 下一步: SUMMARY.html*

> **数据来源声明**：
> - 修复方案：Bug 3523357 Comment #17 (Xianjun.Zeng, 2026-08-31)
> - 硬件分析：Bug 3523357 Comment #11 (Ke.Wang1, 2026-08-26)
> - 代码路径：Bug 3523357 Comment #17 中列出的修改文件列表
> - 注：未提供内核源码路径，代码级分析基于 Bug 评论中的描述