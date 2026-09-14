"""Consolidate per-change *_findings.json files into a single all_findings.json.

Glob reviews/*_findings.json, merge all findings, deduplicate by
(change_id, file, line, description), and write consolidated output.

Usage:
  python3 consolidate_findings.py <run_directory>
"""

import argparse
import glob
import json
import os
import sys

from shared import load_json_safe, update_progress, get_project_count, ensure_cross_project_review_done, cross_project_review_path


def consolidate(run_dir):
    base_dir = os.path.abspath(run_dir)
    reviews_dir = os.path.join(base_dir, "reviews")

    if not os.path.isdir(reviews_dir):
        print(f"Error: '{reviews_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    ensure_cross_project_review_done(run_dir, "consolidate (Step 3.5b)")

    patterns = [
        os.path.join(reviews_dir, "*_findings.json"),
    ]

    finding_files = []
    seen = set()
    for pat in patterns:
        for f in sorted(glob.glob(pat)):
            real = os.path.abspath(f)
            if real not in seen:
                seen.add(real)
                finding_files.append(f)

    if not finding_files:
        print(f"Error: no *_findings.json found in '{reviews_dir}'", file=sys.stderr)
        sys.exit(1)

    # Merge all findings
    all_findings = []
    for fpath in finding_files:
        data = load_json_safe(fpath)
        if not isinstance(data, list):
            print(f"Warning: {os.path.basename(fpath)} root is not a JSON array, skipping", file=sys.stderr)
            continue
        all_findings.extend(data)

    # Deduplicate by (change_id, file, line, description)
    dedup = {}
    for f in all_findings:
        key = (
            f.get("change_id", ""),
            f.get("file", ""),
            f.get("line", 0),
            f.get("description", ""),
        )
        if key not in dedup:
            dedup[key] = f

    consolidated = list(dedup.values())

    # Write output
    output_path = os.path.join(base_dir, "all_findings.json")
    with open(output_path, 'w', encoding="utf-8") as f:
        json.dump(consolidated, f, indent=2)
        f.write('\n')

    # Count cross-project findings
    cross_count = sum(1 for f in consolidated if f.get("cross_project"))
    cross_files = [os.path.basename(f) for f in finding_files if "_cross_project" in f]
    cross_review_ran = cross_project_review_path(run_dir).is_file()

    print(f"Consolidated {len(all_findings)} finding(s) from {len(finding_files)} file(s)")
    print(f"After deduplication: {len(consolidated)} finding(s)")
    if cross_count > 0:
        print(f"CROSS_PROJECT_FINDINGS={cross_count} (from {', '.join(cross_files)})")
        print(f">>> Run Step 4.1 (cross-project validation) after per-project validation.")
    elif cross_review_ran:
        print(f"CROSS_PROJECT_FINDINGS=0 (Step 3.1 completed — no cross-project issues found)")
        print(f">>> Skip Step 4.1 (no cross-project findings).")
    else:
        print(f"CROSS_PROJECT_FINDINGS=0")
        print(f">>> Skip Step 4.1 (no cross-project findings).")
    print(f"Output: {output_path}")
    update_progress(run_dir, "consolidate")


def main():
    parser = argparse.ArgumentParser(description="Consolidate per-change findings into all_findings.json")
    parser.add_argument("run_directory", help="Run directory containing reviews/*_findings.json")
    args = parser.parse_args()
    consolidate(args.run_directory)


if __name__ == "__main__":
    main()
