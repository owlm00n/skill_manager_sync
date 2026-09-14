# Bug 3476234 — 分析总结

**TEST_ID**: `TEST.PD.PS.SNK.01`

## Bug 信息

- **Bug ID**: 3476234
- **测试项**: TEST.PD.PS.SNK.01

## 最终根因

**CC检测与PD通信时序配合**（置信度 90%）

支持证据：
- TEST_ID: TEST.PD.PS.SNK.01
- 失败现象: TEST.PD.PS.SNK.01 PDO Transitions As Sink测试fail
- Log 分析: - **命中事件数**：14998

## 修复建议

- [HIGH] 调整 PD 状态机相关 timer 参数
  - 文件: `drivers/usb/typec/sc27xx-typec.c`

## 参数调优

- `tTypeCSendSourceCap`: (需确认) → ≤150ms (规范要求)
- `tCCDebounce`: (需确认) → ≤200ms (规范要求)

## 复测验证

1. 在修改后的代码上重新运行 TEST.PD.PS.SNK.01 测试
2. 检查 PD 状态机转换是否正常
3. 运行完整 TD.4.x 认证测试套件确认无回归
