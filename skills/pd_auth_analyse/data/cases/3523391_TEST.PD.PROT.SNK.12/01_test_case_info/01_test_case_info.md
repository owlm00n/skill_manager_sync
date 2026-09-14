# Phase 1: 测试用例信息收集 — Bug 3523391 TEST.PD.PROT.SNK.12

**分析时间**: 2026-09-09
**Case 目录**: `3523391_TEST.PD.PROT.SNK.12`

---

## 1.1 输入材料清单

| # | 文件 | 类型 | 路径 | 大小 |
|---|------|------|------|------|
| 1 | `0-kernel.log` | Kernel Log | `Attachements/20260827_155005/003-0827_050107_poweron/0-kernel.log` | ~2.8 MB |
| 2 | `Teledyne LeCroy USB Compliance Result__UNISOC-P610F01-1.0.html` | Lecroy 报告 (HTML) | `Attachements/20260827_155005/` | ~86 行 |
| 3 | `UNISOC__P610F01__REV-1.0__1.0.xml` | VIF 配置文件 | `Attachements/` | 10 KB |
| 4 | `TEST-PD-PROT-SNK-12.7z` | 首次测试数据 | `Attachements/` | 3.9 MB |
| 5 | `TEST.PD.PROT.SNK.12-8-24.7z` | 2026-08-24 测试数据 | `Attachements/` | 3.8 MB |
| 6 | `20260827_155005.7z` | 2026-08-27 测试数据 | `Attachements/` | 6.5 MB |
| 7 | `原理图/` (4 PNG) | 原理图截图 | `Attachements/` | ~240 KB |
| 8 | `bug_summary.txt` | Bug 摘要 | 工作区根目录 | <1 KB |

