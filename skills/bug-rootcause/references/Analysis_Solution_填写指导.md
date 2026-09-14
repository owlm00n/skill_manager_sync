# Analysis_Solution 填写指导说明（Unisoc Wiki 标准）

> **来源**: cmwiki.unisoc.com — Analysis_Solution填写指导说明 (pageId=91097254)  
> **版本**: V0.1 | **作者**: 吉姗 | **日期**: 2023-06-21

---

## 一、ChangeType 与必填项关系

| ChangeType | 必填项 | 说明 |
|-----------|--------|------|
| **Defect** | 1~4 必填，5~6 可选 | 标准Bug修复场景 |
| **Question** | 第2项 Resolution 必填 | 问题咨询场景 |
| **Task / EnhancementRequest** | 全部可选 | 任务/增强场景 |

---

## 二、完整字段列表（Bugzilla Analysis_Solution 页面实际字段）

> **注意**: 以下格式来自实际 Bugzilla Analysis_Solution 页面（`提示词.txt` 文件），与 Wiki 定义的 6 项相比，额外增加了 NV 相关字段。

```
[1.Root Cause        ]:
[2.Resolution        ]:
[3.Testing Suggestion]:
[4.Impact for customer]:
[5.Self Test Items ]:(Optional)
[6.Reproduce Steps]:(Optional)
[7.NV Modification   ]:(Optional)
[Mandatory for customer(Y/N)]:
[Recalibration (Y/N)        ]:
[NV structural changed(Y/N) ]:
[New NV backup items(Y/N)   ]:
```

### ChangeType 与必填项关系

| ChangeType | 必填项 | 说明 |
|-----------|--------|------|
| **Defect** | 1~4 必填，5~7 可选 | 标准Bug修复场景 |
| **Question** | 第2项 Resolution 必填 | 问题咨询场景 |
| **Task / EnhancementRequest** | 全部可选 | 任务/增强场景 |

### [1] Root Cause — 根本原因

| 项目 | 要求 |
|------|------|
| **状态** | **Root-Cause 状态必填** |
| **长度** | ≥ 12个字符（字母或汉字） |
| **约束** | 不能和 Resolution 填写的完全一样 |
| **含义** | 阐述 Bug 产生的**根本原因**，是什么原因引起或导致 |
| **核心** | 是**根本原因**，不是给出问题现象 |

### [2] Resolution — 解决方案

| 项目 | 要求 |
|------|------|
| **状态** | **Root-Cause 状态必填** |
| **长度** | ≥ 12个字符（字母或汉字） |
| **约束** | 不能和 Root Cause 填写的完全一样 |
| **含义** | 解决问题的**方案说明**，即如何修改或处理 |
| **核心** | 是**解决方案**，不是根本原因和问题现象 |

### [3] Testing Suggestion — 测试建议

| 项目 | 要求 |
|------|------|
| **状态** | **Fixed 状态必填** |
| **约束** | 不能为空，不能和 Impact for customer 完全一样 |
| **含义** | 对当前问题的**回归测试建议**，以确保合入后的版本得到充分验证 |

### [4] Impact for customer — 对客户的影响

| 项目 | 要求 |
|------|------|
| **状态** | **Fixed 状态必填** |
| **约束** | 不能为空，不能和 Testing Suggestion 完全一样 |
| **含义** | 对客户的影响分析：如不合入本修改将对用户造成的具体影响，以及合入本修改时遗留的问题和对用户带来的收益 |

### [5] Self Test Items — 自测情况（可选）

| 项目 | 要求 |
|------|------|
| **状态** | 可选填写 |
| **含义** | 自测情况说明 |

### [6] Reproduce Steps — 复现步骤（可选）

| 项目 | 要求 |
|------|------|
| **状态** | 可选填写 |
| **含义** | 复现步骤说明 |

### [7] NV Modification — NV修改（可选）

| 项目 | 要求 |
|------|------|
| **状态** | 可选填写 |
| **含义** | 是否涉及 NV（Non-Volatile，非易失存储）数据的修改 |

### [Mandatory for customer(Y/N)] — 客户必填项

| 项目 | 要求 |
|------|------|
| **含义** | 此项修复对客户是否为必需要求 |

### [Recalibration (Y/N)] — 需要重新校准

| 项目 | 要求 |
|------|------|
| **含义** | 此项修复是否需要客户重新校准 |

### [NV structural changed(Y/N)] — NV结构变更

| 项目 | 要求 |
|------|------|
| **含义** | 是否涉及 NV 数据结构的变更 |

### [New NV backup items(Y/N)] — 新NV备份项

| 项目 | 要求 |
|------|------|
| **含义** | 是否涉及新的 NV 备份项 |

---

## 三、6 个核心字段详解（Defect 场景补充说明）

> **补充**: 以下是对 4 个核心必填项（1~4）的详细说明。第 5~7 项及 NV 相关字段均为可选，视具体情况填写。

