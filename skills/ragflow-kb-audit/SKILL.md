---
name: ragflow-kb-audit
description: RAGFlow 知识库效果审核与评估。当用户提到 RAGFlow 审核、知识库评估、KB 效果测试、RAG 检索效果、chunk 质量检查、检索召回率验证、hidden-label diff 评测时，必须使用此 skill。也适用于 RAGFlow chunking 配置变更后的回归验证、新增 KB 文档后的上线前验证、定期知识库健康检查。
---

# RAGFlow 知识库效果审核/评估

通过 **hidden-label 测试 diff** 评估 RAGFlow 知识库的检索召回和 LLM 利用效果，核心回答一个问题：

> "KB 文档命中 ≠ chunk 包含足够信息。RAG 检索真的帮到 LLM 了吗？"

## 何时使用

| 场景 | 触发条件 |
|------|---------|
| 新 KB 文档上线前验证 | 新增 KB 文档后，创建对应 hidden-label diff 验证 |
| RAGFlow 配置变更后回归 | chunking 策略、embedding 模型、similarity_threshold 变更 |
| 定期知识库健康检查 | 每周/每月运行，确认已有 KB 文档可正常召回 |
| KB 文档质量审查 | 发现某类 Bug 漏报时，检查对应 KB 文档 |
| 评测方法复现 | 其他子系统需要建立类似 RAG 评测 |

## 前置条件：必须先读方法论文档

⚠️ **执行任何操作前，必须先读取 `references/ragflow_eval_methodology.md`**，重点理解：

- **§2 评估管线**：8 步管线的完整流程（query 提取 → RAGFlow 检索 → 质量过滤 → Chunk 质量检查 → Prompt 构建 → LLM 审查 → 产物生成 → 报告生成）
- **§4 Hidden-Label Diff 设计规范**：goto label body 必须不可见于 diff 的设计原理
- **§5 Chunk Quality 评估方法**：5 项自动检查的原理、0-100 评分公式、passed/failed 判定准则
- **§7 评估局限性**：LLM 非确定性、单模型评估等限制

**不读方法论直接操作的后果：**
- ❌ 不理解 hidden-label 设计意图，误解 NoRAG 基线含义
- ❌ 不理解 chunk_quality 评分逻辑，误判测试结果
- ❌ 添加新 diff 时违反设计规范，评测失效

## 执行步骤

### Step 1: 运行评测管线

评测脚本位于 EAI 项目的实验目录。脚本依赖 EAI 框架环境（LLM API key、RAGFlow 连接）。

```bash
cd experiments/analysis_reports/14_RAGFlow_codereview_eval/03_bug_eval/scripts

# 运行完整评测（4 diff × 2 mode = 8 次 LLM 调用，约 15-30 分钟）
python run_bug_diff_eval.py
```

**输入**：`../data/` 目录下的 `.patch` 文件（hidden-label diff）
**输出**：`../results/{diff_key}/rag/test_summary.json`（含 `chunk_quality` 字段）

### Step 2: 生成报告

```bash
# 依赖 Step 1 产出的 test_summary.json
python generate_reports.py
```

**输出**：
- `../results/master_evaluation_report.html` — 聚合总报告（所有 diff 摘要卡片）
- `../results/test_report_{diff_key}.html` — 每个 diff 的详细报告（含 chunk quality 可视化面板）
- `../results/master_summary.json` — 评测总数据（供程序消费）

### Step 3: 检查结果

```bash
# 查看每个 diff 的评测摘要（重点关注 chunk_quality）
cat ../results/*/rag/test_summary.json | jq '{kb_hit, kb_rank, kb_score, chunk_quality}'

# 打开总报告
start ../results/master_evaluation_report.html
```

### 判定标准

| 结果 | chunk_quality.passed | LLM 正确 | 含义 |
|------|---------------------|---------|------|
| ✅ 完美 | true | ✅ | KB 文档有效增强 LLM 审查 |
| ⚠️ 关注 | true | ❌ | 检索正确但 LLM 理解错误（术语混淆，需消除歧义） |
| ❌ 失败 | false | — | Chunk 内容不完整，需修复 chunking 策略或 KB 文档结构 |

## 评测管线速览

