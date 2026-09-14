#!/usr/bin/env python3
"""
JSONL to Markdown Converter for Claude Code Transcripts.

Converts Claude Code session/sub-agent JSONL transcript files into
human-readable Markdown with proper rendering of tool calls, results,
thinking blocks, and conversation flow.

Usage:
    python jsonl2md.py input.jsonl
    python jsonl2md.py input.jsonl -o output.md
    python jsonl2md.py --dir /path/to/session_dir/
    python jsonl2md.py input.jsonl --max-output 5000
"""

import json
import os
import sys
import argparse
from datetime import datetime

MAX_TOOL_OUTPUT = 3000


def parse_jsonl(filepath):
    """Parse a JSONL file, return list of records."""
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def truncate(text, max_len=MAX_TOOL_OUTPUT):
    """Truncate long text with a note."""
    if not text:
        return "(empty)"
    text = str(text)
    if len(text) > max_len:
        return text[:max_len] + f"\n\n... [truncated, {len(text) - max_len} more chars]"
    return text


def format_tool_input(inp):
    """Format tool input parameters nicely."""
    if not inp:
        return ""
    parts = []
    for k, v in inp.items():
        if isinstance(v, str):
            if len(v) > 200:
                v = v[:200] + "..."
            parts.append(f"- **{k}**: `{v}`")
        elif isinstance(v, bool):
            parts.append(f"- **{k}**: `{v}`")
        elif isinstance(v, (int, float)):
            parts.append(f"- **{k}**: `{v}`")
        else:
            parts.append(f"- **{k}**: `{json.dumps(v, ensure_ascii=False)[:200]}`")
    return "\n".join(parts)


def process_content_blocks(blocks, max_output=MAX_TOOL_OUTPUT):
    """Process a list of content blocks from a message."""
    out = []
    for block in blocks:
        bt = block.get("type", "?")
        if bt == "text":
            text = block.get("text", "")
            if text.strip():
                out.append(text)
        elif bt == "tool_use":
            name = block.get("name", "?")
            inp = block.get("input", {})
            out.append(f"\n> 🔧 **Tool Call: `{name}`**\n")
            if inp:
                out.append(format_tool_input(inp))
            out.append("")
        elif bt == "thinking":
            thinking = block.get("thinking", "")
            if thinking.strip():
                out.append(
                    f"\n<details>\n<summary>💭 Thinking</summary>\n\n{thinking}\n\n</details>\n"
                )
        elif bt == "tool_result":
            result = block.get("content", "")
            is_error = block.get("is_error", False)
            prefix = "❌ **Error:** " if is_error else ""
            out.append(
                f"\n> 📤 **Tool Result:**\n>\n> {prefix}{truncate(str(result), max_output)}\n"
            )
        else:
            out.append(f"\n> [{bt}]\n")
    return "\n".join(out)


def detect_type(records):
    """Detect if this is a main session or sub-agent transcript."""
    for rec in records[:10]:
        if rec.get("agentId") and rec.get("type") == "user":
            return "sub-agent"
        if rec.get("type") == "user" and "agentId" not in rec:
            return "main-session"
    return "unknown"


def extract_metadata(records):
    """Extract metadata from the first few records."""
    meta = {
        "session_id": "unknown",
        "cwd": "unknown",
        "timestamp": "unknown",
        "agent_type": "unknown",
        "agent_description": "unknown",
    }

    for rec in records[:20]:
        meta["session_id"] = rec.get("sessionId", meta["session_id"])
        meta["cwd"] = rec.get("cwd", meta["cwd"])

        ts = rec.get("timestamp", "")
        if ts:
            meta["timestamp"] = ts

        if rec.get("agentId"):
            meta["agent_type"] = rec.get("attributionAgent", "unknown")

        # Check attachment for skill listing (indicates sub-agent type)
        if rec.get("type") == "attachment":
            content = rec.get("attachment", {}).get("content", "")
            if "skillCount" in str(rec.get("attachment", {})):
                continue

    return meta


def extract_conversation(records, max_output=MAX_TOOL_OUTPUT):
    """Extract readable conversation from JSONL records."""
    lines = []
    msg_count = 0
    tool_count = 0

    for rec in records:
        rec_type = rec.get("type", "")

        # Skip attachments
        if rec_type == "attachment":
            continue

        msg = rec.get("message", {})
        if not msg:
            continue

        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        # Process content
        if isinstance(content, list):
            # Count tool calls
            tool_count += sum(1 for b in content if b.get("type") == "tool_use")
            rendered = process_content_blocks(content, max_output)
        elif isinstance(content, str):
            rendered = content
        else:
            rendered = str(content)

        if not rendered or not rendered.strip():
            continue

        msg_count += 1

        if role == "user":
            # Check if this is actually a tool_result wrapper
            if isinstance(content, list):
                has_tool_result = any(
                    b.get("type") == "tool_result" for b in content
                )
                if has_tool_result:
                    for block in content:
                        if block.get("type") == "tool_result":
                            result = block.get("content", "")
                            is_error = block.get("is_error", False)
                            prefix = "❌ **Error:**\n" if is_error else ""
                            truncated = truncate(str(result), max_output)
                            lines.append(
                                f"\n> 📤 **Tool Result:**\n>\n> {prefix}{truncated}\n"
                            )
                    continue

            lines.append(f"\n---\n### 👤 User\n\n{rendered}\n")
        elif role == "assistant":
            lines.append(f"\n### 🤖 Assistant\n\n{rendered}\n")
        elif role == "system":
            if len(rendered.strip()) > 10:
                lines.append(f"\n### ⚙️ System\n\n```\n{rendered[:2000]}\n```\n")
        else:
            lines.append(f"\n### ❓ {role}\n\n{rendered}\n")

    return "\n".join(lines), msg_count, tool_count


