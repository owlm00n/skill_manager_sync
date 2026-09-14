# PD 协议状态机

> 来源: `USB_PD_R3_2 V1.0 2023-10.pdf`, Section 6.12 (Protocol Layer) & Section 8.3.3 (Policy Engine)
> 
> 提取日期: 2026-07-28

---

## 概述

USB PD 协议定义了两层状态机：
1. **Protocol Layer State Machines** (Section 6.12) — 协议层，负责消息的发送/接收
2. **Policy Engine State Machines** (Section 8.3.3) — 策略引擎，负责 USB PD 策略决策

---

## 一、Protocol Layer 状态机 (Section 6.12)

### 1.1 架构

Protocol Layer 为每种 SOP* 通信类型维护独立的实例：
- 每个 SOP* 通信方向有独立的 Tx/Rx 状态机
- 每个实例有独立的 Counter 和 Timer
- Hard Reset 同时应用于所有实例
- Soft Reset 仅应用于目标 SOP* 类型的实例

### 1.2 通用 Message Transmission 状态机 (Section 6.12.2.2.1)

```
PRL_Tx_PHY_Layer_Reset  →  PRL_Tx_Wait_for_Message_Request
                                        ↓
                              PRL_Tx_Layer_Reset_for_Transmit
                                        ↓
                              PRL_Tx_Construct_Message
                                        ↓
                              PRL_Tx_Wait_for_PHY_Response
                                        ↓
                              PRL_Tx_Match_MessageID
                                        ↓
                              PRL_Tx_Message_Sent
```

**关键状态说明:**

| 状态 | 说明 |
|------|------|
| PRL_Tx_PHY_Layer_Reset | 物理层复位后发送端初始化 |
| PRL_Tx_Wait_for_Message_Request | 等待策略引擎请求发送消息 |
| PRL_Tx_Layer_Reset_for_Transmit | 在发送前复位 MessageID 计数器（Soft/Hard Reset 后） |
| PRL_Tx_Construct_Message | 构造消息（Header + Data + CRC） |
| PRL_Tx_Wait_for_PHY_Response | 等待 PHY 层发送完成，监控 GoodCRC |
| PRL_Tx_Match_MessageID | 验证 GoodCRC 的 MessageID 匹配 |
| PRL_Tx_Message_Sent | 通知 Policy Engine 消息已发送 |
| PRL_Tx_Check_RetryCounter | 检查重试次数，超限则触发 Soft Reset |
| PRL_Tx_Transmission_Error | 传输错误，重试或上报 |
| PRL_Tx_Discard_Message | 丢弃消息 |

### 1.3 Source Protocol Layer 额外状态 (Section 6.12.2.2.2)

| 状态 | 说明 |
|------|------|
| PRL_Tx_Src_Sink_Tx | Sink 正在发送，Source 等待 |
| PRL_Tx_Src_Source_Tx | Source 自己发送 |
| PRL_Tx_Src_Pending | 等待发送机会 |

### 1.4 Sink Protocol Layer 额外状态 (Section 6.12.2.2.3)

| 状态 | 说明 |
|------|------|
| PRL_Tx_Snk_Start_of_AMS | Sink 发起 AMS，检查 SinkTxOk |
| PRL_Tx_Snk_Pending | 等待 Source 允许发送 |

### 1.5 Message Reception 状态机 (Section 6.12.2.3)

```
PRL_Rx_Wait_for_PHY_Message
            ↓ (收到消息)
PRL_Rx_Layer_Reset_for_Receive
            ↓
PRL_Rx_Send_GoodCRC          ← CRCReceiveTimer 启动
            ↓
PRL_Rx_Check_MessageID
            ↓
PRL_Rx_Store_MessageID
            ↓
   (传递给 Policy Engine)
```

### 1.6 Hard Reset 状态机 (Section 6.12.2.4)

| 状态 | 说明 |
|------|------|
| PRL_HR_Reset_Layer | 复位所有 Protocol Layer 实例 |
| PRL_HR_Indicate_Hard_Reset | 通知 Policy Engine 发生 Hard Reset |

### 1.7 Chunking 状态机 (Section 6.12.2.1)

| 状态机 | 状态数 | 说明 |
|--------|--------|------|
| Chunked Rx | 6 状态 | RCH_* 接收端分块处理 |
| Chunked Tx | 10 状态 | TCH_* 发送端分块处理 |
| Chunked Message Router | 4 状态 | RTR_* Chunk 请求/响应路由 |

---

## 二、Policy Engine 状态机 (Section 8.3.3)

### 2.1 SenderResponseTimer 状态机 (Section 8.3.3.1.1)

通用的请求-响应超时管理，Source 和 Sink 共用。

