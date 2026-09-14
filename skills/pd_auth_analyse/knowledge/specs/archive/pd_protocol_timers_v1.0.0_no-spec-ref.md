# PD协议关键Timer参数 (PD R3.2 Chapter 6)

## 概述
本文档整理PD R3.2规范第6章中与认证测试(CTS)相关的关键定时器参数。这些参数是CTS合规性检查的核心指标。

## CC检测与连接时序

| Timer | 规范值 | 说明 | 相关测试项 |
|-------|--------|------|-----------|
| tCCDebounce | 100ms~200ms | CC引脚去抖动时间 | TD.4.1.x |
| tTypeCSendSourceCap | 50ms~100ms | CC连接建立后发送SourceCap的最大延迟 | TD.4.2.x |
| tTypeCSinkWaitCap | max 310ms | Sink端等待SourceCap的最大时间 | TD.4.3.x |
| tPDDebounce | 10ms~30ms | PD消息去抖动时间 | TD.4.1.1 |

## 电源协商时序

| Timer | 规范值 | 说明 | 相关测试项 |
|-------|--------|------|-----------|
| tSenderResponse | 24ms~30ms | 发送方等待GoodCRC的timeout | TD.4.5.x |
| tReceiverResponse | max 15ms | 接收方回复GoodCRC的最大时间 | TD.4.5.x |
| tPSTransition | max 550ms | PS_RDY后Vbus转换的最大时间 | TD.4.6.x |
| tPSSourceOn | max 400ms (SPR) / 450ms (EPR) | Source端Vbus从0到额定值 | TD.4.6.1 |
| tPSSourceOff | max 920ms (SPR) / 1.1s (EPR) | Source端Vbus从额定到0 | TD.4.6.2 |
| tSinkP | max 920ms | Sink端完成电源转换的最大时间 | TD.4.6.3 |

## PR_Swap时序

| Timer | 规范值 | 说明 | 相关测试项 |
|-------|--------|------|-----------|
| tSwapSourceStart | max 22ms | 新Source端开始输出Vbus的最大延迟 | TD.4.8.x |
| tPSSourceOn | max 400ms | 新Source端Vbus达到额定值 | TD.4.8.1 |
| tPSSourceOff | max 920ms | 旧Source端Vbus降到vSafe0V | TD.4.8.1 |
| tSwapSinkWaitCap | max 310ms | 新Sink端等待SourceCap | TD.4.8.2 |
| tSwapSinkRequest | max 120ms | 新Sink端发Request的最大时间 | TD.4.8.2 |

## DR_Swap时序

| Timer | 规范值 | 说明 | 相关测试项 |
|-------|--------|------|-----------|
| tSwapSourceStart | max 22ms | DR_Swap后Vbus转换 | TD.4.9.x |
| tPSSourceOn (DR_Swap) | max 400ms | DR_Swap后Vbus达到额定值 | TD.4.9.1 |
| tPSSourceOff (DR_Swap) | max 920ms | DR_Swap后Vbus降到vSafe0V | TD.4.9.1 |

## 硬复位时序

| Timer | 规范值 | 说明 | 相关测试项 |
|-------|--------|------|-----------|
| tHardResetComplete | 25ms~50ms | 硬复位后进入初始状态的延迟 | TD.4.10.x |
| tTypeCSendSourceCap (HR) | 50ms~100ms | 硬复位后重发SourceCap | TD.4.10.1 |

## VConn Swap时序 (PD 3.2新增)

| Timer | 规范值 | 说明 | 相关测试项 |
|-------|--------|------|-----------|
| tVConnSwap | max 4ms | VConn切换完成的最大时间 | TD.4.11.x |
| tVConnSourceOff | max 2ms | 旧VConn源关断时间 | TD.4.11.1 |

## 常见认证失败根因总结

1. **tTypeCSendSourceCap超标**: 通常因CC检测完成后PD消息发送被其他中断/工作队列延迟
2. **tPSSourceOn超标**: 通常因Charger Manager升压配置时序过长
3. **tSwapSourceStart超标**: PR_Swap/DR_Swap时Vbus控制切换未及时完成
4. **tSinkP超时**: Sink端接受新功率合同时Vbus不稳定
