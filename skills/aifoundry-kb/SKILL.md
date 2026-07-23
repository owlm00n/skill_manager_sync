---
name: aifoundry-kb
description: AI Foundry 知识库管理：查询知识库列表、搜索知识库、检索知识库内容、查看知识库详情和应用列表。当用户需要查询、搜索、管理 AI Foundry 上的知识库时使用。
---

# AI Foundry 知识库管理

通过 `knowledge_api.py`（AI Foundry API）和 `dify_knowledge_api.py`（Dify 控制台 API）操作知识库。

## 脚本位置

```
D:\06_Project\aifoundry_knowledge_api\
├── knowledge_api.py        # AI Foundry 后端 API（列表、详情、应用）
├── dify_knowledge_api.py   # Dify 控制台 API（检索知识库内容）
├── API_DOCUMENTATION.md    # 完整 API 文档
└── OPERATION_MANUAL.md     # 操作手册
```

## 操作指南

### 1. 查看我的知识库列表

```bash
cd D:\06_Project\aifoundry_knowledge_api && python knowledge_api.py -u xianjun.zeng -p uioqwer1234. --action my_kb
```

### 2. 搜索知识库（按名称）

```bash
cd D:\06_Project\aifoundry_knowledge_api && python knowledge_api.py -u xianjun.zeng -p uioqwer1234. --action all_kb --search "<关键词>"
```

### 3. 查看知识库详情

```bash
cd D:\06_Project\aifoundry_knowledge_api && python knowledge_api.py -u xianjun.zeng -p uioqwer1234. --action kb_detail --id <知识库ID>
```

### 4. 检索知识库内容

使用 Dify 控制台 API 检索指定知识库的文档内容：

```bash
cd D:\06_Project\aifoundry_knowledge_api && python dify_knowledge_api.py --query "<查询内容>" --top-k 3
```

指定其他知识库 ID：
```bash
cd D:\06_Project\aifoundry_knowledge_api && python dify_knowledge_api.py --query "<查询内容>" --id "<Dify知识库UUID>" --top-k 3
```

### 5. 查看我的应用列表

```bash
cd D:\06_Project\aifoundry_knowledge_api && python knowledge_api.py -u xianjun.zeng -p uioqwer1234. --action my_apps
```

### 6. 查看应用详情

```bash
cd D:\06_Project\aifoundry_knowledge_api && python knowledge_api.py -u xianjun.zeng -p uioqwer1234. --action app_detail --id <应用ID>
```

## 已知知识库

| 名称 | 系统ID | Dify UUID |
|------|--------|-----------|
| PD protocol layer | 2412 | `502201b2-9cab-4a95-95d8-b9877b58bd0e` |

## 已知应用

| 名称 | 系统ID | Dify UUID |
|------|--------|-----------|
| log analyst | 4278 | `dfdb5b5a-b676-4b6d-8eb4-eba3b88d093c` |

## 注意事项

- 检索知识库内容时，默认使用 PD protocol layer 知识库，可通过 `--id` 切换
- 检索参数：hybrid_search（关键词权重 0.3 + 向量权重 0.7），默认 top_k=3
- 知识库内容主要来自英文 USB PD 规范文档，英文查询效果更好
- 首次检索会自动登录 Dify 控制台获取 token
- `knowledge_api.py` 需要 AI Foundry 密码，`dify_knowledge_api.py` 使用空密码 autologin