"""
UART Log File Finder — 查找和分析 MobaXterm 串口日志文件

找到活跃日志文件，识别重启点，分析文件关系。

用法:
    python find_log.py                    # 分析当前活跃日志
    python find_log.py --session "COM (1)"  # 查看指定 Session 的所有日志文件
    python find_log.py --file "E:/11_log/MobaXterm/[COM (1)] (10-09_163449).log"  # 分析指定文件
"""

import sys
import os
import json
import re
import time
import argparse

LOG_DIR = "E:/11_log/MobaXterm"

# ============================================================
# UMS9230 平台 reboot 锚点关键词（按 boot 阶段排序）
# ============================================================
REBOOT_END_OF_LAST = [       # 上一次系统结束
    "reboot: Restarting system",
    "sysrq: Terminate All Tasks",
]

REBOOT_BOOTLOADER = [        # Bootloader 阶段（最早出现，不依赖内核版本）
    "ddr init start!!!",
]

REBOOT_ATF = [               # ARM Trusted Firmware
    "NOTICE:  BL31:",
]

REBOOT_EDK2 = [              # EDK2 UEFI
    "UEFI firmware",
    "BoardName:",
]

REBOOT_KERNEL = [            # 内核启动（最确定但出现较晚）
    "Booting Linux on physical CPU",
    "Linux version",
]

# 统一的重启检测关键词（按优先级排序：最早的锚点排前面）
ALL_REBOOT_KEYWORDS = (
    REBOOT_END_OF_LAST +
    REBOOT_BOOTLOADER +
    REBOOT_ATF +
    REBOOT_EDK2 +
    REBOOT_KERNEL
)


# ============================================================
# 文件锁检测
# ============================================================

def is_file_locked(filepath):
    """Windows 下检测文件是否被其他进程占用（如 MobaXterm 正在写入）"""
    try:
        f = open(filepath, 'ab')
        f.close()
        return False
    except (IOError, PermissionError):
        return True


# ============================================================
# 文件查找
# ============================================================

def find_session_logs(session_name="COM (1)"):
    """找到某个 Session 的所有日志文件，按时间倒序"""
    # 方括号在 glob 中是通配符，用 os.listdir + 手动过滤替代
    prefix = f"[{session_name}]"
    file_info = []
    try:
        for name in os.listdir(LOG_DIR):
            if name.startswith(prefix) and name.endswith(".log"):
                fpath = os.path.join(LOG_DIR, name)
                if os.path.isfile(fpath):
                    stat = os.stat(fpath)
                    file_info.append({
                        "path": fpath,
                        "name": name,
                        "size_bytes": stat.st_size,
                        "size_kb": round(stat.st_size / 1024, 1),
                        "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                        "mtime_epoch": stat.st_mtime,
                        "locked": is_file_locked(fpath),
                    })
    except FileNotFoundError:
        pass
    file_info.sort(key=lambda x: x["mtime_epoch"], reverse=True)
    return file_info


def find_active_log(session_name="COM (1)"):
    """找到当前活跃的日志文件（MobaXterm 正在写入的那个）"""
    logs = find_session_logs(session_name)

    # 优先：被进程锁定的文件 = 当前正在写
    locked = [f for f in logs if f["locked"]]
    if locked:
        active = locked[0]
        active["detection_method"] = "file_locked"
        return active

    # 降级：最新修改的文件
    if logs:
        active = logs[0]
        active["detection_method"] = "latest_mtime"
        return active

    return None


# ============================================================
# 重启点分析
# ============================================================

def find_reboot_points(filepath):
    """扫描日志文件，找到所有 reboot 点"""
    reboots = []

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        return {"error": str(e), "reboots": []}

    for i, line in enumerate(lines):
        for kw in ALL_REBOOT_KEYWORDS:
            if kw in line:
                reboots.append({
                    "line": i + 1,
                    "keyword": kw,
                    "content": line.strip()[:200],
                })
                break  # 一行只匹配一个关键词

    # 去重相近的行（同一阶段可能匹配多个关键词，取最早的那个）
    if reboots:
        deduped = [reboots[0]]
        for r in reboots[1:]:
            last = deduped[-1]
            # 距离上次匹配 < 50 行且关键词不同 → 合并到同一阶段，保留更早的关键词
            if r["line"] - last["line"] < 50:
                # 取更早的锚点（更接近 boot 开始）
                pass
            else:
                deduped.append(r)
        reboots = deduped

    # 找"最近一次重启"的起始行
    last_boot_info = None
    if reboots:
        # 从后往前找最近的 boot 锚点
        for r in reversed(reboots):
            if any(kw in r["keyword"] for kw in (
                "ddr init start!!!", "NOTICE:  BL31:", "UEFI firmware",
                "Booting Linux", "Linux version",
            )):
                last_boot_info = r
                break
        if not last_boot_info:
            last_boot_info = reboots[-1]

    return {
        "file": os.path.basename(filepath),
        "total_lines": len(lines),
        "reboot_count": len(reboots),
        "reboot_markers": reboots,
        "last_boot_start": {
            "line": last_boot_info["line"] if last_boot_info else None,
            "keyword": last_boot_info["keyword"] if last_boot_info else None,
            "content": last_boot_info["content"][:200] if last_boot_info else None,
        } if last_boot_info else None,
        "last_boot_lines": len(lines) - (last_boot_info["line"] - 1) if last_boot_info else 0,
        "header_line": lines[0].strip() if lines else "",
    }


# ============================================================
# 主函数
# ============================================================

def analyze(session_name="COM (1)", filepath=None):
    """主分析函数，输出结构化 JSON"""
    if filepath:
        # 分析指定文件
        if not os.path.exists(filepath):
            return {"status": "error", "message": f"文件不存在: {filepath}"}
        reboot_info = find_reboot_points(filepath)
        return {
            "status": "ok",
            "file_analyzed": os.path.basename(filepath),
            "is_active": is_file_locked(filepath),
            "reboot_info": reboot_info,
        }

    # 分析活跃日志 + 历史文件
    active = find_active_log(session_name)
    all_logs = find_session_logs(session_name)

    if not active:
        return {
            "status": "no_logs",
            "message": f"未找到 [{session_name}] 的日志文件",
            "log_dir": LOG_DIR,
        }

    reboot_info = find_reboot_points(active["path"])

    return {
        "status": "ok",
        "session": session_name,
        "log_dir": LOG_DIR,
        "active_file": {
            "name": active["name"],
            "path": active["path"],
            "size_kb": active["size_kb"],
            "mtime": active["mtime"],
            "locked": active["locked"],
            "detection_method": active.get("detection_method", "unknown"),
        },
        "reboot_info": reboot_info,
        "history_files": [
            {
                "name": f["name"],
                "size_kb": f["size_kb"],
                "mtime": f["mtime"],
                "is_active": f["path"] == active["path"],
            }
            for f in all_logs
        ],
    }


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UART Log File Finder")
    parser.add_argument("--session", type=str, default="COM (1)", help="Session 名称")
    parser.add_argument("--file", type=str, help="分析指定日志文件")
    parser.add_argument("--reboots", action="store_true", help="仅输出重启点列表")
    args = parser.parse_args()

    if args.reboots and args.file:
        result = find_reboot_points(args.file)
    else:
        result = analyze(session_name=args.session, filepath=args.file)

    print(json.dumps(result, indent=2, ensure_ascii=False))