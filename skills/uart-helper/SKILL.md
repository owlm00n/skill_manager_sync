---
name: uart-helper
description: 展锐平台手机 UART 串口调试助手。管理 MobaXterm 串口连接的完整环境：COM 口自动识别、MobaXterm Session 配置、串口日志查找/分析、通过 SendInput 发送 shell 命令。当用户提到串口、UART、COM口、MobaXterm、抓log、调 log 等级、发串口命令时使用此 skill。
---

# UART Helper — 串口调试助手

管理展锐平台手机 UART 串口调试的完整环境。MobaXterm 负责串口连接和日志抓取，本 Skill 负责 COM 口自动识别、MobaXterm Session 自动配置、日志归档/监控/分析。

## 环境总览

### 软件

| 项目 | 值 |
|------|-----|
| 终端 | MobaXterm v21.3 Build 4736 |
| 安装路径 | `C:\Program Files (x86)\Mobatek\MobaXterm\MobaXterm.exe` |
| 配置文件 | `C:\Users\Xianjun.Zeng\Documents\MobaXterm\MobaXterm.ini` |
| 启动方式 | 开始菜单 → MobaXterm → 侧边栏选 Session |
| 多实例 | 禁止（AllowMultiInstances=0） |
| Session 列表 | `COM (1)`, `COM (1) A13`, `COM (2)`, `COM (2) A13`, `COM (3)`, `COM (3) A13` |

### 串口硬件

| 项目 | 值 |
|------|-----|
| 连接方式 | USB转串口小板 → 手机 UART 测试点（TX/RX/GND） |
| USB芯片 | FTDI/CP210x 系列，插入后产生 **4 个连续 COM 口** |
| 串口参数 | 8 数据位, 1 停止位, 无校验, 无流控 |

### 波特率

| 平台代 | 波特率 |
|--------|--------|
| A13 之前 | 115200 |
| A13 及之后 | 921600（主流） |
| A13 自身 | 两种都可能 |

### 日志存储

| 项目 | 值 |
|------|-----|
| 日志目录 | `E:\11_log\MobaXterm\` |
| 文件命名 | `[SessionName] (MM-DD_HHMMSS).log` |

---

## 能力 0: COM 口自动识别 ⭐ 核心能力

**pyserial 直接读 COM 口数据，根据输出内容判断哪个是 kernel UART 口。检测时 MobaXterm 未连接该 COM 口，不冲突。**

### 检测原理

```
USB 小板 → 4 个连续 COM 口 → pyserial 逐个打开读数据
                                  │
                    kernel 关键词命中 → 判断为 UART 口
                    AT 指令/乱码     → 排除
                    silent          → 设备未上电
```

### 检测策略（按优先级）

```
1. 查 platform_com_map.json → 已知平台 → 直接返回映射（零等待）
2. 运行时扫描 → 每个口 3 秒 × 波特率（A+B: 已知平台用记录波特率，未知先 921600 再 115200）
3. 4 口全 silent → 提示用户重启手机，boot 阶段再扫（输出密集，2 秒够用）
```

### 用户交互流程

```
用户: "检测串口"

AI:
  1. 运行 detect_com.py → 拿到 JSON
  2. status="known"     → "UMS9230 → COM45 @921600，直接用 COM(1) Session"
  3. status="detected"  → "检测到 kernel UART = COM45 (第1口) @921600。这是什么平台？"
                          用户回复平台名 → AI 自动写入 platform_com_map.json
  4. status="need_power"→ "4个口都没数据，手机可能没上电。请确认上电后告诉我，或直接说'重启检测'"
  5. status="no_device" → "未找到 USB 小板，请确认已插入"
