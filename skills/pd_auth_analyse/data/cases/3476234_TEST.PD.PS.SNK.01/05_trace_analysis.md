# Bug 3476234 — Trace 分析

## 结论

- **TEST_ID**：`TEST.PD.PS.SNK.01`
- **trace 文件数**：32
- **解析方式**：`text_export_needed`
- **提取事件数**：48
- **缺口**：
  - 共 32 个 .usb 文件，仅处理前 10 个（可在 Step 5 配置 MAX_USB_FILES 调整）
  - 01_TC_CableDetection_cvs0.usb: Lecroy 二进制格式，文本提取无结果。请用 Lecroy 导出为文本后重试
  - 27255_VBusSelfTest.usb: Lecroy 二进制格式，文本提取无结果。请用 Lecroy 导出为文本后重试
  - 01_TC_CableDetection_cvs0.usb: Lecroy 二进制格式，文本提取无结果。请用 Lecroy 导出为文本后重试
  - 27255_VBusSelfTest.usb: Lecroy 二进制格式，文本提取无结果。请用 Lecroy 导出为文本后重试

## Trace 文件清单

- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\Preliminary\01_TC_CableDetection_cvs0.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\Preliminary\27255_VBusSelfTest.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_01\01_TEST.PD.PS.SNK.1_Rev2Snk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_01\02_TEST.PD.PS.SNK.1_Rev3ChkdSnk_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_02\01_TEST.PD.PS.SNK.1_Rev2Snk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_02\02_TEST.PD.PS.SNK.1_Rev3ChkdSnk_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_03\01_TEST.PD.PS.SNK.1_Rev2Snk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_03\02_TEST.PD.PS.SNK.1_Rev3ChkdSnk_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\Preliminary\01_TC_CableDetection_cvs0.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\Preliminary\27255_VBusSelfTest.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_01\01_TEST.PD.PS.SNK.1_Rev2Snk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_01\02_TEST.PD.PS.SNK.1_Rev3ChkdSnk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_02\01_TEST.PD.PS.SNK.1_Rev2Snk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_02\02_TEST.PD.PS.SNK.1_Rev3ChkdSnk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_03\01_TEST.PD.PS.SNK.1_Rev2Snk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_03\02_TEST.PD.PS.SNK.1_Rev3ChkdSnk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\Preliminary\01_TC_CableDetection_cvs0.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\Preliminary\27255_VBusSelfTest.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_01\01_TEST.PD.PS.SNK.1_Rev2Snk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_01\02_TEST.PD.PS.SNK.1_Rev3ChkdSnk_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_02\01_TEST.PD.PS.SNK.1_Rev2Snk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_02\02_TEST.PD.PS.SNK.1_Rev3ChkdSnk_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_03\01_TEST.PD.PS.SNK.1_Rev2Snk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3FILL0PASS   357766\20260706_210703\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_03\02_TEST.PD.PS.SNK.1_Rev3ChkdSnk_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\Preliminary\01_TC_CableDetection_cvs0.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\Preliminary\27255_VBusSelfTest.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_01\01_TEST.PD.PS.SNK.1_Rev2Snk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_01\02_TEST.PD.PS.SNK.1_Rev3ChkdSnk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_02\01_TEST.PD.PS.SNK.1_Rev2Snk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_02\02_TEST.PD.PS.SNK.1_Rev3ChkdSnk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_03\01_TEST.PD.PS.SNK.1_Rev2Snk.usb`
- `E:\08_Bug\CQ\Bug 3476234(SPCSS01684954) - [UMS9230H][HUAQIN_BD2][PD机]TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail\Attachements\SPCSS01684954\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\TEST.PD.PS.SNK.01 PDO Transitions As Sink   3pass  360579\USB Power Delivery\TEST.PD.PS.SNK.1\Repeat_03\02_TEST.PD.PS.SNK.1_Rev3ChkdSnk.usb`

## 协议事件序列

| # | 时间戳 | 消息类型 | 方向 | 详情 |
|---|--------|----------|------|------|
| 1 |  | Request | N/A | <HTML>The UUT sent Request message</HTML> |
| 2 |  | Request | N/A | <HTML>The UUT sent Request message</HTML> |
| 3 |  | Request | N/A | The UUT sent Request message |
| 4 |  | Request | N/A | The UUT sent Request message |
| 1 |  | Request | N/A | <HTML>The UUT sent Request message</HTML> |
| 2 |  | Hard_Reset | → | <HTML>Err#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal.</HTML> |
| 3 |  | Hard_Reset | → | <HTML>Err#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal.</HTML> |
| 4 |  | Hard_Reset | → | <HTML>Err#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal.</HTML> |
| 5 |  | Request | → | [TEST.PD.PS.SNK.1#2] The UUT did not send a Request message. |
| 6 |  | Request | → | [TEST.PD.PS.SNK.1#7] The UUT did not send a Request message.</HTML> |
| 7 |  | Request | N/A | The UUT sent Request message |
| 8 |  | Hard_Reset | → | TErr#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal. |
| 9 |  | Hard_Reset | → | TErr#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal. |
| 10 |  | Hard_Reset | → | TErr#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal. |
| 11 |  | Request | → | [TEST.PD.PS.SNK.1#2] The UUT did not send a Request message. |
| 12 |  | Request | → | [TEST.PD.PS.SNK.1#7] The UUT did not send a Request message. |
| 1 |  | Request | N/A | <HTML>The UUT sent Request message</HTML> |
| 2 |  | Request | N/A | <HTML>The UUT sent Request message</HTML> |
| 3 |  | Request | N/A | The UUT sent Request message |
| 4 |  | Request | N/A | The UUT sent Request message |
| 1 |  | Request | N/A | <HTML>The UUT sent Request message</HTML> |
| 2 |  | Hard_Reset | → | <HTML>Err#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal.</HTML> |
| 3 |  | Hard_Reset | → | <HTML>Err#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal.</HTML> |
| 4 |  | Hard_Reset | → | <HTML>Err#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal.</HTML> |
| 5 |  | Request | → | [TEST.PD.PS.SNK.1#2] The UUT did not send a Request message. |
| 6 |  | Request | → | [TEST.PD.PS.SNK.1#7] The UUT did not send a Request message.</HTML> |
| 7 |  | Request | N/A | The UUT sent Request message |
| 8 |  | Hard_Reset | → | TErr#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal. |
| 9 |  | Hard_Reset | → | TErr#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal. |
| 10 |  | Hard_Reset | → | TErr#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal. |
| 11 |  | Request | → | [TEST.PD.PS.SNK.1#2] The UUT did not send a Request message. |
| 12 |  | Request | → | [TEST.PD.PS.SNK.1#7] The UUT did not send a Request message. |
| 1 |  | Request | N/A | <HTML>The UUT sent Request message</HTML> |
| 2 |  | Request | N/A | <HTML>The UUT sent Request message</HTML> |
| 3 |  | Request | N/A | The UUT sent Request message |
| 4 |  | Request | N/A | The UUT sent Request message |
| 1 |  | Request | N/A | <HTML>The UUT sent Request message</HTML> |
| 2 |  | Hard_Reset | → | <HTML>Err#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal.</HTML> |
| 3 |  | Hard_Reset | → | <HTML>Err#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal.</HTML> |
| 4 |  | Hard_Reset | → | <HTML>Err#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal.</HTML> |
| 5 |  | Request | → | [TEST.PD.PS.SNK.1#2] The UUT did not send a Request message. |
| 6 |  | Request | → | [TEST.PD.PS.SNK.1#7] The UUT did not send a Request message.</HTML> |
| 7 |  | Request | N/A | The UUT sent Request message |
| 8 |  | Hard_Reset | → | TErr#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal. |
| 9 |  | Hard_Reset | → | TErr#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal. |
| 10 |  | Hard_Reset | → | TErr#  0x02A8: COMMON.CHECK.PD.5.2 The UUT was not allowed to send Hard_Reset signal. |
| 11 |  | Request | → | [TEST.PD.PS.SNK.1#2] The UUT did not send a Request message. |
| 12 |  | Request | → | [TEST.PD.PS.SNK.1#7] The UUT did not send a Request message. |

## 合规检查点

| Timer | 期望上限 | 实际值 | 结果 | 备注 |
|-------|----------|--------|------|------|
| tSenderResponse | 30ms | N/A | ? 未知 | 缺少 SourceCap 或 Request 时间戳，无法检查 |
| tSenderResponse | 30ms | N/A | ? 未知 | 缺少 Request 或 Accept 时间戳，无法检查 |
| tPSTransition | 550ms | N/A | ? 未知 | 缺少 Accept 或 PS_RDY 时间戳，无法检查 |

## 与 Log 时间线对齐

- Trace#1 [] Request N/A — ✗ log 中未找到对应记录
- Trace#2 [] Request N/A — ✗ log 中未找到对应记录
- Trace#3 [] Request N/A — ✗ log 中未找到对应记录
- Trace#4 [] Request N/A — ✗ log 中未找到对应记录
- Trace#1 [] Request N/A — ✗ log 中未找到对应记录
- Trace#2 [] Hard_Reset → — ✗ log 中未找到对应记录
- Trace#3 [] Hard_Reset → — ✗ log 中未找到对应记录
- Trace#4 [] Hard_Reset → — ✗ log 中未找到对应记录
- Trace#5 [] Request → — ✗ log 中未找到对应记录
- Trace#6 [] Request → — ✗ log 中未找到对应记录
- Trace#7 [] Request N/A — ✗ log 中未找到对应记录
- Trace#8 [] Hard_Reset → — ✗ log 中未找到对应记录
- Trace#9 [] Hard_Reset → — ✗ log 中未找到对应记录
- Trace#10 [] Hard_Reset → — ✗ log 中未找到对应记录
- Trace#11 [] Request → — ✗ log 中未找到对应记录
- Trace#12 [] Request → — ✗ log 中未找到对应记录
- Trace#1 [] Request N/A — ✗ log 中未找到对应记录
- Trace#2 [] Request N/A — ✗ log 中未找到对应记录
- Trace#3 [] Request N/A — ✗ log 中未找到对应记录
- Trace#4 [] Request N/A — ✗ log 中未找到对应记录
- Trace#1 [] Request N/A — ✗ log 中未找到对应记录
- Trace#2 [] Hard_Reset → — ✗ log 中未找到对应记录
- Trace#3 [] Hard_Reset → — ✗ log 中未找到对应记录
- Trace#4 [] Hard_Reset → — ✗ log 中未找到对应记录
- Trace#5 [] Request → — ✗ log 中未找到对应记录
- Trace#6 [] Request → — ✗ log 中未找到对应记录
- Trace#7 [] Request N/A — ✗ log 中未找到对应记录
- Trace#8 [] Hard_Reset → — ✗ log 中未找到对应记录
- Trace#9 [] Hard_Reset → — ✗ log 中未找到对应记录
- Trace#10 [] Hard_Reset → — ✗ log 中未找到对应记录
