---
name: adb-helper
description: ADB 全功能调试工具 — 设备管理、root、shell、push/pull、logcat、安装APK、开机向导跳过、dumpsys、getprop、forward、fastboot、重启操作。触发词：adb、安卓调试、手机调试、logcat、adb shell、skip wizard、开机向导、安装apk、adb push、adb pull、dumpsys、fastboot
version: "1.0"
tags: [adb, android, debug, logcat, fastboot, device]
---

# ADB Helper — Android 调试助手

完整的 ADB 调试工具集，覆盖日常 Android 设备调试的所有场景。

## 触发条件

- 用户说"adb"、"安卓调试"、"手机调试"、"连手机"
- 用户说"logcat"、"拉日志"、"看日志"
- 用户说"安装apk"、"安装应用"、"卸载应用"
- 用户说"跳过开机向导"、"skip wizard"、"setup wizard"
- 用户说"dumpsys"、"getprop"、"查看属性"
- 用户说"重启手机"、"adb reboot"、"进recovery"
- 用户说"fastboot"、"刷机"、"进bootloader"
- 用户说"adb push"、"adb pull"、"拉文件"、"推文件"
- 用户说"端口转发"、"adb forward"、"reverse"

## 前置条件

- ADB 已安装且在 PATH 中（`adb version` 可执行）
- 设备已连接（USB 或网络）
- 部分操作需要 root 权限

## 执行原则（核心规则）

**先执行，失败再诊断** — 禁止在执行目标命令前做预检查询。

| 场景 | ❌ 禁止做法 | ✅ 正确做法 |
|------|------------|------------|
| 用户要执行 adb 命令 | 先 `adb devices -l` 检查设备，再 `adb root` 检查权限，最后才执行 | **直接执行目标命令**，命令失败后才按需诊断 |
| 命令执行失败 | 提前做各种检查 | 根据错误信息针对性诊断：`device not found` → 查 devices；`permission denied` → 查 root |
| shell 命令 | 先 `adb shell whoami` 确认用户 | 直接执行，失败再 `adb root` |

**降级链（仅失败时触发）**：
1. 目标命令失败 → 看错误信息
2. `device not found` / `no devices` → `adb devices -l` 诊断
3. `permission denied` → `adb root` 后重试
4. 其他错误 → 针对性排查

## 功能清单

### 1. 设备管理

| 操作 | 命令 | 说明 |
|------|------|------|
| 列出设备 | `adb devices -l` | 显示所有已连接设备及详细信息 |
| 等待设备 | `adb wait-for-device` | 阻塞等待设备连接 |
| 断开连接 | `adb disconnect <ip>` | 断开网络 ADB 连接 |
| 网络连接 | `adb connect <ip>:5555` | 通过网络连接设备 |
| 重启 ADB | `adb kill-server && adb start-server` | 重启 ADB 服务 |

### 2. Root & 权限

| 操作 | 命令 | 说明 |
|------|------|------|
| 获取 root | `adb root` | 以 root 权限重启 adbd |
| 禁用 root | `adb unroot` | 恢复非 root 模式 |
| 重新挂载 | `adb remount` | 重新挂载系统分区为可读写 |
| 检查 root | `adb shell whoami` | 检查当前 shell 用户身份 |

### 3. Shell 操作

| 操作 | 命令 | 说明 |
|------|------|------|
| 交互 shell | `adb shell` | 进入设备 shell |
| 执行命令 | `adb shell <cmd>` | 执行单条 shell 命令 |
| 查看属性 | `adb shell getprop <prop>` | 获取系统属性 |
| 设置属性 | `adb shell setprop <key> <value>` | 设置系统属性 |
| dumpsys | `adb shell dumpsys <service>` | 导出系统服务状态 |
| 截屏 | `adb shell screencap -p > file.png` | 截取屏幕截图 |
| 录屏 | `adb shell screenrecord /sdcard/demo.mp4` | 录制屏幕视频 |

**常用 dumpsys 服务**：
- `dumpsys battery` — 电池状态
- `dumpsys wifi` — WiFi 信息
- `dumpsys meminfo` — 内存使用
- `dumpsys package <pkg>` — 包信息
- `dumpsys activity activities` — 当前 Activity 栈
- `dumpsys power` — 电源管理状态

### 4. 文件传输

| 操作 | 命令 | 说明 |
|------|------|------|
| 推送到设备 | `adb push <local> <remote>` | 将文件推送到设备 |
| 从设备拉取 | `adb pull <remote> [local]` | 从设备拉取文件 |
| 同步目录 | `adb sync <dir>` | 同步目录到设备 |

