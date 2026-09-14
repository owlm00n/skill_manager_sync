# Bug 3437194 — Trace 分析

## 结论

- **TEST_ID**：`TD.4.5.4.V`
- **trace 文件数**：99
- **解析方式**：`binary_text_extract`
- **提取事件数**：12
- **缺口**：
  - 共 99 个 .usb 文件，仅处理前 10 个（可在 Step 5 配置 MAX_USB_FILES 调整）
  - 01_TC_CableDetection_cvs0.usb: Lecroy 二进制格式，文本提取无结果。请用 Lecroy 导出为文本后重试
  - 02_TC_CableOrientation_Device.usb: Lecroy 二进制格式，文本提取无结果。请用 Lecroy 导出为文本后重试
  - 27255_VBusSelfTest.usb: Lecroy 二进制格式，文本提取无结果。请用 Lecroy 导出为文本后重试
  - 02_TD.4.5.4.C.2_FAIL.usb: Lecroy 二进制格式，文本提取无结果。请用 Lecroy 导出为文本后重试

## Trace 文件清单

- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\Preliminary\01_TC_CableDetection_cvs0.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\Preliminary\02_TC_CableOrientation_Device.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\Preliminary\27255_VBusSelfTest.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\01_TD.4.5.4.C.1.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\02_TD.4.5.4.C.2_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\03_TD.4.5.4.C.3.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\04_TD.4.5.4.C.4_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\05_TD.4.5.4.C.5_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\06_TD.4.5.4.C.6_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\07_TD.4.5.4.C.7_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\08_TD.4.5.4.C.8_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\09_TD.4.5.4.C.9_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\01_TD.4.5.4.C.1.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\02_TD.4.5.4.C.2_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\03_TD.4.5.4.C.3.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\04_TD.4.5.4.C.4_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\05_TD.4.5.4.C.5.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\06_TD.4.5.4.C.6_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\07_TD.4.5.4.C.7_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\08_TD.4.5.4.C.8_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\09_TD.4.5.4.C.9_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\01_TD.4.5.4.C.1.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\02_TD.4.5.4.C.2.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\03_TD.4.5.4.C.3.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\04_TD.4.5.4.C.4_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\05_TD.4.5.4.C.5.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\06_TD.4.5.4.C.6_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\07_TD.4.5.4.C.7.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\08_TD.4.5.4.C.8.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\09_TD.4.5.4.C.9.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\TD4.10.3_3FAIL_0606\20260606_132831\USB Type-C\Preliminary\01_TC_CableDetection_cvs0.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\TD4.10.3_3FAIL_0606\20260606_132831\USB Type-C\Preliminary\02_TC_CableOrientation_Device.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\TD4.10.3_3FAIL_0606\20260606_132831\USB Type-C\Preliminary\27255_VBusSelfTest.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\TD4.10.3_3FAIL_0606\20260606_132831\USB Type-C\TD.4.10.3\Repeat_01\01_TD.4.10.3_USB2_Step1-5.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\TD4.10.3_3FAIL_0606\20260606_132831\USB Type-C\TD.4.10.3\Repeat_01\02_TD.4.10.3_USB2_Step6-9.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\TD4.10.3_3FAIL_0606\20260606_132831\USB Type-C\TD.4.10.3\Repeat_01\03_TD.4.10.3_USB2_Step10-13.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\TD4.10.3_3FAIL_0606\20260606_132831\USB Type-C\TD.4.10.3\Repeat_01\04_TD.4.10.3_USB2_Step14_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\TD4.10.3_3FAIL_0606\20260606_132831\USB Type-C\TD.4.10.3\Repeat_02\01_TD.4.10.3_USB2_Step1-5.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\TD4.10.3_3FAIL_0606\20260606_132831\USB Type-C\TD.4.10.3\Repeat_02\02_TD.4.10.3_USB2_Step6-9.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\TD4.10.3_3FAIL_0606\20260606_132831\USB Type-C\TD.4.10.3\Repeat_02\03_TD.4.10.3_USB2_Step10-13.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\TD4.10.3_3FAIL_0606\20260606_132831\USB Type-C\TD.4.10.3\Repeat_02\04_TD.4.10.3_USB2_Step14_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\TD4.10.3_3FAIL_0606\20260606_132831\USB Type-C\TD.4.10.3\Repeat_03\01_TD.4.10.3_USB2_Step1-5.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\TD4.10.3_3FAIL_0606\20260606_132831\USB Type-C\TD.4.10.3\Repeat_03\02_TD.4.10.3_USB2_Step6-9.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\TD4.10.3_3FAIL_0606\20260606_132831\USB Type-C\TD.4.10.3\Repeat_03\03_TD.4.10.3_USB2_Step10-13.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\TD4.10.3_3FAIL_0606\20260606_132831\USB Type-C\TD.4.10.3\Repeat_03\04_TD.4.10.3_USB2_Step14_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\Preliminary\01_TC_CableDetection_cvs0.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\Preliminary\02_TC_CableOrientation_Device.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\Preliminary\27255_VBusSelfTest.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.1\Repeat_01\01_TD.4.10.1_USB2_ExtractInfo_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.1\Repeat_01\02_TD.4.10.1.C.2_Step1-19.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.1\Repeat_01\05_TD.4.10.1.C.3.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.1\Repeat_02\01_TD.4.10.1_USB2_ExtractInfo_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.1\Repeat_02\02_TD.4.10.1.C.2_Step1-19.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.1\Repeat_02\05_TD.4.10.1.C.3.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.1\Repeat_03\01_TD.4.10.1_USB2_ExtractInfo_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.1\Repeat_03\02_TD.4.10.1.C.2_Step1-19.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.1\Repeat_03\05_TD.4.10.1.C.3.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.3\Repeat_01\01_TD.4.10.3_USB2_Step1-5_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.3\Repeat_01\02_TD.4.10.3_USB2_Step6-9_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.3\Repeat_01\03_TD.4.10.3_USB2_Step10-13_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.3\Repeat_01\04_TD.4.10.3_USB2_Step14_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.3\Repeat_02\01_TD.4.10.3_USB2_Step1-5_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.3\Repeat_02\02_TD.4.10.3_USB2_Step6-9_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.3\Repeat_02\03_TD.4.10.3_USB2_Step10-13_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.3\Repeat_02\04_TD.4.10.3_USB2_Step14_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.3\Repeat_03\01_TD.4.10.3_USB2_Step1-5_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.3\Repeat_03\02_TD.4.10.3_USB2_Step6-9_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.3\Repeat_03\03_TD.4.10.3_USB2_Step10-13_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\0606_4_10_3\V8_pass\20260604_204254\USB Type-C\TD.4.10.3\Repeat_03\04_TD.4.10.3_USB2_Step14_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\Preliminary\01_TC_CableDetection_cvs0.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\Preliminary\02_TC_CableOrientation_Device.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\Preliminary\27255_VBusSelfTest.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\01_TD.4.5.4.C.1.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\02_TD.4.5.4.C.2_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\03_TD.4.5.4.C.3.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\04_TD.4.5.4.C.4_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\05_TD.4.5.4.C.5_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\06_TD.4.5.4.C.6_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\07_TD.4.5.4.C.7_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\08_TD.4.5.4.C.8_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_01\09_TD.4.5.4.C.9_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\01_TD.4.5.4.C.1.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\02_TD.4.5.4.C.2_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\03_TD.4.5.4.C.3.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\04_TD.4.5.4.C.4_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\05_TD.4.5.4.C.5.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\06_TD.4.5.4.C.6_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\07_TD.4.5.4.C.7_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\08_TD.4.5.4.C.8_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_02\09_TD.4.5.4.C.9_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\01_TD.4.5.4.C.1.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\02_TD.4.5.4.C.2.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\03_TD.4.5.4.C.3.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\04_TD.4.5.4.C.4_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\05_TD.4.5.4.C.5.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\06_TD.4.5.4.C.6_FAIL.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\07_TD.4.5.4.C.7.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\08_TD.4.5.4.C.8.usb`
- `E:\08_Bug\CQ\Bug 3437194(SPCSS01670383) - [UMS9230H][HUAQIN_BD2][PDer ID with well-formed messages\Attachements\SPCSS01670383\20260601_211246\USB Type-C\TD.4.5.4\Repeat_03\09_TD.4.5.4.C.9.usb`

## 协议事件序列

| # | 时间戳 | 消息类型 | 方向 | 详情 |
|---|--------|----------|------|------|
| 1 |  | Request | N/A | <HTML>UUT sent a request</HTML> |
| 2 |  | Request | N/A | UUT sent a request |
| 1 |  | Request | N/A | <html>uut sent a request</html> |
| 2 |  | Request | N/A | UUT sent a request |
| 1 |  | Request | N/A | <html>uut sent a request</html> |
| 2 |  | Request | N/A | UUT sent a request |
| 1 |  | Request | N/A | <html>uut sent a request</html> |
| 2 |  | Request | N/A | UUT sent a request |
| 1 |  | Request | N/A | <html>uut sent a request</html> |
| 2 |  | Request | N/A | UUT sent a request |
| 1 |  | Request | N/A | <html>uut sent a request</html> |
| 2 |  | Request | N/A | UUT sent a request |

## 合规检查点

| Timer | 期望上限 | 实际值 | 结果 | 备注 |
|-------|----------|--------|------|------|
| tSenderResponse | 30ms | N/A | ? 未知 | 缺少 SourceCap 或 Request 时间戳，无法检查 |
| tSenderResponse | 30ms | N/A | ? 未知 | 缺少 Request 或 Accept 时间戳，无法检查 |
| tPSTransition | 550ms | N/A | ? 未知 | 缺少 Accept 或 PS_RDY 时间戳，无法检查 |

## 与 Log 时间线对齐

- Trace#1 [] Request N/A — ✓ log 中有对应记录
- Trace#2 [] Request N/A — ✓ log 中有对应记录
- Trace#1 [] Request N/A — ✓ log 中有对应记录
- Trace#2 [] Request N/A — ✓ log 中有对应记录
- Trace#1 [] Request N/A — ✓ log 中有对应记录
- Trace#2 [] Request N/A — ✓ log 中有对应记录
- Trace#1 [] Request N/A — ✓ log 中有对应记录
- Trace#2 [] Request N/A — ✓ log 中有对应记录
- Trace#1 [] Request N/A — ✓ log 中有对应记录
- Trace#2 [] Request N/A — ✓ log 中有对应记录
- Trace#1 [] Request N/A — ✓ log 中有对应记录
- Trace#2 [] Request N/A — ✓ log 中有对应记录
