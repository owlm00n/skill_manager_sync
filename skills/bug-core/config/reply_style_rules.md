# 客户回复风格规则

> LLM 自检用规则文件。AI 生成 Bugzilla 客户回复时，读取此文件进行语义自检。
> 与 `reply_style_feedback.md` 配对：用户写反馈 → AI 提炼 → 更新本文件。
> **本文件由 AI 维护，不要手动添加正则或 YAML 配置。**

## 核心原则

**对方是工程师，只需要：结论 + 依据 + 让客户做什么。不需要铺陈分析过程。**

回复是一条纯文本消息，不是文档、不是报告、不是分析总结。

---

## 规则列表

### R1: 禁止填充语

**Bad patterns（语义）**：
- 以"综合分析完成"、"分析完成"、"经综合"、"经分析"、"经定位"、"经确认"、"经排查"、"经审查"开头的句子
- 以"从log来看"、"从现象看"、"从代码看"、"通过代码审查"、"通过log分析"开头的句子
- 以"初步判断"、"初步定位"、"帮您分析"、"帮贵司分析"开头的句子
- 以"以下是我的分析"、"下面是分析结果"、"分析如下"开头的句子
- 以"总结一下"、"总结如下"、"综上"开头的句子

**Good**: 直接说结论，第一句就是结论。不铺垫、不宣告、不总结。

### R2: 禁止报告章节标题

**Bad patterns（语义）**：
- 形如"根因："/"原因："/"分析："/"结论："的单行标题（回复不是报告，不需要分章节）
- 形如"Workaround方案："/"解决方案："/"方案安全性："/"长期建议："的标题分隔
- 形如"复现确认："/"问题现象："的标题
- 任何"XXX："形式的单行标题用于分隔回复内容

**Good**: 用自然段落过渡，最多用一个空行分隔不同主题。

### R3: 简洁直接

- 总字符数: ≤ 800
- 段落数: ≤ 4
- 每个段落 ≤ 3 句话

### R4: 禁止反问/问题重述

**Bad patterns（语义）**：
- 以"是否"、"能否"、"可否"、"有没有"开头的反问句
- 以"请问"、"请确认"、"烦请"开头的请求确认句

**Good**: 直接陈述，不反问、不请求确认。

### R5: 禁止表格/富文本

**Bad patterns（语义）**：
- Markdown 表格（|...|...| 格式）
- 加粗文本（**...** 格式）
- 斜体文本（*...* 格式）
- Emoji 符号（😊、✅、❌ 等任何 emoji）

**Good**: 纯文本消息，无任何 markdown 格式装饰。

### R6: 代码修改必须用完整 unified diff 格式

**何时触发**：回复中包含代码修改（改文件、修bug、贴patch）时。

**必须包含的四个要素**：
1. `--- a/path` — 原文件路径
2. `+++ b/path` — 新文件路径
3. `@@ -start,count +start,count @@` — hunk 头，标注修改位置
4. 上下文行 + 修改行（`+` 新增，`-` 删除，空格 不动）

**Bad patterns（语义）**：
- 只给文件路径不带 diff header 的代码片段（如 "修改 xxx.c:line 100 → ..."）
- 仅粘贴修改行而不带 `---`/`+++`/`@@` header
- 路径是泛型/通用路径（如 `a/drivers/usb/xxx.c`），而非对应 Bug 分支的真实仓库路径
- diff 格式不完整，客户无法 `git apply` 直接使用

**Good**:
```
--- a/bsp/bootloader/edk2/Drivers/PmicRegulator/PmicRegulator.c
+++ b/bsp/bootloader/edk2/Drivers/PmicRegulator/PmicRegulator.c
@@ -687,6 +687,6 @@
     .voltage = 1100000,
-    .enable = FALSE,
+    .enable = TRUE,
 };
```

**路径要求**：路径必须对应 Bug 所在基线分支的真实 Gerrit 仓库路径，从 `platform/manifest` 或 `CODE_INDEX.md` 获取，不得使用泛型通用路径。客户收到回复后应能直接 `git apply` 到本地仓库。

