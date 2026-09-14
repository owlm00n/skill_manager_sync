#!/usr/bin/env python
"""prepare_cross_project_index.py -- Build a compact cross-project review index.

The index gives the Step 3.1 cross-project agent a low-context map of changed
projects, touched files, Android-system signals, and likely provider/consumer
edges before it opens large raw diffs.

Usage:
  python scripts/prepare_cross_project_index.py <run_dir>
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from shared import load_json_safe


MAX_SIGNAL_VALUES = 40
MAX_PROJECT_FILES = 80

SIGNAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("kernel_module", re.compile(r"\b[\w.-]+\.ko\b")),
    ("android_property", re.compile(r"\b(?:ro|persist|vendor|sys|ctl|debug)\.[A-Za-z0-9_.-]+\b")),
    ("aidl_interface", re.compile(r"\b[A-Za-z_][\w.]*\.aidl\b|interface\s+[A-Za-z_]\w*")),
    ("hidl_interface", re.compile(r"@[0-9]+\.[0-9]+::[A-Za-z_]\w*|I[A-Z]\w+\.hal\b")),
    ("init_service", re.compile(r"^\s*service\s+([A-Za-z0-9_.-]+)\b")),
    ("selinux_type", re.compile(r"\b(?:type|allow|neverallow|typeattribute|init_daemon_domain)\s+([A-Za-z0-9_]+)")),
    ("shared_library", re.compile(r"\b(?:lib[A-Za-z0-9_.-]+\.so|cc_library(?:_shared|_static)?)\b")),
    ("vintf_manifest", re.compile(r"\b(?:manifest\.xml|compatibility_matrix|vintf)\b")),
    ("device_tree", re.compile(r"\b[\w,.-]+(?:-supply|gpios?|interrupts?|reg|compatible)\b")),
    ("boot_config", re.compile(r"\b(?:bootargs|cmdline|dtbo|vendor_boot|BOARD_[A-Z0-9_]+|PRODUCT_[A-Z0-9_]+)\b")),
    ("secure_interface", re.compile(r"\b(?:smc|SMC|tee|TEE|trusty|tos|atf|sip|fastcall)\b")),
    ("native_service", re.compile(r"\b(?:addService|getService|defaultServiceManager|AServiceManager_[A-Za-z0-9_]+)\b")),
    ("java_service", re.compile(r"\b(?:SystemService|ServiceManager|getSystemService|BinderService)\b")),
]

SYMBOL_PATTERN = re.compile(
    r"^\+\s*(?:"
    r"(?:static\s+|inline\s+|extern\s+|public\s+|private\s+|protected\s+|final\s+|native\s+)*"
    r"[A-Za-z_][\w:<>,\s\*&\[\]]+\s+"
    r"([A-Za-z_]\w*)\s*\([^;]*\)\s*(?:\{|$)"
    r"|#define\s+([A-Za-z_]\w*)"
    r"|class\s+([A-Za-z_]\w*)"
    r"|struct\s+([A-Za-z_]\w*)"
    r"|enum\s+([A-Za-z_]\w*)"
    r")"
)


def _limited_add(bucket: dict[str, list[str]], key: str, value: str) -> None:
    value = value.strip()
    if not value:
        return
    values = bucket.setdefault(key, [])
    if value not in values and len(values) < MAX_SIGNAL_VALUES:
        values.append(value)


def _normalize_diff_path(path: str) -> str:
    path = path.strip()
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def _project_domain(project: str, files: list[str]) -> str:
    joined = " ".join([project] + files).lower()
    if "framework" in joined:
        return "framework"
    if "system/" in joined or "native" in joined or "service" in joined:
        return "native"
    if "hardware" in joined or "hal" in joined or "aidl" in joined or "hidl" in joined:
        return "hal"
    if "kernel" in joined or ".dts" in joined or ".dtsi" in joined or "defconfig" in joined:
        return "kernel"
    if "device/" in joined or "vendor/" in joined or "product" in joined:
        return "device_config"
    if "bootloader" in joined or "u-boot" in joined or "lk" in joined:
        return "bootloader"
    if "atf" in joined or "arm-trusted-firmware" in joined:
        return "atf"
    if "tos" in joined or "trusty" in joined or "tee" in joined:
        return "tos"
    return "unknown"


def _extract_file_from_diff_line(line: str) -> str | None:
    if line.startswith("diff --git "):
        parts = line.split()
        if len(parts) >= 4:
            return _normalize_diff_path(parts[3])
    if line.startswith("+++ "):
        path = line[4:].strip()
        if path != "/dev/null":
            return _normalize_diff_path(path)
    return None


def _parse_diff(diff_path: Path) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    signals: dict[str, list[str]] = {}
    changed_symbols: list[str] = []
    current_file = ""
    added_total = 0
    deleted_total = 0

    if not diff_path.is_file():
        return {
            "diff_path": str(diff_path),
            "diff_exists": False,
            "diff_bytes": 0,
            "files": [],
            "signals": {},
            "changed_symbols": [],
            "added_lines": 0,
            "deleted_lines": 0,
        }

    for line in diff_path.read_text(encoding="utf-8", errors="replace").splitlines():
        maybe_file = _extract_file_from_diff_line(line)
        if maybe_file:
            current_file = maybe_file
            files.setdefault(current_file, {"path": current_file, "added_lines": 0, "deleted_lines": 0})
            for signal_name, pattern in SIGNAL_PATTERNS:
                if pattern.search(current_file):
                    _limited_add(signals, signal_name, current_file)
            continue

        if not current_file:
            continue

        file_entry = files.setdefault(current_file, {"path": current_file, "added_lines": 0, "deleted_lines": 0})
        if line.startswith("+") and not line.startswith("+++"):
            added_total += 1
            file_entry["added_lines"] += 1
            payload = line[1:]
            symbol_match = SYMBOL_PATTERN.match(line)
            if symbol_match:
                symbol = next((g for g in symbol_match.groups() if g), "")
                if symbol and symbol not in changed_symbols and len(changed_symbols) < MAX_SIGNAL_VALUES:
                    changed_symbols.append(symbol)
            for signal_name, pattern in SIGNAL_PATTERNS:
                matches = pattern.findall(payload)
                if not matches and pattern.search(payload):
                    _limited_add(signals, signal_name, payload[:160])
                for match in matches:
                    if isinstance(match, tuple):
                        match = next((m for m in match if m), "")
                    _limited_add(signals, signal_name, str(match))
        elif line.startswith("-") and not line.startswith("---"):
            deleted_total += 1
            file_entry["deleted_lines"] += 1

    return {
        "diff_path": str(diff_path),
        "diff_exists": True,
        "diff_bytes": diff_path.stat().st_size,
        "files": list(files.values())[:MAX_PROJECT_FILES],
        "signals": signals,
        "changed_symbols": changed_symbols,
        "added_lines": added_total,
        "deleted_lines": deleted_total,
    }


def _edge_reason(left: dict[str, Any], right: dict[str, Any]) -> str | None:
    left_signals = left.get("signals", {})
    right_signals = right.get("signals", {})
    shared = sorted(set(left_signals) & set(right_signals))
    if shared:
        return "shared signals: " + ", ".join(shared[:6])

    domains = {left.get("domain"), right.get("domain")}
    if {"framework", "native"} <= domains:
        return "framework/native service boundary"
    if "hal" in domains and ("framework" in domains or "native" in domains):
        return "HAL interface boundary"
    if "kernel" in domains and ("device_config" in domains or "hal" in domains or "native" in domains):
        return "kernel/provider vs consumer/config boundary"
    if ("bootloader" in domains or "atf" in domains or "tos" in domains) and "kernel" in domains:
        return "boot chain or secure/kernel ABI boundary"
    if "device_config" in domains and ("framework" in domains or "native" in domains or "hal" in domains):
        return "device config consumed by Android runtime components"
    return None


def _build_edges(changes: list[dict[str, Any]]) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for idx, left in enumerate(changes):
        for right in changes[idx + 1:]:
            reason = _edge_reason(left, right)
            if not reason:
                continue
            edges.append({
                "from_change": str(left["change_id"]),
                "from_project": left["project"],
                "to_change": str(right["change_id"]),
                "to_project": right["project"],
                "reason": reason,
            })
    return edges


def _write_markdown(index: dict[str, Any], output_path: Path) -> None:
    lines = [
        "# Cross-Project Review Index",
        "",
        f"Run directory: `{index['run_dir']}`",
        f"Workspace: `{index['workspace_dir']}`",
        f"Changes: {index['change_count']} across {index['project_count']} projects",
        "",
        "## Changes",
    ]
    for change in index["changes"]:
        lines.extend([
            "",
            f"### {change['project']} ({change['change_id']})",
            f"- Workspace path: `{change['workspace_path']}`",
            f"- Domain: {change['domain']}",
            f"- Diff: `{change['diff_path']}` ({change['diff_bytes']} bytes)",
            f"- Added/deleted lines: +{change['added_lines']} / -{change['deleted_lines']}",
        ])
        if change.get("description"):
            lines.append(f"- Description: {change['description']}")
        if change.get("changed_symbols"):
            lines.append("- Changed symbols: " + ", ".join(change["changed_symbols"]))
        if change.get("signals"):
            lines.append("- Signals:")
            for signal_name, values in sorted(change["signals"].items()):
                lines.append(f"  - {signal_name}: " + ", ".join(values[:12]))
        if change.get("files"):
            lines.append("- Touched files:")
            for file_entry in change["files"][:25]:
                lines.append(
                    f"  - `{file_entry['path']}` (+{file_entry['added_lines']}/-{file_entry['deleted_lines']})"
                )

    lines.extend(["", "## Likely Cross-Project Edges"])
    if index["likely_edges"]:
        for edge in index["likely_edges"]:
            lines.append(
                f"- {edge['from_project']}({edge['from_change']}) <-> "
                f"{edge['to_project']}({edge['to_change']}): {edge['reason']}"
            )
    else:
        lines.append("- No high-confidence edges found by heuristics. The reviewer should still scan purposes and diffs.")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_cross_project_index(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    reviews_dir = run_dir / "reviews"
    change_summary_path = run_dir / "change_summary.json"
    workspace_dir = str((run_dir.parent / "workspace").resolve())

    changes_raw = load_json_safe(str(change_summary_path))
    changes: list[dict[str, Any]] = []
    project_signals: dict[str, dict[str, list[str]]] = defaultdict(dict)

    for raw in changes_raw:
        change_id = str(raw["change_id"])
        workspace_path = raw.get("workspace_path", "")
        diff_path = reviews_dir / f"{workspace_path}-{change_id}.diff"
        diff_info = _parse_diff(diff_path)
        files = [f["path"] for f in diff_info["files"]]
        domain = _project_domain(raw.get("project", ""), files)

        change = {
            "change_id": change_id,
            "project": raw.get("project", ""),
            "workspace_path": workspace_path,
            "branch": raw.get("branch", ""),
            "description": (raw.get("description") or "").strip(),
            "domain": domain,
            **diff_info,
        }
        changes.append(change)

        for signal_name, values in change["signals"].items():
            for value in values:
                _limited_add(project_signals[change["project"]], signal_name, value)

    unique_projects = sorted({c["project"] for c in changes})
    index = {
        "run_dir": str(run_dir),
        "workspace_dir": workspace_dir,
        "change_count": len(changes),
        "project_count": len(unique_projects),
        "projects": unique_projects,
        "changes": changes,
        "project_signals": project_signals,
        "likely_edges": _build_edges(changes),
    }
    return index


def write_cross_project_index(run_dir: Path) -> tuple[Path, Path]:
    run_dir = run_dir.resolve()
    reviews_dir = run_dir / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)

    index = build_cross_project_index(run_dir)
    json_path = reviews_dir / "_cross_project_index.json"
    md_path = reviews_dir / "_cross_project_index.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")
    _write_markdown(index, md_path)
    return json_path, md_path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/prepare_cross_project_index.py <run_dir>", file=sys.stderr)
        sys.exit(1)

    run_dir = Path(sys.argv[1]).resolve()
    if not run_dir.is_dir():
        print(f"Error: '{sys.argv[1]}' is not a directory", file=sys.stderr)
        sys.exit(1)

    json_path, md_path = write_cross_project_index(run_dir)
    index = load_json_safe(str(json_path))
    print(f"Cross-project index JSON: {json_path}")
    print(f"Cross-project index Markdown: {md_path}")
    print(f"Changes: {index['change_count']} across {index['project_count']} projects")
    print(f"Likely edges: {len(index['likely_edges'])}")


if __name__ == "__main__":
    main()
