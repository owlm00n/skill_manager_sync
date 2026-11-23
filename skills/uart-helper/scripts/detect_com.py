"""
UART COM Port Detector — 自动识别 USB 转串口小板的 kernel UART 口

VCP 组（4 个连续 COM 口）中只有 1 个是 kernel UART log 口。
此脚本通过 pyserial 直接读 COM 口数据判断，输出结构化 JSON。
交互逻辑由 AI 处理，脚本只负责检测 + 输出结果。

用法:
    python detect_com.py              # 自动检测（运行时扫描）
    python detect_com.py --boot       # boot 模式（需要用户重启手机）
    python detect_com.py --platform UMS9230  # 指定平台查询已知映射
    python detect_com.py --scan       # 强制重新扫描（忽略已知映射）
"""

import sys
import os
import json
import re
import time
import argparse
from collections import OrderedDict

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
MAP_FILE = os.path.join(SKILL_DIR, "platform_com_map.json")

# ============================================================
# Kernel log 特征关键词
# ============================================================
KERNEL_KEYWORDS = [
    b"Linux version", b"Booting Linux", b"Starting kernel",
    b"Kernel command line", b"bootconsole",
    b"sc27xx_typec", b"sc27xx_pd", b"sprd_tcpm",
    b"sprd_", b"unisoc", b"Unisoc",
    b"spipe", b"sipc", b"sprd-ddr",
]

# Modem/AT 口特征（排除用）
MODEM_KEYWORDS = [
    b"AT+", b"+CME", b"+CREG", b"+CSQ",
    b"DIAG", b"FTM", b"QMI",
    b"+CPIN", b"+CFUN", b"+CIMI",
]

# ============================================================
# 注册表 / COM 口扫描
# ============================================================

def get_com_ports():
    """从注册表读取所有 COM 端口映射"""
    import winreg
    ports = OrderedDict()
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"HARDWARE\DEVICEMAP\SERIALCOMM") as key:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    ports[name] = value
                    i += 1
                except OSError:
                    break
    except OSError:
        pass
    return ports


def parse_com_number(com_str):
    """'COM45' → 45"""
    m = re.match(r'COM(\d+)', com_str, re.IGNORECASE)
    return int(m.group(1)) if m else None


def find_vcp_groups(ports):
    """找出所有连续 VCP COM 口组（≥3 个连续算一组），返回 COM 名称列表"""
    vcp_ports = []
    for device, com_name in ports.items():
        if 'VCP' in device:
            num = parse_com_number(com_name)
            if num:
                vcp_ports.append((num, com_name))

    vcp_ports.sort()

    groups = []
    i = 0
    while i < len(vcp_ports):
        group = [vcp_ports[i]]
        j = i + 1
        while j < len(vcp_ports) and vcp_ports[j][0] == vcp_ports[j-1][0] + 1:
            group.append(vcp_ports[j])
            j += 1
        if len(group) >= 3:
            groups.append([g[1] for g in group])
        i = j

    return groups


# ============================================================
# pyserial 检测
# ============================================================

def try_read_port(com_name, baud, duration=3.0):
    """
    打开 COM 口，读数据，判断是否是 kernel UART log 口。

    返回: dict {is_uart, reason, sample_preview, keyword_hits}
    """
    try:
        import serial
    except ImportError:
        return {
            "is_uart": False,
            "reason": "pyserial_not_installed",
            "sample_preview": "",
            "keyword_hits": [],
        }

    try:
        ser = serial.Serial(
            port=com_name,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.5,
        )
    except Exception as e:
        return {
            "is_uart": False,
            "reason": f"open_failed: {e}",
            "sample_preview": "",
            "keyword_hits": [],
        }

    ser.reset_input_buffer()
    deadline = time.time() + duration
    all_data = b""

    try:
        while time.time() < deadline:
            chunk = ser.read(4096)
            if chunk:
                all_data += chunk
            time.sleep(0.1)
    finally:
        ser.close()

    if not all_data or len(all_data) < 10:
        return {
            "is_uart": False,
            "reason": "silent",
            "sample_preview": "",
            "keyword_hits": [],
        }

    # 匹配 kernel 关键词
    kernel_hits = [kw.decode(errors='replace') for kw in KERNEL_KEYWORDS
                   if kw.lower() in all_data.lower()]
    modem_hits = [kw.decode(errors='replace') for kw in MODEM_KEYWORDS
                  if kw in all_data]

    if kernel_hits:
        return {
            "is_uart": True,
            "reason": "kernel_log",
            "sample_preview": repr(all_data[:200]),
            "keyword_hits": kernel_hits,
        }

    if modem_hits:
        return {
            "is_uart": False,
            "reason": "modem_at",
            "sample_preview": repr(all_data[:200]),
            "keyword_hits": modem_hits,
        }

    # 可读性判断
    printable = sum(32 <= b <= 126 or b in (10, 13) for b in all_data[:500])
    ratio = printable / min(500, len(all_data)) if all_data else 0

    if ratio > 0.7:
        return {
            "is_uart": False,
            "reason": f"readable_unknown (ratio={ratio:.1%})",
            "sample_preview": repr(all_data[:200]),
            "keyword_hits": [],
        }
    else:
        return {
            "is_uart": False,
            "reason": f"binary_noise (ratio={ratio:.1%})",
            "sample_preview": repr(all_data[:200]),
            "keyword_hits": [],
        }


# ============================================================
# 平台映射管理
# ============================================================

def load_map():
    """加载已知平台映射"""
    if os.path.exists(MAP_FILE):
        with open(MAP_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if not k.startswith('_')}
    return {}


