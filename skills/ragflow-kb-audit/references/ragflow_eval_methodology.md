# RAGFlow 代码审查知识库效果评估方法

> **文档版本**: v1.0 | **日期**: 2026-09-23
> **位置**: `experiments/analysis_reports/14_RAGFlow_codereview_eval/03_bug_eval/`
> **关联脚本**: `scripts/run_bug_diff_eval.py`, `scripts/generate_reports.py`

---

## 1. 评估目标

评估 RAGFlow 知识库检索是否能有效增强 LLM 代码审查的 Bug 检出能力，特别是对于**仅从 diff 上下文无法推导**的 Bug。

### 1.1 核心假设

代码审查中，某些 Bug 需要的领域知识（如寄存器保护协议、goto-label 锁语义）**不包含在 diff 上下文中**。纯 NoRAG 模式下 LLM 只能猜测；RAG 模式下，知识库提供这些隐藏的语义信息，使 LLM 能够精准定位 Bug。

### 1.2 评估维度

| 维度 | 指标 | 评估方法 |
|------|------|---------|
| **检索召回** | KB 命中率、命中排名、命中分数 | 对比 expected_kb 与实际检索结果 |
| **Chunk 质量** | 内容完整性、语义完整性 | 自动化 `check_chunk_quality()` 检查 |
| **LLM 利用** | Bug 检出正确性、置信度、覆盖率 | RAG vs NoRAG 对比分析 |
| **端到端增量** | 从模糊/错误 → 精准诊断的数量 | 逐 diff 对比 verdict 变化 |

---

## 2. 评估管线

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG vs NoRAG 评测管线                          │
│                                                                   │
│  [1] Query提取 ──→ [2] RAGFlow检索 ──→ [3] 质量过滤              │
│       │                    │                  │                   │
│       ▼                    ▼                  ▼                   │
│  skeleton方法        top_k=10           score >= 0.3              │
│  函数名+文件名+API    similarity_th=0.2   min_results=1           │
│                                                                   │
│  [4] Chunk质量检查 ──→ [5] Prompt构建 ──→ [6] LLM审查            │
│       │                    │                  │                   │
│       ▼                    ▼                  ▼                   │
│  5项自动检查           eval-direct模板     deepseek-v4-pro        │
│  table_only/frontmatter  镜像生产prompt     纯文本API              │
│  code/text/completeness  唯一变量=RAG上下文                        │
│                                                                   │
│  [7] 产物生成 ←── [8] 报告生成                                    │
│       │              │                                            │
│       ▼              ▼                                            │
│  test_summary.json  per-diff HTML + master HTML                   │
│  all_findings.json  RAG_vs_NoRAG_评测报告.md                       │
│  verified_findings.json                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 Step 1: Query 提取 (Skeleton 方法)

从 diff 中自动提取检索 query，无需手工构造：

```
输入: diff patch 文件
处理: extract_diff_skeleton() → 提取文件路径、函数名、goto labels、关键 API
输出: "{file_path} {function_names} {key_apis}" 格式的 query 字符串
```

**示例**：
```
# Diff D (寄存器保护 Bug)
drivers/usb/typec/tcpm/sc27xx_pd.c sc27xx_pd_reconfig_cc sc27xx_pd_set_cc_rd 
sc27xx_pd_set_cc_rp sc27xx_init_tcpc_dev mutex_lock mutex_unlock

# Diff F (goto-label 双重解锁 Bug)
drivers/usb/typec/tcpm/sprd_tcpm.c sprd_tcpm_handle_data_role_swap 
mutex_lock port_unlock done
```

### 2.2 Step 2: RAGFlow 检索

```json
{
  "dataset_ids": ["<dataset_id>"],
  "question": "<query>",
  "top_k": 10,
  "similarity_threshold": 0.2
}
```

返回结果规范化：
- `similarity` → `score`（统一字段名）
- `content_with_weight` → `content`（统一内容字段）
- `docnm_kwd` 作为 source 标识符

**产物**：`retrieval_raw.json`, `retrieval_ranking.txt`

### 2.3 Step 3: 质量过滤

```python
SCORE_THRESHOLD = 0.3  # 分数阈值
MIN_RESULTS = 1        # 最少结果数
```

过滤逻辑：
- 所有 chunks 分数 >= threshold 且数量 >= min_results → PASS
- 否则 → FAIL（记录失败原因）

**产物**：`quality_filter_detail.json`

### 2.4 Step 4: Chunk 内容质量检查 ⭐ NEW

这是 **P0 关键步骤**，解决了"文档命中但 chunk 内容不足以支撑 LLM 推理"的问题。

RAGFlow 的 AST-based chunking 会将 Markdown 按 AST 节点类型拆分：
- `<table>` 节点成为独立 chunk（`doc_type_kwd: "table"`）
- 文本段落成为独立 chunk
- **表格式的摘要 chunk 可能脱离其说明性正文**

