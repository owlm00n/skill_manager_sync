---
name: ragflow-doc-advisor
description: RAGFlow 文档解析配置顾问 — 分析文档特征，推荐最佳 chunk_method 和解析参数。当用户说"分析这个文档"、"推荐解析参数"、"RAGFlow 配置"时触发。
version: "1.0"
tags: [ragflow, document-parsing, chunk-method, knowledge-base, advisor]
---

# RAGFlow 文档解析配置顾问

分析任意文档（PDF/DOCX/TXT/MD/HTML/JSON 等 17 种格式），提取 14 项文档特征，通过规则引擎 + LLM 终判推荐最佳 RAGFlow `chunk_method` 和解析参数。

## 触发条件

- 用户说"分析这个文档"、"推荐 RAGFlow 解析参数"、"文档用什么 chunk_method"
- 用户需要批量分析一个目录下的文档
- 用户想了解某个文档适合什么解析配置
- 用户说"RAGFlow 配置顾问"、"文档解析配置"

## 工作流程（引导式）

### 1. 收集输入

询问用户需要分析的文档路径（单文件或目录）：

> "请告诉我需要分析的文档路径：
> - 单个文件：`/path/to/doc.pdf`
> - 整个目录：`/path/to/docs/`
> 
> 可选选项：
> - `--no-llm`：仅规则引擎，不调用 LLM（更快但准确度略低）
> - `--csv results.csv`：批量分析时导出 CSV"

### 2. 执行分析

根据用户输入，运行 CLI 工具：

**关键路径**（相对于 ENG_AI 项目根目录）：
- 核心模块：`experiments/analysis_reports/15_文档解析自动化/scripts/ragflow_config_advisor.py`
- CLI 入口：`experiments/analysis_reports/15_文档解析自动化/scripts/run_configure_parser.py`

**命令**：

```bash
# 单文件分析
cd D:/06_Project/ENG_AI
python experiments/analysis_reports/15_文档解析自动化/scripts/run_configure_parser.py file --file "<filepath>"

# 单文件分析 + LLM 终判
python experiments/analysis_reports/15_文档解析自动化/scripts/run_configure_parser.py file --file "<filepath>"

# 仅规则引擎（不调 LLM）
python experiments/analysis_reports/15_文档解析自动化/scripts/run_configure_parser.py file --file "<filepath>" --no-llm

# JSON 格式输出（适合程序化处理）
python experiments/analysis_reports/15_文档解析自动化/scripts/run_configure_parser.py file --file "<filepath>" --json

# 批量分析目录
python experiments/analysis_reports/15_文档解析自动化/scripts/run_configure_parser.py dir --dir "<dirpath>"

# 批量分析 + 导出 CSV
python experiments/analysis_reports/15_文档解析自动化/scripts/run_configure_parser.py dir --dir "<dirpath>" --csv results.csv
```

### 3. 解读结果并给出建议

分析完成后，向用户呈现：

1. **推荐结果**：chunk_method + 置信度 + 理由
2. **候选列表**：Top-3 候选方法及得分
3. **关键特征**：语言、代码密度、QA 密度、实体密度等
4. **建议参数**：chunk_token_num、delimiter、layout_recognize 等

**互动环节**：询问用户是否满意推荐结果：

> "推荐 `{method}`，置信度 `{confidence}`。是否需要调整参数？或者想了解其他候选方案？"

### 4. 参数调整（可选）

如果用户想调整，可以：
- 尝试其他候选 method
- 手动覆盖特定参数
- 重新分析（更改 `--no-llm` 等选项）

## 14 种支持的 Chunk Method

| Method | 适用场景 |
|--------|---------|
| `naive` | 通用文本，按 token 数切分 |
| `general` | 通用文档（含简单结构） |
| `manual` | 手动指定分隔符 |
| `qa` | QA 问答对文档 |
| `table` | 表格密集型文档 |
| `paper` | 学术论文 |
| `book` | 书籍/长文档 |
| `laws` | 法律/规范文档 |
| `presentation` | PPT/演示文稿 |
| `picture` | 图片为主文档 |
| `one` | 整个文档作为一个 chunk |
| `knowledge_graph` | 知识图谱构建 |
| `email` | 邮件文档 |
| `tag` | HTML/XML 标签文档 |

## 14 项文档特征

| 层级 | 特征 | 说明 |
|------|------|------|
| L0 | 扩展名、文件大小、页数估算 | 零成本，文件名即可获取 |
| L1 | 语言、列表分布、代码密度、QA密度、实体密度、条款密度、内容采样 | 需解析文档内容 |

## 降级机制

1. **LLM 可用** → 规则引擎 Top-3 → LLM 终判 → 推荐结果
2. **LLM 不可用** → 规则引擎 Top-1 → 推荐结果（标记 `source: rules_only`）
3. **文档无法解析** → 基于扩展名回退推荐

## 注意事项

- **环境要求**：Python 3.8+，需要安装 `ragflow` 的 `rag.nlp` 和 `deepdoc` 模块
- **LLM API**：默认从环境变量 `LLM_API_BASE` 或 `DEEPSEEK_API_BASE` 读取，回退到 `http://localhost:8000/v1`
- **大文件**：超过 100MB 的文件可能解析缓慢，建议先用 `--no-llm` 快速评估
- **批量分析**：无 `--csv` 时仅终端输出汇总表；加 `--csv` 导出结构化数据

## 代码位置

- SKILL 文件：`skills_sync/skills/ragflow-doc-advisor/SKILL.md`
- 核心模块：`ENG_AI/experiments/analysis_reports/15_文档解析自动化/scripts/ragflow_config_advisor.py`
- CLI 入口：`ENG_AI/experiments/analysis_reports/15_文档解析自动化/scripts/run_configure_parser.py`
- 单元测试：`ENG_AI/experiments/analysis_reports/15_文档解析自动化/scripts/test_ragflow_config_advisor.py`
- 实施报告：`ENG_AI/experiments/analysis_reports/15_文档解析自动化/03-RAGFlow文档解析配置顾问_实施报告_v1.0.html`