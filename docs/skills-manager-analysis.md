# Skills Manager 功能逻辑分析

> 基于 https://github.com/xingkongliang/skills-manager 的完整功能梳理
> 用于指导 skills_sync Web UI 的功能设计

---

## 一、核心概念模型

```
                    ┌─────────────────────┐
                    │   Central Library    │  ← 中央仓库 (~/.skills-manager/skills/)
                    │   (所有 skill 的单一源) │     所有 skill 先安装到这里
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
       ┌──────▼──────┐ ┌──────▼──────┐ ┌───────▼──────┐
       │   Presets   │ │   Global    │ │   Project    │
       │  (预设分组)  │ │  Workspace  │ │  Workspace   │
       │ 命名 skill   │ │ (全局工作区) │ │ (项目工作区)  │
       │ 集合，一键    │ │ 每个 agent  │ │ 项目级 skill  │
       │ 激活/停用    │ │ 独立管理页面 │ │ 管理         │
       └─────────────┘ └─────────────┘ └──────────────┘
```

### 关键区分：Install vs Sync
- **Install（安装）**：将 skill 从外部来源（Git/本地/zip/市场）导入到**中央仓库**
- **Sync（同步）**：将中央仓库的 skill **部署到** agent 的全局/项目目录
- 这是两步操作，install 不等于 sync

---

## 二、技能库（Library）

### 2.1 安装来源
| 来源 | 说明 |
|------|------|
| 本地文件夹 | `skills install ./my-skill` |
| Git 仓库 | `skills install https://github.com/foo/bar.git` |
| skills.sh 市场 | `skills install vercel-labs/agent-skills@react-best-practices` |
| .zip / .skill 归档 | 拖拽或选择归档文件 |

### 2.2 安装行为
1. 从来源复制 skill 到中央仓库 `~/.skills-manager/skills/<name>/`
2. 解析 SKILL.md frontmatter（name, description, tags）
3. 记录来源元数据（Git URL、本地路径等）用于后续更新检查
4. **默认仅安装到仓库，不同步到 agent**（除非加 `--sync` 参数）

### 2.3 技能卡片信息
每张 skill 卡片显示：
- 名称、描述、标签
- 来源标识（user/project/plugin）
- 启用/禁用状态
- **Agent 图标徽章**：每个已启用的 agent 显示一个图标
  - 点击图标 → 为该 agent 安装/移除此 skill
  - 图标样式反映实时同步状态

### 2.4 技能操作
| 操作 | 说明 |
|------|------|
| Enable/Disable | 重命名 SKILL.md ↔ SKILL.md.disabled（非破坏性） |
| Edit | 修改 frontmatter（name/description），自动创建 .bak |
| Delete | 软删除到回收站（~/.skills-manager/trash/），记录原始路径 |
| Undelete | 从回收站恢复，支持单个或全部恢复 |
| Tag | 添加/移除标签，用于分组和过滤 |
| Update | 检查 Git 上游更新，重新导入本地 skill |
| Preview | 查看 SKILL.md / README.md 完整内容 |
| Export | 一次性复制到任意目录（不受管理） |

### 2.5 批量操作
- 多选 skill → 批量 enable/disable/export/delete
- 过滤：按来源（user/project/plugin）、按标签、未标记（Untagged）

---

## 三、Preset（预设）

### 3.1 概念
- Preset 是**命名的 skill 集合**
- 在任何工作区中，点击 preset 标签即可**一键激活/停用**其所有 skill
- **重要：激活 preset 是一次性复制操作，不是实时同步**
  - 激活后，preset 包含的 skill 被复制到 agent 目录
  - 之后向 preset 添加新 skill 不会自动同步到已激活的 agent
  - 需要重新 apply preset 才能更新

### 3.2 状态显示
| 状态 | 显示 | 含义 |
|------|------|------|
| ✓ 激活 | 绿色/高亮 | preset 所有 skill 已部署到当前 agent |
| 3/5 | 数量徽章 | 部分 skill 已部署（5 个中 3 个） |
| 无标记 | 灰色 | preset 未对当前 agent 激活 |

### 3.3 操作
| 命令 | 说明 |
|------|------|
| `presets list` | 列出所有 preset |
| `presets preview <name>` | 查看 preset 包含的 skill |
| `presets apply <name>` | 在当前工作区激活 preset |
| `presets add-skill <preset> <skill>` | 向 preset 添加 skill |
| `presets remove-skill <preset> <skill>` | 从 preset 移除 skill |

### 3.4 重叠处理
- 多个 preset 可包含同一 skill
- 停用某个 preset 时，只移除该 preset **独有**的 skill
- 与其他活跃 preset 共享的 skill 保留

---

## 四、全局工作区（Global Workspace）

### 4.1 概念
- 每个已安装的 agent 有**独立的全局 skill 目录**
  - Claude Code: `~/.claude/skills/`
  - Cursor: `~/.cursor/skills/`
  - 等等...
- 全局工作区为每个 agent 提供**独立页面**
- 页面显示该 agent 全局目录中的**所有 skill**，包括非 Skills Manager 安装的

### 4.2 Agent 页面
- **每个 agent 一个页面**：侧边栏选择 agent（如 Claude Code）
- 显示该 agent skills 目录中的所有内容
- 即使 skill 不是通过 Skills Manager 安装的，也会显示（"adopt" 概念）
- 操作：
  - **+ Add Skills**：从中央仓库选择 skill 添加到该 agent
    - 打开统一选择器
    - 搜索中央仓库
    - 可切换目标 agent（always-visible chips）
    - 支持批量添加
  - **Remove**：从 agent 目录移除 skill
  - **Enable/Disable**：切换 skill 状态
  - **Preset 标签**：在页面顶部显示所有 preset，点击激活/停用

