---
name: bug-rootcause
description: Bugzilla RootCause Analysis - 从Bug comment和附件分析推导，填写Bugzilla Analysis_Solution框。严格遵循公司填写规范。
---

# Bug RootCause Analysis Skill

## 何时使用

- 需要对 Bugzilla Bug 填写 Analysis_Solution（Root Cause / Resolution / Testing Suggestion / Impact for customer）
- 用户说"填写rootcause"、"分析bug原因"、"填写Analysis_Solution"、"写解决方案"
- 用户提供 Bug ID 要求分析并填写

## ChangeType 与必填项

| ChangeType | 必填项 | 说明 |
|-----------|--------|------|
| **Defect** | 1~4 必填，5~7 可选 | 标准Bug修复场景 |
| **Question** | 第2项 Resolution 必填 | 问题咨询场景 |
| **Task / EnhancementRequest** | 全部可选 | 任务/增强场景 |

## 核心执行流程

### 步骤 1：获取 Bug 完整信息

1. 通过 Bugzilla MCP 获取 Bug 元数据（status、assignee、product）
2. 获取所有 Comment（含结构化评论，如 FTP 路径、UNC 路径）
3. 获取附件列表，阅读关键附件（log、trace、VIF 等）

### 步骤 2：提取关键信息

从 Bug comment 和附件中提取：
- **问题现象**：什么错误、什么环境、什么操作下出现
- **测试工具**：用的什么仪器/软件版本
- **硬件配置**：DUT 型号、小板/配件版本
- **配置信息**：dts、VIF、寄存器配置等
- **日志证据**：trace、log 中的关键错误信息

### 步骤 3：推导 Root Cause

**方法论**：从证据链倒推根本原因。

- 不是写"问题现象"，要写"因为 A 导致 B"
- 问自己：是什么代码/配置/逻辑缺陷导致了这个问题？
- 区分直接原因和根本原因（5-Why 原则）
- 可编号列出多条原因

**常见模式**：
- 硬件设计问题：引脚未连接、电源配置错误
- 驱动配置冲突：dts 中两个配置互斥
- 声明与实现不一致：VIF 声明了不支持，但硬件实际有
- 时序/状态问题：前一次操作未清理导致后续操作异常

### 步骤 4：编写 Resolution

- 不是重复原因，要写具体修改动作
- 可编号列出多条解决方案，与 Root Cause 一一对应
- 写清楚：改哪个文件/配置、怎么改

### 步骤 5：编写 Testing Suggestion

格式：`『环境/工具』+『操作步骤』+『预期通过结果』`

- 写清楚测试需要的仪器/软件版本
- 写清楚操作步骤
- 写清楚预期结果（Pass/Fail）

### 步骤 6：编写 Impact for customer

格式：`『不合入会怎样』+『合入后有什么好处』`

- 两句话即可，不要和 Testing Suggestion 一样

## 字段填写规则

### [1] Root Cause — 根本原因
- **状态**：Root-Cause 状态必填
- **长度**：≥ 12个字符（字母或汉字）
- **约束**：不能和 Resolution 完全一样
- **核心**：是根本原因，不是问题现象
- **格式**：一句话总结：谁（模块/文件）+ 为什么出错（代码/配置/逻辑问题）+ 导致什么。可编号列多条。

### [2] Resolution — 解决方案
- **状态**：Root-Cause 状态必填
- **长度**：≥ 12个字符（字母或汉字）
- **约束**：不能和 Root Cause 完全一样
- **核心**：是解决方案，不是根本原因
- **格式**：一句话总结：改了什么（文件/配置）+ 怎么改的。可编号列多条。

### [3] Testing Suggestion — 测试建议
- **状态**：Fixed 状态必填
- **约束**：不能为空，不能和 Impact for customer 完全一样
- **格式**：『环境/工具』+『操作』+『预期通过结果』

### [4] Impact for customer — 对客户的影响
- **状态**：Fixed 状态必填
- **约束**：不能为空，不能和 Testing Suggestion 完全一样
- **格式**：『不合入会怎样』+『合入后有什么好处』

### [5] Self Test Items — 自测情况（可选）
- 一句话说明自测内容

### [6] Reproduce Steps — 复现步骤（可选）
- 编号步骤，方便复现

### [7] NV Modification — NV修改（可选）
- Y/N + 一句话说明

### NV 相关字段（可选）
- `[Mandatory for customer(Y/N)]`：此项修复对客户是否必需要求
- `[Recalibration (Y/N)]`：是否需要客户重新校准
- `[NV structural changed(Y/N)]`：是否涉及 NV 数据结构变更
- `[New NV backup items(Y/N)]`：是否涉及新的 NV 备份项

## 输出模板

