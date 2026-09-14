# Bug 3442513 — 代码 & Patch 分析

## 结论

- **TEST_ID**：`TD.4.10.3.V`
- **搜索函数数**：6
- **找到函数数**：25
- **Patch 链接数**：2
- **客户代码目录数**：5
- **发现数**：6

## 相关代码定位

| 函数名 | 文件路径 | 行号 |
|--------|----------|------|
| `sc27xx_typec_state_machine ~(fuzzy: sc27xx)` | `sprd_charger/sc27xx_fast_charger.c` | L180 |
| `sc27xx_typec_state_machine ~(fuzzy: sc27xx)` | `sprd_charger/sc27xx_fast_charger.c` | L243 |
| `sc27xx_typec_state_machine ~(fuzzy: sc27xx)` | `sprd_charger/sc27xx_fast_charger.c` | L288 |
| `sc27xx_typec_state_machine ~(fuzzy: sc27xx)` | `sprd_charger/sc27xx_fast_charger.c` | L316 |
| `sc27xx_typec_state_machine ~(fuzzy: sc27xx)` | `sprd_charger/sc27xx_fast_charger.c` | L401 |
| `typec_send_source_cap ~(fuzzy: typec)` | `sprd_charger/sprd_fuel_gauge_core.c` | L3561 |
| `typec_send_source_cap ~(fuzzy: typec)` | `sprd_charger/sprd_vchg_detect.c` | L255 |
| `typec_send_source_cap ~(fuzzy: typec)` | `sprd_charger/sprd_vchg_detect.c` | L320 |
| `typec_send_source_cap ~(fuzzy: typec)` | `power_delivery/sc27xx_pd.c` | L70 |
| `typec_send_source_cap ~(fuzzy: typec)` | `power_delivery/sc27xx_pd.c` | L98 |
| `cc_detect_debounce ~(fuzzy: detect)` | `sprd_charger/fan54015-charger.c` | L1094 |
| `cc_detect_debounce ~(fuzzy: detect)` | `sprd_charger/fan54015-charger.c` | L1149 |
| `cc_detect_debounce ~(fuzzy: detect)` | `sprd_charger/hl7139-charger.c` | L1113 |
| `cc_detect_debounce ~(fuzzy: detect)` | `sprd_charger/hl7139-charger.c` | L2221 |
| `cc_detect_debounce ~(fuzzy: detect)` | `sprd_charger/sc27xx_fast_charger.c` | L288 |
| `musb_gadget_vbus_draw ~(fuzzy: vbus)` | `sprd_charger/fan54015-charger.c` | L960 |
| `musb_gadget_vbus_draw ~(fuzzy: vbus)` | `sprd_charger/fan54015-charger.c` | L1020 |
| `musb_gadget_vbus_draw ~(fuzzy: vbus)` | `sprd_charger/fan54015-charger.c` | L1039 |
| `musb_gadget_vbus_draw ~(fuzzy: vbus)` | `sprd_charger/fan54015-charger.c` | L1083 |
| `musb_gadget_vbus_draw ~(fuzzy: vbus)` | `sprd_charger/fan54015-charger.c` | L1088 |
| `charger_manager_vbus_control ~(fuzzy: charger)` | `sprd_charger/fan54015-charger.c` | L133 |
| `charger_manager_vbus_control ~(fuzzy: charger)` | `sprd_charger/fan54015-charger.c` | L168 |
| `charger_manager_vbus_control ~(fuzzy: charger)` | `sprd_charger/fan54015-charger.c` | L182 |
| `charger_manager_vbus_control ~(fuzzy: charger)` | `sprd_charger/fan54015-charger.c` | L198 |
| `charger_manager_vbus_control ~(fuzzy: charger)` | `sprd_charger/fan54015-charger.c` | L224 |

## Patch / Gerrit 链接

- [http://uni-patch.unisoc.com/](http://uni-patch.unisoc.com/) — ? 未确认
  - 需人工确认是否已合入客户代码
- [http://uni-patch.unisoc.com/add-samplecode](http://uni-patch.unisoc.com/add-samplecode) — ? 未确认
  - 需人工确认是否已合入客户代码

## 客户代码 vs 参考代码 Diff

- `sc27xx_typec_state_machine`: 客户代码与参考代码有差异 → E:\08_Bug\CQ\Bug 3442513(SPCSS01672238) - [UMS9230H][HUAQIN_BD2][PD draws power greater than 25 mW\Attachements\0610\vivo-sgm41512_charger_new.c\vivo-sgm41512_charger_new-200265d96c322e17975db3308808df60.c:4536
- `typec_send_source_cap`: 客户代码与参考代码有差异 → E:\08_Bug\CQ\Bug 3442513(SPCSS01672238) - [UMS9230H][HUAQIN_BD2][PD draws power greater than 25 mW\Attachements\0610\vivo-sgm41512_charger_new.c\vivo-sgm41512_charger_new-200265d96c322e17975db3308808df60.c:4113
- `cc_detect_debounce`: 客户代码与参考代码有差异 → E:\08_Bug\CQ\Bug 3442513(SPCSS01672238) - [UMS9230H][HUAQIN_BD2][PD draws power greater than 25 mW\Attachements\0610\vivo-sgm41512_charger_new.c\vivo-sgm41512_charger_new-200265d96c322e17975db3308808df60.c:3087
- `musb_gadget_vbus_draw`: 客户代码与参考代码有差异 → E:\08_Bug\CQ\Bug 3442513(SPCSS01672238) - [UMS9230H][HUAQIN_BD2][PD draws power greater than 25 mW\Attachements\0610\vivo-sgm41512_charger_new.c\vivo-sgm41512_charger_new-200265d96c322e17975db3308808df60.c:192
- `charger_manager_vbus_control`: 客户代码与参考代码有差异 → E:\08_Bug\CQ\Bug 3442513(SPCSS01672238) - [UMS9230H][HUAQIN_BD2][PD draws power greater than 25 mW\Attachements\0610\vivo-sgm41512_charger_new.c\vivo-sgm41512_charger_new-200265d96c322e17975db3308808df60.c:2708

## 发现

| 函数 | 归属假设 | 客户代码中 | 严重度 | 摘要 |
|------|----------|------------|--------|------|
| `sc27xx_typec_state_machine` | CC检测与PD通信时序配合 | ✓ | warning | 有差异 |
| `typec_send_source_cap` | CC检测与PD通信时序配合 | ✓ | warning | 有差异 |
| `cc_detect_debounce` | CC检测与PD通信时序配合 | ✓ | warning | 有差异 |
| `sgm41512_set_vinlimit` | VBUS限流/HIZ控制异常 | ✓ | info | 参考代码中未找到 |
| `musb_gadget_vbus_draw` | VBUS限流/HIZ控制异常 | ✓ | warning | 有差异 |
| `charger_manager_vbus_control` | VBUS限流/HIZ控制异常 | ✓ | warning | 有差异 |
