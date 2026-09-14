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
