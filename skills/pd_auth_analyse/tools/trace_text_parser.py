"""
Trace 文本解析辅助工具（可选，非主流程）

用途：将 Lecroy 导出的文本格式 trace（_extracted.txt）结构化为 JSON，便于分析。
本工具不是必须的 —— Agent 可以直接阅读文本报告。

用法：
    python trace_text_parser.py <trace_file> [--output <output.json>]

示例：
    python trace_text_parser.py 01_TC_CableDetection_cvs0_extracted.txt
    python trace_text_parser.py report_extracted.txt -o parsed.json
"""

import re
import json
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict

# PD 消息类型
PD_MESSAGES = [
    "SourceCap", "SinkCap", "Request", "Accept", "Reject",
    "PS_RDY", "Get_SinkCap", "Get_SourceCap",
    "PR_Swap", "DR_Swap", "VCONN_Swap",
    "Soft_Reset", "Hard_Reset", "Not_Supported",
    "Ping", "GoodCRC", "Alert", "GotoMin",
]

# 匹配 Lecroy 导出格式的行
# 典型格式: "  123  0.012345  S→D  SourceCap  [5V/3A, 9V/3A]"
LINE_PATTERN = re.compile(
    r"^\s*(\d+)\s+"           # 序号
    r"(\d+\.\d+)\s+"          # 时间戳
    r"([SsDd→←\-]+)\s+"      # 方向
    r"(\w+)"                  # 消息类型
    r"\s*(.*)?$"              # 数据（可选）
)


@dataclass
class TraceEvent:
    seq: int
    time: float
    direction: str
    message: str
    data: str = ""


def parse_trace_file(filepath: Path) -> list[TraceEvent]:
    """解析 Lecroy 导出的文本 trace 文件。"""
    events = []

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            m = LINE_PATTERN.match(line)
            if m:
                events.append(TraceEvent(
                    seq=int(m.group(1)),
                    time=float(m.group(2)),
                    direction=m.group(3),
                    message=m.group(4),
                    data=m.group(5).strip() if m.group(5) else "",
                ))

    return events


def compute_timers(events: list[TraceEvent]) -> dict:
    """计算关键 timer 值。"""
    timers = {}

    for i, ev in enumerate(events):
        # tSenderResponse: SourceCap → Request
        if ev.message == "SourceCap":
            for j in range(i + 1, min(i + 10, len(events))):
                if events[j].message == "Request":
                    timers["tSenderResponse"] = round(events[j].time - ev.time, 6)
                    break

        # tPSTransition: PS_RDY → 下一个非 GoodCRC 事件
        if ev.message == "PS_RDY":
            for j in range(i + 1, min(i + 20, len(events))):
                if events[j].message not in ("GoodCRC", ""):
                    timers["tPSTransition_approx"] = round(events[j].time - ev.time, 6)
                    break

    return timers


def main():
    parser = argparse.ArgumentParser(description="Lecroy Trace 文本解析辅助")
    parser.add_argument("trace_file", help="Lecroy 导出的文本 trace 文件")
    parser.add_argument("--output", "-o", help="输出 JSON 文件路径（默认 stdout）")
    args = parser.parse_args()

    filepath = Path(args.trace_file)
    if not filepath.is_file():
        print(f"[ERROR] 文件不存在: {filepath}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] 解析文件: {filepath}", file=sys.stderr)
    events = parse_trace_file(filepath)
    print(f"[INFO] 解析到 {len(events)} 条事件", file=sys.stderr)

    timers = compute_timers(events)
    if timers:
        print(f"[INFO] 计算到 timer: {timers}", file=sys.stderr)

    result = {
        "file": str(filepath),
        "event_count": len(events),
        "events": [asdict(e) for e in events],
        "timers": timers,
    }

    output_text = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"[INFO] 已写入: {args.output}", file=sys.stderr)
    else:
        print(output_text)


if __name__ == "__main__":
    main()
