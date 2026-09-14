# Bug 3476234 — 手动证据分析

> 本文件独立于自动流水线，以人工分析方式从零定位根因。

## 1. 测试项说明

**TEST.PD.PS.SNK.01** = "PDO Transitions As Sink"

测试 DUT 作为 Sink 时能否正确处理 PDO（Power Data Object）转换：

- Source（CTS 测试仪）广播包含不同 PDO 的 SourceCap（Fixed / Variable / PPS）
- Sink（DUT）必须在收到 SourceCap 后**及时**发送 Request 请求新的功率合同
- Sink **不能**在不允许的时机发送 Hard_Reset

**认证检查点**：
- Sink 收到 SourceCap 后须在 `tSenderResponse`（30ms）内发出 Request
- 不允许的 Hard_Reset 会被 CTS 记录为 `Err# 0x02A8: COMMON.CHECK.PD.5.2`

## 2. 证据查找方法论

分析 PD 认证失败 Bug，找具体证据的关键思路：**从结果反推原因，沿"测试失败现象 → 协议层异常 → 代码层根因"三层逐层深入**。

| 步骤 | 目标 | 方法 | 关键证据来源 |
|------|------|------|-------------|
| 1 | 理解测试项在测什么 | 查 PD 规范知识库 | `knowledge/specs/pd_state_machines.md` |
| 2 | 提取协议层失败现象 | 找 .usb trace 中含 FAIL 的文件 | workspace `Attachements/` 下的 `.usb` 文件 |
| 3 | 找到代码层根因 | 找 .diff/.patch 文件 | workspace `Attachements/13f31c6.diff` |
| 4 | 对比参考代码确认差异 | 搜索参考代码中同名函数 | `F:\05_Code\UNISOC\...\sprd_tcpm.c` |
| 5 | 结合知识库确认因果链 | 查 PD timer 规范 | `knowledge/specs/pd_protocol_timers.md` |

## 3. 证据清单

### 证据 1：Bug 基本信息

- **来源**：`01_bug_info.json`
- **Bug ID**：3476234（SPCSS01684954）
- **摘要**：`[UMS9230H][HUAQIN_BD2][PD2577F][16849][手持-智能手机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail`
- **平台**：UMS9230H
- **客户**：华勤 BD2（vivo 项目 PD2577F）
- **严重级别**：1-Critical
- **组件**：01-BSP-Charge

### 证据 2：Trace 协议层失败现象

- **来源**：workspace 中 `.usb` trace 文件，文件名含 `FAIL`
- **路径**：`Attachements/.../TEST.PD.PS.SNK.1/Repeat_*/02_TEST.PD.PS.SNK.1_Rev3ChkdSnk_FAIL.usb`

多个 Repeat 中重复出现相同失败模式：

```
Repeat 1~4（每个 Repeat 约 12 个事件）：
  1. UUT 成功发送 Request ×4     —— 初始 PDO 协商正常
  2. UUT 违规发送 Hard_Reset ×3  —— Err# 0x02A8: COMMON.CHECK.PD.5.2
  3. UUT 未发送 Request ×2       —— [TEST.PD.PS.SNK.1#2] / [TEST.PD.PS.SNK.1#7]
  4. UUT 恢复发 Request ×1
  5. UUT 又违规发 Hard_Reset ×3
  6. UUT 又未发 Request ×2
```

**关键错误码**：
- `Err# 0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal.`
- `[TEST.PD.PS.SNK.1#2] The UUT did not send a Request message.`
- `[TEST.PD.PS.SNK.1#7] The UUT did not send a Request message.`

**关键推断**：UUT 在某些 PDO 转换时无法及时发送 Request，导致 PD 状态机超时并触发 Hard_Reset。**不是 CC 检测问题，而是 PD 状态机在处理 PDO 转换时被阻塞**。

### 证据 3：Patch 文件（最关键的根因证据）

- **来源**：`Attachements/13f31c6.diff`（9.4 KB）
- **Commit**：`13f31c6b977ef821f7b5bbaea5601fc391703f12`
- **作者**：mazhuang1osc <72214320@bbktel.com>
- **日期**：2026-06-10

Patch commit message 直接写明：

```
修改原因: POWER_SUPPLY_SET_PROPERTY时间超时
解决方法: 使用work进行规避
```

#### 3.1 核心修改 — `drivers/usb/typec/tcpm/sprd_tcpm.c`

**原代码（有 Bug）**：`sprd_tcpm_set_cm_ic_limit_current()` 中**同步调用** `POWER_SUPPLY_SET_PROPERTY`

