---
name: protocol-parser
description: PD/USB/CC协议智能解析与可视化 - 3层架构：确定提取→HTML可视化→文档
version: "4.0"
tags: [pd, usb, type-c, cc, protocol, visualization, extractor, visualizer]
---

# 协议智能解析与可视化

## 核心理念

**3 层架构：确定提取 → HTML 可视化 → 文档固化。**

- Layer 1: `smart_extractor.py` — 展锐 SC27XX 日志的确定性解析，输出结构化 JSON
- Layer 2: `visualizer.py` — 力科风格双栏 HTML 报告，无外部依赖
- Layer 3: `SKILL.md` — 架构文档与使用指南（本文件）

## 架构

```
用户提供 log 文件（展锐 SC27XX TCPM/PD 日志）
         │
         ▼
┌─────────────────────────────────────────────────┐
│  Layer 1: 确定性提取器                            │
│  smart_extractor.py                             │
│                                                 │
│  extract_structured(path) → dict                │
│                                                 │
│  输入: hardreset_ok.txt (内核日志)               │
│  输出: {                                        │
│    metadata, timeline[470],                     │
│    hard_reset_phases[1], pd_negotiations[3],     │
│    state_machine_summary{transitions[19]},      │
│    anomalies[12], charger_summary               │
│  }                                              │
│                                                 │
│  核心能力:                                       │
│  ├── 30+ 正则模式匹配展锐日志格式                 │
│  ├── PD Header hex 解码 → 消息类型/SpecRev/      │
│  │   角色/MessageID/DataObjects                 │
│  ├── PDO/RDO 结构解析                            │
│  ├── 状态机流转追踪 (PE_SRC_*)                   │
│  ├── Hard Reset 阶段识别                         │
│  ├── 协商周期分组 (SourceCap→Request→Accept→     │
│  │   PS_RDY)                                    │
│  ├── 异常检测 (Delay/Pending/超时/重协商)        │
│  └── 充电器信息汇总 (VID/PID/SpecRev/PDO)        │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  Layer 2: HTML 可视化渲染                        │
│  visualizer.py                                  │
│                                                 │
│  generate_html(extraction_result, title) → html │
│  save_report(html, output_path)                 │
│                                                 │
│  力科协议分析仪风格 (Dark Theme):                 │
│  ├── 摘要卡片 (协商/HR/转换/异常/消息数/时长)    │
│  ├── 双栏主视图:                                │
│  │   ├── 左: TCPM 状态机 (垂直流+状态节点+      │
│  │   │   阶段分隔线)                            │
│  │   └── 右: PD 协议报文时间线 (按HR/协商分组,  │
│  │       时间同步)                               │
│  ├── Hover Tooltip: 解码Header字段+PDO/RDO详情   │
│  ├── 底部Tab页: 协商流程 | 异常列表 | 原始事件表  │
│  ├── 事件类型过滤器 (STATE/PD/CC/CHARGER/MUSB/   │
│  │   TYPEC/OTHER)                               │
│  └── Hard Reset 阶段红色高亮, 协商绿色分组       │
│                                                 │
│  特性:                                          │
│  ├── 自包含HTML (inline CSS+JS, 零外部依赖)      │
│  ├── Dark Theme (130+ CSS变量)                   │
│  └── 点击事件行 → 滚动/高亮对应事件              │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  Layer 3: 文档与使用指南                          │
│  SKILL.md (本文件)                               │
│                                                 │
│  ├── extract_structured() API 文档               │
│  ├── 输出 JSON Schema 参考                       │
│  ├── visualizer API 文档                         │
│  └── 使用示例                                    │
└─────────────────────────────────────────────────┘
```

## 触发条件

- 用户上传展锐 SC27XX 内核日志（`sprd_tcpm_log` / `sprd_pd_log`）
- 用户说"解析协议"、"PD分析"、"USB枚举"、"CC状态"
- 其他 skill（如 bug-assistant）提供 log 文件路径
- 用户需要可视化 PD 协议交互时序

## Layer 1 API: smart_extractor

### extract_structured(log_path) → dict

确定性提取展锐 SC27XX TCPM/PD 日志，输出结构化 JSON。

```python
from smart_extractor import extract_structured

result = extract_structured('/path/to/hardreset_ok.txt')
```

