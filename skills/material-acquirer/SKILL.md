---
name: material-acquirer
description: 主动材料获取 — 分析报告生成后，自动调用 code-puller/isupport-downloader 获取代码和文档，结果写回报告
version: "1.0"
tags: [material, acquisition, code-puller, isupport, async, agent]
---

# 主动材料获取 (Material Acquirer)

Bug 分析报告生成后，解析"还需要获取"清单，异步调用 code-puller / isupport-downloader 等 Skill 获取代码和文档，并将结果写回分析报告。

## 触发条件

- **自动化联动**：bug-core 生成分析报告后，自动启动本 Agent 异步获取材料
- 用户说"获取材料"、"下载文档"、"拉取代码"时也可手动触发

## 设计原则

- **异步执行**：不影响 bug-core 主流程，用户先看到报告，材料后台获取
- **结果写回**：获取完成后直接更新分析报告中的"材料清单"章节
- **命名透明**：Agent 会话以目标任务命名，如 `获取UMS312-DCDC驱动代码和平台文档`

## 输入参数

| 参数 | 必填 | 来源 | 说明 |
|------|:----:|------|------|
| `bug_id` | ✅ | bug-core 传入 | 当前 Bug ID，如 `SPCSS01696773` |
| `report_path` | ✅ | bug-core 传入 | 分析报告完整路径 |
| `workspace_path` | ✅ | bug-core 传入 | Bug 工作区根目录 |
| `platform` | ✅ | 从 Bug Product 提取 | 如 `UMS312`、`UMS512` |
| `base_on_version` | ✅ | 从 Bug `cf_base_on_ver` 提取 | 如 `SPRDROID16_SYS_MAIN_W25.35.4` |

## 工作流程

### 阶段 1：解析"还需要获取"清单

1. 读取 `report_path` 中的分析报告
2. 找到 `### 还需要获取` 或 `### 主动获取结果` 章节
3. 解析表格，提取每项材料的类型、说明、优先级
4. 按优先级排序（🔴高 → 🟡中 → 🟢低）

### 阶段 2：材料类型识别与 Skill 调度

根据材料说明自动判断类型，调用对应 Skill：

| 材料特征 | 类型 | 调用 Skill | 关键参数推导 |
|---------|------|-----------|-------------|
| 包含"代码"、"驱动"、"kernel"、"源码" | `code` | `code-puller` | repo_path 从描述推导（如"电源管理"→ `kernel/linux`），branch 从 `base_on_version` 推导 |
| 包含"文档"、"DVFS"、"OPP"、"配置"、"手册" | `document` | `isupport-downloader` | 搜索关键词从描述提取，`--chip` 从 `platform` 提取 |
| 包含"规格书"、"datasheet"、"FB"、"分压" | `datasheet` | PyPDF2 / Read | 在 `workspace_path/Attachements/` 下查找对应 PDF |
| 包含"历史 Bug"、"Bug 引用" | `reference_bug` | Bugzilla REST API | 从描述中提取 Bug ID |

### 阶段 3：逐项获取

#### 3a. 代码获取（code-puller）

```
调用 Skill: code-puller
参数:
  - repo_path: 从材料描述推导（见下方映射表）
  - branch: 从 base_on_version 推导分支名
```

**Component → Repo 映射**（参考 code-puller references/gerrit_servers.md）：

| 驱动/组件 | repo_path |
|----------|-----------|
| Power/PMIC/Charger/DCDC/DVFS | `kernel/linux`（优先） |
| Bootloader | `bsp/bootloader/edk2` |
| 未明确指定 | 根据 Bug Component 字段推导 |

**Branch 推导**：从 `base_on_version`（如 `SPRDROID16_SYS_MAIN_W25.35.4`）→ 参考 code-puller `references/branch_guide.md` 映射到实际 git 分支名。

#### 3b. 文档获取（isupport-downloader）

```
调用 Skill: isupport-downloader
参数:
  - 搜索关键词: 从材料描述提取（如 "DVFS OPP UMS312"）
  - --chip: {platform}
```

搜索流程：
```bash
cd D:\06_Project\isupport_down
python src/main.py search "<关键词>" --chip {platform} --max 20
```

展示搜索结果，下载匹配度最高的文档。

#### 3c. 规格书分析（PyPDF2）

```
在 workspace_path/Attachements/ 下查找 PDF 文件
使用 PyPDF2 提取文本
```

如果 PDF 为图片格式无法提取，标记为 ⚠️。

#### 3d. 历史 Bug 查询（REST API）

```
GET https://bugzilla.unisoc.com/bugzilla/rest/bug/{bug_id}
GET https://bugzilla.unisoc.com/bugzilla/rest/bug/{bug_id}/comment
```

### 阶段 4：结果写回报告

将获取结果更新到 `report_path` 的"材料清单"章节：

1. 找到 `### 还需要获取` 或 `### 主动获取结果` 章节
2. 将"还需要获取"表格替换为"主动获取结果"表格，每项标记状态：

| 状态 | 含义 |
|:----:|------|
| ✅ | 成功获取，已提取关键信息 |
| ⚠️ | 部分获取（如 PDF 为图片格式） |
| ❌ | 获取失败，需用户提供 |
| ➖ | 未尝试（如"客户电压实测数据"只能等客户） |

3. 如果获取到关键结论，追加到报告"技术分析"章节

## 代码仓库路径推导规则

### 从 Bug Component 推导 repo_path

| Bug Component | 推导 repo_path |
|--------------|---------------|
| `BSP_Power_Deep/Light/DVFS` | `kernel/linux` |
| `BSP_Kernel` | `kernel/linux` |
| `BSP_Bootloader` | `bsp/bootloader/edk2` |
| `BSP_Charger` | `kernel/linux` |
| 其他 | 从材料描述关键词推断，或标记为"需用户指定" |

### 从 Base On Version 推导 branch

| Base On Version 特征 | git 分支 |
|---------------------|---------|
| `SPRDROID16_*` | `sprdroid16_*`（具体用 `git ls-remote` 确认） |
| `SPRDROID15_*` | `sprdroid15_*` |
| `SPRDROID13_*` | `sprdroid13_*` |

> ⚠️ `cf_base_on_ver` 和实际 git 分支名可能不同，优先使用 `git ls-remote --heads` 确认。

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| code-puller Skill 不存在 | 标记为 ❌ "code-puller Skill 未配置" |
| isupport-downloader 认证失败 | 标记为 ❌ "isupport 认证过期，需手动登录" |
| Git 分支推导失败 | 标记为 ❌ "无法从 {base_on_version} 推导分支名，需用户指定" |
| PDF 无法提取文字 | 标记为 ⚠️ "PDF 为图片格式，无法提取文字" |
| 搜索无结果 | 标记为 ❌ "未找到相关文档" |

## 相关 Skill

- **code-puller**: Gerrit 代码拉取（repo_path + branch）
- **isupport-downloader**: DCC 文档搜索下载（关键词 + chip）
- **bug-core**: 分析报告生成，启动本 Agent

## 代码位置

| 文件 | 说明 |
|------|------|
| `skills/material-acquirer/SKILL.md` | 本文件，完整工作流 |
| `agents/material-acquirer.md` | Agent 定义（精简入口） |