### [1] Root Cause — 根本原因

| 项目 | 要求 |
|------|------|
| **状态** | **Root-Cause 状态必填** |
| **长度** | ≥ 12个字符（字母或汉字） |
| **约束** | 不能和 Resolution 填写的完全一样 |
| **含义** | 阐述 Bug 产生的**根本原因**，是什么原因引起或导致 |
| **核心** | 是**根本原因**，不是给出问题现象 |

### [2] Resolution — 解决方案

| 项目 | 要求 |
|------|------|
| **状态** | **Root-Cause 状态必填** |
| **长度** | ≥ 12个字符（字母或汉字） |
| **约束** | 不能和 Root Cause 填写的完全一样 |
| **含义** | 解决问题的**方案说明**，即如何修改或处理 |
| **核心** | 是**解决方案**，不是根本原因和问题现象 |

### [3] Testing Suggestion — 测试建议

| 项目 | 要求 |
|------|------|
| **状态** | **Fixed 状态必填** |
| **约束** | 不能为空，不能和 Impact for customer 完全一样 |
| **含义** | 对当前问题的**回归测试建议**，以确保合入后的版本得到充分验证 |

### [4] Impact for customer — 对客户的影响

| 项目 | 要求 |
|------|------|
| **状态** | **Fixed 状态必填** |
| **约束** | 不能为空，不能和 Testing Suggestion 完全一样 |
| **含义** | 对客户的影响分析：如不合入本修改将对用户造成的具体影响，以及合入本修改时遗留的问题和对用户带来的收益 |

### [5] Self Test Items — 自测情况（可选）

| 项目 | 要求 |
|------|------|
| **状态** | 可选填写 |
| **含义** | 自测情况说明 |

### [6] Reproduce Steps — 复现步骤（可选）

| 项目 | 要求 |
|------|------|
| **状态** | 可选填写 |
| **含义** | 复现步骤说明 |

---

## 四、填写优秀案例

### 案例一（WiFi漫游）

**Root Cause**: 2.4G→5G漫游时，因为前一次5G→2.4G漫游的相关信息还未清除，导致这次漫游5G AP没有被save到，所以无法连接。

**Resolution**: 在设置5G优先漫游连接之前，先初始化相关的信息。

---

### 案例二（信号测量）

**Root Cause**: 
1) hold模式下从TEACQ_fineAcqProc转为TEACQ_coarseAcqProc时，出现corInterval数值未及时更新，codeFreq设置错误，进而导致dataCount出错(0x90，正常值为0x64)；
2) MeasNav[40][0]的dataCount为0x90（正常值为0x64），导致后续执行memcpy等操作时内存被踩，触发assert。

**Resolution**: 
1) 增加数组越界的主动assert机制；
2) 纠正corInterval出错，同步更新其数值。

---

### 案例三（通话录音）

**Root Cause**: 通话录音功能只能录下行不能录上行，是由于在添加通话录播功能时只在AUDEV_RECORD_TYPE_DEBUG_DUMP模式进行了上行数据的保存，mix通话录音AUDEV_RECORD_TYPE_VOICE没有加。

**Resolution**: 需要在上行数据保存时添加type为AUDEV_RECORD_TYPE_VOICE的条。

---

### 案例四（CFU业务）

**Root Cause**: 进入界面进行全查询，隔了6s设置CFU，L4去激活了xcap承载，又重新建立了xcap承载，所以下发了新的IP_CHANGE_SS，导致power_reset，把init标志位重置为false，此时会重新复制默认的xml，相当于未保存全查询结果，所以put使用了默认的xml进行设置，设置成功。但再次查询时，有两个CFU节点，第一个是原本的cfu节点为去激活，而第二个是默认put上去的，为激活。此时测试机上报了第一个节点的状态，因此设置之后再查询为关闭。

**Resolution**: Telenet网络（206 005）下要求不进行根节点查询，每次IP_CHANGE_SS下来需要进行的根节点查询修改为全查询，同步xml信息用于后续的设置。

**Testing Suggestion**:
- 『复现场景和环境』：Telenet网络（206 005）下的call forwarding业务
- 『版本和操作说明』：先查询call forwarding业务，等5s后（保证已去激活XCAP承载），再设置CFU业务，然后再次查询CFU，检查CFU是否为激活且号码是否存在
- 『测试方法和建议』：CFU为激活且号码为之前设置的号码为正常

---

## 五、有提升空间的案例（反面教材）

### 案例一：Root Cause 与 Testing Suggestion 一样

❌ **Root Cause**: kernel 侧缺少AVDD&AVEE 驱动  
❌ **Testing Suggestion**: kernel 侧缺少AVDD&AVEE 驱动（**不合规！**）

> **问题**: Root Cause 填写的其实是"问题现象"而非"根本原因"，Testing Suggestion 完全等于 Root Cause。

---

### 案例二：Root Cause 与 Resolution 完全一样

