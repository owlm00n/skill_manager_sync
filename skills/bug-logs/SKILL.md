---
name: bug-logs
description: ⚠️ DEPRECATED — Bug日志目录查询 & 附件下载功能已合并到 bug-workspace (v3.0)。请使用 bug-workspace 代替。
version: "2.0-deprecated"
tags: [bugzilla, log-directory, structured-parsing, unc, ftp, download, rayfile, deprecated]
---

# ⚠️ 已废弃 — Bug日志目录查询 & 附件下载

> **此 Skill 已废弃（2026-08-27）。** 所有功能已合并到 [bug-workspace](../bug-workspace/SKILL.md) v3.0。
>
> **迁移指南：**
> - `parse_unisoc_structured_fields()` → `bug_workspace.py` 同名函数
> - `list_log_directory()` → `bug_workspace.py` 同名函数
> - `fetch_bug_with_logs()` → `bug_workspace.py` 同名函数
> - `detect_attachment_type()` → `bug_workspace.py` 同名函数
> - `download_from_unc_path()` → `bug_workspace.py` 同名函数（v3.0 重写，支持 full/incremental 模式）
> - `download_from_rayfile()` → `bug_workspace.py` 同名函数
> - `download_bug_attachments()` → `bug_workspace.py` 同名函数（v3.0 重写，`download_mode` 参数替代 `download`+`refresh`）
> - `normalize_downloaded_folder()` → `bug_workspace.py` 同名函数
> - `copy_missing()` → `bug_workspace.py` 同名函数
>
> **MCP 工具：** `bug_logs` MCP 工具已废弃，请使用 `bug_workspace` 工具（支持 `download_mode` 参数）。
>
> **代码文件：** `bug_logs.py` 保留作为历史参考，但不再维护。所有新功能请在 `bug_workspace.py` 中开发。

## 原始功能概述（已迁移）

以下功能已迁移到 bug-workspace：

### 结构化评论解析
解析 unisoc Bugzilla Comment #0 的 19 字段模板格式。

### 日志目录列表
支持 UNC + FTP 双通道列出日志目录内容。

### 智能附件类型检测
自动判断 Bug 的附件类型（UNC / rayfile / none）。

### 附件下载
UNC 路径复制 + rayfile FTP 下载 + 目录规范化。

## 相关 Skill

- **bug-workspace**: **当前推荐** — 工作区创建 + 附件下载 + 结构化解析（v3.0 已合并本 Skill 全部功能）
- **bug-core**: Bug 查询核心

## 代码位置

| 文件 | 说明 |
|------|------|
| `bug_logs.py` | 原始下载+日志模块（~924行，仅保留作为历史参考，不再维护） |
| `config/bugzilla_instances.json` | 实例配置（含FTP凭证） |
| `comment_0.txt` | 测试用结构化评论样本 |
| `tests/test_logs.py` | 日志测试套件（51用例） |