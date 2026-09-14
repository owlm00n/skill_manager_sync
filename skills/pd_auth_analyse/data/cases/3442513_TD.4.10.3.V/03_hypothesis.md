# Bug 3442513 — 根因假设 & 排查地图

## 结论

- **TEST_ID**：`TD.4.10.3.V`
- **失败现象**：
  - 18 fail
  - TD.4.10.3.V.18 fail
  - Check_Class::Verify()::Check if any Bring-up has failed.
  - Error(0x000000FA): The PUT draws power greater than 25 mW.
  - Verification Result: FAILED
- **keyword-vault 推荐关键字**：`fail`

## Top-3 候选根因

### #1. CC检测与PD通信时序配合  （置信度 40%）

**支持证据**：
- 18 fail
- TD.4.10.3.V.18 fail
- Check_Class::Verify()::Check if any Bring-up has failed.

**Log 搜索关键字**（供 Step 4）：
```
sc27xx-typec DRP state event tTypeCSendSourceCap tCCDebounce
```

**代码定位函数**（供 Step 6）：
- `sc27xx_typec_state_machine`
- `typec_send_source_cap`
- `cc_detect_debounce`

**判定理由**：基于失败现象 + TEST_ID(TD.4.10.3.V) + keyword-vault 推荐关键字综合打分

### #2. VBUS限流/HIZ控制异常  （置信度 40%）

**支持证据**：
- 18 fail
- TD.4.10.3.V.18 fail
- Check_Class::Verify()::Check if any Bring-up has failed.

**Log 搜索关键字**（供 Step 4）：
```
sgm41512_set_vinlimit musb_gadget_vbus_draw HIZ vinlimit
```

**代码定位函数**（供 Step 6）：
- `sgm41512_set_vinlimit`
- `musb_gadget_vbus_draw`
- `charger_manager_vbus_control`

**判定理由**：基于失败现象 + TEST_ID(TD.4.10.3.V) + keyword-vault 推荐关键字综合打分

## 排查地图

按以下顺序排查，每步产物保存后进入下一步：

1. 假设 **CC检测与PD通信时序配合** → 用关键字 ['sc27xx-typec', 'DRP', 'state'] 在 log 中搜索 → 定位函数 ['sc27xx_typec_state_machine', 'typec_send_source_cap']
2. 假设 **VBUS限流/HIZ控制异常** → 用关键字 ['sgm41512_set_vinlimit', 'musb_gadget_vbus_draw', 'HIZ'] 在 log 中搜索 → 定位函数 ['sgm41512_set_vinlimit', 'musb_gadget_vbus_draw']