### 输出 Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| `metadata` | dict | 源文件、平台、芯片、提取时间等元信息 |
| `timeline` | list[Event] | 完整事件时间线 (e.g. 470 events) |
| `hard_reset_phases` | list[Phase] | Hard Reset 阶段 (名称/事件范围/起止时间/延迟/描述) |
| `pd_negotiations` | list[Negotiation] | PD 协商周期 (SourceCap/Request/Accept/PS_RDY/PDO/RDO) |
| `state_machine_summary` | dict | 状态机汇总 (transitions/statistics/restarts) |
| `anomalies` | list[Anomaly] | 检测到的异常 (类型/严重度/描述/关联事件) |
| `charger_summary` | dict | 充电器信息 (VID/PID/SpecRev/类型/PDO列表/最终电压电流) |

### Timeline Event 结构

```python
{
    'id': int,           # 事件序号 (0-based)
    'seq': float,        # 序列号
    'kernel_ts': float,  # 内核时间戳 (秒, 6位精度)
    'wall_clock': str,   # 挂钟时间 (可选)
    'cpu': int,          # CPU 核号
    'thread': int,       # 线程 PID
    'subsystem': str,    # 子系统: TCPM/PD
    'event_type': str,   # 事件类型: STATE/PD/CC/CHARGER/MUSB/TYPEC/OTHER
    'content_raw': str,  # 原始日志行内容
    'decoded': dict,     # 解码后数据 (PD header解码/PDO/RDO/状态转换等)
    'flags': list[str],  # 标记: hard_reset/pending/delayed/no_response/retry
    'state_from': str,   # 状态转换起始
    'state_to': str,     # 状态转换目标
    'delay_ms': float,   # 延迟毫秒
    'is_pending': bool,  # 是否处于 Pending 状态
    'is_delayed': bool,  # 是否延迟执行
    'charger_info': str, # 充电器信息
    'cc_info': str,      # CC 状态信息
    'voltage_mv': int,   # 电压 (mV)
    'current_ma': int,   # 电流 (mA)
}
```

### PD Negotiation 结构

```python
{
    'cycle': int,            # 协商周期序号
    'label': str,            # 标签 (e.g. "Negotiation 1")
    'event_ids': [int, int], # 关联事件ID范围
    'start_ts': float,       # 开始时间戳
    'end_ts': float,         # 结束时间戳
    'source_cap': {          # Source Capabilities 消息
        'event_id': int, 'ts': float,
        'header_raw': str, 'header_decoded': dict,
        'message_type': str, 'pdos': [...]
    },
    'request': {...},        # Request 消息
    'accept': {...},         # Accept 消息
    'ps_rdy': {...},         # PS_RDY 消息
    'result': {              # 协商结果
        'voltage_mv': int, 'current_ma': int,
        'final_state': str
    }
}
```

## Layer 2 API: visualizer

### generate_html(extraction_result, title=None) → str

将 `extract_structured()` 输出转换为自包含 HTML 报告。

```python
from visualizer import generate_html, save_report

result = extract_structured('/path/to/log.txt')
html = generate_html(result, title='My PD Analysis')
save_report(html, '/path/to/report.html')
```

### 命令行用法

```bash
# 先生成 JSON
python smart_extractor.py log.txt --json > extract.json

# 再生成 HTML
python visualizer.py extract.json -o report.html -t "PD Protocol Analysis"
```

### 可视化功能

| 功能 | 说明 |
|------|------|
| 摘要卡片 | 协商次数、Hard Reset 次数、状态转换数、异常数、报文数、分析时长 |
| 双栏时间线 | 左: TCPM 状态机流转 (垂直流) | 右: PD 协议报文 (时间同步) |
| Hard Reset 高亮 | 红色背景+边框标注 Hard Reset 阶段 |
| 协商分组 | 绿色标签括号分组每个 PD 协商周期 |
| Hover Tooltip | 鼠标悬停报文行 → 显示解码 Header (消息类型/SpecRev/角色/MessageID/DataObjects) + PDO/RDO |
| 事件过滤 | 按类型过滤: STATE/PD/CC/CHARGER/MUSB/TYPEC/OTHER |
| Tab 页 | 协商流程卡片 (PDO详情) | 异常列表 | 原始事件表 (可过滤) |
| 交互 | 点击状态/报文行 → 滚动高亮对应事件 |

## 使用指南

protocol-parser 提供两种操作方式：**命令行（CLI）** 和 **bug-hub Dashboard（UI）**。两种方式共享同一 v4.0 3 层架构（`extract_structured()` → `generate_html()`），输出一致的自包含力科风格 HTML 报告。

### 方式一：bug-hub Dashboard（推荐）

Dashboard 提供 Web UI，支持文件浏览、关键词过滤、一键解析和可视化。

#### 解析单个日志文件

