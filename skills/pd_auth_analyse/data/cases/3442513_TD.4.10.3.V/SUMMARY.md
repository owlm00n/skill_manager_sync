# Bug 3442513 — 分析总结

**TEST_ID**: `TD.4.10.3.V`

## Bug 信息

- **Bug ID**: 3442513
- **测试项**: TD.4.10.3.V

## 最终根因

**CC检测与PD通信时序配合**（置信度 50%）

支持证据：
- TEST_ID: TD.4.10.3.V
- 失败现象: 18 fail
- 失败现象: TD.4.10.3.V.18 fail
- 失败现象: Check_Class::Verify()::Check if any Bring-up has failed.
- Log 分析: - **命中事件数**：33672

## 修复建议

- [HIGH] 函数 `sc27xx_typec_state_machine` 在客户代码中与参考代码有差异，建议对齐
  - 文件: `E:\08_Bug\CQ\Bug 3442513(SPCSS01672238) - [UMS9230H][HUAQIN_BD2][PD draws power greater than 25 mW\Attachements\0610\vivo-sgm41512_charger_new.c\vivo-sgm41512_charger_new-200265d96c322e17975db3308808df60.c`
- [HIGH] 函数 `typec_send_source_cap` 在客户代码中与参考代码有差异，建议对齐
  - 文件: `E:\08_Bug\CQ\Bug 3442513(SPCSS01672238) - [UMS9230H][HUAQIN_BD2][PD draws power greater than 25 mW\Attachements\0610\vivo-sgm41512_charger_new.c\vivo-sgm41512_charger_new-200265d96c322e17975db3308808df60.c`
- [HIGH] 函数 `cc_detect_debounce` 在客户代码中与参考代码有差异，建议对齐
  - 文件: `E:\08_Bug\CQ\Bug 3442513(SPCSS01672238) - [UMS9230H][HUAQIN_BD2][PD draws power greater than 25 mW\Attachements\0610\vivo-sgm41512_charger_new.c\vivo-sgm41512_charger_new-200265d96c322e17975db3308808df60.c`
- [HIGH] 函数 `musb_gadget_vbus_draw` 在客户代码中与参考代码有差异，建议对齐
  - 文件: `E:\08_Bug\CQ\Bug 3442513(SPCSS01672238) - [UMS9230H][HUAQIN_BD2][PD draws power greater than 25 mW\Attachements\0610\vivo-sgm41512_charger_new.c\vivo-sgm41512_charger_new-200265d96c322e17975db3308808df60.c`
- [HIGH] 函数 `charger_manager_vbus_control` 在客户代码中与参考代码有差异，建议对齐
  - 文件: `E:\08_Bug\CQ\Bug 3442513(SPCSS01672238) - [UMS9230H][HUAQIN_BD2][PD draws power greater than 25 mW\Attachements\0610\vivo-sgm41512_charger_new.c\vivo-sgm41512_charger_new-200265d96c322e17975db3308808df60.c`
- [HIGH] 调整 PD 状态机相关 timer 参数
  - 文件: `drivers/usb/typec/sc27xx-typec.c`

## 参数调优

- `tTypeCSendSourceCap`: (需确认) → ≤150ms (规范要求)
- `tCCDebounce`: (需确认) → ≤200ms (规范要求)

## 复测验证

1. 在修改后的代码上重新运行 TD.4.10.3.V 测试
2. 检查 PD 状态机转换是否正常
3. 运行完整 TD.4.x 认证测试套件确认无回归
