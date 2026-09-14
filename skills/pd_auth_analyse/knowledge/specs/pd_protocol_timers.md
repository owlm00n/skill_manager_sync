# PD 协议关键 Timer 参数

> 来源: `USB_PD_R3_2 V1.0 2023-10.pdf`, Section 6.6 (Timers) & Section 6.6.22 (Time Values and Timers)
> 
> 提取日期: 2026-07-28

---

## 概述

所有 Timer 以总线上的 bit 为基准定义，无论其在逻辑架构中的实现位置。这确保了 Timer 启停的固定参考点。

---

## 时间值表 (Table 6.69 "Time Values")

### 协议层 Timer

| 参数 | 最小值 | 典型值 | 最大值 | 单位 | 用途 |
|------|--------|--------|--------|------|------|
| tReceive | 0.9 | 1.0 | 1.1 | ms | CRCReceiveTimer 超时，检测 Message 丢失 |
| tTransmit | — | — | 195 | µs | 接收方发送 GoodCRC 的最大延迟 |
| tRetry | — | — | 195 | µs | 重试间隔，CRCReceiveTimer 过期后重发 Preamble 的时间 |
| tSenderResponse | 27 | 30 | 33 | ms | 请求方等待响应的超时 |
| tReceiverResponse | — | — | 15 | ms | 接收方响应请求的最大时间 |
| tSinkTx | 16 | 18 | 20 | ms | Sink 发送 Message 的时间限制 |

### 能力检测 Timer

| 参数 | 最小值 | 典型值 | 最大值 | 单位 | 用途 |
|------|--------|--------|--------|------|------|
| tFirstSourceCap | — | — | 250 | ms | Attach/Hard Reset/PR_Swap/FR_Swap 后首次发送 Source_Capabilities 的时限 |
| tTypeCSendSourceCap | 100 | 150 | 200 | ms | SourceCapabilityTimer 周期，Source 定期发送 Source_Capabilities |
| tTypeCSinkWaitCap | 310 | 465 | 620 | ms | SinkWaitCapTimer 超时，Sink 未收到 Source_Capabilities 时触发 Hard Reset |

### 等待 Timer

| 参数 | 最小值 | 典型值 | 最大值 | 单位 | 用途 |
|------|--------|--------|--------|------|------|
| tSinkRequest | — | — | 100 | ms | 收到 Wait 后，Sink 重新发 Request 的最小间隔 |
| tPRSwapWait | — | — | 100 | ms | 收到 Wait 后，重发 PR_Swap 的最小间隔 |
| tDRSwapWait | — | — | 100 | ms | 收到 Wait 后，重发 DR_Swap 的最小间隔 |
| tVCONNSwapWait | — | — | 100 | ms | 收到 Wait 后，重发 VCONN_Swap 的最小间隔 |
| tEnterUSBWait | — | — | 100 | ms | 收到 Wait 后，重发 Enter_USB 的最小间隔 |

### 电源供应 Timer

| 参数 | 最小值 | 典型值 | 最大值 | 单位 | 用途 |
|------|--------|--------|--------|------|------|
| tPSTransition (SPR) | 450 | 500 | 550 | ms | 电源转换超时，等 PS_RDY 的最大时间 |
| tPSTransition (EPR) | 830 | 925 | 1020 | ms | EPR 模式下电源转换超时 |
| tPSSourceOff (SPR) | 750 | 835 | 920 | ms | PR_Swap/FR_Swap 期间等旧 Source 关断的 PS_RDY 超时 |
| tPSSourceOff (EPR) | 1120 | 1260 | 1400 | ms | EPR 模式下的 PSSourceOff |
| tPSSourceOn (SPR) | 390 | 435 | 480 | ms | PR_Swap/FR_Swap 期间等新 Source 启动的 PS_RDY 超时 |

### 无响应 Timer

