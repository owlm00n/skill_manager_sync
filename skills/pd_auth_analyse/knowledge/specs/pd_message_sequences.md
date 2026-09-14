# PD 协议消息与原子消息序列 (AMS)

> 来源: `USB_PD_R3_2 V1.0 2023-10.pdf`, Section 6.3-6.5 (Messages) & Section 8.3.2 (Atomic Message Sequences)
> 
> 提取日期: 2026-07-28

---

## 概述

USB PD 协议使用结构化消息进行通信。消息分为三种类型：Control Messages（控制消息）、Data Messages（数据消息）和 Extended Messages（扩展消息）。原子消息序列（AMS）定义了在特定场景下必须遵循的消息交互顺序。

---

## 一、消息类型

### 1.1 Control Messages (控制消息)

Control Messages 是短消息，用于协议控制，不携带数据对象。

| 消息 | 发起方 | 用途 |
|------|--------|------|
| GoodCRC | 接收方 | 确认消息接收正确 |
| Accept | 接收方 | 接受请求消息 |
| Reject | 接收方 | 拒绝请求消息 |
| Wait | 接收方 | 忙，稍后重试 |
| PS_RDY | Source/Sink | 电源转换完成 |
| Get_Source_Cap | Sink | 请求 Source 能力 |
| Get_Sink_Cap | Source | 请求 Sink 能力 |
| Soft_Reset | Source/Sink | 协议层软复位 |
| Hard_Reset | — | PHY 层硬复位信令 |
| Not_Supported | 接收方 | 不支持该消息 |
| Data_Reset | DFP/UFP | 数据复位 |
| Data_Reset_Complete | 接收方 | 数据复位完成 |
| Ping | Source | 链路保活 |

### 1.2 Data Messages (数据消息)

Data Messages 携带数据对象，用于协商电源参数。

| 消息 | 发起方 | 数据对象 | 用途 |
|------|--------|---------|------|
| Source_Capabilities | Source | PDO[] | 宣告 Source 供电能力 |
| Request | Sink | RDO | Sink 请求特定电力配置 |
| BIST | Tester | BIST DO | BIST 测试模式 |
| Sink_Capabilities | Sink | PDO[] | 宣告 Sink 的供电/耗电能力 |
| Battery_Status | Source/Sink | BSO | 电池状态 |
| Alert | Source/Sink | ADO | 告警 |
| Get_Country_Info | Source/Sink | — | 请求国家信息 |
| Enter_USB | DFP | — | 进入 USB 模式 |
| Vendor_Defined | Source/Sink | VDM[] | 厂商自定义（VDM） |

### 1.3 Extended Messages (扩展消息)

Extended Messages 支持更大数据负载和 Chunking。

| 消息 | 发起方 | 用途 |
|------|--------|------|
| Source_Capabilities_Extended | Source | 扩展 Source 能力 |
| Status | Source/Sink | 状态信息 |
| Get_Battery_Cap | Source/Sink | 请求电池能力 |
| Get_Battery_Status | Source/Sink | 请求电池状态 |
| Battery_Capabilities | Source/Sink | 电池能力 |
| Get_Manufacturer_Info | Source/Sink | 请求制造商信息 |
| Manufacturer_Info | Source/Sink | 制造商信息 |
| Security_Request | Source/Sink | 安全请求 |
| Security_Response | Source/Sink | 安全响应 |
| Firmware_Update_Request | Source/Sink | 固件更新请求 |
| Firmware_Update_Response | Source/Sink | 固件更新响应 |
| PPS_Status | Source/Sink | PPS 状态 |
| Country_Info | Source/Sink | 国家信息 |
| Country_Codes | Source/Sink | 国家代码 |
| EPR_Source_Capabilities | Source | EPR Source 能力 |
| EPR_Request | Sink | EPR 请求 |
| EPR_Mode | Source/Sink | EPR 模式进入/退出 |
| EPR_Get_Source_Cap | Sink | EPR 请求 Source 能力 |
| EPR_KeepAlive | Sink | EPR 保活 |
| EPR_KeepAlive_Ack | Source | EPR 保活应答 |

---

## 二、基本消息流

### 2.1 成功消息交换

