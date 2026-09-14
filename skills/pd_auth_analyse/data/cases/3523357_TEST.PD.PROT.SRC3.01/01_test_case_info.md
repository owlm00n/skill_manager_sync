# Phase 1: 信息收集 — TEST.PD.PROT.SRC3.01

**分析时间**: 2026-08-31
**Bug ID**: 3523357 (unicase005573)
**平台**: UMS512 (zte_sh / P610F01)
**Case ID**: TEST.PD.PROT.SRC3.01

---

## 1. 输入材料清单

### 1.1 Kernel Log（3 组测试）

| # | 测试组 | 路径 | 状态 |
|:---:|------|------|:---:|
| 1 | ORIGINAL FAIL | `Attachements/TEST-PD-PROT-SRC3-01/.../005-0820_195808_poweron/0-kernel.log` | ✅ 已解析 |
| 2 | 8-24 FAIL | `Attachements/TEST.PD.PROT.SRC3.01-8-24/.../002-0820_045111_poweron/0-kernel.log` | ✅ 已解析 |
| 3 | AFTER CODE CHANGE FAIL | `Attachements/修改代码之后fail/20260825_170153/001-0822_040356_poweron/0-kernel.log` | ✅ 已解析 |

**来源命令**: `list_attachments.py` → 遍历 Attachements 目录

### 1.2 客户代码

| 文件 | 大小 | 说明 |
|------|------|------|
| `code.7z` | — | 客户上传的代码压缩包 |
| `sprd_tcpm.c` | 207,946 bytes | TCPM 状态机 (kernel 6.18) |
| `sc27xx_pd.c` | 94,592 bytes | SC27XX PD 控制器驱动 |
| `sc27xx_typec.c` | 48,514 bytes | Type-C 控制器驱动 |
| `musb_sprd.c` | 88,304 bytes | MUSB 控制器 |
| `sqc_bq2560x.c` | 109,476 bytes | BQ2560x 充电 IC 驱动 |
| `zte_charger.dtsi` | 29,274 bytes | 充电器 DTS 配置 |

**来源命令**: `extract_code.py` → py7zr 解压 `code.7z`

### 1.3 Bugzilla 评论

| 评论 | 作者 | 内容摘要 |
|------|------|---------|
| #0 | 肖荣国 (ZTE) | 提交 Bug，附带 lecroy 测试日志 |
| #6 | Yongqing.Wang | 提出 kernel5.15 修改 `SPRD_PD_T_SEND_SOURCE_CAP` 150→180 |
| #12 | Ke.Wang1 | 硬件分析：CC 线 5 次发送，20 个包（5×4 硬件重试） |
| #15 | Yongqing.Wang | 提出 kernel6.18 相同修改（已测试，仍 FAIL） |
| #18 | 客户 (ZTE) | 上传代码 `code.7z`（6 个文件） |

### 1.4 知识库文件

| 文件 | 路径 | 状态 |
|------|------|:---:|
| CTS 规范 PDF | `knowledge/cts/USB_PD3_CTS_Q4_2024_OR.pdf` | ✅ 已读取 |
| CTS 测试流程 | `knowledge/cts/TEST.PD.PROT.SRC3.01.md` | ✅ 已生成 |
| PD Timer 规范 | `knowledge/specs/pd_protocol_timers.md` | 待读取 |
| PD 消息序列规范 | `knowledge/specs/pd_message_sequences.md` | 待读取 |
| PD 状态机定义 | `knowledge/specs/pd_state_machines.md` | 待读取 |
| 历史 Bug 模式 | `knowledge/bugs/top_issue_patterns.md` | 待读取 |
| Bug 知识库 | `knowledge/bugs/auth_knowledge_base.json` | 待读取 |

---

## 2. Bug 上下文

| 字段 | 值 |
|------|-----|
| **Bug ID** | 3523357 (unicase005573) |
| **标题** | [UMS512][zte_sh][P610F01][17353][手持-智能手机]PD CE认证失败项 TEST.PD.PROT.SRC3.01 |
| **状态** | Assigned |
| **优先级/严重度** | 2-Give High Attention / 2-Major |
| **产品/组件** | SPCSS_UMS512_Android / BSP_Charge |
| **指派人** | Xianjun.Zeng@unisoc.com |
| **Base On Version** | SPRDROID17_SYS_MAIN_PLUS_SPRDROID17_VND_MAIN_PLUS_SPRDLINUX6.18_KERNEL_MAIN_W26.30.5 |
| **创建时间** | 2026-08-21T06:09:38Z |

---

## 3. 测试项识别

- **Case ID**: TEST.PD.PROT.SRC3.01
- **测试名称**: SourceCapabilityTimer Timeout
- **测试目的**: 验证 SourceCapabilityTimer 超时后重试 Source Capabilities 消息的时序是否符合规范（≥100.9ms）
- **测试方法**: Tester 故意不回复 GoodCRC，测量连续 Source Capabilities 消息之间的间隔
- **关键判定**: 第 3→4 条消息间隔必须 ≥100.9ms 且 ≤201.1ms

---

## 4. 现有分析成果

已有一份完整的分析报告（`unicase005573_UMS512_PD CE认证失败项 TEST.PD.PROT.SRC3.01.md`），包含：

- ✅ 根因定位：SC27XX PD 控制器硬件 TX 自动重试（1-2ms 间隔）违反 100.9ms 要求
- ✅ 修复方案：在 `sprd_tcpm.c` 中禁用 `enable_tx_auto_retry`
- ✅ 客户代码 diff（kernel 6.18 适配）
- ✅ 6 个修改点说明（SRC_READY / SRC_SEND_CAPABILITIES / HARD_RESET_SEND / SRC_SEND_CAPABILITIES 重试 / sprd_hard_reset_state / sprd_tcpm_reset_port）

---

## 5. 缺失材料

| 优先级 | 材料 | 目的 | 影响 |
|:---:|------|------|------|
| 🔴 高 | Lecroy .usb 二进制 trace 文件 | 精确协议层时序分析（CC 线消息间隔） | 无法验证修复后的实际效果 |
| 🟡 中 | Lecroy HTML fail 报告 | 确认测试仪的精确 FAIL 判定和测量值 | 缺少仪器侧的直接证据 |
| 🟢 低 | 客户 VIF 文件 | 确认 PD Port Type 和能力声明 | 不影响根因判断 |

---

## 6. 材料可用性汇总

| 类别 | 可用性 | 备注 |
|------|:---:|------|
| Kernel Log | ✅ 完整 | 3 组测试日志，已解析 TX 周期时序 |
| 客户代码 | ✅ 完整 | kernel 6.18 版本，已确认 `enable_tx_auto_retry` 接口存在 |
| Lecroy Trace | ❌ 缺失 | 无 .usb 二进制文件或 HTML 报告 |
| Bug 信息 | ✅ 完整 | 18 条评论，含硬件分析 |
| CTS 规范 | ✅ 完整 | PDF 已读取，测试流程已生成 |
| 历史 Bug | 待查询 | Phase 5 将查询 |

---

*Phase 1 完成 | 产物: `00_input/input_meta.json`, `01_test_case_info.md`, `knowledge/cts/TEST.PD.PROT.SRC3.01.md`*