| 参数 | 最小值 | 典型值 | 最大值 | 单位 | 用途 |
|------|--------|--------|--------|------|------|
| tNoResponse | 4.5 | 5.0 | 5.5 | s | 等 Source_Capabilities 的 GoodCRC 超时，触发额外 Hard Reset |

### Hard Reset 相关 Timer

| 参数 | 最小值 | 典型值 | 最大值 | 单位 | 用途 |
|------|--------|--------|--------|------|------|
| tHardReset | — | — | 5 | ms | Hard Reset Signaling 的持续时间 |
| tHardResetComplete | 4 | 4.5 | 5 | ms | Hard Reset 完成后协议层恢复时间 |
| tPSHardReset | 25 | 30 | 35 | ms | 电源转换期间协议错误后发送 Hard Reset 的最大时间 |
| tProtErrHardReset | — | — | 15 | ms | 电源转换期间协议错误 → Hard Reset 的时限 |
| tProtErrSoftReset | — | — | 15 | ms | 协议错误 → Soft_Reset 的时限 |
| tSoftReset | — | — | 15 | ms | CRCReceiveTimer 过期后发送 Soft_Reset 的时限 |

### Power Role Swap 相关 Timer

| 参数 | 最小值 | 典型值 | 最大值 | 单位 | 用途 |
|------|--------|--------|--------|------|------|
| tSwapSourceStart | — | — | 20 | ms | 新 Source 发送 Source_Capabilities 的最早时间 |
| tSwapSinkReady | — | — | 15 | ms | 新 Sink 准备好接收 Source_Capabilities 的时间 |

### Data Reset Timer

| 参数 | 最小值 | 典型值 | 最大值 | 单位 | 用途 |
|------|--------|--------|--------|------|------|
| tDataReset | 200 | 225 | 250 | ms | Data_Reset 流程完成时限 |
| tDataResetFail | — | 300 | 400 | ms | DFP DataResetFailTimer 超时 |
| tDataResetFailUFP | — | 450 | 550 | ms | UFP DataResetFailUFPTimer 超时 |
| tVCONNSourceDischarge | 160 | 200 | 240 | ms | VCONN 放电等待超时 |

### VDM Timer

| 参数 | 最小值 | 典型值 | 最大值 | 单位 | 用途 |
|------|--------|--------|--------|------|------|
| tVDMSenderResponse | 24 | 27 | 30 | ms | VDM 请求方等响应的超时 |
| tVDMReceiverResponse | — | — | 15 | ms | VDM 接收方响应的最大时间 |
| tVDMEnterMode | — | — | 25 | ms | Enter Mode 完成时限 |
| tVDMExitMode | — | — | 25 | ms | Exit Mode 完成时限 |
| tVDMWaitModeEntry | 40 | 45 | 50 | ms | Enter Mode 等待间隔 |
| tVDMWaitModeExit | 40 | 45 | 50 | ms | Exit Mode 等待间隔 |
| tVDMBusy | — | — | 50 | ms | VDM Busy 响应间隔 |

### BIST Timer

| 参数 | 最小值 | 典型值 | 最大值 | 单位 | 用途 |
|------|--------|--------|--------|------|------|
| tBISTCarrierMode | — | — | 300 | ms | 进入 BIST Carrier Mode 的最大延迟 |
| tBISTContMode | 30 | 45 | 60 | ms | BIST Carrier Mode 持续时间 |
| tBISTSharedTestMode | — | — | 1 | s | 进入 BIST Shared Capacity Test Mode 的最大延迟 |

### EPR Timer

| 参数 | 最小值 | 典型值 | 最大值 | 单位 | 用途 |
|------|--------|--------|--------|------|------|
| tEnterEPR | 450 | 500 | 550 | ms | EPR Mode 进入流程完成时限 |
| tSinkEPRKeepAlive | 0.250 | 0.375 | 0.500 | s | EPR Sink 保活间隔 |
| tSourceEPRKeepAlive | 0.750 | 0.875 | 1.000 | s | EPR Source 保活间隔 |
| tEPRSourceCableDiscovery | — | — | 2 | s | EPR 模式下发现 Cable Plug 的时限 |

