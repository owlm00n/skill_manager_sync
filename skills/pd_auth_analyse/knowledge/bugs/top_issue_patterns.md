# PD认证测试 — 常见失败模式

> **索引模式 (Index Mode)**: 仅记录 Bug ID + 标题 + 失败摘要 + 链接，不预判根因结论。
> AI 每次重新基于原始证据独立判断，避免结论被历史记录固化。
> **归档说明**: `archive/top_issue_patterns_v1.0.0_inferred.md` 为初版（预判了根因结论），已归档，不可作为分析依据。

---

## 1. CC检测与PD通信时序配合 (CC_TIMING)
- **现象**: Type-C插入后CC检测完成到PD消息发送的时序窗口不满足认证要求
- **涉及测试项**: TD.4.x.x Source/Sink Cap时序测试
- **关键日志**: `sc27xx-typec: now works as DRP and is in X state`
- **关键参数**: tTypeCSendSourceCap, tCCDebounce
- **常见修复**: 调整CC检测debounce时间, 优化PD消息发送时序

## 2. PD协议栈状态机实现缺陷 (PD_STATE_MACHINE)
- **现象**: PR_Swap/DR_Swap状态转换时序不满足PD 3.0/3.1规范
- **涉及测试项**: TD.4.8.x PR_Swap, TD.4.9.x DR_Swap
- **关键参数**: tPSSourceOn, tPSSourceOff, tSwapSinkWaitCap
- **常见修复**: 对齐状态机timer值到PD规范

### 2a. PD 2.0 PRL_Tx_Layer Message Retransmission Defect — SC27XX CRC-Only GoodCRC Validation (PD_STATE_MACHINE — ✅ confirmed, 2 cases)
- **状态**: ✅ confirmed — 代码级验证通过 (2026-09-28)
- **代码证据**: `sprd_tcpm.c:974` unconditional `message_id++` on TX_SUCCESS; `sc27xx_pd.c:2348-2352` TX_OK_FLAG fires on CRC-only validation; `sc27xx_pd.c:150-162` no MessageID validation register bit in CFG1; zero `nRetryCount` in all 7 source files; zero `PRL_Tx` state machine in software; zero `PD_SPEC_REVISION` branches for retry/validation
- **触发Case**: [[SPCSS01702417]] (UMS9230E/LONGCHEER_BU2, ALL.01, 2026-09-23, Phase 6 code-verified 2026-09-28), [[SPCSS01702421]] (UMS9230E/LONGCHEER_BU2, ALL.02, same platform/DUT/date)
- **现象**: PD 2.0 (PD_SPEC_REVISION_2) 模式下 TEST.PD.PROT.ALL.01/ALL.02 测试 FAIL，PD 3.0 (PD_SPEC_REVISION_3) 模式下同一 DUT 同一测试项 PASS。
  - **ALL.01 表现 (SPCSS01702417)**: Check #10 (nRetryCount=2 retransmission after wrong MessageID GoodCRC) FAIL + Check #11 (retransmission with same MessageID at 35μs AMS interrupt gap) FAIL。
  - **ALL.02 表现 (SPCSS01702421)**: Check #5 (nRetryCount retransmission after CRC error) FAIL (0x000001F5) + Check #15 (retransmission after CRC error — second scenario) FAIL (0x000001F5) + Check #19 (Hard Reset escalation after nRetryCount exhaustion) FAIL (0x00000273)。