def save_map(platform, port_index, baud, method):
    """自动保存平台映射（静默写入）"""
    meta = {}
    if os.path.exists(MAP_FILE):
        with open(MAP_FILE, 'r', encoding='utf-8') as f:
            meta = json.load(f)

    # 保留元数据
    result = {k: v for k, v in meta.items() if k.startswith('_')}
    # 加载已有映射
    for k, v in meta.items():
        if not k.startswith('_'):
            result[k] = v
    # 写入新映射
    result[platform] = {
        "port_index": port_index,
        "baud": baud,
        "confirmed": time.strftime("%Y-%m-%d"),
        "note": f"auto-detected: {method}",
    }

    with open(MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return MAP_FILE


# ============================================================
# 主检测函数
# ============================================================

def detect(platform_hint=None, force_scan=False, boot_mode=False):
    """
    主检测流程。

    Returns:
        dict — 结构化 JSON 结果，status 字段决定 AI 后续行为
    """
    # ---------- Step 1: 扫描注册表 ----------
    ports = get_com_ports()
    if not ports:
        return {
            "status": "no_device",
            "message": "未找到任何 COM 口，请确认 USB 小板已插入",
        }

    # ---------- Step 2: 找 VCP 组 ----------
    groups = find_vcp_groups(ports)
    if not groups:
        return {
            "status": "no_device",
            "message": "未找到连续 VCP COM 口组，请确认 USB 转串口小板已插入",
            "all_ports": list(ports.values()),
        }

    active_group = groups[0]  # 单设备场景，只取第一组

    # ---------- Step 3: 查已知映射 ----------
    known_map = load_map()
    if platform_hint and platform_hint in known_map and not force_scan:
        info = known_map[platform_hint]
        target_com = active_group[min(info['port_index'], len(active_group)-1)]
        return {
            "status": "known",
            "com_port": target_com,
            "port_index": info["port_index"],
            "baud": info["baud"],
            "group": active_group,
            "platform": platform_hint,
        }

    # ---------- Step 4: pyserial 扫描 ----------
    baud_rates = [921600, 115200]
    port_results = []

    for idx, com_name in enumerate(active_group):
        port_entry = {"com": com_name, "port_index": idx, "baud_results": []}

        for baud in baud_rates:
            result = try_read_port(com_name, baud)
            result["com"] = com_name
            result["port_index"] = idx
            result["baud"] = baud
            port_entry["baud_results"].append(result)
            port_results.append(result)

    # 找最佳匹配
    uart_hits = [r for r in port_results if r["is_uart"]]

    if uart_hits:
        best = uart_hits[0]
        scan_results = {
            "status": "detected",
            "com_port": best["com"],
            "port_index": best["port_index"],
            "baud": best["baud"],
            "group": active_group,
            "method": "runtime_scan",
            "confidence": "high",
            "keyword_hits": best["keyword_hits"],
            "all_results": [
                {
                    "com": r["com"],
                    "port_index": r["port_index"],
                    "baud": r["baud"],
                    "is_uart": r["is_uart"],
                    "reason": r["reason"],
                }
                for r in port_results
            ],
        }
        return scan_results

    # 检查是否有可读但未识别的口（可能是 modem AT 口）
    readable = [r for r in port_results if "readable" in r.get("reason", "")]
    modem_hits = [r for r in port_results if "modem" in r.get("reason", "")]

    # 检查是否有被占用的口（MobaXterm 已连接 → 大概率就是 UART 口）
    locked = [r for r in port_results if "open_failed" in r.get("reason", "")]
    if locked and not uart_hits:
        # 按 port_index 去重（每个口有两个波特率结果）
        locked_ports = {}
        for r in locked:
            idx = r["port_index"]
            if idx not in locked_ports:
                locked_ports[idx] = r
        sorted_locked = sorted(locked_ports.values(), key=lambda r: r["port_index"])

        return {
            "status": "locked",
            "group": active_group,
            "message": "部分 COM 口被占用，无法读取",
            "hint": "请关闭 MobaXterm 中占用这些 COM 口的 Session，然后重试检测。已占用的口大概率就是 UART 口。",
            "retry_cmd": "python detect_com.py --scan",
            "locked_ports": [
                {"com": r["com"], "port_index": r["port_index"], "reason": r["reason"]}
                for r in sorted_locked
            ],
            "all_details": [
                {
                    "com": r["com"],
                    "port_index": r["port_index"],
                    "baud": r["baud"],
                    "reason": r["reason"],
                }
                for r in port_results
            ],
        }

    # 没有 UART 口 → 提示需要上电或重启
    return {
        "status": "need_power",
        "group": active_group,
        "message": "所有端口运行时无 kernel log 输出",
        "hint": "请确认手机已上电，或重启手机后重试",
        "retry_cmd": "python detect_com.py --boot",
        "details": [
            {
                "com": r["com"],
                "port_index": r["port_index"],
                "baud": r["baud"],
                "reason": r["reason"],
            }
            for r in port_results
        ],
        "readable_count": len(readable),
        "modem_count": len(modem_hits),
    }


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UART COM Port Detector")
    parser.add_argument("--scan", action="store_true", help="强制重新扫描（忽略已知映射）")
    parser.add_argument("--platform", type=str, help="指定平台名查询")
    parser.add_argument("--boot", action="store_true", help="boot 模式检测（提示用户重启手机）")
    args = parser.parse_args()

    result = detect(
        platform_hint=args.platform,
        force_scan=args.scan,
        boot_mode=args.boot,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))