### PPS Timer

| 参数 | 最小值 | 典型值 | 最大值 | 单位 | 用途 |
|------|--------|--------|--------|------|------|
| tPPSRequest | — | — | 10 | s | PPS Sink 保活请求间隔 |
| tPPSTimeout | 12.0 | 13.5 | 15.0 | s | PPS Source 通信超时 → Hard Reset |

### 其他 Timer

| 参数 | 最小值 | 典型值 | 最大值 | 单位 | 用途 |
|------|--------|--------|--------|------|------|
| tSinkDelay | — | — | 5 | ms | Sink 延迟 |
| tSrcHoldsBus | — | — | 50 | ms | Source 保持 VBUS 的时间 |
| tVCONNSourceOn | — | — | 50 | ms | VCONN 开启时间 |
| tVCONNSourceOff | — | — | 25 | ms | VCONN 关断时间 |
| tVCONNSourceTimeout | 100 | 150 | 200 | ms | VCONN 开启超时 |
| tCableMessage | — | — | 750 | µs | Cable Message 时间 |
| tDiscoverIdentity | — | 40 | 50 | ms | Discover Identity 超时 |
| tFRSwap5V | — | — | 15 | ms | Fast Role Swap 后 VBUS 降到 vSafe5V 的时间 |
| tFRSwapComplete | — | — | 15 | ms | Fast Role Swap 完成 |
| tFRSwapInit | — | — | 15 | ms | Fast Role Swap 发起 |
| tEnterUSB | — | — | 500 | ms | Enter_USB 发送时限 |
| tDRSwapHardReset | — | — | 15 | ms | DR_Swap 后 Hard Reset 时限 |
| tACTempUpdate | — | — | 500 | ms | AC 温度更新 |
| tChunkingNotSupported | 40 | 45 | 50 | ms | Chunking 不支持超时 |
| tChunkSenderRequest | 24 | 27 | 30 | ms | Chunk 发送方请求超时 |
| tChunkSenderResponse | 24 | 27 | 30 | ms | Chunk 发送方响应超时 |
| tChunkReceiverRequest | — | — | 15 | ms | Chunk 接收方请求响应时间 |
| tChunkReceiverResponse | — | — | 15 | ms | Chunk 接收方响应响应时间 |

---

## Timer 与 Policy Engine 对应关系 (Table 6.70 "Timers")

