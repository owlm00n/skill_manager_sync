# Bug 2912824 — 代码 & Patch 分析

## 结论

- **TEST_ID**：`TEST.PD.PROT.SRC.10`
- **搜索函数数**：7
- **找到函数数**：30
- **Patch 链接数**：0
- **客户代码目录数**：0
- **发现数**：7

## 相关代码定位

| 函数名 | 文件路径 | 行号 |
|--------|----------|------|
| `sprd_tcpm_pd_swap ~(fuzzy: sprd)` | `sprd_charger/fan54015-charger.c` | L230 |
| `sprd_tcpm_pd_swap ~(fuzzy: sprd)` | `sprd_charger/sgm41511-charger.c` | L517 |
| `sprd_tcpm_pd_swap ~(fuzzy: sprd)` | `sprd_charger/sprd-bc1p2.c` | L90 |
| `sprd_tcpm_pd_swap ~(fuzzy: sprd)` | `sprd_charger/sprd-bc1p2.c` | L108 |
| `sprd_tcpm_pd_swap ~(fuzzy: sprd)` | `sprd_charger/sprd-bc1p2.c` | L125 |
| `sprd_tcpm_dr_swap ~(fuzzy: sprd)` | `sprd_charger/fan54015-charger.c` | L230 |
| `sprd_tcpm_dr_swap ~(fuzzy: sprd)` | `sprd_charger/sgm41511-charger.c` | L517 |
| `sprd_tcpm_dr_swap ~(fuzzy: sprd)` | `sprd_charger/sprd-bc1p2.c` | L90 |
| `sprd_tcpm_dr_swap ~(fuzzy: sprd)` | `sprd_charger/sprd-bc1p2.c` | L108 |
| `sprd_tcpm_dr_swap ~(fuzzy: sprd)` | `sprd_charger/sprd-bc1p2.c` | L125 |
| `pe_src_send_swap ~(fuzzy: src)` | `sprd_charger/hl7139-charger.c` | L1453 |
| `pe_src_send_swap ~(fuzzy: src)` | `sprd_charger/hl7139-charger.c` | L1597 |
| `pe_src_send_swap ~(fuzzy: src)` | `sprd_charger/sc8546-charger.c` | L1265 |
| `pe_src_send_swap ~(fuzzy: src)` | `sprd_charger/sc8546-charger.c` | L1313 |
| `pe_src_send_swap ~(fuzzy: src)` | `sprd_charger/sprd_charger_manager.c` | L6197 |
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

## 客户代码 vs 参考代码 Diff

（无 diff 数据，可能缺少客户代码或参考代码）

## 发现

| 函数 | 归属假设 | 客户代码中 | 严重度 | 摘要 |
|------|----------|------------|--------|------|
| `sprd_tcpm_pd_swap` | PD协议栈状态机实现缺陷 | ✗ | info | 参考代码命中 5 处 (如 sprd_charger/fan54015-charger.c:L230)，客户代码缺失 |
| `sprd_tcpm_dr_swap` | PD协议栈状态机实现缺陷 | ✗ | info | 参考代码命中 5 处 (如 sprd_charger/fan54015-charger.c:L230)，客户代码缺失 |
| `pe_src_send_swap` | PD协议栈状态机实现缺陷 | ✗ | info | 参考代码命中 5 处 (如 sprd_charger/hl7139-charger.c:L1453)，客户代码缺失 |
| `pd_state_machine` | PD协议栈状态机实现缺陷 | ✗ | info | 客户代码和参考代码中均未找到 |
| `sc27xx_typec_state_machine` | CC检测与PD通信时序配合 | ✗ | info | 参考代码命中 5 处 (如 sprd_charger/sc27xx_fast_charger.c:L180)，客户代码缺 |
| `typec_send_source_cap` | CC检测与PD通信时序配合 | ✗ | info | 参考代码命中 5 处 (如 sprd_charger/sprd_fuel_gauge_core.c:L3561)，客户代 |
| `cc_detect_debounce` | CC检测与PD通信时序配合 | ✗ | info | 参考代码命中 5 处 (如 sprd_charger/fan54015-charger.c:L1094)，客户代码缺失 |
