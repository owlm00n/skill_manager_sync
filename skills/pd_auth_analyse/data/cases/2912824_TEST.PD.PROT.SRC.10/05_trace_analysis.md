# Bug 2912824 — Trace 分析

## 结论

- **TEST_ID**：`TEST.PD.PROT.SRC.10`
- **trace 文件数**：3
- **解析方式**：`binary_text_extract`
- **提取事件数**：44
- **缺口**：
  - 01_TC_CableDetection_cvs0.usb: Lecroy 二进制格式，文本提取无结果。请用 Lecroy 导出为文本后重试

## Trace 文件清单

- `F:\PD认证\SPROCOMM\Bug 2912824 – (SPCSS01467901) [UMS9230E][SPROCOMM][blade-A56-u][15704][手持-智能手机][PD认证]TEST.PD.PROT.SRC.10 PR_Swap - PSSourceOnTimer Timeout\Attachements\TEST.PD.PROT.SRC.10\TEST.PD.PROT.SRC.10\USB Power Delivery\Preliminary\01_TC_CableDetection_cvs0.usb`
- `F:\PD认证\SPROCOMM\Bug 2912824 – (SPCSS01467901) [UMS9230E][SPROCOMM][blade-A56-u][15704][手持-智能手机][PD认证]TEST.PD.PROT.SRC.10 PR_Swap - PSSourceOnTimer Timeout\Attachements\TEST.PD.PROT.SRC.10\TEST.PD.PROT.SRC.10\USB Power Delivery\TEST.PD.PROT.SRC.10\01_TEST.PD.PROT.SRC.10_Rev2Src_FAIL.usb`
- `F:\PD认证\SPROCOMM\Bug 2912824 – (SPCSS01467901) [UMS9230E][SPROCOMM][blade-A56-u][15704][手持-智能手机][PD认证]TEST.PD.PROT.SRC.10 PR_Swap - PSSourceOnTimer Timeout\Attachements\TEST.PD.PROT.SRC.10\TEST.PD.PROT.SRC.10\USB Power Delivery\TEST.PD.PROT.SRC.10\02_TEST.PD.PROT.SRC.10_Rev3ChkdSrc_FAIL.usb`

## 协议事件序列

| # | 时间戳 | 消息类型 | 方向 | 详情 |
|---|--------|----------|------|------|
| 1 |  | Accept | N/A | <HTML>The UUT sent an Accept Message. |
| 2 |  | Accept | N/A | The UUT sent an Accept Message. |
| 3 |  | Accept | N/A | The UUT sent an Accept Message. |
| 4 |  | Accept | N/A | The UUT sent an Accept Message. |
| 5 |  | Accept | N/A | The UUT sent an Accept Message. |
| 6 |  | Accept | N/A | The UUT sent an Accept Message.</HTML> |
| 7 |  | PR_Swap | → | <html>the tester sends a pr_swap message to the uut</html> |
| 8 |  | Accept | N/A | <html>the uut sent an accept message</html> |
| 9 |  | Accept | N/A | <html>tester sent a goodcrc message corresponded to uut accept message</html> |
| 10 |  | Hard_Reset | → | <HTML>Err#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal.</HTML> |
| 11 |  | Hard_Reset | → | <HTML>Err#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal.</HTML> |
| 12 |  | Accept | N/A | The UUT sent an Accept Message. |
| 13 |  | Accept | N/A | The UUT sent an Accept Message. |
| 14 |  | Accept | N/A | The UUT sent an Accept Message. |
| 15 |  | Accept | N/A | The UUT sent an Accept Message. |
| 16 |  | Accept | N/A | The UUT sent an Accept Message. |
| 17 |  | Accept | N/A | The UUT sent an Accept Message. |
| 18 |  | PR_Swap | → | -The Tester sends a PR_Swap message to the UUT |
| 19 |  | Accept | N/A | The UUT sent an Accept message |
| 20 |  | Accept | N/A | @Tester sent a GoodCRC message corresponded to UUT Accept message |
| 21 |  | Hard_Reset | → | TErr#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal. |
| 22 |  | Hard_Reset | → | TErr#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal. |
| 1 |  | Accept | N/A | <HTML>The UUT sent an Accept Message. |
| 2 |  | Accept | N/A | The UUT sent an Accept Message. |
| 3 |  | Accept | N/A | The UUT sent an Accept Message. |
| 4 |  | Accept | N/A | The UUT sent an Accept Message. |
| 5 |  | Accept | N/A | The UUT sent an Accept Message. |
| 6 |  | Accept | N/A | The UUT sent an Accept Message.</HTML> |
| 7 |  | PR_Swap | → | <html>the tester sends a pr_swap message to the uut</html> |
| 8 |  | Accept | N/A | <html>the uut sent an accept message</html> |
| 9 |  | Accept | N/A | <html>tester sent a goodcrc message corresponded to uut accept message</html> |
| 10 |  | Hard_Reset | → | <HTML>Err#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal.</HTML> |
| 11 |  | Hard_Reset | → | <HTML>Err#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal.</HTML> |
| 12 |  | Accept | N/A | The UUT sent an Accept Message. |
| 13 |  | Accept | N/A | The UUT sent an Accept Message. |
| 14 |  | Accept | N/A | The UUT sent an Accept Message. |
| 15 |  | Accept | N/A | The UUT sent an Accept Message. |
| 16 |  | Accept | N/A | The UUT sent an Accept Message. |
| 17 |  | Accept | N/A | The UUT sent an Accept Message. |
| 18 |  | PR_Swap | → | -The Tester sends a PR_Swap message to the UUT |
| 19 |  | Accept | N/A | The UUT sent an Accept message |
| 20 |  | Accept | N/A | @Tester sent a GoodCRC message corresponded to UUT Accept message |
| 21 |  | Hard_Reset | → | TErr#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal. |
| 22 |  | Hard_Reset | → | TErr#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal. |

## 合规检查点

| Timer | 期望上限 | 实际值 | 结果 | 备注 |
|-------|----------|--------|------|------|
| tSenderResponse | 30ms | N/A | ? 未知 | 缺少 SourceCap 或 Request 时间戳，无法检查 |
| tSenderResponse | 30ms | N/A | ? 未知 | 缺少 Request 或 Accept 时间戳，无法检查 |
| tPSTransition | 550ms | N/A | ? 未知 | 缺少 Accept 或 PS_RDY 时间戳，无法检查 |

## 与 Log 时间线对齐

- Trace#1 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#2 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#3 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#4 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#5 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#6 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#7 [] PR_Swap → — ✗ log 中未找到对应记录
- Trace#8 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#9 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#10 [] Hard_Reset → — ✗ log 中未找到对应记录
- Trace#11 [] Hard_Reset → — ✗ log 中未找到对应记录
- Trace#12 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#13 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#14 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#15 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#16 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#17 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#18 [] PR_Swap → — ✗ log 中未找到对应记录
- Trace#19 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#20 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#21 [] Hard_Reset → — ✗ log 中未找到对应记录
- Trace#22 [] Hard_Reset → — ✗ log 中未找到对应记录
- Trace#1 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#2 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#3 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#4 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#5 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#6 [] Accept N/A — ✗ log 中未找到对应记录
- Trace#7 [] PR_Swap → — ✗ log 中未找到对应记录
- Trace#8 [] Accept N/A — ✗ log 中未找到对应记录