- **根因**: **代码验证确认** — SC27XX PD Controller 硬件仅校验 GoodCRC 的 CRC，不校验 MessageID。`SC27XX_PD_CFG1` 寄存器无 MessageID 校验控制位。硬件在 CRC 有效但 MessageID 不匹配时报告 `TX_OK`，驱动层 `sprd_tcpm_pd_transmit()` 无条件递增 `message_id`，不触发重传。软件无 `nRetryCount` 计数器、无 `PRL_Tx` 状态机、无 `PD_SPEC_REVISION` 条件分支 — 所有 TX 层管理完全委托给无法检测 MessageID 不匹配的硬件。
- **5 个确认缺陷**: (1) SC27XX_PD_CFG1 无 MessageID 校验控制位 (sc27xx_pd.c:150-162); (2) ISR TX_OK_FLAG 无条件报告 TX_SUCCESS (sc27xx_pd.c:2348-2352); (3) sprd_tcpm_pd_transmit() 无条件递增 message_id (sprd_tcpm.c:974); (4) 代码无 nRetryCount 计数器 — grep 零匹配; (5) 软件无 PRL_Tx_Layer 状态机 — grep 零匹配
- **诊断特征**: (1) Rev2Src 阶段 FAIL, Rev3ChkdSrc 阶段 PASS — 差异化变量为 PD_SPEC_REVISION_2 vs PD_SPEC_REVISION_3; (2) ALL.01: Check #5 (CRC 错误重试) PASS 但 Check #10 (MessageID 不匹配重试) FAIL — 重试仅由 CRC 错误门控; (3) ALL.01: Check #11 Error(0x0000050F) 在 AMS 中断间隙 35μs 时以相同 MessageID 重传; (4) Common Checks (Preamble/Header/GoodCRC) 全部 PASS — 物理层/链路层无异常
- **排除标准**: Common Checks 全 PASS; Rev3ChkdSrc 全 PASS
- **关键代码路径**: sprd_tcpm.c:972-975 (MSGID inc), sc27xx_pd.c:2348-2352 (TX_OK ISR), sc27xx_pd.c:150-162 (CFG1 register), sc27xx_pd.c:1725 (GoodCRC PKG_RV dispatch)
- **影响范围**: TEST.PD.PROT.ALL.01 (Corrupted GoodCRC), TEST.PD.PROT.ALL.02 (Soft Reset and Hard Reset), 可能影响所有 PD 2.0 模式 PROT.ALL 系列测试; 共享根因 — SPCSS01702421 极可能被同一修复解决
- **建议措施**: (1) 应用 MessageID 校验 + nRetryCount fix 到 sprd_tcpm_pd_transmit() (diff 见 SPCSS01702417/06_code_root_cause.md Section 7); (2) 添加 retry_counter + last_goodcrc_msgid 字段到 struct sprd_tcpm_port; (3) 在 sc27xx_pd_read_message() 提取 received GoodCRC MessageID 传递给 TCPM 层; (4) 跨应用 fix 到 SPCSS01702421; (5) 修复后 Rev2Src 模式回归 ALL PROT 系列
- **严重度**: 🔴 Critical — 影响 PD 2.0 模式所有重传场景，PD 认证 PROT.ALL 系列测试阻塞


## 3. TCPCI/PD Controller IC通信异常 (TCPCI_COMM)
- **现象**: I2C通信超时、TCPCI Alert未及时响应、Message Buffer配置错误
- **关键日志**: `tcpci_transmit`, `tcpci_read`, `tcpci_write`
- **关键路径**: `/sys/bus/i2c/devices/*/`
- **常见修复**: 检查I2C时序配置, 确认Alert中断处理优先级

## 4. BC1.2检测干扰PD通信 (BC12_INTERFERENCE)
- **现象**: BC1.2检测流程延迟导致PD SourceCap/SinkCap消息发送超时
- **关键函数**: `vbos_ok_work`, BC1.2检测状态机
- **排查方法**: 临时禁用BC1.2检测验证是否改善
- **常见修复**: 调整BC1.2检测与PD通信的时序关系

## 5. VBUS限流/HIZ控制异常 (VBUS_CONTROL)
- **现象**: 认证测试要求特定Vbus状态(HiZ/限流)未正确设置
- **关键日志**: `sgm41512_set_vinlimit`, `musb_gadget_vbus_draw`
- **常见修复**: 检查Charger Manager投票逻辑

## 6. 认证Patch适配不完整 (PATCH_ADAPTATION)
- **现象**: 不同平台/项目间Type-C认证patch合入不完整或冲突
- **排查方法**: Gerrit搜索 `typec认证`/`pd认证`/`欧代认证`
- **常见修复**: 对齐认证实验室测试脚本版本, 确认patch合入完整

## 7. 客户充电框架替换导致平台PD限流通路断开 (CHARGER_FRAMEWORK_REPLACEMENT — provisional, 1 case)
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

## 8. LeCroy CTS 工具缺陷类 (TESTER_CONDITION_TABLE_ERRATA — provisional parent, 2 cases)

> **父模式**: LeCroy v8.1.3 USB Compliance Suite 固件行为变化导致的测试工具侧缺陷（非 DUT 缺陷）。

