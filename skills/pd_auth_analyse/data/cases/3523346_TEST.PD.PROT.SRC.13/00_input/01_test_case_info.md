# Phase 1: Test Case Info — Bug 3523346 / TEST.PD.PROT.SRC.13

> **分析日期**: 2026-09-10
> **Skill 版本**: pd_auth_analyse v3.0
> **数据来源**: 本报告中每个数据小节末尾标注来源命令和原始文件路径

---

## 1. 输入材料清单

### 1.1 Kernel Logs

| # | 测试日期 | 文件名 | 大小 | 状态 | 路径 |
|---|---------|--------|------|------|------|
| 1 | Aug 21 (初始) | `0-kernel.log` | 1.42 MB | 待解析 | `Attachements\TEST-PD-PROT-SRC-13\TEST-PD-PROT-SRC-13\004-0820_195556_poweron\0-kernel.log` |
| 2 | Aug 24 (复测) | `0-kernel.log` | 1.64 MB | 待解析 | `Attachements\TEST.PD.PROT.SRC.13-8-24\TEST.PD.PROT.SRC.13-8-24\001-0820_044827_poweron\0-kernel.log` |
| 3 | Aug 27 (复测) | `0-kernel.log` | 1.73 MB | 待解析 | `Attachements\TEST.PD.PROT.SRC.13--8-27\20260827_144948\002-0827_040022_poweron\0-kernel.log` |

> **来源**: `python C:/Users/xianjun.zeng/AppData/Local/Temp/list_src13_files.py` — 遍历工作区文件枚举

### 1.2 Lecroy Trace 文件 (.usb 二进制)

| # | 测试日期 | Sub-test | 结果 | 大小 | 路径 |
|---|---------|----------|------|------|------|
| 1 | Aug 21 | Rev2Src | **FAIL** | 7.23 MB | `...\TEST.PD.PROT.SRC.13\01_TEST.PD.PROT.SRC.13_Rev2Src_FAIL.usb` |
| 2 | Aug 21 | Rev3ChkdSrc | **FAIL** | 12.64 MB | `...\TEST.PD.PROT.SRC.13\02_TEST.PD.PROT.SRC.13_Rev3ChkdSrc_FAIL.usb` |
| 3 | Aug 24 | Rev2Src | **PASS** | 7.27 MB | `...\TEST.PD.PROT.SRC.13\01_TEST.PD.PROT.SRC.13_Rev2Src.usb` |
| 4 | Aug 24 | Rev3ChkdSrc | **FAIL** | 12.38 MB | `...\TEST.PD.PROT.SRC.13\02_TEST.PD.PROT.SRC.13_Rev3ChkdSrc_FAIL.usb` |
| 5 | Aug 27 | Rev2Src | **PASS** | 7.25 MB | `...\TEST.PD.PROT.SRC.13\01_TEST.PD.PROT.SRC.13_Rev2Src.usb` |
| 6 | Aug 27 | Rev3ChkdSrc | **FAIL** | 12.59 MB | `...\TEST.PD.PROT.SRC.13\02_TEST.PD.PROT.SRC.13_Rev3ChkdSrc_FAIL.usb` |

> **来源**: `python C:/Users/xianjun.zeng/AppData/Local/Temp/list_src13_files.py` — 文件名中的 `_FAIL` 后缀表示测试失败

### 1.3 Lecroy HTML 测试报告

| # | 测试日期 | 文件 | 大小 | 路径 |
|---|---------|------|------|------|
| 1 | Aug 21 | `USB_ComplianceTestLog.html` | 59.1 KB | `...\TEST-PD-PROT-SRC-13\TEST-PD-PROT-SRC-13\USB Power Delivery\TEST.PD.PROT.SRC.13\` |
| 2 | Aug 24 | `USB_ComplianceTestLog.html` | 58.7 KB | `...\TEST.PD.PROT.SRC.13-8-24\TEST.PD.PROT.SRC.13-8-24\USB Power Delivery\TEST.PD.PROT.SRC.13\` |
| 3 | Aug 27 | `USB_ComplianceTestLog.html` | 58.7 KB | `...\TEST.PD.PROT.SRC.13--8-27\20260827_144948\USB Power Delivery\TEST.PD.PROT.SRC.13\` |

> **来源**: `python C:/Users/xianjun.zeng/AppData/Local/Temp/list_src13_files.py`

### 1.4 Bugzilla 评论

| 来源 | URL |
|------|-----|
| Bug 3523346 (unisoc) | `https://bugzilla.unisoc.com/bugzilla/show_bug.cgi?id=3523346` |

