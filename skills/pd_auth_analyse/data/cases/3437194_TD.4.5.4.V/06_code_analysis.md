# Bug 3437194 — 代码 & Patch 分析

## 结论

- **TEST_ID**：`TD.4.5.4.V`
- **搜索函数数**：3
- **找到函数数**：15
- **Patch 链接数**：2
- **客户代码目录数**：0
- **发现数**：3

## 相关代码定位

| 函数名 | 文件路径 | 行号 |
|--------|----------|------|
| `sc27xx_typec_state_machine ~(fuzzy: sc27xx)` | `sprd_charger/sc27xx_fast_charger.c` | L180 |
| `sc27xx_typec_state_machine ~(fuzzy: sc27xx)` | `sprd_charger/sc27xx_fast_charger.c` | L243 |
| `sc27xx_typec_state_machine ~(fuzzy: sc27xx)` | `sprd_charger/sc27xx_fast_charger.c` | L288 |
| `sc27xx_typec_state_machine ~(fuzzy: sc27xx)` | `sprd_charger/sc27xx_fast_charger.c` | L316 |
| `sc27xx_typec_state_machine ~(fuzzy: sc27xx)` | `sprd_charger/sc27xx_fast_charger.c` | L401 |
| `typec_send_source_cap ~(fuzzy: typec)` | `sprd_charger/sprd_fuel_gauge_core.c` | L3561 |
| `typec_send_source_cap ~(fuzzy: typec)` | `sprd_charger/sprd_fuel_gauge_core_v2.c` | L7211 |
| `typec_send_source_cap ~(fuzzy: typec)` | `sprd_charger/sprd_vchg_detect.c` | L255 |
| `typec_send_source_cap ~(fuzzy: typec)` | `sprd_charger/sprd_vchg_detect.c` | L320 |
| `typec_send_source_cap ~(fuzzy: typec)` | `power_delivery/sc27xx_pd.c` | L70 |
| `cc_detect_debounce ~(fuzzy: detect)` | `sprd_charger/fan54015-charger.c` | L1094 |
| `cc_detect_debounce ~(fuzzy: detect)` | `sprd_charger/fan54015-charger.c` | L1149 |
| `cc_detect_debounce ~(fuzzy: detect)` | `sprd_charger/hl7139-charger.c` | L1113 |
| `cc_detect_debounce ~(fuzzy: detect)` | `sprd_charger/hl7139-charger.c` | L2221 |
| `cc_detect_debounce ~(fuzzy: detect)` | `sprd_charger/sc27xx_fast_charger.c` | L288 |

## Patch / Gerrit 链接

- [http://uni-patch.unisoc.com/](http://uni-patch.unisoc.com/) — ? 未确认
  - 需人工确认是否已合入客户代码
- [http://uni-patch.unisoc.com/add-samplecode](http://uni-patch.unisoc.com/add-samplecode) — ? 未确认
  - 需人工确认是否已合入客户代码

## 客户代码 vs 参考代码 Diff

（无 diff 数据，可能缺少客户代码或参考代码）

## 发现

| 函数 | 归属假设 | 客户代码中 | 严重度 | 摘要 |
|------|----------|------------|--------|------|
| `sc27xx_typec_state_machine` | CC检测与PD通信时序配合 | ✗ | info | 参考代码命中 5 处 (如 sprd_charger/sc27xx_fast_charger.c:L180)，客户代码缺 |
| `typec_send_source_cap` | CC检测与PD通信时序配合 | ✗ | info | 参考代码命中 5 处 (如 sprd_charger/sprd_fuel_gauge_core.c:L3561)，客户代 |
| `cc_detect_debounce` | CC检测与PD通信时序配合 | ✗ | info | 参考代码命中 5 处 (如 sprd_charger/fan54015-charger.c:L1094)，客户代码缺失 |
