# PD协议状态机关键行为 (PD R3.2 Chapter 6)

## 概述
本文档整理PD R3.2规范第6章中PD Policy Engine和Protocol Layer的状态机关键行为，用于排查状态机实现缺陷。

## 1. Policy Engine状态机

### PE_SRC (Source模式) 关键状态

```
PE_SRC_Startup → PE_SRC_Discovery (CC检测)
  → PE_SRC_Send_Source_Cap (发送能力)
    → PE_SRC_Negotiate_Cap (协商)
      → PE_SRC_Ready (稳定供电)
```

**Source端状态转换要求**:
- CC连接检测 (PE_SRC_Discovery): 必须在tCCDebounce (100-200ms) 内完成
- SourceCap发送 (PE_SRC_Send_Source_Cap): 必须在tTypeCSendSourceCap (50-100ms) 内发起
- 收到Request后必须立即停止SourceCap重发
- Accept必须以tSenderResponse内发出

### PE_SNK (Sink模式) 关键状态

```
PE_SNK_Startup → PE_SNK_Discovery (CC检测)
  → PE_SNK_Wait_for_Cap (等待SourceCap)
    → PE_SNK_Evaluate_Cap (评估能力)
      → PE_SNK_Select_Cap (选择/Request)
        → PE_SNK_Ready (稳定供电)
```

**Sink端状态转换要求**:
- 等待SourceCap: tTypeCSinkWaitCap (max 310ms), 超时则Hard Reset
- Request发送: 评估能力后立即发出
- 等待PS_RDY: tPSTransition (max 550ms)

## 2. Protocol Layer状态机

### PHY层消息收发状态

```
PHY_Idle ←→ PHY_SOP (消息开始检测)
  → PHY_Message (接收消息)
    → PHY_EOP (消息结束检测)
      → PHY_CRC (CRC校验)
        → PHY_Send_GoodCRC / PHY_Receive_GoodCRC
```

**关键约束**:
- GoodCRC必须在tReceiverResponse (15ms) 内回复
- CRC错误不回复GoodCRC, 进入丢弃流程

### 重发机制 (Retry)

| 场景 | 重试策略 |
|------|---------|
| GoodCRC超时 (tSenderResponse) | 最多2次重试, 间隔无要求 |
| No_Response | 立即重发, 最多1次 |
| 连续3次失败 | 触发Error Recovery |

## 3. Type-C Connection状态机

```
Unattached.SNK ←→ AttachWait.SNK ←→ Attached.SNK
Unattached.SRC ←→ AttachWait.SRC ←→ Attached.SRC
Attached.SNK ←→ Attached.SRC (PR_Swap后)
```

**状态转换时序**:
- Unattached → AttachWait: CC引脚检测到对端Rp/Rd
- AttachWait → Attached: tCCDebounce (100-200ms) 稳定后
- Attached → Unattached: CC断开, tPDDebounce (10-30ms) 后

## 4. PR_Swap状态机

```
SRC_Ready → PR_Swap_SNK_SRC_Transition
  → (旧Source关Vbus, 新Source开Vbus)
    → Vbus达到vSafe5V
      → PE_SRC_Send_Source_Cap (角色交换完成)
```

**关键约束**:
- tSwapSourceStart: max 22ms (Accept后到开始Vbus转换)
- tPSSourceOff: max 920ms (旧Source Vbus→0V)
- tPSSourceOn: max 400ms (新Source Vbus→5V)
- 必须有Vbus drain机制确保快速放电

## 5. DR_Swap状态机

```
SRC_Ready → DR_Swap_DFP_UFP_Transition
  → Data Role交换 (USB Host ↔ Device)
    → 新的DFP/UFP状态确认
```

**关键约束**:
- DR_Swap不涉及Vbus变化
- 必须等待USB数据通道重新枚举
- DR_Swap期间不停止PD消息处理

## 6. Error Recovery状态机

```
Error Recovery → Hard Reset → tHardResetComplete (25-50ms)
  → tCCDebounce (100-200ms) → re-attach
    → re-send SourceCap
```

**触发条件**:
- 连续GoodCRC超时
- 消息格式错误无法恢复
- 状态机卡死超时
- CC逻辑异常

## 7. VConn控制状态机 (PD 3.2新增)

VConn Source负责给Cable/Plug供电 (5V, max 1W), VConn Swap允许交换VConn供电角色。

```
VConn_SRC → VConn Swap Request
  → tVConnSwap (4ms)内切换
    → 旧VConn Source: tVConnSourceOff (2ms)关断
    → 新VConn Source: tVConnSourceOn (2ms)开启
```

## 常见状态机实现缺陷

| 缺陷 | 表现 | 影响 |
|------|------|------|
| PR_Swap后状态未切换到SNK | SinkCap不发送 | PR_Swap测试失败 |
| Error Recovery未重置timer | Hard Reset超时 | 无法恢复通信 |
| Vbus Drain未使能 | tPSSourceOff超2s | PR_Swap CTS失败 |
| CC Debounce状态未清除 | 重复CC检测 | SourceCap发送延迟 |
| 状态机锁死无超时退出 | 永久卡在中间状态 | 需物理重连 |
