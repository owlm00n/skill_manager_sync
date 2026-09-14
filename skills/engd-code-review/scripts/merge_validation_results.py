"""Merge per-group validation results into verified_findings.json.

Reads all `_verified_<CHANGE_ID>.json` files written by parallel validation agents.
Merges, deduplicates by stable key (change_id, file, line, title), and writes
`verified_findings.json`.

Usage:
    python3 merge_validation_results.py <run_dir>
"""
import json
import os
import sys
import glob as globmod

from shared import load_json_safe, update_progress


def _stable_key(entry: dict) -> tuple:
    """Build a stable key from the 4 identifying fields of a verdict."""
    return (
        str(entry.get("change_id", "")),
        str(entry.get("file", "")),
        entry.get("line", 0),
        str(entry.get("title", "")),
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: merge_validation_results.py <run_dir>", file=sys.stderr)
        sys.exit(1)

    run_dir = sys.argv[1]
    reviews_dir = os.path.join(run_dir, "reviews")

    # Load manifest
    manifest_path = os.path.join(reviews_dir, "_validation_manifest.json")
    with open(manifest_path, encoding='utf-8') as f:
        manifest = json.load(f)

    # Load all findings to build expected key set
    all_findings_path = os.path.join(run_dir, "all_findings.json")
    with open(all_findings_path, encoding='utf-8') as f:
        all_findings = json.load(f)
    expected_count = len(all_findings)

    expected_keys = set()
    for finding in all_findings:
        expected_keys.add((
            str(finding.get("change_id", "")),
            str(finding.get("file", "")),
            finding.get("line", 0),
            str(finding.get("title", "")),
        ))

    output_path = os.path.join(run_dir, "verified_findings.json")

    if expected_count == 0:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("No findings to validate - wrote empty verified_findings.json")
        update_progress(run_dir, "merge_validation")
        return

    # Load all group results
    group_files = sorted(globmod.glob(os.path.join(reviews_dir, "_verified_*.json")))
    if not group_files:
        print("Error: no _verified_*.json files found", file=sys.stderr)
        sys.exit(1)

    merged = []
    seen_keys = set()
    empty_groups = []

    for gf in group_files:
        group_name = os.path.basename(gf)
        data = load_json_safe(gf)
        if not isinstance(data, list):
            print(f"Warning: {group_name} does not contain a JSON array, skipping", file=sys.stderr)
            empty_groups.append(group_name)
            continue

        for entry in data:
            key = _stable_key(entry)
            if key == ("", "", 0, ""):
                print(f"Warning: {group_name} entry has empty key fields, skipping", file=sys.stderr)
                continue
            if key in seen_keys:
                print(f"Warning: duplicate key {key} in {group_name}, skipping duplicate", file=sys.stderr)
                continue
            seen_keys.add(key)
            merged.append(entry)

    # Sort by (change_id, file, line) for stable ordering
    merged.sort(key=lambda x: (str(x.get("change_id", "")), str(x.get("file", "")), x.get("line", 0)))

    # Verification
    missing_keys = expected_keys - seen_keys
    extra_keys = seen_keys - expected_keys

    errors = []
    if missing_keys:
        errors.append(f"Missing findings ({len(missing_keys)}): {sorted(missing_keys)[:5]}...")
    if extra_keys:
        errors.append(f"Extra findings ({len(extra_keys)}): {sorted(extra_keys)[:5]}...")
    if len(merged) != expected_count:
        errors.append(f"Merged {len(merged)} entries, expected {expected_count}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Merged {len(merged)} verified findings from {len(group_files)} group(s) -> {output_path}")

    if empty_groups:
        print(f"  Warning: {len(empty_groups)} group file(s) were empty or invalid: {empty_groups}", file=sys.stderr)

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"All {expected_count} findings matched. Verification passed.")
    update_progress(run_dir, "merge_validation")


if __name__ == "__main__":
    main()