> **状态**: 尚未拉取（待 bug-core 获取评论详情）

### 1.5 知识库文件

| 文件 | 用途 | Phase |
|------|------|:-----:|
| `knowledge/cts/TEST.PD.PROT.SRC.13.md` | SRC.13 测试流程（新生成） | Phase 2 |
| `knowledge/cts/TEST.PD.PROT.SRC.10.md` | SRC.10 模板参考 | Phase 2 |
| `knowledge/specs/pd_protocol_timers.md` | PD 协议 Timer 限值 | Phase 3 |
| `knowledge/specs/pd_message_sequences.md` | PD 消息序列规范 | Phase 3 |
| `knowledge/specs/pd_state_machines.md` | PD 状态机定义 | Phase 3/4 |
| `knowledge/bugs/top_issue_patterns.md` | 6 大失败模式 | Phase 5 |
| `knowledge/bugs/auth_knowledge_base.json` | 历史 Bug 结构化知识库 | Phase 5 |

---

## 2. Bug 上下文

| 字段 | 值 |
|------|-----|
| **Bug ID** | 3523346 |
| **平台** | UMS512 (SPRDLINUX 6.18 kernel) |
| **客户** | ZTE |
| **项目** | P610F01 |
| **问题** | PD CE 认证失败 — `TEST.PD.PROT.SRC.13` |
| **Lecroy 仪器** | Teledyne LeCroy Voyager M310e, v7.92 Build 1198 |
| **测试软件** | USB Compliance Suite |

---

## 3. 测试项识别

### 3.1 TEST.PD.PROT.SRC.13 — PR_Swap: GoodCRC not sent in Response to PS_RDY

| 属性 | 值 |
|------|-----|
| **全称** | `TEST.PD.PROT.SRC.13` |
| **测试目的** | 验证 UUT 在 PR_Swap 后，PS_RDY 未收到对端 GoodCRC 时能正确进入 Error Recovery |
| **Sub-tests** | 2 个（Rev2Src / Rev3ChkdSrc） |
| **Key Timer** | tCtsErrorRecovery = 15ms |
| **检查点数** | 3（SRC.13#1/#2/#3） |
| **UUT 角色** | PR_Swap 前为 Sink，Swap 后为新 Source |

### 3.2 三次测试结果汇总

| 日期 | Rev2Src | Rev3ChkdSrc | 备注 |
|------|:-------:|:-----------:|------|
| Aug 21 | ❌ FAIL #3 (0x00000381) | ❌ BU.1#1 (0x000003A9) | 初始测试，两个 sub-test 均失败 |
| Aug 24 | ✅ PASS | ❌ BU.1#1 (0x000003A9) | **Rev2Src 已修复** |
| Aug 27 | ✅ PASS | ❌ BU.1#1 (0x000003A9) | Rev3ChkdSrc 持续失败 |

> **来源**: Lecroy ComplianceTestLog.html 文件中的失败判定信息（已在上一 session 中通过 Python 脚本读取确认）

### 3.3 失败详情

**Rev2Src#3 FAIL (仅 Aug 21)**:
- **错误码**: `0x00000381`
- **错误描述**: "USB Type-C Error Recovery was not detected within 15ms after the last bit of the EOP of the last retried PS_RDY Message"
- **状态**: 已在 Aug 24/27 复测中修复 ✅

