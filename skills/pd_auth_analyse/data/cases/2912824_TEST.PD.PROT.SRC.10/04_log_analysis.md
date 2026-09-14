# Bug 2912824 — Log 分析

## 结论

- **分析器**：`log-analyzer`
- **log 文件数**：6
- **关键字数**：12
- **命中事件数**：12
- **按候选根因分布**：
  - CC检测与PD通信时序配合: 12 次

## 关键事件时间线

| # | 时间戳 | 文件 | 行号 | 命中关键字 | 归属假设 | 原文 |
|---|--------|------|------|------------|----------|------|
| 1 |  | md_20250216-161322.log | 7 | event | CC检测与PD通信时序配合 | ~~~~ZZ	\[~~~~4ZZp	\,2912022d000130~~~~ZZ	\(srmi uart: get event EVENT_DATA_TO_READLsrmi_uart_rx dev_handle:-1922952148, buff:0x8cdf16f0, size:256, tim |
| 2 |  | md_20250216-161322.log | 261 | event | CC检测与PD通信时序配合 | vG	vOkYZZZuPނd``ߝ,;+gn5~~~~ZZY](srmi uart: get event EVENT_DATA_TO_READLsrmi_uart_rx dev_handle:-1922952148, buff:0x8cdf16f0, size:256, timeout:0ZZ0sr |
| 3 |  | md_20250216-161322.log | 271 | event | CC检测与PD通信时序配合 | :~~~~ZZn](srmi uart: get event EVENT_DATA_TO_READLsrmi_uart_rx dev_handle:-1922952148, buff:0x8cdf16f0, size:256, timeout:0ZZ0srmi_uart_rx max:0, curr |
| 4 |  | md_20250216-161322.log | 281 | event | CC检测与PD通信时序配合 | -;+YJޜq	3hE~~~~ZZ](srmi uart: get event EVENT_DATA_TO_READLsrmi_uart_rx dev_handle:-1922952148, buff:0x8cdf16f0, size:256, timeout:0ZZ0srmi_uart_rx ma |
| 5 |  | md_20250216-161322.log | 294 | event | CC检测与PD通信时序配合 | vG	vAkYZ~~~~ZZ](srmi uart: get event EVENT_DATA_TO_READLsrmi_uart_rx dev_handle:-1922952148, buff:0x8cdf16f0, size:256, timeout:0ZZ0srmi_uart_rx max:0 |
| 6 |  | md_20250216-161322.log | 305 | event | CC检测与PD通信时序配合 | ނd``,;+gn5l l .jGGKO.ڞ}L 6~~~~ZZ](srmi uart: get event EVENT_DATA_TO_READLsrmi_uart_rx dev_handle:-1922952148, buff:0x8cdf16f0, size:256, timeout:0ZZ0 |
| 7 |  | md_20250216-161322.log | 326 | event | CC检测与PD通信时序配合 | :ipqq@E.DU\|YYYZQ~~~~ZZ](srmi uart: get event EVENT_DATA_TO_READLsrmi_uart_rx dev_handle:-1922952148, buff:0x8cdf16f0, size:256, timeout:0ZZ0srmi_uart_ |
| 8 |  | md_20250216-161322.log | 339 | event | CC检测与PD通信时序配合 | I^=*޲***)A)9ޓ(~~~~ZZ](srmi uart: get event EVENT_DATA_TO_READLsrmi_uart_rx dev_handle:-1922952148, buff:0x8cdf16f0, size:256, timeout:0ZZ0srmi_uart_rx |
| 9 |  | md_20250216-161322.log | 351 | event | CC检测与PD通信时序配合 | ނd``ށ,;+go5~~~~ZZ](srmi uart: get event EVENT_DATA_TO_READLsrmi_uart_rx dev_handle:-1922952148, buff:0x8cdf16f0, size:256, timeout:0ZZ0srmi_uart_rx ma |
| 10 |  | md_20250216-161322.log | 363 | event | CC检测与PD通信时序配合 | :i~~~~ZZ](srmi uart: get event EVENT_DATA_TO_READLsrmi_uart_rx dev_handle:-1922952148, buff:0x8cdf16f0, size:256, timeout:0ZZ0srmi_uart_rx max:0, curr |
| 11 |  | slogdbg_19700101-000958.log | 21 | state, event | CC检测与PD通信时序配合 | 1970-01-01  00:09:59.464  [INFO]   process_cp_evt: cptype:4, CpStateHandler::CpEvent:4 |
| 12 |  | slogdbg_20250215-175328.log | 26 | state, event | CC检测与PD通信时序配合 | 2025-02-15  17:53:30.648  [INFO]   process_cp_evt: cptype:0, CpStateHandler::CpEvent:4 |