| 状态 | 说明 |
|------|------|
| SRT_Stopped | Timer 未启动 |
| SRT_Running | Timer 运行中，等待响应 |
| SRT_Expired | Timer 超时，通知 Policy Engine |

---

### 2.2 Source Port 状态机 (Section 8.3.3.2)

```
PE_SRC_Startup
      ↓
PE_SRC_Discovery              ← SourceCapabilityTimer 运行
      ↓ (Timer 到期, CapsCounter ≤ nCapsCount)
PE_SRC_Send_Capabilities      ← 发送 Source_Capabilities
      ↓ (收到 Request)
PE_SRC_Negotiate_Capability   ← 评估 Request
      ↓ (Accept)
PE_SRC_Transition_Supply      ← PSTransitionTimer 启动
      ↓ (PS_RDY 发送)
PE_SRC_Ready                  ← 稳定供电
```

**Source 状态清单:**

| 状态 | 说明 | 关键动作 |
|------|------|---------|
| PE_SRC_Startup | 初始状态 | 初始化变量 |
| PE_SRC_Discovery | 发现阶段 | 启动 SourceCapabilityTimer (tTypeCSendSourceCap) |
| PE_SRC_Send_Capabilities | 发送能力 | 发送 Source_Capabilities，CapsCounter++ |
| PE_SRC_Negotiate_Capability | 协商能力 | 评估 Request，检查 PDO 匹配 |
| PE_SRC_Transition_Supply | 电源转换 | 调整 VBUS，启动 PSTransitionTimer |
| PE_SRC_Ready | 就绪 | 稳定供电，响应 Ping/Get_Source_Cap |
| PE_SRC_Disabled | 禁用 | 不响应任何消息 |
| PE_SRC_Capability_Response | 响应能力查询 | 响应 Get_Source_Cap |
| PE_SRC_Hard_Reset | 硬复位 | 请求 Hard Reset Signaling |
| PE_SRC_Hard_Reset_Received | 收到硬复位 | 处理 Hard Reset 后恢复 |
| PE_SRC_Transition_to_default | 转换到默认 | 返回 vSafe5V |
| PE_SRC_Get_Sink_Cap | 获取 Sink 能力 | 发送 Get_Sink_Cap |
| PE_SRC_Wait_New_Capabilities | 等待新能力 | 等待能力变更 |
| PE_SRC_EPR_Keep_Alive | EPR 保活 | 发送 EPR_KeepAlive_Ack |
| PE_SRC_Give_Source_Cap | 提供能力 | 响应 Get_Source_Cap |

---

### 2.3 Sink Port 状态机 (Section 8.3.3.3)

```
PE_SNK_Startup
      ↓
PE_SNK_Discovery              ← 等待 VBUS 稳定
      ↓
PE_SNK_Wait_for_Capabilities  ← SinkWaitCapTimer 启动 (tTypeCSinkWaitCap)
      ↓ (收到 Source_Capabilities)
PE_SNK_Evaluate_Capability    ← 评估 PDO
      ↓ (选择 PDO)
PE_SNK_Select_Capability      ← 发送 Request
      ↓ (收到 Accept)
PE_SNK_Transition_Sink        ← 等待 PS_RDY
      ↓ (收到 PS_RDY)
PE_SNK_Ready                  ← 稳定工作
```

**Sink 状态清单:**

| 状态 | 说明 | 关键动作 |
|------|------|---------|
| PE_SNK_Startup | 初始状态 | 初始化变量 |
| PE_SNK_Discovery | 发现阶段 | 等待 VBUS 稳定 |
| PE_SNK_Wait_for_Capabilities | 等待能力 | 启动 SinkWaitCapTimer |
| PE_SNK_Evaluate_Capability | 评估能力 | 解析 PDO，评估匹配 |
| PE_SNK_Select_Capability | 选择能力 | 发送 Request |
| PE_SNK_Transition_Sink | 转换中 | 等待 PS_RDY |
| PE_SNK_Ready | 就绪 | 正常工作，响应消息 |
| PE_SNK_Hard_Reset | 硬复位 | 触发 Hard Reset |
| PE_SNK_Transition_to_default | 回默认 | 返回安全状态 |
| PE_SNK_Give_Sink_Cap | 提供能力 | 响应 Get_Sink_Cap |
| PE_SNK_EPR_Keep_Alive | EPR 保活 | 发送 EPR_KeepAlive |
| PE_SNK_Get_Source_Cap | 请求能力 | 发送 Get_Source_Cap |

---

### 2.4 Soft Reset 状态机 (Section 8.3.3.4)

**Source Port:**