```
Diff (.patch) → [Skeleton Query] → [RAGFlow 检索] → [质量过滤]
                                                        ↓
                                             [Chunk 质量检查] ← P0 关键步骤
                                                        ↓
                                             [Prompt 构建 (eval-direct)]
                                                        ↓
                                             [LLM 审查 (deepseek-v4-pro)]
                                                        ↓
                                             [产物 + 报告生成]
```

**详细管线说明见 `references/ragflow_eval_methodology.md` §2。**

## 常见失败模式与诊断

### 模式 1: KB 文档未被检索到 (kb_hit = false)

**诊断步骤**：
1. 检查 KB 文档是否已上传到正确 dataset（`aa3a7fa2ab8211f1aababf754581223c`）
2. 检查 RAGFlow 解析状态
3. 检查 skeleton query 是否包含足够的特征词
4. 在 RAGFlow UI 中手动检索确认

**修复方向**：增强 query 提取、降低 similarity_threshold、检查 embedding 模型

### 模式 2: KB 命中但 chunk_quality 不通过 (passed = false)

**这是 Diff D 的经典失败模式**（RAGFlow AST chunking 将摘要表和说明文字拆分为独立 chunk）。

**诊断步骤**：
1. 查看 `chunk_quality.issues` 了解具体问题
2. 打开 `retrieval_raw.json` 查看命中 chunk 的实际内容
3. 对比原始 MD 文件，确认 chunking 是否正确切分

**修复方向**：
- RAGFlow 侧：调整 chunking 策略（增大 chunk 大小、禁用 AST chunking）
- KB 文档侧：将表格和说明文字放在同一段落，避免 AST 拆分
- Prompt 侧：增大 top_k 取多个 chunk 合并

### 模式 3: KB 命中 + chunk 完整但 LLM 理解错误

**诊断步骤**：对比 RAG prompt 中的 KB 上下文和 LLM 输出，定位误解点

**修复方向**：KB 文档消歧术语、Prompt 增加术语区分指令、增加 few-shot 示例

### 模式 4: RAG 结果与 NoRAG 无差异

**可能原因**：
- Diff 不满足 hidden-label 条件（关键知识在 diff 中可见）
- KB 检索命中的内容与 diff 已有信息重叠
- LLM 忽略了 RAG 上下文

**诊断后参考 `references/ragflow_eval_methodology.md` §4 检查 diff 设计**

## 扩展：为新 Bug 类型添加评测

1. **阅读** `references/ragflow_eval_methodology.md` **§4** — 了解 hidden-label diff 设计规范
2. **创建 KB 文档**（遵循 §4.2 格式要求：YAML frontmatter、label 语义表、审计规则、代码示例）
3. **创建 hidden-label diff**（`.patch` 文件放到 `data/`）
4. **注册到评测脚本**：

```python
# 在 scripts/run_bug_diff_eval.py 的 DIFFS 字典中添加
DIFFS = {
    "H_new_bug_type": {
        "patch_file": "data/H_new_bug_type.patch",
        "description": "新 Bug 类型的描述",
        "bug_type": "new_category",
    },
}
# 在 scripts/generate_reports.py 中添加对应条目
EXPECTED_KB_MAP = {
    "H_new_bug_type": "new_kb_document.md",
}
```

5. 上传 KB 文档到 RAGFlow → 运行评测

## 相关资源

| 资源 | 路径 | 说明 |
|------|------|------|
| 📖 **评估方法论** | `references/ragflow_eval_methodology.md` | **必读** — 完整管线、hidden-label 规范、chunk quality 原理 |
| 🔧 **评测执行器** | `scripts/run_bug_diff_eval.py` | Step 1 运行 — 产出 test_summary.json（含 chunk_quality） |
| 📊 **报告生成器** | `scripts/generate_reports.py` | Step 2 运行 — 产出 HTML 报告 |
| 📝 **评测报告** | `RAG_vs_NoRAG_评测报告.md` | 人工评测报告 |
| 📁 **KB 源文件** | `EAI/employees/cuijian/knowledge/code_knowledge/PD/` | 上传到 RAGFlow 的 MD 源文件 |
| ⚙️ **RAGFlow 配置** | Dataset `aa3a7fa2ab8211f1aababf754581223c` | 检索目标 dataset |
| 🧪 **Diff 数据** | `data/` 目录下 `.patch` 文件 | Hidden-label test diffs |

---

*Skill 版本: v1.0 | 适配 run_bug_diff_eval.py v2+ | 2026-09-24*