```
Source                              Sink
  |                                    |
  |--- Source_Capabilities ----------->|  (1) Source 发送能力宣告
  |<-- GoodCRC -----------------------|  (2) Sink 确认接收
  |<-- Request -----------------------|  (3) Sink 请求电力
  |--- GoodCRC ----------------------->|  (4) Source 确认接收
  |--- Accept ------------------------>|  (5) Source 接受请求
  |<-- GoodCRC -----------------------|  (6) Sink 确认接收
  |--- PS_RDY ------------------------>|  (7) Source 电源就绪
  |<-- GoodCRC -----------------------|  (8) Sink 确认接收
```

### 2.2 消息响应时间约束

| 阶段 | 方向 | 时间约束 | 超时响应 |
|------|------|---------|---------|
| Sink 等待 GoodCRC | Source→Sink | tTransmit ≤ 195µs | CRCReceiveTimer 超时 |
| Source 等待 GoodCRC | Sink→Source | tTransmit ≤ 195µs | CRCReceiveTimer 超时 |
| 请求方等待响应 | — | tSenderResponse ≤ 30ms | SenderResponseTimer 超时 |
| 接收方响应请求 | — | tReceiverResponse ≤ 15ms | — |

---

## 三、原子消息序列 (AMS) 类型

> 来源: Table 8.4 "Atomic Message Sequences"

### 3.1 AMS 类型总览

| AMS 类型 | 参考表 | 参考章节 | 说明 |
|----------|--------|---------|------|
| Power Negotiation (SPR) | Table 8.5 | Section 8.3.2.2.1 | SPR 电源协商 |
| Power Negotiation (EPR) | Table 8.6 | Section 8.3.2.2.2 | EPR 电源协商 |
| Unsupported Message | Table 8.7 | Section 8.3.2.3 | 不支持消息处理 |
| Ping | Table 8.8 | Section 8.3.2.4 | Ping 链路保活 |
| Soft Reset | Table 8.9 | Section 8.3.2.5 | 软复位 |
| Data Reset | Table 8.10 | Section 8.3.2.6 | 数据复位 |
| Power Role Swap | Table 8.11 | Section 8.3.2.8 | 电源角色交换 |
| Fast Role Swap | Table 8.12 | Section 8.3.2.9 | 快速角色交换 |
| Data Role Swap | Table 8.13 | Section 8.3.2.10 | 数据角色交换 |
| VCONN Swap | Table 8.14 | Section 8.3.2.11 | VCONN 交换 |
| Structured VDM | Table 8.15 | Section 8.3.2.12 | 结构化 VDM |
| Status | Table 8.16 | Section 8.3.2.10.2 | 状态查询 |
| Source/Sink Capabilities (SPR) | Table 8.17 | Section 8.3.2.12.3 | SPR 能力查询 |
| Source/Sink Capabilities (EPR) | Table 8.18 | Section 8.3.2.12.3.2 | EPR 能力查询 |
| Extended Capabilities | Table 8.19 | Section 8.3.2.12.4 | 扩展能力查询 |
| Battery Capabilities | Table 8.20 | Section 8.3.2.12.5 | 电池能力查询 |
| Manufacturer Information | Table 8.21 | Section 8.3.2.12.6 | 制造商信息 |
| Country Codes/Info | — | Section 8.3.2.13 | 国家代码/信息 |
| Security | — | Section 8.3.2.14 | 安全消息 |
| Firmware Update | — | Section 8.3.2.15 | 固件更新 |
| Cable Proprietary | — | Section 8.3.2.16 | 线缆私有消息 |

---

## 四、关键 AMS 序列详解

### 4.1 SPR Power Negotiation (SPR 电源协商)

**AMS: SPR Explicit Contract Negotiation (Accept)**
```
1) Source_Capabilities  →  (Source → Sink, 定期发送或 Responding to Request)
2) Request              ←  (Sink → Source, 选择 PDO)
3) Accept               →  (Source → Sink, 接受请求)
4) PS_RDY               →  (Source → Sink, 电源转换完成)
```