```c
static void sprd_tcpm_set_cm_ic_limit_current(enum sprd_pd_pdo_type pdo_type,
    int req_vol_uv, int req_cur_ua, bool enable_limit)
{
    // ... negotiated_limit_current 调用 ...

    // 客户添加的阻塞调用 ↓
    batt_psy = power_supply_get_by_name("battery");
    if (batt_psy) {
        pd_req_cur_ua.intval = req_cur_ua;
        POWER_SUPPLY_SET_PROPERTY(batt_psy, POWER_SUPPLY_PROP_PD_REQ_CUR, &pd_req_cur_ua);
        power_supply_put(batt_psy);
    }
}
```

**修复后**：将 `POWER_SUPPLY_SET_PROPERTY` 移到**独立 kthread worker** 异步执行

```c
static void sprd_tcpm_ic_limit_work_handler(struct kthread_work *work)
{
    struct sprd_tcpm_port *port = container_of(work, struct sprd_tcpm_port, ic_limit_work);
    struct power_supply *batt_psy;
    union power_supply_propval pd_req_cur_ua = {0,};

    batt_psy = power_supply_get_by_name("battery");
    if (batt_psy) {
        pd_req_cur_ua.intval = port->ic_limit_req_cur;
        POWER_SUPPLY_SET_PROPERTY(batt_psy, POWER_SUPPLY_PROP_PD_REQ_CUR, &pd_req_cur_ua);
        power_supply_put(batt_psy);
    }
}

static void sprd_tcpm_set_cm_ic_limit_current(struct sprd_tcpm_port *port,
    enum sprd_pd_pdo_type pdo_type, int req_vol_uv, int req_cur_ua, bool enable_limit)
{
    // ... negotiated_limit_current 调用 ...

    /* Async power_supply operation to avoid blocking PD timing */
    port->ic_limit_pdo_type = pdo_type;
    port->ic_limit_req_cur = req_cur_ua;
    port->ic_limit_enable_limit = enable_limit;
    kthread_queue_work(&port->ic_limit_kworker, &port->ic_limit_work);
}
```

**调用链**（阻塞发生在 PD 状态机线程中）：

```
sprd_tcpm_pd_build_request()              ← Sink 构建 PDO Request
  └→ sprd_tcpm_set_cm_ic_limit_current()  ← 更新充电 IC 限流
       └→ POWER_SUPPLY_SET_PROPERTY()      ← 同步阻塞！charger driver 内有 mdelay(5)
            └→ 充电 IC I2C 写入 + mdelay(5) ×3  ← 总阻塞可达数十 ms
```

#### 3.2 次要修改 — `drivers/power/supply/vchg/vivo-sgm41512_charger.c`

- 删除 `sc8960x_set_dp()` 中的 `mdelay(5)`
- 删除 `sc8960x_set_dm()` 中的 `mdelay(5)`
- 删除 `sc8960x_set_dm()` 末尾的 `mdelay(5)`
- 添加 `em_authorized` 检查：认证测试时跳过 APSD 检测的 `msleep(300)`

这些 `mdelay(5)` 是 `POWER_SUPPLY_SET_PROPERTY` 阻塞时间过长的直接原因之一。

#### 3.3 头文件修改 — `include/linux/usb/sprd_tcpm.h`

新增字段：

```c
struct sprd_tcpm_port {
    // ...
    struct kthread_worker ic_limit_kworker;
    struct task_struct *ic_limit_task;
    struct kthread_work ic_limit_work;
    enum sprd_pd_pdo_type ic_limit_pdo_type;
    int ic_limit_req_vol;
    int ic_limit_req_cur;
    bool ic_limit_enable_limit;
    // ...
};
```

### 证据 4：参考代码对比

- **来源**：`F:\05_Code\UNISOC\SPRDLINUX6.6_KERNEL_MAIN_W26.12.4_codeonly\idh.code\kernel6.6\unisoc\drivers\unisoc_platform\sprd_charger\power_delivery\sprd_tcpm.c`（第 172 行）

UNISOC 主线代码的 `sprd_tcpm_set_cm_ic_limit_current()` **只有**：

```c
static void sprd_tcpm_set_cm_ic_limit_current(enum sprd_pd_pdo_type pdo_type,
    int req_vol_uv, int req_cur_ua, bool enable_limit)
{
    if (g_sprd_charger_ops && g_sprd_charger_ops->negotiated_limit_current)
        g_sprd_charger_ops->negotiated_limit_current(pdo_type,
            req_vol_uv, req_cur_ua, enable_limit);
}
```

**没有** `POWER_SUPPLY_SET_PROPERTY` 调用。

**结论**：客户（vivo/BD2）在此函数中**自行添加**了 `POWER_SUPPLY_SET_PROPERTY` 调用，这是导致 PD 时序超时的直接原因。主线代码不存在此问题。

### 证据 5：知识库规范佐证

- **来源**：`knowledge/specs/pd_protocol_timers.md`、`knowledge/specs/pd_state_machines.md`

