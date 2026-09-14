# Phase 6: 代码级根因分析 — TEST.PD.PROT.SNK.12

**分析时间**: 2026-09-09

---

## 6.1 状态

**⏭️ 已跳过** — 未提供内核源码路径。

---

## 6.2 跳过原因

| 原因 | 说明 |
|------|------|
| 无内核源码路径 | 用户未提供 SPRDLINUX6.18 内核源码路径 |
| 无环境变量 | `PD_KERNEL_ROOT` 未设置 |

---

## 6.3 如需代码分析的排查建议

当内核源码可用时，按以下路径排查：

### 关键文件

```
drivers/usb/typec/tcpm/sprd_tcpm.c          — sprd_tcpm 状态机
drivers/usb/typec/tcpm/tcpm.c               — 通用 TCPM 状态机
drivers/mfd/sc27xx-typec.c                  — SC27xx Type-C 控制器驱动
drivers/mfd/sc27xx-typec-pd.c               — SC27xx PD PHY 驱动
```

### 关键函数

| 函数 | 文件 | 排查重点 |
|------|------|---------|
| `sc27xx_typec_pr_swap_no_chk_detach()` | sc27xx-typec.c | 是否过度禁用 CC 检测功能 |
| `sprd_tcpm_typec_pr_swap_no_chk_detach()` | sprd_tcpm.c | 状态机侧 CC 检测禁用 |
| `run_state_machine()` | tcpm.c | PR_SWAP_SNK_SRC_SINK_OFF 转换条件 |
| `tcpm_pr_swap_snk_src_sink_off_entry()` | sprd_tcpm.c | 进入 Sink Off 时的逻辑 |
| CC 中断处理函数 | sc27xx-typec.c | irq=78 的处理逻辑 |

### 排查问题

1. `sc27xx_typec_pr_swap_no_chk_detach(on=1)` 内部具体禁用了哪些功能？
   - 是否仅禁用 detach 检测？
   - 是否同时也禁用了 CC 状态变化事件？
   - 是否影响 CC 角色切换（Rd↔Rp）？

2. sprd_tcpm 状态机在 PR_SWAP_SNK_SRC_SINK_OFF 的转换条件是什么？
   - 是等待 CC 事件回调？
   - 是等待 VBUS 状态变化？
   - 是等待某个内部标志位？

3. CC 中断 (irq=78) 的触发条件是什么？
   - 为什么在 PD 3.0 模式下提前触发？
   - 为什么在 PD 2.0 模式下不触发？

---

*Phase 6 完成 | 2026-09-09 ⏭️ 已跳过（无源码）*