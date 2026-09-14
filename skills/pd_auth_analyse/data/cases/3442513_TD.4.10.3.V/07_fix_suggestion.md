# Bug 3442513 — 综合修复建议

## 最终根因结论

- **根因**：CC检测与PD通信时序配合
- **置信度**：50%
- **支持证据**：
  - TEST_ID: TD.4.10.3.V
  - 失败现象: 18 fail
  - 失败现象: TD.4.10.3.V.18 fail
  - 失败现象: Check_Class::Verify()::Check if any Bring-up has failed.
  - Log 分析: - **命中事件数**：33672
- **备选原因**：
  - VBUS限流/HIZ控制异常

## 修复建议

### 建议 1: 函数 `sc27xx_typec_state_machine` 在客户代码中与参考代码有差异，建议对齐

- **类型**：code_patch
- **优先级**：high
- **文件**：`E:\08_Bug\CQ\Bug 3442513(SPCSS01672238) - [UMS9230H][HUAQIN_BD2][PD draws power greater than 25 mW\Attachements\0610\vivo-sgm41512_charger_new.c\vivo-sgm41512_charger_new-200265d96c322e17975db3308808df60.c`
- **函数**：`sc27xx_typec_state_machine`
- **diff**：
```
有差异
```

### 建议 2: 函数 `typec_send_source_cap` 在客户代码中与参考代码有差异，建议对齐

- **类型**：code_patch
- **优先级**：high
- **文件**：`E:\08_Bug\CQ\Bug 3442513(SPCSS01672238) - [UMS9230H][HUAQIN_BD2][PD draws power greater than 25 mW\Attachements\0610\vivo-sgm41512_charger_new.c\vivo-sgm41512_charger_new-200265d96c322e17975db3308808df60.c`
- **函数**：`typec_send_source_cap`
- **diff**：
```
有差异
```

### 建议 3: 函数 `cc_detect_debounce` 在客户代码中与参考代码有差异，建议对齐

- **类型**：code_patch
- **优先级**：high
- **文件**：`E:\08_Bug\CQ\Bug 3442513(SPCSS01672238) - [UMS9230H][HUAQIN_BD2][PD draws power greater than 25 mW\Attachements\0610\vivo-sgm41512_charger_new.c\vivo-sgm41512_charger_new-200265d96c322e17975db3308808df60.c`
- **函数**：`cc_detect_debounce`
- **diff**：
```
有差异
```

### 建议 4: 函数 `musb_gadget_vbus_draw` 在客户代码中与参考代码有差异，建议对齐

- **类型**：code_patch
- **优先级**：high
- **文件**：`E:\08_Bug\CQ\Bug 3442513(SPCSS01672238) - [UMS9230H][HUAQIN_BD2][PD draws power greater than 25 mW\Attachements\0610\vivo-sgm41512_charger_new.c\vivo-sgm41512_charger_new-200265d96c322e17975db3308808df60.c`
- **函数**：`musb_gadget_vbus_draw`
- **diff**：
```
有差异
```

### 建议 5: 函数 `charger_manager_vbus_control` 在客户代码中与参考代码有差异，建议对齐

- **类型**：code_patch
- **优先级**：high
- **文件**：`E:\08_Bug\CQ\Bug 3442513(SPCSS01672238) - [UMS9230H][HUAQIN_BD2][PD draws power greater than 25 mW\Attachements\0610\vivo-sgm41512_charger_new.c\vivo-sgm41512_charger_new-200265d96c322e17975db3308808df60.c`
- **函数**：`charger_manager_vbus_control`
- **diff**：
```
有差异
```

### 建议 6: 调整 PD 状态机相关 timer 参数

- **类型**：parameter_tuning
- **优先级**：high
- **文件**：`drivers/usb/typec/sc27xx-typec.c`
- **函数**：`sc27xx_typec_state_machine`
- **diff**：
```
// 建议检查 tTypeCSendSourceCap / tCCDebounce 配置
```

## 参数调优建议

| 参数 | 当前值 | 建议值 | 理由 |
|------|--------|--------|------|
| tTypeCSendSourceCap | (需确认) | ≤150ms (规范要求) | CC 检测到 Rp 后需在 tTypeCSendSourceCap 内发送 SourceCap |
| tCCDebounce | (需确认) | ≤200ms (规范要求) | CC 去抖时间影响连接检测稳定性 |

## 复测验证步骤

1. **在修改后的代码上重新运行 TD.4.10.3.V 测试**
   - 预期 log：kernel log 中无异常错误信息
   - 预期 trace：trace 中消息序列完整
2. **检查 PD 状态机转换是否正常**
   - 预期 log：log 中 sc27xx-typec 状态机无异常跳转
   - 预期 trace：trace 中 SourceCap/SinkCap 消息按时序发送
3. **运行完整 TD.4.x 认证测试套件确认无回归**
   - 预期 log：所有测试项 PASS
   - 预期 trace：无异常 trace

## 自学习反馈

- 已回写 keyword-vault: CC检测与PD通信时序配合...