**来源**: Bug 3523391 工作区 `E:\08_Bug\Bug 3523391(unicase005585) - [UMS512][zte_sh][P610F01][17353][现场-客户手机]PD CE认证失败 TEST.PD.PROT.SNK.12\`

---

## 1.2 Bug 上下文

| 字段 | 值 |
|------|-----|
| **Bug ID** | 3523391 (unicase005585) |
| **标题** | [UMS512][zte_sh][P610F01][17353][现场-客户手机]PD CE认证失败 TEST.PD.PROT.SNK.12 |
| **状态** | Assigned |
| **优先级/严重度** | ? / 2-Major |
| **产品/组件** | SPCSS_UMS512_Android / 硬件-驱动-Power |
| **指派人** | Xianjun.Zeng@unisoc.com |
| **创建时间** | 2026-08-21T06:23:12Z |
| **Base On Version** | SPRDROID17_SYS_MAIN_PLUS_SPRDROID17_VND_MAIN_PLUS_SPRDLINUX6.18_KERNEL_MAIN_W26.30.5 |
| **平台** | UMS512 |
| **客户** | ZTE P610F01 |
| **测试设备** | Teledyne LeCroy Voyager M310e, USB Compliance Suite 7.92 Build 1198 |
| **测试标准** | USB PD CTS Q4 2024 RC1 (full) |

**来源**: Bugzilla REST API + `bug_summary.txt`

---

## 1.3 Case ID 识别

| 识别来源 | Case ID |
|----------|---------|
| Bug 标题 | **TEST.PD.PROT.SNK.12** |
| Lecroy 报告 | TEST.PD.PROT.SNK.12 (PR_Swap - PSSourceOffTimer Timeout) |

**测试项全称**: TEST.PD.PROT.SNK.12 — PR_Swap — PSSourceOffTimer Timeout

---

## 1.4 测试结果概览

| 测试项 | 结果 | 说明 |
|--------|:----:|------|
| **TEST.PD.PROT.SNK.12** | **FAIL** | PR_Swap - PSSourceOffTimer Timeout |
| ├─ Rev2Snk (PD 2.0) | **PASS** | COMMON.PROC.BU.2#1 ✅, SNK.12#1 ✅, SNK.12#2 ✅ |
| └─ Rev3ChkdSnk (PD 3.0) | **FAIL** | Test scenario aborted. Check trace file. |

**关键差异**: PD 2.0 PR_Swap 通过，PD 3.0 PR_Swap 失败。

**来源**: `Teledyne LeCroy USB Compliance Result__UNISOC-P610F01-1.0.html`

---

## 1.5 VIF 配置摘要

| 配置项 | 值 | 说明 |
|--------|-----|------|
| PD Spec Revision | 3.1 (Rev 3, Ver 1.8) | PD 3.1 协议 |
| Port Type | DRP | 双角色端口 |
| Accepts_PR_Swap_As_Src | true | 作为 Source 接受 PR_Swap |
| Accepts_PR_Swap_As_Snk | true | 作为 Sink 接受 PR_Swap |
| Sink PDOs | 5V/3A, 9V/3A | 最大 23W 吸入 |
| Source PDO | 5V/1A | 最大 5W 输出 |
| RP_Value | 1.5A | Type-C 默认电流 |
| FR_Swap | Not supported | 不支持快速角色交换 |

**来源**: `UNISOC__P610F01__REV-1.0__1.0.xml`

---

## 1.6 关键评论汇总

| 评论# | 作者 | 日期 | 关键内容 |
|-------|------|------|---------|
| #5 | Yongqing.Wang | 8/24 | PDO 不匹配 — APDO 5000mV 100mA, PDO 0: 5000mV 100mA [mismatch] |
| #8 | Yongqing.Wang | 8/25 | 第二次 PR_Swap — Tester 未收到 UUT 发送的 PS_RDY |
| #10 | Ke.Wang1 | 8/25 | 未收到 RX 数据包 — Tester 等待 PS_RDY 但未收到 |
| #13 | Ke.Wang1 | 8/26 | 硬件分析无异常。Rev2Snk 通过，Rev3ChkdSnk 失败 — Tester 发送 Source Cap 但 DUT 未回复 GoodCRC |
| #19 | Ke.Wang1 | 8/27 | ~~客户使用独立 CC LOGIC 芯片~~ **⚠️ 已被用户纠正** |
| #22 | Ke.Wang1 | 9/3 | GoodCRC 无响应不一定是硬件问题。硬件排查无异常 |
| #27 | Yongqing.Wang | 9/8 | PD 2.0 首次 PR_Swap 成功。PD 3.0 第二次 PR_Swap 未收到 PS_RDY。VBUS 时序日志匹配 |

**来源**: Bugzilla REST API `GET /rest/bug/3523391/comment`

---

## 1.7 ⚠️ 关键纠正：CC LOGIC 芯片身份

| 项目 | 之前假设（Comment #19） | **用户纠正** |
|------|------------------------|------------|
| CC LOGIC 芯片 | 客户使用独立外部 CC LOGIC 芯片 | **CC 是平台 SC27xx PMIC 集成 Type-C 控制器** |
| 根因方向 | 外部芯片接口问题 | **sprd_tcpm 状态机 / sc27xx-typec 驱动内部逻辑问题** |

**此纠正对根因分析的影响**: 问题从"外部芯片 CC 线切换失败"转变为"SC27xx PMIC 内部 CC 检测在 PR_Swap 期间被禁用，导致 sprd_tcpm 状态机无法完成 Sink→Source 转换"。

---

## 1.8 可用/缺失材料汇总

| 类别 | 状态 | 说明 |
|------|:----:|------|
| Kernel Log | ✅ 可用 | 完整 PR_Swap 序列，含 sprd_tcpm 状态机日志 |
| Lecroy 报告 | ✅ 可用 | HTML 格式，含 FAIL 判定 |
| VIF 配置 | ✅ 可用 | PD 3.1 DRP 完整配置 |
| Lecroy Trace (.usb) | ❌ 缺失 | 无二进制 trace 文件，无法做协议层精确时序分析 |
| 内核源码 | ❌ 缺失 | 无法做代码级根因分析（Phase 6 跳过） |
| 知识库 CTS 文件 | ❌ 缺失 | `knowledge/cts/TEST.PD.PROT.SNK.12.md` 不存在，需在 Phase 2 生成 |
| 知识库历史 Bug | ❌ 缺失 | `knowledge/bugs/auth_knowledge_base.json` 不存在，Phase 5 跳过 |

---

*Phase 1 完成 | 2026-09-09*