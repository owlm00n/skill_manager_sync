# Skills Sync Manager

多 Agent 技能同步管理工具，支持 Junction/Symlink/Copy 三种模式。

## 功能

- **中央技能库**：统一管理所有 skills
- **Global Workspace**：为每个 agent 独立管理 skills
- **Project Workspace**：项目级 skill 管理，支持 auto-detect 扫描
- **Preset 预设**：命名 skill 集合，一键激活/停用
- **多同步模式**：Junction（免管理员）、Symlink、Copy
- **23+ Agent 支持**：Claude Code、Qoder、Cursor、Hermes 等自动发现

## 技术栈

- Python 3.8+ (后端)
- PowerShell (同步脚本)
- 原生 JavaScript (前端)

## 快速开始

```bash
# 启动 Web UI
python web-ui.py

# 访问 http://127.0.0.1:8780
```

## 项目结构

```
skills_sync/
├── web-ui.py          # Python 后端
├── sync.ps1           # PowerShell 同步脚本
├── scan-agents.ps1    # Agent 扫描脚本
├── config.yaml        # 配置文件（需按本地环境修改）
├── skills/            # 中央技能库
└── static/            # 前端文件
    ├── index.html
    ├── css/
    └── js/
```

## 文档

- [功能设计与实现状态](docs/skills-manager-analysis.md)
- [Bug 报告](docs/BUG_REPORT.md)
- [会话历史](docs/conversation-history.md)
- [会话总结](docs/session-summary.md)

## License

MIT
