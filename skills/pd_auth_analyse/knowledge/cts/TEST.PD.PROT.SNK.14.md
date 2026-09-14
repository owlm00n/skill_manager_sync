# TEST.PD.PROT.SNK.14: Valid Use of GoodCRC on Power up

## 测试目的
验证 Sink 设备在刚上电后收到 Source_Capabilities 时，不会在完全准备好之前过早发送 GoodCRC。Tester 在上电后仅等待 1ms 就发送 Source_Capabilities，检查 UUT 是否能在发送第一个 GoodCRC 后的 tReceiverResponse 时间内正确回复 Request Message。

## 测试配置
- 角色: Sink (DUT)
- Tester: Source (发送 Source_Capabilities)
- 设备: Lecroy Voyager M310e / USB Compliance Suite

## 测试条件 (Test Conditions)

| Condition Code | 适用 UUT 类型 |
|---------------|--------------|
| Rev2Snk | Consumer Only, DRP, Consumer/Provider |
| Rev3ChkdSnk | Consumer Only, DRP, Consumer/Provider |

> 注: Provider Only 和 Provider/Consumer 不适用此测试。

## 测试步骤

| Step | Tester 操作 | DUT 预期响应 | Timer/限值 |
|------|------------|-------------|-----------|
| 1 | 测试从断开状态开始 | — | — |
| 2 | 施加 Rp | UUT 检测到连接 | — |
| 3 | 检测到 UUT 连接后，施加 VCONN (如检测到 Ra) 和 vSafe5V | — | — |
| 4 | **等待 1ms** | — | — |
| 5 | 发送 Source_Capabilities (单 PDO: 5V @ 100mA, Source only) | UUT 回复 GoodCRC | — |
| 6 | 如未收到 GoodCRC，延迟 tTypeCSendSourceCap (min~max) 后重发 Source_Capabilities，**至少重复 50 次** | — | tTypeCSendSourceCap < 100ms |
| 7 | — | UUT 在发送第一个 GoodCRC 后的 tReceiverResponse 内回复 Request Message | tReceiverResponse < 15ms |
| 8 | 回复 Accept Message | — | tSenderResponse < 30ms |
| 9 | VBUS 稳定后，在 tSrcTransReq max 内发送 PS_RDY | — | tSrcTransReq |
| 10 | 显式合约建立 | — | — |

## 判定标准
- [ ] UUT 在发送第一个 GoodCRC 后，tReceiverResponse (15ms) 内发送 Request Message
- [ ] UUT 不会在完全初始化之前过早发送 GoodCRC

## 唯一检查点 (Check ID)
- **[TEST.PD.PROT.SNK.14#1]**: The check fails if the UUT does not respond with a Request Message, within tReceiverResponse of the UUT sending the first GoodCRC.

## 常见失败模式

- **Request Message 发送超时 (tReceiverResponse > 15ms)**: Sink 在 GoodCRC 后未能在 15ms 内发送 Request
  → 通常原因: PD 协议栈在构建 Request (Build Request) 路径中存在阻塞操作，如 I2C 通信、power_supply 属性设置 (`POWER_SUPPLY_SET_PROPERTY`)、charger IC 限流配置等耗时操作占用了消息发送时间窗口
  → 调试方法: 在 `sprd_tcpm_pd_build_request()` 和 `sprd_tcpm_set_cm_ic_limit_current()` 路径中插入时间戳 log，定位具体耗时点在哪个函数调用

- **power_supply_get_by_name("battery") 导致路径阻塞**: 每次构建 Request 时动态查找 battery psy 设备
  → 通常原因: `power_supply_get_by_name()` 在 power supply 子系统中遍历查找，涉及链表遍历和锁竞争，耗时可达 ~30ms，远超 tReceiverResponse 限值
  → 修复方案: 将 `batt_psy = power_supply_get_by_name("battery")` 移至 probe 阶段 (`sprd_tcpm_register_port`) 赋值给全局静态变量 `static struct power_supply *batt_psy`，在 shutdown 和 unregister 时置 NULL

- **charger IC 限流配置耗时**: `g_sprd_charger_ops->negotiated_limit_current()` 回调中 I2C 写 charger IC 寄存器
  → 通常原因: I2C 总线竞争或 charger IC 响应慢，导致 `sprd_tcpm_set_cm_ic_limit_current()` 整体耗时 > 10ms
  → 缓解方案: 检查 charger ops 回调路径是否有可优化的锁等待或 I2C 重试逻辑

- **偶发性超时**: 非每次必现的超时
  → 通常原因: 系统负载变化 (如后台线程调度、中断风暴) 导致 PD 状态机工作线程被抢占，偶发性的延迟累积
  → 定位方法: 单 case 单测，在 fail 时立即导出 ylog，对比 pass/fail 时的时间戳差异

## 参考 Bug 案例
- **Bug 3397942**: TEST.PD.PROT.SNK.14#1 Fail — Request Message 超时 (tReceiverResponse > 15ms)，根因定位为 `power_supply_get_by_name("battery")` → `POWER_SUPPLY_SET_PROPERTY` 路径耗时 ~30ms，修复方案为 probe 阶段缓存 `batt_psy` 全局变量，修复后 3/3 PASS
- **Bug 2821559**: TEST.PD.PROT.SNK.14 Fail — EU 认证 (EN IEC 62680-1-3/1-2) 测试中 SNK.14 失败

---

## 来源
- 官方规范: `knowledge/specs/USB_PD3_CTS_Q4_2024_OR.pdf`, Section 5.4.1, Page 171-172
- 实测数据: `ref/pd_bugs_detail.json`, Bug 3397942
- Timer 规范: `knowledge/specs/pd_protocol_timers.md`