---
name: jsonl2md
description: Convert Claude Code JSONL transcript files (main session or sub-agent) to readable Markdown. Use when the user wants to view, export, or share CC conversation records in a human-readable format. Triggers on: "convert jsonl", "jsonl to markdown", "export transcript", "view agent record", "jsonl2md".
allowed-tools: Bash, Read, Write, Glob, Grep
---

# JSONL to Markdown Converter

将 Claude Code 的 JSONL 会话记录文件转换为人眼可读的 Markdown 格式。

## 何时使用

- 用户想查看某个 session 或 sub-agent 的完整对话记录
- 用户说 "转换 jsonl"、"导出会话记录"、"查看 agent 运行记录"
- 用户想分享或归档 CC 对话历史

## 支持的 JSONL 类型

| 类型 | 特征 | 示例 |
|------|------|------|
| 主会话记录 | `{sessionId}.jsonl`，含完整对话流 | `a86cc123-...jsonl` |
| Sub-agent 记录 | `subagents/agent-*.jsonl`，含 agent 专用对话 | `agent-a465d978...jsonl` |

## 执行步骤

### 1. 确定输入

询问或自动识别 JSONL 文件路径。如果用户只给了 session ID 或 agent 描述，搜索 `~/.claude/projects/` 目录下的对应文件。

### 2. 运行转换脚本

```bash
python "d:/06_Project/skills_sync/skills/jsonl2md/scripts/jsonl2md.py" <input.jsonl> [output.md]
```

**参数说明：**
- `input.jsonl` — 必填，JSONL 源文件路径
- `output.md` — 可选，输出 Markdown 路径（默认与输入同目录、同名 .md）
- `--max-output N` — 可选，工具结果截断长度（默认 3000 字符）
- `--dir` — 可选，批量转换目录下所有 JSONL 文件

### 3. 展示结果

转换完成后，告知用户输出文件路径和统计信息（消息数、工具调用次数、文件大小）。

## 输出格式

生成的 Markdown 包含：

| 元素 | 渲染方式 |
|------|----------|
| 👤 User | 用户消息 / 工具返回 |
| 🤖 Assistant | AI 回复 |
| 🔧 Tool Call | 工具名 + 参数 |
| 📤 Tool Result | 工具输出（超长截断） |
| 💭 Thinking | 折叠思考过程 |
| ❌ Error | 失败标记 |

## 脚本位置

- 核心脚本：`scripts/jsonl2md.py`
- 可独立运行：`python jsonl2md.py input.jsonl`