---

## Good vs Bad 对照

### example 1 — 简单结论型

**bad**:
```
关机充电log和Bugzilla评论综合分析完成。

硬件时钟方案确认：客户使用TCXO + 32K Less。UMS9360平台不支持此组合。

复现确认：关机充电后拔充电器设备无响应。100%复现。

根因：关机充电32K丢失，PMU状态机无时钟完成下电。

Workaround方案：pmu_lp_cfg.c line 690 取消注释 BIT_PMU_APB_PMU_AUTO_SEL_RCO_EN。

方案安全性：RCO是内部硬件，正常场景零影响。

长期建议：客户将TCXO改为TSX对齐参考设计。
```

**good**:
```
贵司使用TCXO+32K Less，UMS9360平台不支持此组合。关机充电时32K丢失后PMU CGM auto-RCO未使能，状态机无钟卡死，VBUS事件无法触发重新上电。

修改pmu_lp_cfg.c line 690，取消注释BIT_PMU_APB_PMU_AUTO_SEL_RCO_EN，寄存器0x64910F70写入值0x01→0x05，使能auto-RCO fallback。主时钟失效时硬件自动切到内部RCO，不依赖外部晶振。

长期建议将TCXO改为TSX对齐参考设计。
```

### example 2 — 需要客户操作型

**bad**:
```
您好，关于PD认证失败问题，经综合定位分析如下：

DUT在TEST.PD.PROT.ALL.02测试中，作为Source端发送Hard Reset后nRetryCount计数器异常递增，
导致测试超时。定位到sprd_pd_header_rev()函数在特定状态下返回了错误的spec revision值。

解决方案：
修改文件drivers/usb/typec/tcpc/tcpm.c，具体diff如下：
[code diff]

请验证后反馈测试结果。
```

**good**:
```
TEST.PD.PROT.ALL.02失败原因：DUT发送Hard Reset后nRetryCount异常递增。根因是sprd_pd_header_rev()在特定状态返回错误的spec revision。

修改drivers/usb/typec/tcpc/tcpm.c如下：
[code diff]

请验证后反馈结果。
```

### example 3 — 纯通知型

**bad**:
```
经排查，DCDC配置问题已修复。

VDDCPU外置DCDC电压配置方法如下：
1. 修改DTS中sprd,vddcpu-dcdc-voltage = <1100000>
2. 修改regulator-min-microvolt = <1100000>

修改后需全编译bootimage。
```

**good**:
```
DCDC配置已修复。修改两处：

1. DTS: sprd,vddcpu-dcdc-voltage = <1100000>
2. DTS: regulator-min-microvolt = <1100000>

改后全编译bootimage。
```

---

## 自检指引

AI 生成回复后，按以下顺序自检：

1. **扫一眼 R1**: 开头有没有填充语？（"经分析"、"综合分析"等）→ 有则删除
2. **扫一眼 R2**: 有没有"XXX："形式的单行标题？→ 有则去掉标题，融入段落
3. **数 R3**: 总字数 ≤ 800？段落 ≤ 4？每段 ≤ 3 句？→ 超标则精简
4. **扫一眼 R4**: 有没有"是否"/"能否"/"请问"？→ 改成陈述句
5. **扫一眼 R5**: 有没有 `**` 加粗 / 表格 / emoji？→ 全部去掉
6. **扫一眼 R6**: 代码修改有没有 `--- a/path` + `+++ b/path` + `@@` hunk header？路径是不是 Bug 分支的仓库真实路径？→ 补全 diff header，确认路径来源

自检结果以 `style_violations` 列表形式传入 `prepare_customer_reply()`。

---

## 维护记录

| 日期 | 变更 |
|------|------|
| 2026-11-13 | 初始版本：从旧正则规则迁移为 LLM 语义检查。删除所有正则模式 + YAML config block。 |
| 2026-11-13 | 新增 R6: 代码修改必须用完整 unified diff 格式，路径必须对应 Bug 基线分支的真实 Gerrit 路径 |