| Timer 名称 | 参数 | 使用者 | 用途 |
|------------|------|--------|------|
| CRCReceiveTimer | tReceive | Protocol Layer | 检测 Message 丢失 |
| SenderResponseTimer | tSenderResponse | Policy Engine | 等待请求响应超时 |
| SourceCapabilityTimer | tTypeCSendSourceCap | Policy Engine | 定期发送 Source_Capabilities |
| SinkWaitCapTimer | tTypeCSinkWaitCap | Policy Engine | 等待 Source_Capabilities 超时 |
| SinkRequestTimer | tSinkRequest | Policy Engine | 收到 Wait 后重发 Request 的间隔 |
| PSTransitionTimer | tPSTransition | Policy Engine | 电源转换超时 |
| PSSourceOffTimer | tPSSourceOff | Policy Engine | PR_Swap/FR_Swap 关断超时 |
| PSSourceOnTimer | tPSSourceOn | Policy Engine | PR_Swap/FR_Swap 启动超时 |
| NoResponseTimer | tNoResponse | Policy Engine | 无响应超时 → Hard Reset |
| HardResetCompleteTimer | tHardResetComplete | Protocol Layer | Hard Reset 完成 |
| PSHardResetTimer | tPSHardReset | Policy Engine | 电源转换时协议错误 → Hard Reset |
| SwapSourceStartTimer | tSwapSourceStart | Policy Engine | 新 Source 延迟发送 Source_Capabilities |
| DataResetFailTimer | tDataResetFail | Policy Engine | Data Reset 失败超时 |
| DataResetFailUFPTimer | tDataResetFailUFP | Policy Engine | UFP Data Reset 失败超时 |
| VCONNDischargeTimer | tVCONNSourceDischarge | Policy Engine | VCONN 放电超时 |
| VCONNOnTimer | tVCONNSourceTimeout | Policy Engine | VCONN 开启超时 |
| VDMResponseTimer | tVDMSenderResponse | Policy Engine | VDM 响应超时 |
| VDMModeEntryTimer | tVDMWaitModeEntry | Policy Engine | Enter Mode 等待 |
| VDMModeExitTimer | tVDMWaitModeExit | Policy Engine | Exit Mode 等待 |
| BISTContModeTimer | tBISTContMode | Policy Engine | BIST 连续模式超时 |
| SinkTxTimer | tSinkTx | Protocol Layer | Sink 发送窗口 |
| SinkPPSPeriodicTimer | tPPSRequest | Policy Engine | PPS 保活 |
| SourcePPSCommTimer | tPPSTimeout | Policy Engine | PPS 通信超时 |
| SinkEPREnterTimer | tEnterEPR | Policy Engine | EPR 进入超时 |
| SinkEPRKeepAliveTimer | tSinkEPRKeepAlive | Policy Engine | EPR Sink 保活 |
| SourceEPRKeepAliveTimer | tSourceEPRKeepAlive | Policy Engine | EPR Source 保活 |
| ChunkingNotSupportedTimer | tChunkingNotSupported | Policy Engine | Chunking 不支持 |
| ChunkSenderRequestTimer | tChunkSenderRequest | Protocol Layer | Chunk 发送方请求 |
| ChunkSenderResponseTimer | tChunkSenderResponse | Protocol Layer | Chunk 发送方响应 |
| DiscoverIdentityTimer | tDiscoverIdentity | Policy Engine | Discover Identity 超时 |

---

## 计数器 (Table 6.71 "Counter parameters")

| 参数 | 值 | 用途 |
|------|----|------|
| nRetryCount | 2 | Message 重试次数 |
| nHardResetCount | 2 | Hard Reset 重试次数 |
| nCapsCount | 50 | Source_Capabilities 发送上限 |
| nMessageIDCount | 7 | MessageID 滚动范围 |
| nDiscoverIdentityCount | 20 | Discover Identity 重试次数 |
| nBusyCount | 5 | VDM Busy 响应次数 |

---

## CTS 测试中常用的 Timer 检查

在 CTS 测试中，以下 Timer 最为关键：

| Timer | CTS 场景 | 典型检查 |
|-------|---------|---------|
| tReceive | 所有通信测试 | GoodCRC 响应是否在 1ms 内 |
| tSenderResponse | 请求-响应测试 | 响应是否在 30ms 内 |
| tFirstSourceCap | 上电/复位测试 | 首次 Source_Capabilities 是否在 250ms 内 |
| tTypeCSendSourceCap | Source 能力宣告 | 周期性发送在 100-200ms 内 |
| tTypeCSinkWaitCap | Sink 等待能力 | 超时 310-620ms 后发 Hard Reset |
| tPSTransition | 电源转换 | PS_RDY 在 500ms(SPR)/925ms(EPR) 内 |
| tPSSourceOff | PR_Swap/FR_Swap | 关断在 835ms(SPR)/1260ms(EPR) 内 |
| tNoResponse | 无响应处理 | 5s 无响应 → Hard Reset |
| tSinkTx | Sink 发送 | Sink 需在 18ms 内完成发送 |
| tSoftReset | 协议错误 | 15ms 内发送 Soft_Reset |

---

## 来源

- 官方规范: `USB_PD_R3_2 V1.0 2023-10.pdf`
  - Section 6.6 (Timers), Pages 271-291
  - Section 6.6.22 (Time Values and Timers), Pages 292-295
  - Table 6.69 (Time Values), Pages 293-294
  - Table 6.70 (Timers), Page 295
  - Table 6.71 (Counter parameters), Page 298