#### 检查项

| # | 检查项 | 判定逻辑 | 权重 |
|---|--------|---------|------|
| 1 | `is_table_only` | HTML `<table>` 主导，非表格文本 < 300 chars | 30 pts |
| 2 | `has_frontmatter` | 内容以 `---` 开头（YAML frontmatter） | 20 pts |
| 3 | `has_code_examples` | 含 code fences 或缩进 C 代码模式 | 20 pts |
| 4 | `has_explanatory_text` | 实质性散文段落 >= 100 chars | 30 pts |
| 5 | `semantic_completeness` | `complete` / `partial` / `fragment` | — |

#### 综合评分

```
quality_score = 0
quality_score += 30  if NOT is_table_only
quality_score += 20  if has_frontmatter
quality_score += 20  if has_code_examples
quality_score += 30  if has_explanatory_text

passed = (quality_score >= 70) AND (completeness != "fragment")
```

#### 内容类型分类

| 类型 | 特征 | 示例 |
|------|------|------|
| `table_only` | 仅 HTML table，无 frontmatter | D diff 的 Rank 1 表格 chunk |
| `mixed` | frontmatter + 文本 + 代码 | 完整的 KB 文档 chunk |
| `frontmatter_only` | 有 frontmatter 但无说明文字 | 元数据完整的空模板 |
| `code_focused` | 有代码但无说明文字 | 纯代码片段 |
| `text_only` | 有说明文字但无代码 | 纯文本文档 |
| `fragment` | 都不完整 | 破损的 chunk |

#### 语义完整性

| 级别 | 条件 | 风险 |
|------|------|------|
| `complete` | frontmatter + 文本 + 代码 三者齐全 | 低 — LLM 可获得完整的知识上下文 |
| `partial` | 有两个元素但不是全部 | 中 — LLM 可能缺少关键信息 |
| `fragment` | 仅一个元素或都不完整 | **高** — 类似 D diff 的失败模式 |

**产物**：`chunk_quality` 字段写入 `quality_filter_detail.json` 和 `test_summary.json`

### 2.5 Step 5: Prompt 构建

使用 **eval-direct** 模板，镜像生产环境 `_llm_review_diff`（`engd_code_review.py:548-574`）：

- **System prompt**：硬编码 13 字段 JSON 输出格式，scope 约束（仅报告变更引入的 Bug）
- **User prompt**：diff 内容内联嵌入 + 可选 RAG 知识库上下文块
- **无工具指令**：无 Read/Write/Bash 等工具调用
- **唯一变量**：RAG 模式下在 diff 后追加知识库上下文块

```python
# RAG 模式
user_prompt = f"Review this diff...\n```diff\n{diff}\n```\n{RAG_CONTEXT_BLOCK}\n"

# NoRAG 模式
user_prompt = f"Review this diff...\n```diff\n{diff}\n```\n"
```

**产物**：`prompt.txt` (system + user 完整 prompt)

### 2.6 Step 6: LLM 审查

- **模型**：`deepseek-v4-pro`
- **调用方式**：纯文本 `chat_simple()`，无工具调用
- **重试策略**：最多 2 次重试，指数退避（5s, 10s）
- **截断**：prompt > 120K chars 时截断

**产物**：`llm_response.txt`, `llm_response.json`

### 2.7 Step 7: 产物生成

```
output_dir/
├── test_summary.json          # 评测结果摘要
├── query.txt                  # 提取的检索 query
├── retrieval_raw.json         # RAGFlow 原始响应
├── retrieval_ranking.txt      # 人类可读的检索排名
├── quality_filter_detail.json # 质量过滤 + chunk_quality
├── rag_context_formatted.txt  # 格式化后的 RAG 上下文
├── diff_skeleton.json         # diff 骨架提取结果
├── debug_info.json            # 调试信息
├── prompt.txt                 # 完整 prompt (system + user)
├── llm_response.txt           # LLM 原始响应文本
├── llm_response.json          # LLM 响应元数据
├── all_findings.json          # 解析后的 findings
├── verified_findings.json     # 自动判定结果
└── report.html                # 单 diff 审查报告
```

---

## 3. 报告生成方法

### 3.1 Per-Diff 报告 (`test_report_{diff_key}.html`)

由 `scripts/generate_reports.py` 生成，包含 5 个部分：

| 部分 | 内容 | 数据来源 |
|------|------|---------|
| **A: Bug 描述** | diff 内容、quick stats（prompt size, findings count） | `test_summary.json`, diff patch 文件 |
| **B: 检索管线** | query 提取 → RAGFlow 请求 → 检索排名 → chunk 质量检查 → RAG 上下文 | `retrieval_ranking.txt`, `quality_filter_detail.json`, `rag_context_formatted.txt` |
| **C: Findings 对比** | RAG/NoRAG 并排对比，原始 findings 卡片 | `llm_response.txt` (parsed) |
| **D: 原始数据** | 中间产物路径索引 | 文件系统路径 |