### 8a. EPR=No 条件表分支缺失 (TESTER_CONDITION_TABLE_ERRATA — provisional, 1 case)
- **状态**: ⚠️ provisional — 积累 ≥3 独立 case 后去 provisional
- **触发Case**: [[SPCSS01702390]] (UMS9230E/LONGCHEER_BU2, 2026-09-22)
- **现象**: VIF EPR_Supported_As_Src=No 场景下，DUT 在 TEST.PD.EPR.SRC3.01 步骤 4 正确回复 Not_Supported 后，LeCroy 8.1.3 条件表未能正确跳转 N/A，继续执行 EPR 后段步骤检查并全部 FAIL (Error 0x6D)。
- **根因**: LeCroy 8.1.3 (基于 Q2 2025 OR CTS) 的条件表 #6/#7/#8/#10/#11 缺少 EPR=No+Not_Supported → N/A 跳转分支。CTS Q3 2024 Revision History 已有对应 "TEST.PD.EPR.SRC3.1 condition table errata fix" 但 LeCroy 8.1.3 未完整合入。
- **诊断特征**: (1) 相同触发条件(EPR=No+Not_Supported+no EPR entry)产生矛盾裁决 — #3/#4/#5/#9 正确标记 N/A，但 #6/#7/#8/#10/#11 错误标记 FAIL; (2) 所有 FAIL 共享 Error(0x6D); (3) Common Checks 41/41 PASS; (4) 步骤 4b (#2) DUT 正确回复 Not_Supported; (5) 内核日志无 PD 错误。
- **排除标准**: Common Checks 41/41 PASS; SPR bring-up (BU.1) 全 PASS; DUT Not_Supported 响应正确; kernel log 无 PD 协议错误
- **影响范围**: TEST.PD.EPR.SRC3.01 的 #6 (EPR_Source_Capabilities), #7 (EPR_Request response), #8 (PS_RDY EPR), #10 (EPR contract), #11 (SPR contract)。可能影响 SRC3.2/SNK3.01 等其他 EPR 测试项。
- **建议措施**: (1) 实验室使用 LeCroy 7.9.2 或含完整 Q3 2024 errata fix 的版本重跑; (2) DUT 无需修改 — 行为完全符合规范; (3) 与 LeCroy 技术支持确认条件表 errata 合入状态
- **涉及测试项**: TEST.PD.EPR.SRC3.01 EPR Entry Process (UUT as VCONN Source)
- **严重度**: 🟡 Medium — 仅影响认证测试结果判定，不影响 DUT 功能

### 8b. IsReadyToRun() VIF 验证严格化 — Alt Mode 字段评估变化 (TESTER_ISREADYTORUN_VIF_ALTMODE — provisional, 1 case)
- **状态**: ⚠️ provisional — 积累 ≥3 独立 case 后去 provisional
- **触发Case**: [[SPCSS01702428]] (UMS9230E/LONGCHEER_BU2, 2026-09-23)
- **现象**: DUT VIF 正确声明 `Modal_Operation_Supported_SOP=NO`, `Type_C_Is_Alt_Mode_Adapter=NO`, `SVID_Fixed_SOP=0xFF` (USB 2.0-only 设备，无 Alt Mode 硬件)。LeCroy v8.1.3 `IsReadyToRun()` 返回 0，显示 "Unable to detect the necessary parameters for testing"，测试 FAIL。test elapsed time ~2s（测试实际未运行），无任何 PD Alt Mode (VDM) 消息交换。v7.9.2 上此测试通过（推测为 N/A skip）。
- **根因**: LeCroy v8.1.3 将 Alt Mode VIF 字段验证从适用性检查阶段推迟到过程内 `IsReadyToRun()` 阶段。v7.9.2 的适用性检查可能包含 `Type_C_Is_Alt_Mode_Controller=YES` 条件，提前将不适用设备标记为 N/A。v8.1.3 适用性检查仅验证 `USB_PD_Support=YES` + `Type_C_State_Machine != SRC`，将 Alt Mode Controller 检查推迟到 VIF 验证阶段，导致 `Modal_Operation_Supported_SOP=NO` 的合法 USB 2.0-only DUT 从 N/A 变为 FAIL。
- **诊断特征**: (1) 所有 Preliminary steps (Cable Detection, Cable Orientation, VBus Self-Test) PASS; (2) 无任何 PD Alt Mode (VDM) 消息交换; (3) `IsReadyToRun()::result = 0`; (4) VIF `Modal_Operation_Supported_SOP=NO`, `SVID_Fixed_SOP=0xFF`; (5) "Unable to detect the necessary parameters" 通用错误; (6) test elapsed ~2s; (7) PD 合约协商成功 (Source Capabilities → Request → Accept → PS_RDY → DR_SWAP)
- **排除标准**: PD 合约协商成功; kernel log 无 PD 错误; charger IC (sc89601) 正常; VBUS 4.978V / CC1 1.70V / CC2 1.54V 在 spec 范围内; 所有 Preliminary checks 通过
- **影响范围**: TD.4.10.6 Sink Alternate Mode Test。可能影响其他依赖 VIF Alt Mode 字段的 Type-C Functional Test 测试项（如 TD.4.10.x 系列）。
- **建议措施**: (1) 实验室使用 LeCroy 7.9.2 重跑确认 N/A 判定; (2) 向认证实验室/LeCroy 确认 USB 2.0-only 设备是否应豁免 Alt Mode 测试; (3) 不建议修改 VIF 声明 Alt Mode 支持 — DUT 确无 Alt Mode 硬件，修改将构成 VIF 合规违规; (4) 若认证实验室确认 USB 2.0-only 设备应豁免，此为 LeCroy v8.1.3 适用性检查回归 bug，需向 LeCroy 报告
- **涉及测试项**: TD.4.10.6 Sink Alternate Mode Test (Type-C Functional Test)
- **严重度**: 🟡 Medium — 仅影响认证测试结果判定，不影响 DUT 功能；USB 2.0-only 设备对 Alt Mode 认证无功能需求