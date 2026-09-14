---
name: doc-acquirer
description: 文档材料获取 — 分析报告生成后，自动调用 isupport-downloader 搜索下载平台文档和规格书，结果写回报告
version: "1.0"
tags: [material, acquisition, isupport-downloader, document, async, agent]
---

# 文档材料获取 (Doc Acquirer)

Bug 分析报告生成后，解析"还需要获取"清单中的文档类材料，调用 isupport-downloader Skill 搜索下载文档，并将结果写回分析报告。

## 触发条件

- **自动化联动**：bug-core 生成分析报告后，自动启动本 Agent（与 code-acquirer 并行）
- 用户说"搜文档"、"下载文档"时也可手动触发

## 设计原则

- **与 code-acquirer 并行**：代码和文档获取同时进行，互不阻塞
- **独立输出文件**：写入 `{report_path}.docs.md`，避免与 code-acquirer 写冲突
- **命名透明**：Agent 会话以目标任务命名，如 `获取UMS312-DVFS配置文档`

## 输入参数

| 参数 | 必填 | 来源 | 说明 |
|------|:----:|------|------|
| `bug_id` | ✅ | bug-core 传入 | 当前 Bug ID |
| `report_path` | ✅ | bug-core 传入 | 分析报告完整路径 |
| `workspace_path` | ✅ | bug-core 传入 | Bug 工作区根目录 |
| `platform` | ✅ | 从 Bug Product 提取 | 如 `UMS312`、`UMS512` |
| `base_on_version` | ✅ | 从 Bug `cf_base_on_ver` 提取 | 如 `SPRDROID16_SYS_MAIN_W25.35.4` |

## 工作流程

### 阶段 1：解析文档类材料

1. 读取 `report_path` 中的分析报告
2. 找到 `### 还需要获取` 章节
3. **只筛选文档类材料**（含"文档/DVFS/OPP/配置/手册/规格书/datasheet/FB/分压"关键词）
4. 按优先级排序（🔴高 → 🟡中 → 🟢低）

### 阶段 2：材料类型识别与 Skill 调度

| 材料特征 | 类型 | 调用方式 |
|---------|------|---------|
| 包含"文档"、"DVFS"、"OPP"、"配置"、"手册" | `document` | `Skill: isupport-downloader`，传关键词 + `--chip {platform}` |
| 包含"规格书"、"datasheet"、"FB"、"分压" | `datasheet` | Read PDF 文件，提取文本 |

### 阶段 3：逐项获取

#### 3a. 平台文档获取（isupport-downloader）

```
Skill: isupport-downloader
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

#### 3b. 规格书分析

```
在 workspace_path/Attachements/ 下查找 PDF 文件
使用 Read 工具提取文本
```

如果 PDF 为图片格式无法提取，标记为 ⚠️。

### 阶段 4：结果写回

写入 `{report_path}.docs.md`：
1. 列出下载的文档路径和关键内容摘录
2. 每项标记状态：✅/⚠️/❌/➖
3. 提取关键结论（配置参数、寄存器值、推荐值）

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| isupport-downloader 认证失败 | 标记为 ❌ "isupport 认证过期，需手动登录" |
| 搜索无结果 | 标记为 ❌ "未找到相关文档" |
| PDF 无法提取文字 | 标记为 ⚠️ "PDF 为图片格式，无法提取文字" |
| 客户实测数据 | 标记为 ➖ "需客户提供，无法自动获取" |

## 相关 Skill

- **isupport-downloader**: DCC 文档搜索下载（关键词 + chip）
- **code-acquirer**: 代码材料获取（并行运行）
- **bug-core**: 分析报告生成，启动本 Agent

## 代码位置

| 文件 | 说明 |
|------|------|
| `skills/doc-acquirer/SKILL.md` | 本文件，完整工作流 |
| `agents/doc-acquirer.md` | Agent 定义（精简入口） |