| 状态 | 说明 |
|------|------|
| PE_SRC_Send_Soft_Reset | 发送 Soft_Reset Message |
| PE_SRC_Soft_Reset | 等待 Accept（超时 tProtErrHardReset → Hard Reset） |

**Sink Port:**

| 状态 | 说明 |
|------|------|
| PE_SNK_Send_Soft_Reset | 发送 Soft_Reset Message |
| PE_SNK_Soft_Reset | 等待 Accept |

---

### 2.5 Data Reset 状态机 (Section 8.3.3.5)

**DFP Initiated:**

| 状态 | 说明 |
|------|------|
| PE_DDR_Send_Data_Reset | DFP 发送 Data_Reset |
| PE_DDR_Data_Reset_Received | 收到响应 |
| PE_DDR_Wait_For_VCONN_Off | 等待 VCONN 放电 |
| PE_DDR_Perform_Data_Reset | 执行数据复位 |

**UFP Initiated:**

| 状态 | 说明 |
|------|------|
| PE_UDR_Send_Data_Reset | UFP 发送 Data_Reset |
| PE_UDR_Data_Reset_Received | 收到响应 |
| PE_UDR_Turn_Off_VCONN | 关闭 VCONN |
| PE_UDR_Send_Ps_Rdy | 发送 PS_RDY |
| PE_UDR_Wait_For_Data_Reset_Complete | 等待完成 |

---

### 2.6 Power Role Swap 状态机 (Section 8.3.3.20.3-20.4)

**Source → Sink (PR_Swap):**

| 状态 | 说明 |
|------|------|
| PE_SRC_Ready | 初始状态（在 PE_SRC_Ready） |
| PE_PRS_SRC_SNK_Evaluate_Swap | 评估是否接受交换 |
| PE_PRS_SRC_SNK_Accept_Swap | 发送 Accept |
| PE_PRS_SRC_SNK_Transition_to_off | 关断 VBUS（PSSourceOffTimer） |
| PE_PRS_SRC_SNK_Assert_Rd | 下拉 Rd（变为 Sink） |
| PE_PRS_SRC_SNK_Wait_Source_on | 等待新 Source 启动（PSSourceOnTimer） |
| PE_PRS_SRC_SNK_Send_Swap | 发起 PR_Swap |
| PE_PRS_SRC_SNK_Reject_Swap | 拒绝 PR_Swap |

**Sink → Source (PR_Swap):**

| 状态 | 说明 |
|------|------|
| PE_SNK_Ready | 初始状态（在 PE_SNK_Ready） |
| PE_PRS_SNK_SRC_Evaluate_Swap | 评估是否接受交换 |
| PE_PRS_SNK_SRC_Accept_Swap | 发送 Accept |
| PE_PRS_SNK_SRC_Transition_to_off | 关断（PSSourceOffTimer） |
| PE_PRS_SNK_SRC_Assert_Rp | 上拉 Rp（变为 Source） |
| PE_PRS_SNK_SRC_Source_on | 启动 VBUS（PSSourceOnTimer） |
| PE_PRS_SNK_SRC_Send_Swap | 发起 PR_Swap |
| PE_PRS_SNK_SRC_Reject_Swap | 拒绝 PR_Swap |

---

### 2.7 Data Role Swap 状态机 (Section 8.3.3.20.1-20.2)

**DFP → UFP:**

| 状态 | 说明 |
|------|------|
| PE_DRS_DFP_UFP_Evaluate_Swap | 评估交换 |
| PE_DRS_DFP_UFP_Accept_Swap | 接受交换 |
| PE_DRS_DFP_UFP_Change_to_UFP | 切换为 UFP |
| PE_DRS_DFP_UFP_Send_Swap | 发起 DR_Swap |
| PE_DRS_DFP_UFP_Reject_Swap | 拒绝交换 |

**UFP → DFP:**

| 状态 | 说明 |
|------|------|
| PE_DRS_UFP_DFP_Evaluate_Swap | 评估交换 |
| PE_DRS_UFP_DFP_Accept_Swap | 接受交换 |
| PE_DRS_UFP_DFP_Change_to_DFP | 切换为 DFP |
| PE_DRS_UFP_DFP_Send_Swap | 发起 DR_Swap |
| PE_DRS_UFP_DFP_Reject_Swap | 拒绝交换 |

---

### 2.8 Fast Role Swap 状态机 (Section 8.3.3.20.5-20.6)

**Source → Sink (Fast Role Swap):**

| 状态 | 说明 |
|------|------|
| PE_FRS_SRC_SNK_Evaluate_Swap | 评估 FRS |
| PE_FRS_SRC_SNK_Accept_Swap | 接受 FRS |
| PE_FRS_SRC_SNK_Transition_to_off | 关断 VBUS |
| PE_FRS_SRC_SNK_Assert_Rd | 下拉 Rd |
| PE_FRS_SRC_SNK_Wait_Source_on | 等待新 Source 上电 |