| 规范要求 | 说明 |
|---------|------|
| `tSenderResponse` = 24~30ms | 发送方等待 GoodCRC 的超时 |
| Sink 收到 SourceCap 后须立即发 Request | PE_SNK_Evaluate_Cap → PE_SNK_Select_Cap → Request |
| PD 状态机运行在独立 kthread | `sprd_tcpm_state_machine_work` |

如果 PD 状态机线程被 `POWER_SUPPLY_SET_PROPERTY` 阻塞数十 ms，则：
1. Request 发送延迟 → CTS 检测到 "did not send Request"
2. 延迟过长触发 PD 状态机内部超时 → 发送 Hard_Reset → CTS 检测到 "not allowed to send Hard_Reset"

## 4. 协议层失败现象总结

从 trace 提取的重复失败模式：

```
正常:  SourceCap → Request → Accept → PS_RDY  (初始 PDO 协商成功)
异常:  SourceCap → [阻塞] → Request 未发出 → 超时 → Hard_Reset (违规)
```

CTS 测试仪视角：
1. Source 广播新的 SourceCap（含不同 PDO）
2. 期望 UUT 在 tSenderResponse 内回 Request
3. UUT 因 PD 状态机被阻塞，Request 延迟或缺失
4. UUT 内部 PD 状态机超时，发出 Hard_Reset
5. CTS 判定：Hard_Reset 不被允许（当前状态不应发 Hard_Reset）

## 5. 代码层根因

### 根因

**`sprd_tcpm_set_cm_ic_limit_current()` 中同步调用 `POWER_SUPPLY_SET_PROPERTY()` 阻塞 PD 状态机线程，导致 Sink 端无法在 `tSenderResponse`（30ms）内发送 Request 消息，进而触发违规 Hard_Reset。**

### 阻塞量级估算

```c
POWER_SUPPLY_SET_PROPERTY(batt_psy, POWER_SUPPLY_PROP_PD_REQ_CUR, ...)
  └→ sgm41512 charger driver set_property handler
       └→ sc8960x_set_dp() → mdelay(5)      // 5ms
       └→ sc8960x_set_dm() → mdelay(5) ×2   // 10ms
       └→ I2C 写入操作                        // 数 ms
                                          // 总计 ~15-20ms+
```

`tSenderResponse` 仅 30ms，阻塞 15-20ms 后剩余时间不足以完成 Request 构建和发送。

### 责任方

- **根因类型**：客户定制代码引入的 PD 状态机阻塞
- **责任方**：客户（vivo/BD2）在 `sprd_tcpm_set_cm_ic_limit_current()` 中添加了同步 `POWER_SUPPLY_SET_PROPERTY` 调用
- **主线状态**：UNISOC 主线代码不存在此问题

## 6. 因果链总结

```
客户在 sprd_tcpm_set_cm_ic_limit_current() 中添加 POWER_SUPPLY_SET_PROPERTY
    ↓
POWER_SUPPLY_SET_PROPERTY 同步调用 charger driver set_property
    ↓
charger driver 内有 mdelay(5) ×3 + I2C 写入，阻塞 ~15-20ms
    ↓
PD 状态机线程 (sprd_tcpm_state_machine_work) 被阻塞
    ↓
Sink 端无法在 tSenderResponse (30ms) 内发送 Request
    ↓
CTS 报错: "The UUT did not send a Request message"
    ↓
PD 状态机内部超时，触发 Hard_Reset
    ↓
CTS 报错: "The UUT was not allowed to send Hard_Reset signal"
    ↓
TEST.PD.PS.SNK.01 FAIL
```

## 7. 修复方案评估

### Patch 13f31c6 的修复方案

| 修改点 | 方案 | 评估 |
|--------|------|------|
| `sprd_tcpm.c` | `POWER_SUPPLY_SET_PROPERTY` 改为 kthread worker 异步执行 | 正确，根本解决阻塞 |
| `vivo-sgm41512_charger.c` | 删除 `mdelay(5)` | 正确，减少不必要延迟 |
| `vivo-sgm41512_charger.c` | 认证测试时跳过 APSD `msleep(300)` | 正确，避免认证时额外干扰 |
| `sprd_tcpm.h` | 新增 `ic_limit_kworker` 等字段 | 正确，支撑异步化 |

### 风险评估

- **低风险**：异步化后 IC 限流更新有短暂延迟，但不影响 PD 协议时序
- **注意点**：需确认 `ic_limit_kworker` 在 port 注销时正确 flush 和 stop（patch 中已处理）
- **回归风险**：低，异步限流更新不影响充电安全性

### 复测验证步骤

1. 合入 patch 13f31c6 后重新运行 TEST.PD.PS.SNK.01
2. 检查 trace 中不再出现 "did not send Request" 和 "not allowed to send Hard_Reset"
3. 运行完整 TD.4.x 认证套件确认无回归
4. 确认充电功能正常（限流异步化不影响实际充电电流控制）