### 3.2 Chunk Quality 可视化

在 per-diff 报告的 B 部分新增 chunk quality 面板：

```
┌──────────────────────────────────────┐
│ Quality Score: 30/100 ❌ FAIL        │
│ Source: register_protocol_031.md     │
│ Content Type: table_only             │
│ Semantic Completeness: ❌ Fragment   │
├──────────────────────────────────────┤
│ Frontmatter ❌ | Code ❌ | Text ❌ │  ← grid 展示
│ Table-Only  ⚠️                        │
├──────────────────────────────────────┤
│ ⚠️ TABLE_ONLY: Chunk is standalone   │  ← issues 列表
│    HTML table with no explanatory... │
│ ⚠️ NO_FRONTMATTER: Chunk lacks...    │
│ ⚠️ NO_CODE: Chunk contains no code.. │
│ ⚠️ NO_EXPLANATORY_TEXT: Chunk lacks..│
│ ⚠️ SEMANTIC_FRAGMENT: Chunk is a...  │
└──────────────────────────────────────┘
```

### 3.3 Master 报告 (`master_evaluation_report.html`)

聚合 4 个 diff 的结果：

- 评测配置总览
- 每个 diff 的摘要卡片（含 findings count, KB hit, chunk quality）
- 完整结果表（8 行：4 diff × 2 mode）
- 分析要点（KB 检索、RAG 增值、失败案例、设计有效性）

### 3.4 人工评测报告 (Markdown)

`RAG_vs_NoRAG_评测报告.md` — 面向人类的完整中文评测报告，包含：
- 逐 diff RAG vs NoRAG 对比分析
- 核心发现和启示
- 端到端链路各环节验证
- 根因分析和修复记录

---

## 4. Test Diff 设计规范

### 4.1 Hidden-Label 设计

所有评测 diff 必须采用 **hidden-label 设计**：

```
关键原则：goto label 的 body 不在 diff 上下文中

diff 中可见：
  mutex_lock(&port->lock);
  mutex_lock(&port->swap_lock);
  goto swap_unlock;          ← 只看到 goto，看不到 label body

diff 中不可见（需要 KB 提供）：
  swap_unlock:
      mutex_unlock(&port->swap_lock);
      return ret;
  done:
      return ret;            ← 什么都不释放
```

这样设计的目的是：
- NoRAG 模式下 LLM 无法从 diff 本身知道 label 释放了哪些锁 → 只能猜测
- RAG 模式下 KB 提供 label 语义 → 精准定位

### 4.2 KB 文档要求

每个 diff 对应的 KB 文档必须包含：

1. **YAML frontmatter**：`knowledge_type`, `severity`, `review_points`, `confidence`
2. **完整的 label 语义表**（对 lock-ordering bug）：每个 label 释放哪些锁
3. **审计规则**：明确的反模式描述（如"goto port_unlock when only swap_lock is held → double unlock"）
4. **代码示例**：正确和错误的代码模式对比
5. **术语消歧**：区分相似概念（如硬件 unlock vs 软件 mutex_unlock）

---

## 5. Chunk Quality 评估方法详解

### 5.1 为什么 Chunk Quality 很重要

**核心发现**：文档级命中 (Rank 1) ≠ chunk 包含足够信息。

以 Diff D (`register_protection`) 为例：

| 层级 | 状态 | 说明 |
|------|------|------|
| 文档检索 | ✅ Rank 1 (score 0.5189) | `register_protocol_031.md` 成功命中 |
| Chunk 内容 | ❌ table_only fragment | 仅 4 行 HTML 摘要表 |
| LLM 理解 | ❌ 错误 | 将"unlock"误解为 mutex_unlock |

**检索到的 chunk（rank 1）实际内容**：
```
Function              | Line  | Pattern
sc27xx_pd_set_cc_rp   | ~450  | Correct: unlock → write → lock
sc27xx_pd_set_cc_rd   | ~470  | Correct: unlock → write → lock
sc27xx_pd_set_cc_open | ~490  | Correct: unlock → write → lock
sc27xx_pd_reconfig_cc | NEW   | ⚠️ BUG: writes CC_CTRL without unlock!
```

**该 chunk 缺失的内容**（在原文档中但被 AST chunking 分离）：
- 0xA55A unlock 序列的具体代码
- 寄存器地址（`SC27XX_PD_CC_CTRL`, `SC27XX_PD_CTRL_UNLOCK`）
- "硬件静默丢弃写入，无错误指示"的警告
- 代码审查 checklist（验证 unlock → writel → lock 序列）
- 常见陷阱（将 mutex_lock 与硬件 unlock 混淆）