```

### MobaXterm Session 自动配置

检测完成后，如果当前 VCP 组 COM 号与 MobaXterm Session 配置不匹配，AI 自动修改 `MobaXterm.ini`：

```
1. 提示用户关闭 MobaXterm
2. 备份 MobaXterm.ini → MobaXterm.ini.bak.{date}
3. 修改 COM(1) Session 的 COM 口号为检测到的 kernel UART 口
4. 提示用户重新打开 MobaXterm，选择 COM(1) Session
```

### 自动化说明

| 环节 | 自动化 | 说明 |
|------|:------:|------|
| 扫注册表找 VCP 组 | ✅ | python 脚本 |
| 运行时 pyserial 检测 | ✅ | 设备已上电无需用户操作 |
| boot 检测 | 🤝 | 提示用户重启手机 |
| 新平台记录映射 | ✅ | 自动写入 platform_com_map.json |
| MobaXterm Session COM 口匹配 | ✅ | AI 自动改 ini + 提示重启 MobaXterm |
| 打开/操作 MobaXterm | ❌ | 用户手动 |

### 自学习机制

`platform_com_map.json` — 平台到 COM口序号 + 波特率的映射。首次遇到新平台时自动记录，之后直接匹配。

---

## 能力 1: 查找和分析串口日志 ⭐

**`scripts/find_log.py`** — 找到 MobaXterm 活跃日志文件，识别重启点，区分"重启 vs 重开会话"。

### 检测原理

```
MobaXterm 日志行为:
  打开 Session → 创建 [COM (1)] (MM-DD_HHMMSS).log → 持续写入
  手机重启     → 同一文件继续写（不新建）
  关闭+重开    → 创建新文件（timestamp 改变）

活跃文件检测:
  1. 文件锁检测: open(file, 'ab') → PermissionError = MobaXterm 正在写
  2. mtime 降级: 锁检测不适用时，取最新修改的文件
```

### 重启点识别

按 boot 阶段顺序扫描文件，匹配以下锚点关键词：

| 阶段 | 关键词 | 说明 |
|------|--------|------|
| 上次系统结束 | `reboot: Restarting system`, `sysrq: Terminate All Tasks` | 关机标记 |
| Bootloader | `ddr init start!!!` | 最早出现，最可靠，不依赖内核版本 |
| ATF | `NOTICE:  BL31:` | ARM Trusted Firmware |
| EDK2 | `UEFI firmware`, `BoardName:` | UEFI 固件 |
| Kernel | `Booting Linux on physical CPU`, `Linux version` | 最确定但出现较晚 |

去重规则：同一阶段匹配多个关键词时，取最早的行；相距 < 50 行的合并到同一 boot。

### 输出结构

```json
{
  "status": "ok",
  "active_file": { "name", "path", "size_kb", "mtime", "locked", "detection_method" },
  "reboot_info": { "total_lines", "reboot_count", "reboot_markers": [...], "last_boot_start": {...} },
  "history_files": [{ "name", "size_kb", "mtime", "is_active" }, ...]
}
```

### 用法

```bash
python scripts/find_log.py                          # 分析当前活跃日志
python scripts/find_log.py --session "COM (2)"      # 指定 Session
python scripts/find_log.py --file "<path>"          # 分析指定文件
python scripts/find_log.py --file "<path>" --reboots # 仅输出重启点
```

**触发**："最新的串口log是什么" / "刚才抓的log在哪" / "这个log里有几次重启" / "日志从哪行开始看的"

---

## 能力 2: 串口发送命令 ⭐

**`scripts/send_to_moba.py`** — 通过 Windows `SendInput` API 向 MobaXterm 串口控制台发送命令。模拟真人键盘打字，使用 `KEYEVENTF_UNICODE` 绕过键盘布局问题。

### 发送原理

```
1. 找到 MobaXterm 'COM(1)' 窗口 (TMobaXtermForm)
2. Alt trick 绕过 Windows 前台窗口锁定
3. SetForegroundWindow → 短暂聚焦 MobaXterm
4. SendInput(KEYEVENTF_UNICODE) → 逐字符发送文本
5. keybd_event(VK_RETURN) → 发送回车
6. 恢复之前的焦点窗口（可选）
```

### 前提条件

- 设备串口上需要 shell（`getty`/`sh`），启动后串口上有 `#` 或 `$` 提示符
- 如果串口只有 kernel log 输出没有 shell，此能力无效（但可通过 MobaXterm 右键 → Send Break 发送 SysRq 指令）

### 用法

```bash
python scripts/send_to_moba.py "echo 8 8 8 8 > /proc/sys/kernel/printk"  # 自定义命令
python scripts/send_to_moba.py loglevel-8      # 快捷方式：调高 log 等级
python scripts/send_to_moba.py printk          # 快捷方式：查看 log 等级
python scripts/send_to_moba.py                 # 仅发回车（唤醒控制台）
python scripts/send_to_moba.py --list          # 列出预设快捷方式
```