### 5. 应用管理

| 操作 | 命令 | 说明 |
|------|------|------|
| 安装 APK | `adb install -r <apk>` | 安装/覆盖安装应用 |
| 卸载应用 | `adb uninstall <pkg>` | 卸载应用 |
| 列出包 | `adb shell pm list packages` | 列出所有已安装包 |
| 清除数据 | `adb shell pm clear <pkg>` | 清除应用数据 |
| 启动应用 | `adb shell am start -n <pkg>/<activity>` | 启动指定 Activity |
| 强制停止 | `adb shell am force-stop <pkg>` | 强制停止应用 |

### 6. 开机向导跳过

自动点击屏幕四角跳过 Android Setup Wizard：

**脚本位置**: `F:\CMD\skip_setupwizard.sh`

```bash
#!/bin/sh
# 自动检测屏幕分辨率，点击四角跳过开机向导
adb root
SIZE=`adb shell wm size`
SIZE=${SIZE##*:}
WIDTH=${SIZE%%x*}
HEIGHT=${SIZE##*x}
offset=100

adb shell input tap $offset $offset
adb shell input tap $((WIDTH - $offset)) $offset
adb shell input tap $((WIDTH - $offset)) $((HEIGHT - $offset))
adb shell input tap $offset $((HEIGHT - $offset))
```

**注意**：此脚本不适用于所有 Setup Wizard 版本，部分版本需要更复杂的交互（如长按、滑动）。仅在确认有效后使用。

### 7. 重启操作

| 操作 | 命令 | 说明 |
|------|------|------|
| 正常重启 | `adb reboot` | 正常重启设备 |
| 重启到 bootloader | `adb reboot bootloader` | 进入 fastboot 模式 |
| 重启到 recovery | `adb reboot recovery` | 进入 recovery 模式 |
| 关机 | `adb shell reboot -p` | 关闭设备 |

### 8. 端口转发

| 操作 | 命令 | 说明 |
|------|------|------|
| 正向转发 | `adb forward tcp:<local> tcp:<remote>` | 本地端口转发到设备 |
| 反向转发 | `adb reverse tcp:<remote> tcp:<local>` | 设备端口转发到本地 |
| 查看转发 | `adb forward --list` | 列出所有转发规则 |
| 移除转发 | `adb forward --remove <local>` | 移除指定转发 |

### 9. Fastboot 操作

| 操作 | 命令 | 说明 |
|------|------|------|
| 列出设备 | `fastboot devices` | 列出 fastboot 模式设备 |
| 刷入镜像 | `fastboot flash <partition> <img>` | 刷入分区镜像 |
| 解锁 | `fastboot oem unlock` | OEM 解锁 |
| 重启 | `fastboot reboot` | 从 fastboot 重启 |

### 10. 日志操作

| 操作 | 命令 | 说明 |
|------|------|------|
| 实时日志 | `adb logcat` | 实时查看所有日志 |
| 过滤 TAG | `adb logcat -s <TAG>` | 只看指定 TAG |
| 清除日志 | `adb logcat -c` | 清除日志缓冲区 |
| 保存到文件 | `adb logcat -d > log.txt` | 导出日志到文件 |
| 内核日志 | `adb shell dmesg` | 查看内核日志 |
| 内核日志持续 | `adb shell cat /proc/kmsg` | 持续查看内核日志 |

## 与其他 Skill 的关系

```
adb-helper (本 Skill)
    ├── 提供原始 ADB 操作能力
    │
    ├──→ ylog-helper: ylog pull/rm 依赖 adb 操作
    │     识别到 "ylog" 关键词时自动触发 ylog-helper
    │
    └──→ log-analyzer: 拉取的日志文件交给 log-analyzer 分析
          识别到 "分析日志" 时自动触发 log-analyzer
```

## 注意事项

1. **生产环境谨慎**：`adb root`、`adb remount` 等操作可能影响设备安全
2. **多设备场景**：多个设备连接时需要用 `-s <serial>` 指定目标设备
3. **大文件传输**：大文件 pull/push 注意超时，可考虑分段传输
4. **网络 ADB**：`adb connect` 需要设备和电脑在同一网络，且设备已开启网络调试
5. **Windows 路径**：`adb push/pull` 在 Windows 下使用反斜杠可能有问题，建议使用正斜杠