```
[1.Root Cause        ]:
一句话总结：谁（模块/文件）+ 为什么出错（代码/配置/逻辑问题）+ 导致什么。可编号列多条。

[2.Resolution        ]:
一句话总结：改了什么（文件/配置）+ 怎么改的。可编号列多条。

[3.Testing Suggestion]:
『环境/工具』+『操作步骤』+『预期通过结果』。

[4.Impact for customer]:
『不合入会怎样』+『合入后有什么好处』。

[5.Self Test Items ]:(Optional)
一句话说明自测内容。

[6.Reproduce Steps]:(Optional)
编号步骤，方便复现。

[7.NV Modification   ]:(Optional)
Y/N + 一句话说明。

[Mandatory for customer(Y/N)]:
Y/N

[Recalibration (Y/N)        ]:
Y/N

[NV structural changed(Y/N) ]:
Y/N

[New NV backup items(Y/N)   ]:
Y/N
```

## 提交方式（必读）

Analysis_Solution 必须写入 Bugzilla **自定义字段 `cf_analysis_solution`**（单一多行文本字段，11 个模板字段整体填入），
**禁止只发 comment 代替字段填写**（comment 不是规范位置）。

```python
import requests

base = "https://bugzilla.unisoc.com/bugzilla"
key = {"api_key": "<从 bug-core config/bugzilla_instances.json 读取>"}

# 1) 写入 Analysis_Solution 字段（完整模板文本）
resp = requests.put(f"{base}/rest/bug/{bug_id}", params=key,
                    json={"cf_analysis_solution": template_text}, timeout=60)

# 2) 状态流转为 Root-Caused（unisoc 实际状态名，可附 comment）
resp = requests.put(f"{base}/rest/bug/{bug_id}", params=key,
                    json={"status": "Root-Caused"}, timeout=60)
# 或用 bug-core 短名：update_bug_status(bug_id, "rootcause", instance="unisoc")
```

关键要点：

- **状态名**：unisoc 的 Root-Cause 状态实际名为 `Root-Caused`（`Root_Cause`/`Root-Cause`/`ROOT_CAUSE` 均报 404）；
  完整流转：NEW→Assigned→Root-Caused→Code-Committed→Fixed→TobeVerified→Closed
- **状态流转图查询**：`GET {base}/rest/field/bug/bug_status?api_key=xxx`（返回各状态 `can_change_to`）
- **字段名探查**：`GET {base}/rest/bug/{bug_id}` 查看返回的 `cf_*` 字段及当前值；
  不要用 `GET /rest/field/bug`（全量字段定义响应过大，会超时）
- **编码**：中文内容用 Python `open(encoding='utf-8')` 读取后提交，
  避免 PowerShell `Get-Content` 默认 GBK 解码导致乱码

## 填写禁忌

1. ❌ Root Cause 和 Resolution 完全一样 → 系统无法提交
2. ❌ Root Cause 写的是问题现象而非根本原因
3. ❌ Testing Suggestion 写 NA 或为空
4. ❌ Testing Suggestion 和 Impact for customer 完全一样
5. ❌ 用加数字后缀的方式绕过相似度检查（如"修改xx1"、"修改xx2"）
6. ❌ 描述过短（<12字符），无法追溯
7. ❌ 套多层标签（【模块】/【触发条件】/【因果链】），AI 容易幻觉

## 示例：Bug 3495846（PD 认证）

```
[1.Root Cause        ]:
1）硬件设计中vconn power引脚未连到实际IC，导致驱动获取vconn regulator为NULL；
2）dts中vddldo-supply与use-pdhub-c2c配置冲突，应移除vddldo-supply；
3）DUT非CC线上有VCONN电压但VIF声明不支持VCONN Swap，CTS检测到不一致。

[2.Resolution        ]:
1）注释掉dts中vddldo-supply配置，添加sprd,support-pd-cts属性和相应flag；
2）确认硬件不需要VCONN Swap，VIF声明正确。

[3.Testing Suggestion]:
Lecroy M310E + USB Compliance Suite 8.41，修改dts重新编译烧录后运行TEST.PD.PROT.SRC.08，应Pass。

[4.Impact for customer]:
不合入则PD认证TEST.PD.PROT.SRC.08持续失败无法出认证报告；合入后通过认证可正常出具报告。

[5.Self Test Items ]:(Optional)
dts编译正常，烧录后TCPC驱动加载正常。

[6.Reproduce Steps]:(Optional)
1）DUT + Lecroy M310E 2）配置VIF声明不支持VCONN 3）运行TEST.PD.PROT.SRC.08 4）预期Fail

[7.NV Modification   ]:(Optional)
N

[Mandatory for customer(Y/N)]:
Y

[Recalibration (Y/N)        ]:
N

[NV structural changed(Y/N) ]:
N

[New NV backup items(Y/N)   ]:
N
```

## 参考文档（references/ 目录）

本 skill 在 `references/` 目录下包含以下支持文档，Claude 在需要时会自动按需加载：

| 文件 | 用途 | 何时加载 |
|------|------|---------|
| `Analysis_Solution_填写指导.md` | 公司 Wiki 完整规范（字段规则、案例、禁忌） | 填写时必读，确保格式合规 |
| `Bugzilla-Analysis_Solution-模板.txt` | Bugzilla 原始页面字段格式（11 个字段） | 提交前对照，确保字段完整 |

## 依赖工具

- **Bugzilla MCP Server**：获取 Bug 信息、Comment、附件
- **bug-logs skill**：解析结构化评论，获取日志目录
- **bug-core skill**：Bug 查询与摘要（如需要）