### 5.2 检查实现

`check_chunk_quality()` 函数（`run_bug_diff_eval.py`）：

```python
def check_chunk_quality(chunk: dict, expected_kb: str = "") -> dict:
    """对检索到的 RAGFlow chunk 进行 5 项自动化内容质量检查。
    
    返回:
        {
            "passed": bool,        # 综合判定
            "score": int,          # 0-100 质量分数
            "issues": [str],       # 人类可读的问题列表
            "checks": {            # 逐项检查结果
                "is_table_only": bool,
                "has_frontmatter": bool,
                "has_code_examples": bool,
                "has_explanatory_text": bool,
                "content_type": str,
                "semantic_completeness": str,
            },
            "source": str,         # 文档名
            "chunk_score": float,  # RAGFlow 相似度分数
        }
    """
```

### 5.3 结果解读指南

| Quality Score | Completeness | 含义 | 行动建议 |
|:---:|:---:|------|------|
| 100 | complete | Chunk 包含完整的知识上下文（frontmatter + 代码 + 文本） | 记录为高质量基线 |
| 70-90 | complete/partial | Chunk 基本完整，可能缺少代码或文本之一 | 确认缺失元素是否为关键信息 |
| 40-60 | partial | Chunk 不完整，缺少多个关键元素 | 检查 RAGFlow chunking 配置 |
| 0-30 | fragment | **严重** — 类似 D diff 失败模式，仅 table/meta 无实质内容 | 需要调整 chunking 策略或启用 merge |

---

## 6. 运行评估

### 6.1 前置条件

1. RAGFlow 服务运行中（`http://10.30.12.54:81`）
2. KB 文档已上传到指定 dataset（`aa3a7fa2ab8211f1aababf754581223c`）
3. EAI 环境变量可用（LLM API key 等）

### 6.2 运行命令

```bash
# Step 1: 运行评测（8 次 LLM 调用，约 15-30 分钟）
cd experiments/analysis_reports/14_RAGFlow_codereview_eval/03_bug_eval/scripts
python run_bug_diff_eval.py

# Step 2: 生成报告
python generate_reports.py
```

### 6.3 输出

```
results/
├── master_summary.json              # 评测总数据
├── master_evaluation_report.html     # 总报告 (HTML)
├── test_report_D_register_protection.html
├── test_report_E_goto_label_lock_leak.html
├── test_report_F_goto_label_double_unlock.html
├── test_report_G_goto_label_wrong_unlock.html
├── D_register_protection/
│   ├── rag/                         # RAG 模式中间产物
│   │   ├── test_summary.json        # 含 chunk_quality 字段
│   │   └── ...                      # 其他产物
│   └── norag/                       # NoRAG 模式中间产物
│       └── ...
├── E_goto_label_lock_leak/
├── F_goto_label_double_unlock/
└── G_goto_label_wrong_unlock/
```

### 6.4 添加新 Test Diff

1. 在 `data/` 目录放置 `.patch` 文件（遵循 hidden-label 设计）
2. 在 `run_bug_diff_eval.py` 的 `DIFFS` 字典中添加条目
3. 在 `generate_reports.py` 的 `DIFFS` 和 `EXPECTED_KB_MAP` 中添加对应条目
4. 按上述命令运行

---

## 7. 评估局限性

| 局限 | 影响 | 缓解措施 |
|------|------|---------|
| **LLM 非确定性** | 同一 prompt 可能产生不同输出 | 置信度 ≥ 80 的发现较为稳定；可多次运行取 mode |
| **KB 文档质量** | KB 文档不准确会导致 RAG 产生错误引导 | 此评估已验证 4/4 KB 文档内容正确 |
| **RAGFlow chunking 不透明** | chunk 边界不能精确控制 | chunk_quality 检查自动化发现此问题 |
| **Hidden-label 覆盖面** | 仅覆盖 goto-label 和寄存器保护两类 Bug | 可扩展到更多 Bug 类型（内存泄漏、引用计数、竞态条件） |
| **单模型评估** | 仅测试 deepseek-v4-pro | 多模型对比需要额外的 eval 配置 |

---

## 8. 相关文档

- **评测报告**: `RAG_vs_NoRAG_评测报告.md`
- **评测脚本**: `scripts/run_bug_diff_eval.py`, `scripts/generate_reports.py`
- **Skill 参考**: `SKILL.md`
- **KB 源文件**: `EAI/employees/cuijian/knowledge/code_knowledge/PD/`
- **Diff 数据**: `data/` 目录下 4 个 `.patch` 文件

---

*文档生成时间: 2026-09-23 | 与 `run_bug_diff_eval.py v2+` 配套*