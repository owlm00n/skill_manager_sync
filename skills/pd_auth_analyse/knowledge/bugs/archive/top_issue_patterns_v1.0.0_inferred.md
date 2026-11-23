# PD认证测试 — 常见失败模式

## 1. CC检测与PD通信时序配合 (最高频)
- **现象**: Type-C插入后CC检测完成到PD消息发送的时序窗口不满足认证要求
- **涉及测试项**: TD.4.x.x Source/Sink Cap时序测试
- **关键日志**: `sc27xx-typec: now works as DRP and is in X state`
- **关键参数**: tTypeCSendSourceCap, tCCDebounce
- **常见修复**: 调整CC检测debounce时间, 优化PD消息发送时序

## 2. PD协议栈状态机实现缺陷
- **现象**: PR_Swap/DR_Swap状态转换时序不满足PD 3.0/3.1规范
- **涉及测试项**: TD.4.8.x PR_Swap, TD.4.9.x DR_Swap
- **关键参数**: tPSSourceOn, tPSSourceOff, tSwapSinkWaitCap
- **常见修复**: 对齐状态机timer值到PD规范

## 3. TCPCI/PD Controller IC通信异常
- **现象**: I2C通信超时、TCPCI Alert未及时响应、Message Buffer配置错误
- **关键日志**: `tcpci_transmit`, `tcpci_read`, `tcpci_write`
- **关键路径**: `/sys/bus/i2c/devices/*/`
- **常见修复**: 检查I2C时序配置, 确认Alert中断处理优先级

## 4. BC1.2检测干扰PD通信
- **现象**: BC1.2检测流程延迟导致PD SourceCap/SinkCap消息发送超时
- **关键函数**: `vbos_ok_work`, BC1.2检测状态机
- **排查方法**: 临时禁用BC1.2检测验证是否改善
- **常见修复**: 调整BC1.2检测与PD通信的时序关系

## 5. VBUS限流/HIZ控制异常
- **现象**: 认证测试要求特定Vbus状态(HiZ/限流)未正确设置
- **关键日志**: `sgm41512_set_vinlimit`, `musb_gadget_vbus_draw`
- **常见修复**: 检查Charger Manager投票逻辑

## 6. 认证Patch适配不完整
- **现象**: 不同平台/项目间Type-C认证patch合入不完整或冲突
- **排查方法**: Gerrit搜索 `typec认证`/`pd认证`/`欧代认证`
- **常见修复**: 对齐认证实验室测试脚本版本, 确认patch合入完整

## 7. 客户充电框架替换导致平台PD限流通路断开 (provisional — 1 case)
- **状态**: ⚠️ provisional — 积累 ≥3 独立 case 后去 provisional
- **触发Case**: SPCSS01699865 (UMS9360/HUAQIN_BD2, 2026-09-17)
- **现象**: PD认证CC眼图测试(TEST.PD.PHY.ALL.2) FAIL, ibus>0 导致CC线电磁耦合噪声。客户充电框架(VFCS)替换了平台 sprd_charger_manager.c, 导致PD协商的电流限制无法到达charger IC。
- **根因**: 充电框架替换(sprd_charger_manager.c → VFCS)后, 平台三条回调(update_ac_usb_online/negotiated_limit_current/set_rp_limit_current)虽然注册, 但框架内部设备ops表(ops[10]/[11])为NULL, PD→charger IC通路断开。
- **关键日志特征**: `ops[10] pfun null` / `ops[11] pfun null`; 无 CHG_PD_VOTER; CHG_DEFAULT_VOTER 未被PD约束
- **关键代码路径**: sprd_tcpm.c → sprd_charger_ops → VFCS vfcs_chg_dev_set_ops() → ops[N] → charger IC
- **排查方法**: 检查 kernel log 中是否有 CHG_PD_VOTER ibus vote; 检查 charger IC 是否有 PD-based 电流限制
- **常见修复**: 完成充电框架设备ops表(ops[10]/[11]), 实现PD协商电流→charger IC寄存器映射。非CC眼图测试专用修复, 对全部PD电力合约都有益。
- **涉及测试项**: TEST.PD.PHY.ALL.2 Transmitter Eye Diagram (CC眼图)
- **严重度**: 🔴 Critical — 所有PD电力合约的电流限制均受影响, 非仅认证