❌ **Root Cause**: 修改RS发送时间间隔为2s  
❌ **Resolution**: 修改RS发送时间间隔为2s

> **问题**: 根本原因和解决方案写的一样。系统检查规则下**无法提交**。

---

### 案例三：全填 NA，无测试建议

❌ **Root Cause**: 音乐播放器快进快退功能失效  
❌ **Resolution**: 修改audio tream宏  
❌ **Testing Suggestion**: NA

> **问题**: 没有任何测试建议，不利于系统测试进行回归验证。即使第4、6项可选，如有影响还是建议填写。

---

### 案例四：绕开系统限制（填写重复描述）

❌ **Root Cause**: 防止误报的代码使用宏控控制，默认为关闭处理  
❌ **Resolution**: 防止误报的代码使用宏控控制，默认为关闭处理1  
❌ **Testing Suggestion**: 防止误报的代码使用宏控控制，默认为关闭处理2

> **问题**: 虽然绕过了系统检查规则（加了数字后缀），但后续遇到类似问题需要查询分析时，**完全看不出想表达什么内容**，不利于追溯。

---

### 案例五：过短描述

❌ **Root Cause**: minidump前通过uart0传log到mcu  
❌ **Resolution**: 支持此功能

> **问题**: 虽然可以提交，但这样的描述在后续查问题时**无法让人知道当时想表达什么**。

---

## 六、填写框架（精简版）

> 原则：**不要套多层标签和子项**（如 `【模块】/【触发条件】/【因果链】` ），AI 总结容易幻觉。只填最核心的 3 行，每行用一句话。

### [1] Root Cause

```
【一句话总结根本原因】：涉及谁 + 为什么出错（代码/配置/逻辑层面）。
```

> 不是现象，要写"因为 A 导致 B"。可以编号列多条原因。

### [2] Resolution

```
【一句话总结解决方案】：改了什么 + 怎么改的。
```

> 不是原因，要写具体修改动作。可以编号列多条。

### [3] Testing Suggestion

```
『环境/工具』+『操作』+『预期通过结果』，一行或三行均可。
```

> 能指导测试回归就行，不要和 Impact 一样。

### [4] Impact for customer

```
『不合入会怎样』+『合入后有什么好处』，两句话即可。
```

> 不要和 Testing Suggestion 一样。

---

### 完整模板（直接复制用）

```
[1.Root Cause        ]:
一句话总结：谁（模块/文件）+ 为什么出错（代码/配置/逻辑问题）+ 导致什么。可编号列多条。

[2.Resolution        ]:
一句话总结：改了什么（文件/配置）+ 怎么改的。可编号列多条。

[3.Testing Suggestion]:
『环境/工具』+『操作步骤』+『预期通过结果』。

[4.Impact for customer]:
『不合入会怎样』+『合入后有什么好处』。

[5.Self Test Items ]:(Optional)
一句话说明自测内容。

[6.Reproduce Steps]:(Optional)
编号步骤，方便复现。

[7.NV Modification   ]:(Optional)
Y/N + 一句话说明。

[Mandatory for customer(Y/N)]:
Y/N

[Recalibration (Y/N)        ]:
Y/N

[NV structural changed(Y/N) ]:
Y/N

[New NV backup items(Y/N)   ]:
Y/N
```

---

## 七、Bug 3495846 填写示范（精简版）

```
[1.Root Cause        ]:
1）硬件设计中vconn power引脚未连到实际IC，导致驱动获取vconn regulator为NULL；
2）dts中vddldo-supply与use-pdhub-c2c配置冲突，应移除vddldo-supply；
3）DUT非CC线上有VCONN电压但VIF声明不支持VCONN Swap，CTS检测到不一致。

[2.Resolution        ]:
1）注释掉dts中vddldo-supply配置，添加sprd,support-pd-cts属性和相应flag；
2）确认硬件不需要VCONN Swap，VIF声明正确。

[3.Testing Suggestion]:
Lecroy M310E + USB Compliance Suite 8.41，修改dts重新编译烧录后运行TEST.PD.PROT.SRC.08，应Pass。

[4.Impact for customer]:
不合入则PD认证TEST.PD.PROT.SRC.08持续失败无法出认证报告；合入后通过认证可正常出具报告。

[5.Self Test Items ]:(Optional)
dts编译正常，烧录后TCPC驱动加载正常。

[6.Reproduce Steps]:(Optional)
1）DUT + Lecroy M310E 2）配置VIF声明不支持VCONN 3）运行TEST.PD.PROT.SRC.08 4）预期Fail

[7.NV Modification   ]:(Optional)
N

[Mandatory for customer(Y/N)]:
Y

[Recalibration (Y/N)        ]:
N

[NV structural changed(Y/N) ]:
N

[New NV backup items(Y/N)   ]:
N
```

---

*文档整理时间: 2026-07-30 | 基于 Unisoc Wiki pageId=91097254 + Bugzilla 实际页面格式（提示词.txt）*