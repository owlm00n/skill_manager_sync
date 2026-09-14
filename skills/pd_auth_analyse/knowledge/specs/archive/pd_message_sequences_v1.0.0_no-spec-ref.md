# PD协议消息序列 (PD R3.2 Chapter 6)

## 概述
本文档描述PD R3.2规范第6章中定义的关键消息交互序列, 用于CTS trace分析时的消息流比对。

## 1. 标准电源协商 (SPR SourceCap → PS_RDY)

```
Source                           Sink
  |                                |
  |--- SourceCap -------------->---|  (Source能力广播)
  |                                |
  |---<------------- Request  -----|  (Sink请求功率)
  |                                |
  |--- Accept  ---------------->---|  (Source接受请求)
  |                                |
  |--- PS_RDY  ---------------->---|  (Source电源就绪)
  |                                |
  |<-- Vbus transition -->|         (Vbus转换)
```

**合规检查点**:
- SourceCap → Request: < tSenderResponse (30ms)
- Request → Accept: < tSenderResponse
- Accept → PS_RDY: < tPSTransition (550ms)
- PS_RDY后Vbus达到目标值: < tPSSourceOn (400ms)

## 2. SinkCap协商序列

```
Source                           Sink
  |                                |
  |--- Get_SinkCap ----------->---|
  |                                |
  |---<------ SinkCap  ------------|
  |                                |
  |--- Get_SourceCap --------->---|
  |                                |
  |---<------ SourceCap -----------|
```

**合规检查点**:
- Get_SinkCap → SinkCap: < tSenderResponse

## 3. PR_Swap序列

```
Source                           Sink
  |                                |
  |--- PR_Swap  --------------->--|  (发起角色交换)
  |                                |
  |---<----------- Accept  --------|  (Sink接受)
  |                                |
  |--- PS_RDY  --------------->---|  (Source指示PS就绪)
  |                                |
  |---<---------- PS_RDY  ---------|  (Sink确认PS就绪)
  |                                |
  |<-- Vbus transition -->|         (Vbus角色交换)
  |                                |
  |---<-- SourceCap (新Source) ----|  (新Source广播能力)
  (角色交换完成)
```

**合规检查点**:
- PR_Swap → Accept: < tSenderResponse
- Accept → PS_RDY(Source): < tSwapSourceStart (22ms)
- PS_RDY → Vbus at vSafe0V: < tPSSourceOff (920ms)
- vSafe0V → 新SourceCap: < tTypeCSendSourceCap (100ms)

## 4. DR_Swap序列

```
Source (DFP)                    Sink (UFP)
  |                                |
  |--- DR_Swap  --------------->--|  (发起数据角色交换)
  |                                |
  |---<----------- Accept  --------|
  |                                |
  (数据角色交换完成, 无Vbus变化)
```

**合规检查点**:
- DR_Swap → Accept: < tSenderResponse
- DR_Swap后USB Host/Device角色切换必须完成

## 5. 硬复位序列

```
Source                           Sink
  |                                |
  |--- Hard Reset Signal ------->--|  (CC引脚Hard Reset)
  |                                |
  |---<-- Vbus → vSafe0V ----------|
  |                                |
  |---<-- Vbus → vSafe5V ----------|  (重新建立连接)
  |                                |
  |--- SourceCap -------------->---|
```

**合规检查点**:
- Hard Reset → Vbus off: < tHardResetComplete (50ms)
- Vbus on → SourceCap: < tTypeCSendSourceCap (100ms)

## 6. VConn Swap序列 (PD 3.2新增)

```
VConn Source (DFP)              VConn Sink (UFP)
  |                                |
  |--- VConn_Swap  ----------->---|  (发起VConn交换)
  |                                |
  |---<----------- Accept  --------|
  |                                |
  |--- PS_RDY  --------------->---|
  |                                |
  (VConn源切换, 旧源关断VConn)
```

**合规检查点**:
- Accept → PS_RDY: < tVConnSwap (4ms)
- VConn Source Off: < tVConnSourceOff (2ms)

## 7. GotoMin协议序列

```
Source                           Sink
  |                                |
  |--- GotoMin  --------------->--|  (Source请求降功率)
  |                                |
  |---<----------- Accept  --------|
  |                                |
  |<-- Sink降功率操作 -->|
```

## 常见异常模式

| 异常 | 表现 | 可能原因 |
|------|------|---------|
| SourceCap超时 | Sink在310ms内未收到SourceCap | CC检测未完成 / PD IC未就绪 |
| GoodCRC超时 | 发送方未收到GoodCRC | PD IC I2C通信异常 / IRQ丢失 |
| PS_RDY超时 | tPSTransition超过550ms | Charger Manager投票未完成 |
| Vbus转换超时 | tPSSourceOn超过400ms | DC-DC升压配置延迟 |
| PR_Swap Vbus不掉 | tPSSourceOff超时 | Vbus drain未使能 |