### 预设快捷方式

| 快捷方式 | 实际命令 | 用途 |
|----------|---------|------|
| `loglevel-8` | `echo 8 8 8 8 > /proc/sys/kernel/printk` | 调到最高 log 等级 |
| `loglevel-7` | `echo 7 7 7 7 > /proc/sys/kernel/printk` | 调到调试等级 |
| `loglevel-4` | `echo 4 4 4 4 > /proc/sys/kernel/printk` | 恢复默认 |
| `printk` | `cat /proc/sys/kernel/printk` | 查看当前 log 等级 |
| `dmesg-clear` | `dmesg -c > /dev/null` | 清空 dmesg |
| `dmesg-tail` | `dmesg \| tail -50` | 看最近 kernel log |
| `version` | `cat /proc/version` | 内核版本 |
| `uptime` | `cat /proc/uptime` | 设备运行时间 |
| `interrupts` | `cat /proc/interrupts \| head -20` | 中断统计 |

**触发**："调高log等级" / "发个命令到串口" / "echo 到设备" / "查看 printk"

---

## 能力 3: 日志归档到 Bug Workspace

```bash
cp "E:/11_log/MobaXterm/[COM (1)] (10-09_143025).log" "E:/08_Bug/SPCSS01701938/uart_20261009_143025.log"
```

**触发**："把这个log归档到 SPCSS01701938" / "存档到 workspace"

---

## 能力 4: 实时关键词监控

在 MobaXterm 抓 log 的同时，AI 后台 tail 日志文件，匹配 PD 关键词：

```
SNK_DEBOUNCED, SNK_ATTACHED, SNK_READY, SNK_WAIT_CAPABILITIES
PORT_RESET, SNK_UNATTACHED, TOGGLING, SNK_ATTACH_WAIT
HARD_RESET, PD TX time out, can_communication, vbus_present
vbus_online, vbus_change, chg_type, bc1p2
sc27xx_typec, sc27xx_pd, sprd_tcpm, upm691
CC1, CC2, Rp, Rd
```

**触发**："监控串口log" / "盯着log看PD状态"

---

## 能力 5: 串口日志快速分析

抓完后对串口 log 执行 PD 状态机分析：

```
- PD 状态机转移序列
- Hard Reset 次数和间隔
- CC 电平变化
- VBUS 通断时间线
- can_communication 变化
- 充电器类型检测结果
```

**触发**："分析串口log" / "看PD状态机"

---

## 能力 6: 配合 Bug 测试的完整流程

```
用户: "用串口抓 SPCSS01701938 的复现 log"

AI:
1. 检测 COM 口（能力 0）→ 识别平台和 UART 口
2. 配置 MobaXterm Session → 提示用户打开
3. 确认 Bug workspace 目录
4. 用户操作手机复现 Bug
5. 用户说"抓完了" → 归档 + 分析 + 输出时间线
```

---

## 与其他 Skill 关系

```
uart-helper (本 Skill)
    │
    ├── COM 口自动识别 ⭐
    │       pyserial 读 COM 口 + AI 交互引导
    │       → platform_com_map.json 自学习
    │       → MobaXterm.ini 自动配置
    │
    ├── 串口命令发送 ⭐
    │       SendInput(KEYEVENTF_UNICODE) 模拟键盘打字
    │       → 修改 log 等级、查看寄存器、执行 shell 命令
    │
    ├── 日志查找 + 重启点分析 ⭐
    │       find_log.py 文件锁 + 关键词扫描
    │       → 区分"重启 vs 重开会话"
    │
    ├── 日志归档 → bug-workspace
    │
    ├── 日志分析 → log-analyzer
    │
    └── Bug 流程集成 ← bug-core
```

## 注意事项

1. **pyserial 依赖**：需 `pip install pyserial`
2. **检测时机**：优先运行时（无需用户操作），降级到 boot（提示重启手机）
3. **单设备场景**：假设只接一台手机，多台会提示"请只保留一台"
4. **波特率策略**：已知平台用记录值，未知先 921600 降 115200；A13 两种都可能
5. **平台映射自学习**：检测到新平台自动记录，映射错误直接改 JSON 即可
6. **MobaXterm 单实例**：改 ini 前需先关闭 MobaXterm