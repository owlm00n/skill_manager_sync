# Gerrit Commit Message 格式自动生成机制分析报告

## 一、现象

commit 943212 (EAI-cuijian) 的提交信息具有以下结构化格式：

```
Bug #3502855 EAI-cuijian: 新增 smart_create_bug 智能创建 Bug 技能

[root cause  ]:need a skill to create bug quickly...
[changes     ]:add smart_create_bug skill...
[side effects]:no
[self test   ]:yes
[download normally]:yes
[power on/off normally]:yes
[do common repository/branch inspection]:yes
[is there dependence]:no
[confirm dependent commit]:no
[board]:NA
[test case]:agent task test
[reviewers]:cuijian

commit_template_version:v1
Signed-off-by: xianjun.zeng <xianjun.zeng@unisoc.com>
Change-Id: I87edb59e...
```

## 二、机制分析

### 2.1 客户端 hook 现状

| 位置 | 文件 | 内容 |
|------|------|------|
| `F:/05_Code/Xiaomi_Kernel_OpenSource-yunluo-s-oss/.git/hooks/` | `commit-msg` (253行) | gerrit-manager 自定义 hook（模板+校验+Change-Id） |
| `F:/05_Code/Xiaomi_Kernel_OpenSource-yunluo-s-oss/.git/hooks/` | `prepare-commit-msg.sample` | Git 标准示例（未启用） |
| `~/.gitconfig` | — | 无 `commit.template` 配置 |
| `~/.git-template/` | — | 不存在 |

**结论：当前客户端没有任何 hook 或配置能自动生成结构化字段。**

### 2.2 Gerrit 服务端

| 组件 | 状态 |
|------|------|
| Gerrit 标准 commit-msg hook (`/tools/hooks/commit-msg`) | 81行，仅生成 Change-Id |
| prepare-commit-msg hook (`/tools/hooks/prepare-commit-msg`) | 不存在 (404) |
| `sprd_commit_monitor` 机器人 | ✅ 活跃，对格式不符的提交自动 -2 |

### 2.3 sprd_commit_monitor 行为

commit 943212 的审批历史：
- Patch Set 1: **-2** by sprd_commit_monitor（格式不符）
- Patch Set 2: **-2** by sprd_commit_monitor（格式仍不符）
- Patch Set 3: +1 by xianjun.zeng（格式正确，通过）

### 2.4 同仓库格式对比

| 仓库 | 所有提交格式 | Bug ID 必填 |
|------|------------|:--:|
| EAI-cuijian | 全部 `Bug #ID: 描述` 格式 | ✅ |
| EAI | 混合：部分 `Bug #ID: 描述`，部分 `feat: 描述` | ❌ 部分缺失 |

## 三、结论

**"自动添加"的机制是：Gerrit 服务端 `sprd_commit_monitor` 机器人强制校验格式，不符合则 -2 拒绝。** 这不是客户端 hook 自动生成的，而是 server-side 强制规范。

### 当前流程（有问题）：
```
用户手动写 commit → 本地 hook 校验（简单格式） → push → sprd_commit_monitor -2 拒绝 → 修改 → 再 push → 可能再次 -2
```

### 目标流程（需要实现）：
```
用户 git commit → hook 生成模板（含 Bug ID + 结构化字段）→ 用户填写 → hook 校验 → push 前确认 → push → sprd_commit_monitor 通过
```

## 四、建议

需要在 `gerrit-manager` skill 中实现：

1. **commit-msg hook**：生成完整的结构化模板（含 Bug ID 获取 + 所有 `[root cause]` 等字段）
2. **pre-push hook**：push 前展示提交摘要，用户确认后执行
3. **Bug ID 获取**：分支名提取 → 交互输入 → Bugzilla 验证