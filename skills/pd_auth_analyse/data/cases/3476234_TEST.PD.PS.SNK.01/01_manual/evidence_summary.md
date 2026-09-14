# Bug 3476234 — 证据收集报告

> 本文档仅收集证据，不做根因分析。

## 一、测试项背景

**TEST.PD.PS.SNK.01** = "PDO Transitions As Sink"

测试目标：验证 Sink 设备能否正确响应 Source 广播的不同 PDO，及时发送 Request 完成功率转换。

关键检查点：
- Sink 收到 SourceCap 后须在 tSenderResponse（30ms）内发送 Request
- 不允许的 Hard_Reset 会被 CTS 判定为失败

## 二、证据检索结果

### 证据 1：Trace 协议交互记录

**来源**：workspace 中 `.usb` trace 文件（文件名含 FAIL）

**关键发现**（多个 Repeat 重复出现）：

| 现象 | 错误码/消息 |
|------|------------|
| UUT 成功发送 Request（初始协商正常） | — |
| UUT 违规发送 Hard_Reset | `Err# 0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal.` |
| UUT 未发送 Request | `[TEST.PD.PS.SNK.1#2] The UUT did not send a Request message.`<br>`[TEST.PD.PS.SNK.1#7] The UUT did not send a Request message.` |

**证据结论**：UUT 在某些 PDO 转换时无法及时发送 Request，导致触发违规 Hard_Reset。

---

### 证据 2：Patch 修复方案

**来源**：`Attachements/13f31c6.diff`（9.4 KB）

**Patch 信息**：
- **Commit**：`13f31c6b977ef821f7b5bbaea5601fc391703f12`
- **作者**：mazhuang1osc <72214320@bbktel.com>
- **日期**：2026-06-10

**Patch commit message**：
```
修改原因: POWER_SUPPLY_SET_PROPERTY时间超时
解决方法: 使用work进行规避
```

**修改的文件**：

| 文件 | 修改内容 |
|------|---------|
| `drivers/usb/typec/tcpm/sprd_tcpm.c` | `sprd_tcpm_set_cm_ic_limit_current()` 中将 `POWER_SUPPLY_SET_PROPERTY` 从同步调用改为 kthread worker 异步执行 |
| `drivers/power/supply/vchg/vivo-sgm41512_charger.c` | 删除 `sc8960x_set_dp()` / `sc8960x_set_dm()` 中的 `mdelay(5)`；添加 `em_authorized` 检查跳过 APSD 检测 |
| `include/linux/usb/sprd_tcpm.h` | 新增 `ic_limit_kworker` / `ic_limit_work` 等字段 |

**证据结论**：客户已提交修复方案，指向 `POWER_SUPPLY_SET_PROPERTY` 调用超时问题。

---

### 证据 3：参考代码对比

**来源**：UNISOC 主线代码 `F:\05_Code\UNISOC\...\sprd_tcpm.c`（第 172 行）

**主线代码**：
```c
static void sprd_tcpm_set_cm_ic_limit_current(enum sprd_pd_pdo_type pdo_type,
    int req_vol_uv, int req_cur_ua, bool enable_limit)
{
    if (g_sprd_charger_ops && g_sprd_charger_ops->negotiated_limit_current)
        g_sprd_charger_ops->negotiated_limit_current(pdo_type,
            req_vol_uv, req_cur_ua, enable_limit);
}
```

**证据结论**：主线代码中 `sprd_tcpm_set_cm_ic_limit_current()` 没有 `POWER_SUPPLY_SET_PROPERTY` 调用，该调用是客户定制代码添加的。

---

### 证据 4：Kernel Log（待补充）

**来源**：workspace 中 kernel_log 文件

**检索状态**：未在 kernel log 中找到明确的 PD 状态机阻塞证据。

**可能原因**：
- Kernel log 中 PD 相关日志可能使用不同的 tag
- 测试期间的 log 可能未完整捕获
- 需要进一步确认 log 的 tag 格式

---

## 三、证据汇总

| 证据类型 | 来源 | 关键信息 | 状态 |
|---------|------|---------|------|
| Trace 协议交互 | .usb trace 文件 | UUT 未发送 Request + 违规 Hard_Reset | 已确认 |
| Patch 修复方案 | 13f31c6.diff | POWER_SUPPLY_SET_PROPERTY 时间超时 | 已确认 |
| 参考代码对比 | UNISOC 主线 sprd_tcpm.c | 主线无 POWER_SUPPLY_SET_PROPERTY 调用 | 已确认 |
| Kernel Log | kernel_log 文件 | 未找到明确证据 | 待补充 |

## 四、待确认事项

1. Kernel log 中 PD 状态机的具体行为（需要确认 log tag 格式）
2. `POWER_SUPPLY_SET_PROPERTY` 的实际阻塞时间（需要 ftrace 或 printk 验证）
3. 客户代码中 `sprd_tcpm_set_cm_ic_limit_current()` 的完整实现（需要客户侧代码）
