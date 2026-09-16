# RAGFlow 语义检索集成（实验性）

> 本文档从 SKILL.md 迁移而来，保留全部 RAGFlow 功能细节。SKILL.md 中仅保留精简引用。

### 概述

pd-auth-analyse 支持双通道 A/B 对比分析：
- **通道 A（基准）**：静态文件搜索（`knowledge/` 目录下的 Markdown/JSON 文件）
- **通道 B（实验）**：RAGFlow 向量语义检索（Dify-compatible API）

### API 端点

- **Base URL**: `http://10.30.12.54:81/api/v1`
- **检索接口**: `POST /dify/retrieval`
- **健康检查**: `GET /dify/retrieval/health`
- **执行脚本**: `scripts/ragflow_search.py`

### 请求格式

```json
{
  "knowledge_id": "<dataset_id>",
  "query": "<查询文本>",
  "use_kg": false,
  "retrieval_setting": {
    "top_k": 5,
    "score_threshold": 0.2
  }
}
```

### 知识库映射

| Phase | KB 名称 | Dataset ID | 状态 |
|-------|---------|------------|------|
| Phase 2 | cts-KB | `ca6740b297af11f19f9e7d0056ecab0b` | ⚠️ PD认证（embedding 异常，自动 fallback） |
| Phase 3 | specs-KB | `ca6740b297af11f19f9e7d0056ecab0b` | ⚠️ PD认证（embedding 异常，自动 fallback） |
| Phase 3 | KB-原始规范 | `ca6740b297af11f19f9e7d0056ecab0b` | ⚠️ PD认证（embedding 异常，自动 fallback） |
| Phase 5 | bugs-KB | `ca6740b297af11f19f9e7d0056ecab0b` | ⚠️ PD认证（embedding 异常，自动 fallback） |
| Phase 6 | PD-Code-KB | `aa3a7fa2ab8211f1aababf754581223c` | ✅ PD_Code_KB_v2（正常） |

### Fallback 机制

当 PD认证 数据集（`ca6740b2`）因 embedding 模型异常返回空结果时，自动降级到 PD_Code_KB_v2（`aa3a7fa2`），确保分析不中断。

### 使用方法

```bash
# Phase 2 CTS 测试流程检索
python scripts/ragflow_search.py "TEST.PD.PS.SNK.01 测试步骤" --phase 2 --top-k 5

# Phase 3 规范检索
python scripts/ragflow_search.py "tPSSourceOn timer 超时规范" --phase 3 --top-k 5

# Phase 5 历史 Bug 检索
python scripts/ragflow_search.py "Hard_Reset 超时 根因" --phase 5 --top-k 5

# Phase 6 代码检索
python scripts/ragflow_search.py "sprd_tcpm pd_notify tcpci_transmit" --phase 6 --top-k 5

# JSON 输出（pipeline 模式）
python scripts/ragflow_search.py "PD协议超时" --phase 3 --json
```

### 健康检查

```bash
python scripts/ragflow_search.py --health
```

### 已知问题

- **PD认证 数据集** (`ca6740b297af11f19f9e7d0056ecab0b`): embedding 模型 `unisoc-embedding-zh@unisoc` 未注册，搜索返回 HTTP 500
- **解决方案**: 需 RAGFlow 管理员注册 `unisoc` embedding 实例，或重新创建数据集使用 `unisoc-qwen3-embedding-8b@maas` 模型
- **当前对策**: 自动 fallback 到 PD_Code_KB_v2（仅覆盖代码级知识，非 PD 认证 CTS/规范/方法论知识）