def convert_file(input_path, output_path=None, max_output=MAX_TOOL_OUTPUT):
    """Convert a single JSONL file to Markdown."""
    if not os.path.exists(input_path):
        print(f"ERROR: File not found: {input_path}", file=sys.stderr)
        return False

    file_size = os.path.getsize(input_path)

    if output_path is None:
        base = os.path.splitext(input_path)[0]
        output_path = base + ".md"

    print(f"Reading: {input_path} ({file_size:,} bytes)")
    records = parse_jsonl(input_path)

    if not records:
        print("ERROR: No valid records found", file=sys.stderr)
        return False

    transcript_type = detect_type(records)
    meta = extract_metadata(records)
    conversation, msg_count, tool_count = extract_conversation(records, max_output)

    # Collect additional stats
    user_msgs = sum(
        1
        for r in records
        if r.get("type") == "user" and r.get("message", {}).get("role") == "user"
    )
    assistant_msgs = sum(
        1
        for r in records
        if r.get("type") == "assistant"
    )

    # Build header
    if transcript_type == "sub-agent":
        header = f"""# Sub-Agent 运行记录

| 属性 | 值 |
|------|-----|
| **Agent ID** | `{os.path.basename(input_path).replace('.jsonl', '')}` |
| **Agent 类型** | `{meta['agent_type']}` |
| **Session** | `{meta['session_id']}` |
| **时间戳** | {meta['timestamp']} |
| **工作目录** | `{meta['cwd']}` |
| **消息轮次** | {msg_count} |
| **工具调用次数** | {tool_count} |
| **原始文件大小** | {file_size:,} bytes |
| **原始文件** | `{os.path.abspath(input_path)}` |

---
"""
    else:
        # Main session
        # Try to get first user message as summary
        first_user_msg = ""
        for rec in records:
            if (
                rec.get("type") == "user"
                and isinstance(rec.get("message", {}).get("content"), str)
                and not rec.get("agentId")
            ):
                first_user_msg = rec["message"]["content"][:200]
                break

        header = f"""# 会话记录

| 属性 | 值 |
|------|-----|
| **Session ID** | `{meta['session_id']}` |
| **时间戳** | {meta['timestamp']} |
| **工作目录** | `{meta['cwd']}` |
| **消息轮次** | {msg_count} |
| **用户消息** | {user_msgs} |
| **Assistant 消息** | {assistant_msgs} |
| **工具调用次数** | {tool_count} |
| **原始文件大小** | {file_size:,} bytes |
| **原始文件** | `{os.path.abspath(input_path)}` |

> **首条消息:** {first_user_msg}

---
"""
    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(conversation)

    out_size = os.path.getsize(output_path)
    print(f"  -> {output_path}")
    print(f"     {out_size:,} bytes, {msg_count} messages, {tool_count} tool calls")
    return True


def convert_directory(dir_path, max_output=MAX_TOOL_OUTPUT):
    """Convert all JSONL files in a directory."""
    count = 0
    for root, dirs, files in os.walk(dir_path):
        for f in files:
            if f.endswith(".jsonl"):
                input_path = os.path.join(root, f)
                if convert_file(input_path, max_output=max_output):
                    count += 1

    print(f"\nConverted {count} file(s) from {dir_path}")
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Convert Claude Code JSONL transcripts to Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python jsonl2md.py session.jsonl
  python jsonl2md.py session.jsonl -o report.md
  python jsonl2md.py --dir ~/.claude/projects/my-project/
  python jsonl2md.py agent.jsonl --max-output 5000
        """,
    )
    parser.add_argument("input", nargs="?", help="Input JSONL file path")
    parser.add_argument("-o", "--output", help="Output Markdown file path")
    parser.add_argument(
        "--max-output",
        type=int,
        default=MAX_TOOL_OUTPUT,
        help=f"Max chars for tool output (default: {MAX_TOOL_OUTPUT})",
    )
    parser.add_argument(
        "--dir", help="Batch convert all JSONL files in a directory"
    )
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="List available sessions in ~/.claude/projects/",
    )

    args = parser.parse_args()

    if args.list_sessions:
        list_sessions()
        return

    if args.dir:
        convert_directory(os.path.expanduser(args.dir), args.max_output)
        return

    if not args.input:
        parser.print_help()
        print("\nERROR: Please provide an input file or --dir", file=sys.stderr)
        sys.exit(1)

    input_path = os.path.expanduser(args.input)
    success = convert_file(input_path, args.output, args.max_output)
    sys.exit(0 if success else 1)


def list_sessions():
    """List available Claude Code session directories."""
    projects_dir = os.path.expanduser("~/.claude/projects/")
    if not os.path.exists(projects_dir):
        print(f"No projects directory found: {projects_dir}")
        return

    print("Available Claude Code sessions:\n")
    for project in sorted(os.listdir(projects_dir)):
        project_path = os.path.join(projects_dir, project)
        if not os.path.isdir(project_path):
            continue

        # Check for jsonl files
        jsonl_files = []
        for root, dirs, files in os.walk(project_path):
            for f in files:
                if f.endswith(".jsonl"):
                    size = os.path.getsize(os.path.join(root, f))
                    jsonl_files.append((os.path.relpath(root, project_path), f, size))

        if jsonl_files:
            print(f"📁 {project}/")
            for rel_path, fname, size in sorted(jsonl_files):
                label = "📄" if "subagents" not in rel_path else "🤖"
                print(f"  {label} {rel_path}/{fname} ({size:,} bytes)")
            print()


if __name__ == "__main__":
    main()