**Rev3ChkdSrc BU.1#1 FAIL (所有三次测试)**:
- **错误码**: `0x000003A9`
- **错误描述**: "The UUT did not present VBus"
- **状态**: 持续失败，未修复 ❌
- **说明**: 该失败发生在 **bring-up 阶段**（COMMON.PROC.BU.1），即测试的第一步，主测试流程（Step 2-7）尚未开始执行

---

## 4. 现有分析结果

### 4.1 已有结论

1. **Rev2Src 问题已解决**：Aug 24/27 两次复测均 PASS，说明 Aug 21 到 Aug 24 之间的某些修改修复了 PD 2.0 模式下的 Error Recovery 超时问题
2. **Rev3ChkdSrc 为独立问题**：PD 3.0 模式下的 VBus 上电失败（BU.1#1）在所有三次测试中持续存在，与 Rev2Src 问题无关

### 4.2 Rev2Src vs Rev3ChkdSrc 分裂分析

| 维度 | Rev2Src | Rev3ChkdSrc |
|------|---------|-------------|
| 失败阶段 | 主测试 Step 7 (SRC.13#3) | Bring-up Step 3 (BU.1#1) |
| 失败类型 | Error Recovery 超时 | VBus 未上电 |
| PD 版本 | PD 2.0 | PD 3.0 |
| 触发方式 | Tester 不回复 GoodCRC | UUT 自身初始化 |
| 修复状态 | ✅ 已修复 | ❌ 未修复 |

### 4.3 初步假设

- **Rev3ChkdSrc BU.1#1**: PD 3.0 模式下的 CC line 检测/VBus 上电逻辑存在缺陷，可能与 PD 3.0 特有的协议初始化流程（如 Source_Capabilities Extended、USB4 支持等）有关
- **Rev2Src#3 (已修复)**: 可能是 PR_Swap 后的状态机处理缺少对 No GoodCRC → Error Recovery 的 fallback 路径

---

## 5. 缺失材料

| 优先级 | 材料 | 说明 | 影响 Phase |
|:------:|------|------|:---------:|
| 🔴 高 | UMS512 内核源码 | `sprd_tcpm.c` / `sc27xx_typec.c` / tcpci driver | Phase 6 (代码根因) |
| 🟡 中 | 客户 VIF 文件 | PD_Port_Type / PR_Swap 支持 / PD_Spec_Revision | Phase 2 (确认 bring-up 方式) |
| 🟡 中 | Aug 21→24 修复 patch | 了解 Rev2Src 修复内容，判断是否适用于 Rev3ChkdSrc | Phase 5/6 |
| 🟢 低 | Bug 3523346 评论 | 客户/厂商讨论历史 | Phase 1 (背景补充) |

---

## 6. 材料可用性总结

| 类型 | 已获取 | 缺失 | 可用率 |
|------|:-----:|:----:|:-----:|
| Kernel Logs | 3/3 | 0 | 100% |
| Lecroy .usb Traces | 6/6 | 0 | 100% |
| Lecroy HTML Reports | 3/3 | 0 | 100% |
| CTS 测试流程 | ✅ (新生成) | 0 | 100% |
| Timer 规范 | ✅ | 0 | 100% |
| 内核源码 | 0 | 1 | 0% |
| VIF 文件 | 0 | 1 | 0% |
| 修复 Patch | 0 | 1 | 0% |

**总体评估**: 测试数据充足，可完成 Phase 2-5。Phase 6 代码分析需获取内核源码后执行。

---

## 7. Phase 1 产物检查

| 产物 | 路径 | 状态 |
|------|------|:----:|
| CTS 知识文件 | `knowledge/cts/TEST.PD.PROT.SRC.13.md` | ✅ 已生成 |
| 材料清单 | `00_input/input_meta.json` | ✅ 已生成 |
| 测试信息报告 | `00_input/01_test_case_info.md` | ✅ 当前文件 |
| Manifest | `manifest.json` | ⏳ 待生成 |

---

> **Phase 1 完成，进入 Phase 2（测试用例说明 & 失败点定位）**