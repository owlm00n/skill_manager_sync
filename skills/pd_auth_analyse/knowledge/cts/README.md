# CTS 测试项流程库索引

本目录存放 USB PD CTS (Compliance Test Suite) 各测试项的详细流程和规范 PDF。

## 规范 PDF

| 文件 | 内容 | 来源 |
|------|------|------|
| `USB_PD3_CTS_Q4_2024_OR.pdf` | **USB PD3 CTS 测试规范 (Q4 2024)**，322 页 | USB-IF 官方 |
| `USB Type C Functional Test Specification 2023 02 23(1).pdf` | **Type-C 功能测试规范** | USB-IF 官方 |

## 文件命名规则

`<CASE_ID>.md` — 如 `TEST.PD.PROT.SNK.14.md`、`TD.4.10.3.V.md`

## 已有测试项

| Case ID | 测试名称 | 角色 | 文件 |
|---------|---------|------|------|
| TEST.PD.PROT.SNK.14 | Valid Use of GoodCRC on Power up | Sink | TEST.PD.PROT.SNK.14.md |

## 文件格式

每个文件包含：
- 测试目的
- 测试配置（角色/设备）
- 测试条件（适用 UUT 类型）
- 完整步骤序列（Step → Tester操作 → DUT预期 → Timer限值）
- 判定标准
- 唯一检查点 (Check ID)
- 关联timer 数值需读取来自 PD 规范
- 常见失败模式（项目经验，标记来源）
- 参考 Bug 案例
- 来源（规范页码 + 实测数据）

---

## ⚠️ 生成规则（所有 Agent 必须遵守）

> **以下规则适用于生成任何新的 CTS 测试流程文件。违反将导致与 SNK.14 初版相同的问题：测试名称/目的/步骤全面错误。**

### 规则 1: 必须读取官方 CTS 规范 PDF

**规范路径**: `knowledge/cts/USB_PD3_CTS_Q4_2024_OR.pdf` (322 页)

在生成任何 CTS 流程文件前，**必须先读取该 PDF 中对应测试项的章节**。规范原文是唯一权威来源。

### 规则 2: 禁止仅从 Bug 数据推断测试规范

| 禁止使用的信息来源 | 原因 |
|-------------------|------|
| Bug 的 Fail 描述 | Fail 现象 ≠ 测试的 Pass 标准 |
| 仪表报告格式 (Run #1, #2, #3) | 报告格式 ≠ 测试步骤 |
| 已有 CTS 文件的内容 | 格式模板 ≠ 内容模板 |
| PD 协议通用知识 | 通用协议 ≠ 特定 CTS 测试设计 |

### 规则 3: 区分规范内容与项目经验

| 内容类型 | 来源 | 标注方式 |
|---------|------|---------|
| 测试名称/目的/步骤/检查点 | 官方 CTS 规范 PDF | 不加标记 |
| 常见失败模式 | Bug 根因分析 | 标注 "→ 通常原因:" |
| 参考 Bug 案例 | Bug 管理系统 | 标注 Bug ID |
| 调试方法 | 项目实践经验 | 标注 "→ 调试方法:" |

### 规则 4: 生成流程

```
步骤 1: 读取 CTS 规范 PDF 对应章节 → 提取规范原文
  步骤 2：补充引用流程获取这两个 Bring-up 流程的完整步骤COMMON.PROC.
步骤 3 ：Timer 数值处理，从 PD R3.1 Spec 补充数值，但明确标注 "来源路径，辅助参考，非 CTS 原文"
步骤 4: 按模板格式填充规范内容（测试名称、目的、步骤、检查点）
步骤 5: 搜索 Bug 数据库 → 补充失败模式和参考案例（标记来源）
步骤 6: 在文件末尾标注来源（PDF 页码 + Bug ID）
```

### 规则 5: 必须包含来源标注

每个文件末尾必须包含：
```markdown
## 来源
- 官方规范: `USB PD3 CTS Q4 2024 OR.pdf`, Section X.X, Page XX-XX
- 实测数据: `ref/pd_bugs_detail.json`, Bug XXXXXX
- Timer 规范: `knowledge/specs/pd_protocol_timers.md`
```

### 规则 6: 教训参考

生成前必须阅读 `knowledge/cts/CTS_GENERATION_LESSONS.md`，了解初版 SNK.14 的 10 类错误及根因。

---

## 扩充指南

1. 从 `USB PD3 CTS Q4 2024 OR.pdf` 中找到对应测试项章节
2. 提取规范原文（测试名称、描述、步骤、检查点）
3. 按本目录已有文件的模板格式填写
4. 搜索 `ref/pd_bugs_detail.json` 和 `knowledge/bugs/` 补充项目经验
5. 标注来源页码和 Bug ID