### 4.3 All Agents 总览
- 一个页面管理**所有 agent** 的 skill
- 每个 skill 显示 agent 图标徽章，反映各 agent 的同步状态
- 点击徽章 → 为该 agent 安装/移除此 skill

---

## 五、项目工作区（Project Workspace）

### 5.1 概念
- 管理**项目本地**的 skill 文件夹
- 例如 `<project>/.claude/skills/` 中的 skill
- 与全局工作区独立，skill 只对该项目生效

### 5.2 功能
- 查看项目中的所有 agent skill 目录
- 与中央仓库**对比**：哪些 skill 是最新的，哪些需要更新
- **双向同步**：
  - 中央仓库 → 项目（添加/更新 skill）
  - 项目 → 中央仓库（导入项目独有的 skill）
- 支持嵌套 skill 目录
- 支持 per-agent 分配（导出时选择目标 agent）
- 支持批量 enable/disable
- 支持 preset 标签（与全局工作区相同的 preset pills）

### 5.3 与全局工作区的区别
| | 全局工作区 | 项目工作区 |
|---|---|---|
| 路径 | `~/.claude/skills/` | `<project>/.claude/skills/` |
| 作用域 | 所有项目 | 仅当前项目 |
| 参与 preset | 是 | 是（独立管理） |
| 显示非 SM 安装的 skill | 是 | 是 |

---

## 六、Linked Workspaces（链接工作区）

- 指向任意目录作为 skill 根目录
- 用于管理不在默认 agent 路径中的 skill
- 作为独立工作区管理，**不参与全局 preset 同步**

---

## 七、多工具同步（Multi-tool Sync）

### 7.1 同步模式
| 模式 | 说明 |
|------|------|
| Symlink | 创建符号链接，修改即生效 |
| Copy | 复制文件，需要手动触发同步 |

### 7.2 同步操作
- **一键同步**：点击 Sync 将 skill 部署到所有已启用的 agent
- **Per-agent 同步**：每个 skill 卡片的 agent 徽章，点击单独安装/移除
- **Per-skill 控制**：每个 skill 可以单独选择在哪些 agent 上启用

### 7.3 状态反馈
- 每个 skill 卡片显示 agent 图标徽章
- 图标样式反映**实时同步状态**：
  - 已同步 → 高亮/彩色
  - 未同步 → 灰色
  - 点击 → 切换安装/移除

---

## 八、备份与多设备同步（Backup）

### 8.1 概念
- 将中央仓库版本化到 Git 仓库
- 支持 GitHub 一键登录（设备流）
- 自动后台备份 + 多设备同步

### 8.2 同步特性
- **Skill-aware merging**：按 skill 粒度合并，不是按行
  - 设备 A 重命名 skill + 设备 B 编辑内容 → 干净合并
- **冲突不阻塞**：冲突的 skill 保留本地版本，标记为 "Needs attention"
  - 用户选择：keep mine / use remote / keep both
- **快照恢复**：手动备份创建快照版本，可随时恢复

### 8.3 备份内容
- ✅ Skills 文件
- ✅ Tags 标签
- ✅ Presets 预设
- ✅ Per-agent skill 开关状态
- ❌ API keys、tokens、proxy 设置（不离开本机）
- ❌ 超过 100MB 的 skill（自动排除）

---

## 九、市场与搜索（Marketplace）

- 浏览 skills.sh 市场的热门 skill
- 关键词搜索
- AI 搜索（需要 API key）
- 一键安装到中央仓库

---

## 十、Web UI 界面结构（当前 skill-manager.py）

### 10.1 布局
```
┌─────────────────────────────────────────────────────┐
│  Header: 标题 + 搜索 + 来源过滤 + 显示禁用 + 刷新 + 回收站 │
├──────────────────────────┬──────────────────────────┤
│  左侧：Skill 表格         │  右侧：详情抽屉           │
│  # | On | Name | Source  │  名称、来源、状态          │
│  点击行 → 选中            │  Enable/Disable/Edit/Del │
│  显示所有来源的 skill      │  SKILL.md 内容预览        │
├──────────────────────────┴──────────────────────────┤
│  回收站模式：显示已删除 skill + restore 按钮           │
└─────────────────────────────────────────────────────┘
```

### 10.2 当前 Web UI 的局限
- 只有技能库管理（list/preview/edit/delete/enable/disable）
- **没有**全局工作区视图
- **没有**项目工作区视图
- **没有**Preset 管理界面
- **没有**Agent 同步状态显示
- **没有**多工具同步功能
- **没有**备份功能
- **没有**市场浏览功能

---

## 十一、skills_sync 需要补充的核心功能

对比 skills-manager，当前 skills_sync Web UI 缺少：

### 高优先级
1. **全局工作区视图**：每个 agent 独立页面，显示其 skills 目录中的所有内容
2. **Agent 图标徽章**：每个 skill 卡片显示各 agent 同步状态，点击切换
3. **+ Add Skills 选择器**：从中央仓库选择 skill 添加到指定 agent
4. **Preset 实际部署逻辑**：当前 preset activate 只是修改 config，需要实际复制/symlink skill

### 中优先级
5. **项目工作区**：扫描项目目录，显示项目级 skill，与中央仓库对比
6. **Skill 安装功能**：从 Git/本地/zip 导入到中央仓库
7. **回收站管理**：Web UI 中的 trash 查看和恢复
8. **批量操作**：多选 enable/disable/delete

### 低优先级
9. **标签系统**：skill 打标签 + 按标签过滤
10. **备份页面**：Git 远程仓库配置 + 快照管理
11. **市场浏览**：skills.sh 搜索和安装
12. **更新检查**：Git 上游更新检测
