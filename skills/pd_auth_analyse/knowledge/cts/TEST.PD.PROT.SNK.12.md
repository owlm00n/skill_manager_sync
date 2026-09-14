# TEST.PD.PROT.SNK.12 — PR_Swap — PSSourceOffTimer Timeout

> **Case ID**: TEST.PD.PROT.SNK.12
> **来源**: USB PD 3.1 规范 Section 8.3.3 (PR_Swap State Machine) + Bug 3523391 实测数据
> **生成时间**: 2026-09-09
> **知识库**: 自学习生成

---

## 测试目的

验证 DUT 作为 Sink 接受 PR_Swap 后，能正确完成 Sink→Source 角色转换，tPSSourceOffTimer 不超时。

## 测试角色

- DUT: Sink (初始) → Source (PR_Swap 后)
- Tester: Source (初始) → Sink (PR_Swap 后)

## 前置条件

1. DUT 配置为 DRP 端口
2. Tester 配置为 Source，提供 5V VBUS
3. PD 协议协商完成，DUT 处于 PE_SNK_Ready 状态

## 测试步骤

### Rev2Snk (PD 2.0)

| 子项 | 测试内容 | 判定标准 |
|------|---------|---------|
| COMMON.PROC.BU.2#1 | PD 2.0 基础通信 | GoodCRC 正常响应 |
| SNK.12#1 | PR_Swap Sink→Source | tPSSourceOffTimer 不超时 |
| SNK.12#2 | PR_Swap 后 Source→Sink 回切 | 正常回切 |

### Rev3ChkdSnk (PD 3.0)

| 子项 | 测试内容 | 判定标准 |
|------|---------|---------|
| SNK.12 | PR_Swap Sink→Source (PD 3.0) | tPSSourceOffTimer 不超时，DUT 发送 PS_RDY |

## PR_Swap Sink→Source 状态机序列

```
PE_SNK_Ready
  → (收到 PR_Swap) → PE_PRS_SNK_SRC_Evaluate_Swap
  → (接受) → PE_PRS_SNK_SRC_Accept_Swap
  → (发送 Accept) → PE_PRS_SNK_SRC_Transition_to_off
  → (关闭 Sink, 切换 CC→Rp) → PE_PRS_SNK_SRC_Assert_Rp
  → (开启 Source VBUS) → PE_PRS_SNK_SRC_Source_on
  → (发送 PS_RDY) → PE_SRC_Send_PS_RDY
  → PE_SRC_Ready
```

## 关键 Timer

| Timer | 值 | 说明 |
|-------|-----|------|
| tPSSourceOff | 835ms (750-920ms) | 等待旧 Source 关闭 VBUS 的超时 |
| tPSSourceOn | 435ms (390-480ms) | 新 Source 开启 VBUS 后的稳定时间 |

## 常见失败模式

| 模式 | 现象 | 根因方向 |
|------|------|---------|
| **CC 检测禁用导致状态机阻塞** | tPSSourceOffTimer 超时 | sc27xx_typec_pr_swap_no_chk_detach 过度禁用 CC 检测 |
| CC 线切换失败 | CC 线未从 Rd 切换到 Rp | 外部 CC LOGIC 芯片未正确响应 |
| PD 消息丢失 | DUT 未收到 PS_RDY | PD PHY 层 RX 异常 |
| VBUS 控制异常 | Source VBUS 无法开启 | Charger IC 调压失败 |

## 已知 Bug 参考

| Bug ID | 平台 | 现象 | 修复 |
|--------|------|------|------|
| 3523391 | UMS512 | PD 3.0 PR_Swap 失败，PD 2.0 通过 | 待修复 |

---

*知识库文件 | 自动生成 2026-09-09*