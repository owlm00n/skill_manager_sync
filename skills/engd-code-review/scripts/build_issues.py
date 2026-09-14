"""Build issues.json from validated findings.

Reads:
  <run_dir>/all_findings.json
  <run_dir>/verified_findings.json
  <run_dir>/change_summary.json

Writes:
  <run_dir>/issues.json

Matches verdicts to findings by stable key (change_id, file, line, title)
instead of array position.
"""
import json
import sys
import os

from shared import load_json_safe, update_progress


def _stable_key(entry: dict) -> tuple:
    """Build a stable key from the 4 identifying fields."""
    return (
        str(entry.get("change_id", "")),
        str(entry.get("file", "")),
        entry.get("line", 0),
        str(entry.get("title", "")),
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: build_issues.py <run_dir>", file=sys.stderr)
        sys.exit(1)

    run_dir = sys.argv[1]

    all_findings = load_json_safe(os.path.join(run_dir, "all_findings.json"))
    verified = load_json_safe(os.path.join(run_dir, "verified_findings.json"))
    change_summary = load_json_safe(os.path.join(run_dir, "change_summary.json"))

    # Build lookup: change_id (string) -> {project, change_id}
    change_map = {}
    for c in change_summary:
        change_map[str(c["change_id"])] = {"project": c["project"], "change_id": c["change_id"]}

    # Build verdict map: stable_key -> verdict/confirmed_severity
    verdict_map = {}
    for v in verified:
        verdict_map[_stable_key(v)] = {"verdict": v["verdict"], "confirmed_severity": v["confirmed_severity"]}

    issues = []
    for finding in all_findings:
        key = _stable_key(finding)
        vm = verdict_map.get(key, {})
        if finding.get("confidence_score", 0) < 80:
            continue
        if vm.get("verdict") not in ("VALID", "PARTIAL", "CONFIRMED", "confirmed"):
            continue
        change_id = str(finding.get("change_id", ""))
        cm = change_map.get(change_id, {})
        raw_line = finding["line"]
        if isinstance(raw_line, int):
            line_val = raw_line
        else:
            line_val = int(str(raw_line).split("-")[0])
        issue = {
            "file": finding["file"],
            "line": line_val,
            "severity": vm.get("confirmed_severity", finding.get("severity")),
            "category": finding["category"],
            "title": finding["title"],
            "description": finding["description"],
            "suggested_fix": finding["suggested_fix"],
            "original_code": finding["original_code"],
            "reviewed_code": finding["reviewed_code"],
            "architectural_comment": finding.get("architectural_comment", ""),
            "project": cm.get("project", ""),
            "change_id": cm.get("change_id", ""),
            "confidence_score": finding.get("confidence_score", 0),
        }
        # Pass through cross-project fields when present
        if finding.get("cross_project"):
            issue["cross_project"] = True
            issue["related_changes"] = finding.get("related_changes", [])
        issues.append(issue)

    output_path = os.path.join(run_dir, "issues.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(issues, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(issues)} issues to {output_path}")
    update_progress(run_dir, "build_issues")

if __name__ == "__main__":
    main()