**备选路径:**
- **Reject**: Accept → Reject (Source 拒绝 Sink 的 Request)
- **Wait**: Accept → Wait (Source 忙，Sink 等 tSinkRequest 后重发 Request)
- **GotoMin**: Source_Capabilities 的 PDO 不满足时，Sink 发送 GotoMin Request

### 4.2 Power Role Swap (电源角色交换)

**Source Initiated PR_Swap (Accept)**
```
1) PR_Swap    →  (Source → Sink)
2) Accept     ←  (Sink → Source)
3) PS_RDY     ←  (Sink → Source, 旧 Source 关断)
4) PS_RDY     →  (Source → Sink, 新 Source 启动)
5) SPR Explicit Contract Negotiation  (新 Source 发送能力)
```

**关键 Timer:**
| 阶段 | Timer | 约束 |
|------|-------|------|
| 旧 Source 关断 | PSSourceOffTimer | SPR: 835ms, EPR: 1260ms |
| 新 Source 启动 | PSSourceOnTimer | SPR: 435ms |
| 新 Source 发送 Capabilities | SwapSourceStartTimer | 20ms |

### 4.3 Data Role Swap (数据角色交换)

**DR_Swap (Accept)**
```
1) DR_Swap    →  (UFP → DFP)
2) Accept     ←  (DFP → UFP)
— 角色交换完成 —
```

### 4.4 Soft Reset (软复位)

**Soft Reset**
```
1) Soft_Reset →  (Source/Sink → 对方)
2) Accept     ←  (对方 → 发起方)
— 协议层复位，MessageID 重置 —
```

### 4.5 Hard Reset (硬复位)

Hard Reset 是 PHY 层信令（非消息）：
- 持续时间: tHardReset ≤ 5ms
- 恢复时间: tHardResetComplete = 4.5ms(典型值)
- 无响应触发: NoResponseTimer 超时 (5.0s) → Hard Reset

### 4.6 EPR Mode Entry (EPR 模式进入)

**Entering EPR Mode (Success)**
```
1) EPR_Mode (Enter)              →  (Sink → Source)
2) EPR_Mode (Enter Acknowledge)  ←  (Source → Sink)
3) EPR_Source_Capabilities       ←  (Source → Sink)
4) EPR_Request                   →  (Sink → Source)
5) Accept                        ←  (Source → Sink)
6) PS_RDY                        ←  (Source → Sink)
```

**关键 Timer:**
- tEnterEPR: 500ms (典型值)

---

## 五、Chunking 支持

### 5.1 Chunking 架构

Extended Messages 可能超过单消息负载限制，需要分块（Chunking）：

| 组件 | 用途 |
|------|------|
| Chunked Tx | 将大消息分割为多个 Chunk 发送 |
| Chunked Rx | 接收多个 Chunk 并重组为完整消息 |
| Chunked Message Router | 管理 Chunk 请求/响应 |

### 5.2 Chunking Timer

| Timer | 值 | 用途 |
|-------|-----|------|
| tChunkingNotSupported | 45ms (典型) | 不支持 Chunking 时的响应延迟 |
| tChunkSenderRequest | 27ms (典型) | Chunk 发送方请求超时 |
| tChunkSenderResponse | 27ms (典型) | Chunk 发送方响应超时 |

---

## 六、CTS 测试中常见 AMS 检查

| AMS 类型 | CTS 场景 | 典型检查点 |
|----------|---------|-----------|
| Power Negotiation | 所有电源测试 | GoodCRC → Accept → PS_RDY 时序 |
| PR_Swap | 角色交换测试 | PS_RDY 对等顺序，PSSourceOff/On 不超时 |
| Soft Reset | 协议错误恢复 | 收到 Soft_Reset → Accept in 15ms |
| Ping | 链路保活 | Ping 周期，Sink 响应 |
| VDM | 模式进入/退出 | Enter/Exit Mode 响应时间 |

---

## 来源

- 官方规范: `USB_PD_R3_2 V1.0 2023-10.pdf`
  - Section 6.3 (Control Messages), Pages 148-155
  - Section 6.4 (Data Messages), Pages 156-166
  - Section 6.5 (Extended Messages), Pages 167-192
  - Section 8.3.2 (Atomic Message Sequences), Pages 450-862
  - Table 8.4 (Atomic Message Sequences), Pages 457-458