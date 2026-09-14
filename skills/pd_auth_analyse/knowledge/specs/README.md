# PD 协议规范知识库

本目录存放 USB PD 协议规范的原始文档和提取文件，供 CTS 测试流程生成和分析使用。

## 文件清单

| 文件 | 内容 | 来源 |
|------|------|------|
| `USB_PD_R3_2 V1.0 2023-10.pdf` | **USB PD R3.2 协议规范**（Timer/序列/状态机权威来源） | USB-IF 官方 |
| `Vendor_Info_File_v3.29 - CLEAN.pdf` | **VIF 规范 v3.29** | USB-IF 官方 |
| `UNISOC-L6__UNISOC-L6-6__REV-1.0__831.xml` | **VIF XML 实例**（Unisoc L6） | 展锐内部 |
| `pd_protocol_timers.md` | PD 协议关键 Timer 参数 | ✅ 已从 PD R3.2 PDF Section 6.6, Table 6.69-6.70 重新提取 (2026-07-28) |
| `pd_message_sequences.md` | PD 消息序列与 AMS 规范 | ✅ 已从 PD R3.2 PDF Section 6.3-6.5, 8.3.2 重新提取 (2026-07-28) |
| `pd_state_machines.md` | PD 协议层与策略引擎状态机 | ✅ 已从 PD R3.2 PDF Section 6.12, 8.3.3 重新提取 (2026-07-28) |

## 旧版文件归档

旧版 `pd_protocol_timers.md`、`pd_message_sequences.md`、`pd_state_machines.md` 的初版已归档至 `archive/` 目录（标记为 `v1.0.0_no-spec-ref`），初版未参考 PD 规范 PDF 生成，不可作为分析依据。

## 相关目录

- CTS 测试规范: `../cts/`（含 `USB_PD3_CTS_Q4_2024_OR.pdf` 和 Type-C 功能测试规范）
- CTS 生成规则: `../cts/README.md`
- CTS 生成教训: `../cts/CTS_GENERATION_LESSONS.md`