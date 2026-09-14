# USB Trace 阅读方法论（精简版）

## 概述

Lecroy Voyager M310e 协议分析仪生成的 `.usb` 文件是专有二进制格式，无法直接阅读。
本文档描述如何从 Lecroy 导出的文本/HTML 报告中提取关键信息。

## 文件类型识别

| 文件类型 | 特征 | 处理方式 |
|---------|------|---------|
| `.usb` | 二进制，36MB+ | 需 Lecroy 软件导出为文本 |
| `*_extracted.txt` | 含时间戳+消息列 | 直接阅读 |
| `*_trace_report.html` | HTML 表格 | 直接阅读 |
| 含 CC1/CC2/Message 列的目录 | 多文件导出 | 按时间排序阅读 |

## 文本报告关键列

```
| # | Time(s) | Direction | Message | Data |
```

- **Time**: 相对时间戳（秒），用于计算 timer
- **Direction**: S→D (Source到Sink) / D→S / 双向
- **Message**: PD 消息类型（SourceCap, Request, Accept, PS_RDY, Hard_Reset 等）
- **Data**: PDO 内容 / 电压电流值

## Timer 计算方法

```
tSenderResponse = Time(Request) - Time(SourceCap)
tPSTransition   = Time(Vbus_stable) - Time(PS_RDY)
tPSSourceOn     = Time(Vbus_target) - Time(PS_RDY)
tTypeCSendSourceCap = Time(SourceCap) - Time(CC_Attached)
```

## 分析要点

1. **找到 FAIL 事件**: 搜索 "FAIL" / "Timeout" / "Error" 关键字
2. **回溯前序事件**: FAIL 前 5~10 条消息是上下文
3. **计算 timer**: 用时间戳差值对照规范限值
4. **检查消息序列**: 对照 `pd_message_sequences.md` 验证顺序
5. **关注异常间隔**: 两条消息间隔异常大 → 可能是驱动延迟

## 常见 Trace 异常模式

| 模式 | 表现 | 指向 |
|------|------|------|
| SourceCap 重复发送 | 连续 3+ 条 SourceCap | GoodCRC 丢失 / Sink 未响应 |
| PS_RDY 后长间隔 | PS_RDY → 下一事件 > 550ms | Vbus 转换超时 |
| Hard Reset 频繁 | 多次 Hard Reset Signal | 协商反复失败 |
| 消息方向异常 | Sink 发了 Source 该发的消息 | 角色混乱 / PR_Swap 异常 |
