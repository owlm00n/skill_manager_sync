# Phase 2: 测试用例说明 & 失败点定位 — TEST.PD.PROT.SNK.12

**分析时间**: 2026-09-09

---

## 2.1 测试项说明

| 属性 | 值 |
|------|-----|
| **Case ID** | TEST.PD.PROT.SNK.12 |
| **测试名称** | PR_Swap — PSSourceOffTimer Timeout |
| **测试目的** | 验证 DUT 作为 Sink 接受 PR_Swap 后，能正确完成 Sink→Source 角色转换 |
| **判定标准** | tPSSourceOffTimer 不超时，DUT 成功变为 Source 并发送 PS_RDY |
| **CTS 规范** | USB PD CTS Q4 2024 RC1 |
| **测试角色** | DUT = Sink (初始), Tester = Source (初始) |

---

## 2.2 测试步骤序列（根据 PD 3.1 规范生成）

> **说明**: 知识库 `knowledge/cts/` 中无 `TEST.PD.PROT.SNK.12.md`，以下流程根据 PD 3.1 规范 PR_Swap 状态机生成。
> **来源**: USB PD 3.1 Spec Section 8.3.3 (PR_Swap State Machine) + `knowledge/specs/pd_state_machines.md`

### 测试前置条件

1. DUT 配置为 DRP 端口，初始角色为 Sink
2. Tester 配置为 Source，提供 5V VBUS
3. DUT 与 Tester 通过 Type-C 线缆连接
4. PD 协议协商完成，DUT 处于 **PE_SNK_Ready** 状态
5. PD 协议版本：PD 3.0 (Rev3ChkdSnk)

### PR_Swap Sink→Source 测试步骤

| 步骤 | 状态机状态 | DUT 动作 | Tester 动作 | 预期结果 |
|:----:|-----------|---------|------------|---------|
| **1** | PE_SNK_Ready | 等待消息 | 发送 PR_Swap 消息 | DUT 收到 PR_Swap |
| **2** | PE_PRS_SNK_SRC_Evaluate_Swap | 评估 PR_Swap 请求 | 等待 Accept | DUT 决定接受 PR_Swap |
| **3** | PE_PRS_SNK_SRC_Accept_Swap | 发送 Accept 消息 | 收到 Accept | Accept 发送成功 |
| **4** | PE_PRS_SNK_SRC_Transition_to_off | 关闭 Sink 电源路径 | 关闭 VBUS Source | DUT 进入 Sink Off 状态 |
| **5** | PE_PRS_SNK_SRC_Assert_Rp | **切换 CC 线从 Rd→Rp** | 切换 CC 线从 Rp→Rd | 🔴 **关键步骤** |
| **6** | PE_PRS_SNK_SRC_Source_on | 开启 VBUS Source (5V) | 检测 VBUS | DUT 成为 Source |
| **7** | PE_SRC_Send_PS_RDY | 发送 PS_RDY 消息 | 收到 PS_RDY | PR_Swap 完成 |
| **8** | PE_SRC_Ready | 作为 Source 正常运行 | 作为 Sink 正常运行 | 测试通过 |

### PSSourceOffTimer 说明

| 参数 | 值 | 说明 |
|------|-----|------|
| **Timer 名称** | tPSSourceOff | PR_Swap Source Off Timer |
| **典型值** | 835 ms | 规范规定值 |
| **范围** | 750–920 ms | 允许范围 |
| **启动时机** | 进入 PE_PRS_SNK_SRC_Transition_to_off | DUT 关闭 Sink 后 |
| **停止条件** | DUT 检测到 VBUS 关闭 + CC 线切换完成 | 正常转换 |
| **超时后果** | → ERROR_RECOVERY | 测试失败 |

**来源**: `knowledge/specs/pd_protocol_timers.md` (tPSSourceOffTimer 章节)

---

## 2.3 失败点定位

### Lecroy 报告 FAIL 判定

**来源**: `Teledyne LeCroy USB Compliance Result__UNISOC-P610F01-1.0.html`