---

### 2.9 VCONN Swap 状态机 (Section 8.3.3.21)

| 状态 | 说明 |
|------|------|
| PE_VCS_Send_Swap | 发送 VCONN_Swap |
| PE_VCS_Evaluate_Swap | 评估交换 |
| PE_VCS_Accept_Swap | 接受交换 |
| PE_VCS_Reject_Swap | 拒绝交换 |

---

### 2.10 其他 Policy Engine 状态机

| 状态机组 | 章节 | 说明 |
|---------|------|------|
| Not Supported | 8.3.3.6 | 不支持消息处理 |
| Ping | 8.3.3.7 | Source 定期 Ping |
| Alert | 8.3.3.8 | Source/Sink 告警 |
| Extended Capabilities | 8.3.3.9 | 扩展能力查询 |
| Source Information | 8.3.3.10 | Source 信息查询 |
| Status | 8.3.3.11 | 状态查询 |
| Battery Capabilities | 8.3.3.12 | 电池能力 |
| Battery Status | 8.3.3.13 | 电池状态 |
| Manufacturer Info | 8.3.3.14 | 制造商信息 |
| Country Codes/Info | 8.3.3.15 | 国家代码/信息 |
| Revision | 8.3.3.16 | 版本查询 |
| Enter_USB | 8.3.3.17 | 进入 USB 模式 |
| Security | 8.3.3.18 | 安全消息 |
| Firmware Update | 8.3.3.19 | 固件更新 |
| Dual-Role Port | 8.3.3.20 | 双角色端口（含 PR_Swap, DR_Swap, FRS） |

---

## 三、CTS 测试中常见状态机检查

| 状态机 | CTS 场景 | 典型检查点 |
|--------|---------|-----------|
| PE_SRC_Send_Capabilities → PE_SRC_Ready | 上电 | Source 能否在 tFirstSourceCap (250ms) 内发送能力 |
| PE_SNK_Wait_for_Capabilities → PE_SNK_Evaluate_Capability | Sink 上电 | SinkWaitCapTimer 不超时 (310-620ms) |
| PE_SRC_Negotiate_Capability | 协商 | 正确评估 Request，错误的 PDO 应 Reject |
| PE_SRC_Transition_Supply | 电源转换 | PSTransitionTimer 不超时 (500ms SPR) |
| PE_PRS_SRC_SNK_Transition_to_off | PR_Swap | PSSourceOffTimer 不超时 (835ms SPR) |
| PE_PRS_SNK_SRC_Source_on | PR_Swap Sink→Source | PSSourceOnTimer 不超时 (435ms SPR) |
| SRT_Expired | 请求响应 | SenderResponseTimer 超时 (30ms) → 正确错误处理 |
| PRL_Tx_Check_RetryCounter | 重试 | nRetryCount=2 次后 → Soft Reset |

---

## 四、Unisoc 平台对应关系

> 来源: 项目经验，辅助参考

| PD 规范状态 | Unisoc 驱动对应 | 说明 |
|------------|----------------|------|
| PE_SRC_Startup/PE_SNK_Startup | sc27xx-typec 初始化 | Type-C 控制器驱动加载 |
| PE_SRC_Discovery/PE_SNK_Discovery | Type-C 状态机 | CC 线检测，Rp/Rd 确定角色 |
| PE_SRC_Send_Capabilities | tcpci 发送 | 通过 TCPC 发送 Source_Capabilities |
| PE_SNK_Evaluate_Capability | sprd_tcpm 评估 | TCPM 解析 PDO 并选择 |
| PE_SRC_Transition_Supply | charger IC 调压 | 通过 I2C 控制充电 IC 调整 VBUS |
| Protocol Layer | tcpci 驱动 | TCPC 硬件处理 GoodCRC/CRC 校验 |

---

## 来源

- 官方规范: `USB_PD_R3_2 V1.0 2023-10.pdf`
  - Section 6.12 (Protocol Layer State Machines), Pages 305-340
  - Section 6.12.2.2 (Message Transmission), Pages 310-320
  - Section 6.12.2.3 (Message Reception), Pages 320-325
  - Section 6.12.2.4 (Hard Reset), Pages 325-330
  - Section 8.3.3 (Policy Engine State Diagrams), Pages 862-960
  - Section 8.3.3.2 (Source Port), Pages 867-875
  - Section 8.3.3.3 (Sink Port), Pages 875-880
  - Section 8.3.3.20 (Dual-Role Port), Pages 920-950