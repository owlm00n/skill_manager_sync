"""
Log 关键字提取辅助工具（可选，非主流程）

用途：当 kernel log 文件过大（>10MB）时，Agent 可调用本脚本快速提取 PD 相关行。
本工具不是必须的 —— Agent 可以直接用 grep/搜索完成同样工作。

用法：
    python log_grep_helper.py <logfile> [--output <output_file>] [--window <seconds>]

示例：
    python log_grep_helper.py kernel_log.txt
    python log_grep_helper.py kernel_log.txt --window 5
"""

import re
import sys
import argparse
from pathlib import Path

# PD/Type-C 相关关键字
PD_KEYWORDS = [
    "sc27xx-typec", "sprd_tcpm", "tcpci", "pd_notify",
    "cc1", "cc2", "DRP", "SourceCap", "SinkCap", "Request",
    "Accept", "PS_RDY", "Hard_Reset", "Soft_Reset",
    "PR_SWAP", "DR_SWAP", "VCONN",
    "sgm41512", "set_vinlimit", "set_voltage", "musb_gadget",
    "charger_manager", "bc1p2", "vbos_ok_work",
    "i2c_write", "i2c_read", "tcpci_transmit", "tcpci_alert",
    "typec_send", "typec_recv", "pd_state",
]

# 时间戳正则
TS_PATTERN = re.compile(r"^\[\s*(\d+\.\d+)\]")


def extract_pd_lines(logfile: Path, window_sec: float = 0) -> list[str]:
    """提取包含 PD 关键字的行，可选时间窗口过滤。"""
    results = []
    keyword_pattern = re.compile("|".join(re.escape(kw) for kw in PD_KEYWORDS), re.IGNORECASE)

    with open(logfile, "r", encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, 1):
            if keyword_pattern.search(line):
                # 清理控制字符
                clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", line).strip()
                if clean:
                    results.append(f"L{line_no}: {clean}")

    return results


def main():
    parser = argparse.ArgumentParser(description="PD Log 关键字提取辅助")
    parser.add_argument("logfile", help="kernel log 文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径（默认 stdout）")
    parser.add_argument("--window", type=float, default=0, help="时间窗口（秒，0=不过滤）")
    args = parser.parse_args()

    logfile = Path(args.logfile)
    if not logfile.is_file():
        print(f"[ERROR] 文件不存在: {logfile}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] 扫描文件: {logfile} ({logfile.stat().st_size / 1024 / 1024:.1f} MB)")
    results = extract_pd_lines(logfile, args.window)
    print(f"[INFO] 匹配到 {len(results)} 行 PD 相关日志")

    output_text = "\n".join(results)

    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"[INFO] 已写入: {args.output}")
    else:
        print(output_text)


if __name__ == "__main__":
    main()