```
TEST.PD.PROT.SNK.12: FAIL
├─ Rev2Snk: PASS
│   ├─ COMMON.PROC.BU.2#1: ✅
│   ├─ SNK.12#1: ✅
│   └─ SNK.12#2: ✅
└─ Rev3ChkdSnk: FAIL
    └─ "Test scenario aborted. Please check the trace file to determine the cause."
```

### 失败步骤定位

| 定位维度 | 结果 |
|----------|------|
| **失败步骤** | **步骤 4→5 转换失败** (PE_PRS_SNK_SRC_Transition_to_off → PE_PRS_SNK_SRC_Assert_Rp) |
| **失败类型** | **tPSSourceOffTimer 超时** (835ms 后触发 ERROR_RECOVERY) |
| **直接表现** | DUT 关闭 VBUS 后，无法完成 CC 线从 Rd→Rp 的切换，状态机卡在 PR_SWAP_SNK_SRC_SINK_OFF 状态 |
| **Tester 观察** | Tester 在 PR_Swap Accept 后未收到 DUT 的 PS_RDY，测试场景中止 |

### 失败上下文（Kernel Log 时间线）

| 时间 (s) | 事件 | 说明 |
|----------|------|------|
| 88.232 | `sc27xx_typec_pr_swap_no_chk_detach, on = 1` | **CC 检测禁用**，触发于 CC 中断 (irq=78) |
| 88.262 | RX: PR_Swap header 0x76a | 收到 PR_Swap 消息 |
| 88.262 | SNK_READY → PR_SWAP_ACCEPT | 状态机进入 PR_SWAP_ACCEPT |
| 88.274 | TX: Accept header 0x243, status: 0 ✅ | Accept 发送成功 |
| 88.280 | PR_SWAP_ACCEPT → PR_SWAP_START | 开始角色交换 |
| 88.285 | **PR_SWAP_START → PR_SWAP_SNK_SRC_SINK_OFF** | **进入 Sink Off 状态** |
| 88.287 | ⏰ `pending: → ERROR_RECOVERY @ 835 ms` | **PSSourceOffTimer 启动** |
| 88.304 | `sc27xx_pd_extcon_vbus_change_event, vbus_online: 0` | VBUS 确认关闭 |
| 89.072 | ⏰ **835ms 超时! → ERROR_RECOVERY** | **🔴 故障触发** |

**来源**: `0-kernel.log` lines 11035-11389

### 关键观察

1. **CC 检测在 PR_Swap 消息到达前就被禁用**: `sc27xx_typec_pr_swap_no_chk_detach, on = 1` 在 88.232s 触发（由 CC 检测中断 irq=78 触发），而 PR_Swap 消息在 88.262s 才收到
2. **VBUS 成功关闭**: 88.304s 确认 VBUS=0，但状态机仍无法完成转换
3. **无 CC 线切换日志**: 在整个 PR_SWAP_SNK_SRC_SINK_OFF 期间，没有任何 CC 线角色切换（Rd→Rp）的日志
4. **835ms 定时器到期**: 状态机在 PR_SWAP_SNK_SRC_SINK_OFF 状态停留满 835ms 后强制进入 ERROR_RECOVERY

---

## 2.4 失败模式总结

```
PR_Swap 正常流程:
  Accept → SinkOff → [CC线Rd→Rp] → SourceOn → PS_RDY → Ready

PR_Swap 实际流程 (Bug 3523391):
  Accept → SinkOff → [CC检测被禁用] → ⏰835ms超时 → ERROR_RECOVERY ❌
```

**根因方向**: sprd_tcpm 状态机在 PR_SWAP_SNK_SRC_SINK_OFF 状态下，需要 CC 线状态变化事件来触发向 PE_PRS_SNK_SRC_Assert_Rp 的转换。但 `sc27xx_typec_pr_swap_no_chk_detach(on=1)` 禁用了 CC 检测，导致状态机永远无法收到转换条件满足的信号。

---

*Phase 2 完成 | 2026-09-09*
*知识库自学习产出: 已生成 `knowledge/cts/TEST.PD.PROT.SNK.12.md`*