# Skill Sync — 统一 Skill 管理仓库

Claude Code Skill 的权威源。通过 symlink 分发到 `~/.claude/skills/`。

## 已注册 Skill

| Skill | 版本 | 用途 |
|-------|------|------|
| bug-hub | v1.1 | 统一编排入口，链式调度子技能 + Web Dashboard (8777) |
| bug-core | - | Bug 信息查询、智能摘要、评论提取 |
| bug-workspace | - | 工作区创建 + 附件下载 + 解压 |
| pd-auth-analyse | v2.0.0 | 6-Phase PD 认证深度分析 |
| log-analyzer | v2.1 | 角色感知日志分析 |
| protocol-parser | v3.0 | PD/USB/CC 协议智能解析与可视化 |
| keyword-vault | v1.0 | 调试关键词收纳系统 |
| code-generator | - | 代码/脚本生成 |

## 使用方式

1. 克隆本仓库到本地
2. 创建 symlink: `mklink /D C:\Users\<user>\.claude\skills\<skill-name> <repo-path>\skills\<skill-name>`
3. Claude Code 自动加载 SKILL.md

## 目录结构

```
skills_sync/
├── README.md
├── .gitignore
└── skills/
    ├── bug-hub/
    ├── bug-core/
    ├── bug-workspace/
    ├── pd-auth-analyse/
    ├── log-analyzer/
    ├── protocol-parser/
    ├── keyword-vault/
    └── code-generator/
```