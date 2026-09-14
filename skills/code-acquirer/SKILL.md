---
name: code-acquirer
description: 代码材料获取 — 分析报告生成后，自动调用 code-puller 获取内核/edk2 等源码，结果写回报告
version: "1.0"
tags: [material, acquisition, code-puller, code, async, agent]
---

# 代码材料获取 (Code Acquirer)

Bug 分析报告生成后，解析"还需要获取"清单中的代码类材料，调用 code-puller Skill 获取源码，并将结果写回分析报告。

## 触发条件

- **自动化联动**：bug-core 生成分析报告后，自动启动本 Agent（与 doc-acquirer 并行）
- 用户说"拉代码"、"获取源码"时也可手动触发

## 设计原则

- **与 doc-acquirer 并行**：代码和文档获取同时进行，互不阻塞
- **独立输出文件**：写入 `{report_path}.code.md`，避免与 doc-acquirer 写冲突
- **命名透明**：Agent 会话以目标任务命名，如 `获取UMS312-内核DCDC驱动代码`

## 输入参数

| 参数 | 必填 | 来源 | 说明 |
|------|:----:|------|------|
| `bug_id` | ✅ | bug-core 传入 | 当前 Bug ID |
| `report_path` | ✅ | bug-core 传入 | 分析报告完整路径 |
| `workspace_path` | ✅ | bug-core 传入 | Bug 工作区根目录 |
| `platform` | ✅ | 从 Bug Product 提取 | 如 `UMS312`、`UMS512` |
| `base_on_version` | ✅ | 从 Bug `cf_base_on_ver` 提取 | 如 `SPRDROID16_SYS_MAIN_W25.35.4` |

## 工作流程

### 阶段 1：解析代码类材料

1. 读取 `report_path` 中的分析报告
2. 找到 `### 还需要获取` 章节
3. **只筛选代码类材料**（含"代码/驱动/kernel/源码/edk2/bootloader"关键词）
4. 按优先级排序（🔴高 → 🟡中 → 🟢低）

### 阶段 2：调用 code-puller 获取代码

```
Skill: code-puller
参数:
  - repo_path: 从材料描述推导
  - branch: 从 base_on_version 推导
```

### 阶段 3：结果写回

写入 `{report_path}.code.md`：
1. 列出获取的代码文件路径和关键片段
2. 每项标记状态：✅/⚠️/❌
3. 提取关键结论（配置值、宏定义、函数逻辑）

## 代码仓库路径推导规则

### 从 Bug Component 推导 repo_path

| Bug Component | 推导 repo_path |
|--------------|---------------|
| `BSP_Power_Deep/Light/DVFS` | `kernel/linux` |
| `BSP_Kernel` | `kernel/linux` |
| `BSP_Bootloader` | `bsp/bootloader/edk2` |
| `BSP_Charger` | `kernel/linux` |
| 其他 | 从材料描述关键词推断，或标记为 ❌ |

### 从 Base On Version 推导 branch

| Base On Version 特征 | git 分支 |
|---------------------|---------|
| `SPRDROID16_*` | `sprdroid16_*`（用 `git ls-remote` 确认） |
| `SPRDROID15_*` | `sprdroid15_*` |
| `SPRDROID13_*` | `sprdroid13_*` |

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| code-puller Skill 不存在 | 标记为 ❌ "code-puller Skill 未配置" |
| Git 分支推导失败 | 标记为 ❌ "无法从 {base_on_version} 推导分支名" |
| 仓库路径无法确定 | 标记为 ❌ "无法确定 repo_path，需用户指定" |

## 相关 Skill

- **code-puller**: Gerrit 代码拉取（repo_path + branch）
- **doc-acquirer**: 文档材料获取（并行运行）
- **bug-core**: 分析报告生成，启动本 Agent

## 代码位置

| 文件 | 说明 |
|------|------|
| `skills/code-acquirer/SKILL.md` | 本文件，完整工作流 |
| `agents/code-acquirer.md` | Agent 定义（精简入口） |