1. 打开 Dashboard：浏览器访问 `http://127.0.0.1:8777`
2. 左侧导航 → **Protocol Parser**
3. 在输入框填写日志文件完整路径（如 `E:\08_Bug\CQ\...\hardreset_ok.txt`）
4. 下拉选择协议类型（默认 `auto` 自动检测）
5. 点击 **Generate Report**
6. 报告在页面内嵌 iframe 中展示，顶部显示：
   - 日志文件名（标题）
   - 协议类型 Badge（PD/USB/CC）
   - 平台/芯片元信息
   - 📂 **Open Source Log** — 在浏览器中打开原始日志文件
   - 🔄 **Parse Another Log** — 跳转回 Dashboard 解析不同日志文件

#### 关键词过滤 + 解析（从 log-analyzer 入口）

1. Dashboard → **Log Analyzer**
2. 填写日志文件路径
3. 勾选方向关键词（如 `charger`、`cc`、`pd` 等）
4. 点击 **Filter & Analyze**
5. 系统先按关键词过滤日志行，再对过滤结果运行 protocol-parser
6. 底部显示 filtered log + 协议分析 iframe

#### 重新解析另一个日志文件

在 HTML 报告顶部点击 **🔄 Parse Another Log** 按钮 → 在新标签页打开 Dashboard 的 Protocol Parser 页面 → 输入新的日志文件路径 → Generate Report。

### 方式二：命令行（CLI）

适用于脚本化、批量处理或无需 Dashboard 的场景。

```bash
# 一键提取+可视化
python -c "
from smart_extractor import extract_structured
from visualizer import generate_html, save_report
result = extract_structured('/path/to/log.txt')
html = generate_html(result, title='PD Protocol Analysis')
save_report(html, '/path/to/report.html')
print('Done: report.html')
"
```

或分步执行：

```bash
# Step 1: 提取结构化 JSON
python smart_extractor.py /path/to/log.txt --json > extract.json

# Step 2: 生成 HTML 报告
python visualizer.py extract.json -o report.html -t "PD Analysis"
```

#### generate_html() 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `extraction_result` | dict | (必需) | `extract_structured()` 的输出 |
| `title` | str \| None | `None` | 报告标题（显示在 topbar） |
| `hub_url` | str | `"http://127.0.0.1:8777"` | Dashboard 地址（用于 🔄 Parse Another Log 按钮） |

> **注意**：CLI 生成报告时不依赖 Dashboard，但 `hub_url` 会嵌入 HTML 中。如果 Dashboard 部署在其他端口/主机，通过 `hub_url` 参数指定。

### 验证数据

| 指标 | hardreset_ok.txt (参考) |
|------|------------------------|
| 事件数 | 470 |
| Hard Reset 阶段 | 1 |
| PD 协商周期 | 3 |
| 状态转换 | 19 |
| 异常 | 12 |

## 知识库

| 文件 | 内容 |
|------|------|
| `knowledge/pd_protocol/pd3.1_spec.md` | PD 3.1 消息类型、PDO 结构、状态机、时序要求、故障模式 |
| `knowledge/usb_protocol/usb_enum_flow.md` | USB 枚举流程、描述符结构、传输类型、速率、故障模式 |

## 代码位置

| 文件 | 用途 |
|------|------|
| `smart_extractor.py` | Layer 1: 确定提取器 (`extract_structured()`) |
| `visualizer.py` | Layer 2: HTML 可视化渲染 (`generate_html()`, `save_report()`) |
| `parsers/pd_parser.py` | PD 解析器（传统正则，兼容旧格式） |
| `parsers/usb_parser.py` | USB 解析器（传统正则，兼容旧格式） |
| `parsers/cc_parser.py` | CC 解析器（传统正则，兼容旧格式） |
| `protocol_combiner.py` | 组合器（自动检测 + 生成报告） |
| `templates/visualization.html` | 旧版可视化模板 |
| `templates/lecroy_style_report.html` | 旧版力科风格报告模板 |
| `tests/` | 测试套件（60 tests） |

## 支持的日志格式

### Level 0: 特定格式（高置信度）
- 展锐 SC27XX TCPM/PD (`sprd_tcpm_log` / `sprd_pd_log`)
- 通用 PD Protocol (`[pd_protocol]`)
- 通用 USB Core (`[usb_core]`)
- 通用 CC Protocol (`[cc_protocol]`)
- 高通 PMIC PD (`[pmic_pd]` / `[qcom_pd]`)
- MTK TCPC (`[mtk_tcpc]`)
- FUSB302/TCPCI (`[fusb302]` / `[tcpci]`)

### Level 1-3: 兜底
- 包含 PD/CC/USB 关键词的任意文本
- 包含充电/VBUS/Type-C 关键词的任意文本
- 完全未知格式 → 裸传给 AI 判断
