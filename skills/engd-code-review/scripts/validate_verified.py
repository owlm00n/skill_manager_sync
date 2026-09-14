#!/usr/bin/env python
"""Validate _verified_*.json files against the 8-field (per-change) or
10-field (cross-project) verdict schema.

Checks every entry in reviews/_verified_*.json for:
  - All required fields present
  - No field is null or whitespace-only (except allowed empties)
  - Correct types (line is int, cross_project is bool when present)
  - original_severity and confirmed_severity in high/medium/low/info
  - verdict is VALID, PARTIAL, or INVALID
  - line is a positive integer (not a string range like "1429-1430")

Usage:
  python scripts/validate_verified.py <run_dir>
  python scripts/validate_verified.py <run_dir> --report
"""

import argparse
import glob
import json
import os
import re
import sys

from shared import fix_json_control_chars, update_progress

REQUIRED_FIELDS_PER_CHANGE = [
    "change_id", "file", "line", "title",
    "original_severity", "verdict", "confirmed_severity", "rationale",
]

REQUIRED_FIELDS_CROSS_PROJECT = REQUIRED_FIELDS_PER_CHANGE + [
    "cross_project", "related_changes",
]

STRING_FIELDS = [
    "change_id", "file", "title",
    "original_severity", "verdict", "confirmed_severity", "rationale",
]

VALID_SEVERITIES = {"high", "medium", "low", "info"}
VALID_VERDICTS = {"VALID", "PARTIAL", "INVALID"}


def is_empty(value):
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def normalize_line(line_val):
    if isinstance(line_val, int):
        return line_val, False
    if isinstance(line_val, float):
        return int(line_val), False
    if isinstance(line_val, str):
        if line_val.strip().isdigit():
            return int(line_val.strip()), False
        m = re.match(r"(\d+)", line_val.strip())
        if m:
            return int(m.group(1)), True
    return None, False


def validate_related_changes(prefix, related, errors):
    valid = True
    if not isinstance(related, list) or len(related) == 0:
        errors.append(f"{prefix}: 'related_changes' must be a non-empty array")
        return False
    for ri, rc in enumerate(related):
        if not isinstance(rc, dict):
            errors.append(f"{prefix}: related_changes[{ri}] is not an object")
            valid = False
            continue
        for req_field in ("project", "file", "line"):
            if req_field not in rc:
                errors.append(f"{prefix}: related_changes[{ri}] missing required field '{req_field}'")
                valid = False
            elif req_field == "line":
                line_val, _ = normalize_line(rc[req_field])
                if line_val is None:
                    errors.append(
                        f"{prefix}: related_changes[{ri}].line is not a valid number "
                        f"(got: {rc[req_field]!r})"
                    )
                    valid = False
            elif isinstance(rc[req_field], str) and not rc[req_field].strip():
                errors.append(f"{prefix}: related_changes[{ri}] field '{req_field}' is empty")
                valid = False
    return valid


def validate_severity(prefix, field_name, value, errors):
    if not isinstance(value, str) or value.lower() not in VALID_SEVERITIES:
        errors.append(
            f"{prefix}: field '{field_name}' must be one of {VALID_SEVERITIES}, got {value!r}"
        )
        return False
    return True


def validate_entry(entry, idx, filepath, errors):
    prefix = f"{os.path.basename(filepath)}[#{idx}]"
    is_cross = os.path.basename(filepath) == "_verified_cross_project.json"
    required = REQUIRED_FIELDS_CROSS_PROJECT if is_cross else REQUIRED_FIELDS_PER_CHANGE
    entry_valid = True

    for field in required:
        if field not in entry:
            errors.append(f"{prefix}: missing field '{field}'")
            entry_valid = False

    if not entry_valid:
        return False

    for field in STRING_FIELDS:
        if is_empty(entry[field]):
            errors.append(f"{prefix}: field '{field}' is empty/null/whitespace")
            entry_valid = False

    line_val, was_range = normalize_line(entry.get("line"))
    if line_val is None:
        errors.append(f"{prefix}: field 'line' is not a valid number (got: {entry.get('line')!r})")
        entry_valid = False
    elif line_val <= 0:
        errors.append(f"{prefix}: field 'line' must be positive (got: {line_val})")
        entry_valid = False
    elif was_range:
        errors.append(
            f"{prefix}: field 'line' is a range string '{entry.get('line')}' (should be int)"
        )
        entry_valid = False

    if not validate_severity(prefix, "original_severity", entry.get("original_severity"), errors):
        entry_valid = False
    if not validate_severity(prefix, "confirmed_severity", entry.get("confirmed_severity"), errors):
        entry_valid = False

    verdict = entry.get("verdict")
    if not isinstance(verdict, str) or verdict not in VALID_VERDICTS:
        errors.append(f"{prefix}: field 'verdict' must be one of {VALID_VERDICTS}, got {verdict!r}")
        entry_valid = False

    if is_cross:
        if entry.get("cross_project") is not True:
            errors.append(f"{prefix}: field 'cross_project' must be boolean true")
            entry_valid = False
        if not validate_related_changes(prefix, entry.get("related_changes"), errors):
            entry_valid = False

    return entry_valid


def load_json_safe(filepath):
    with open(filepath, "rb") as f:
        raw = f.read()
    try:
        return json.loads(raw, strict=True)
    except json.JSONDecodeError:
        pass
    fixed = fix_json_control_chars(raw)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        return None, str(e)


def validate_file(filepath):
    issues = []
    data = load_json_safe(filepath)
    if isinstance(data, tuple):
        issues.append(f"{os.path.basename(filepath)}: invalid JSON: {data[1]}")
        return 0, 1, issues

    if not isinstance(data, list):
        issues.append(f"{os.path.basename(filepath)}: root is not a JSON array")
        return 0, 1, issues

    if len(data) == 0:
        return 0, 0, issues

    valid = 0
    invalid = 0
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            issues.append(f"{os.path.basename(filepath)}[#{idx}]: item is not a JSON object")
            invalid += 1
            continue
        if validate_entry(item, idx, filepath, issues):
            valid += 1
        else:
            invalid += 1

    return valid, invalid, issues


def main():
    parser = argparse.ArgumentParser(
        description="Validate 8-field / 10-field verdict format in _verified_*.json files"
    )
    parser.add_argument("run_dir", help="Run directory containing reviews/_verified_*.json")
    parser.add_argument("--report", action="store_true", help="Output JSON validation report to stdout")
    args = parser.parse_args()

    run_dir = os.path.abspath(args.run_dir)
    reviews_dir = os.path.join(run_dir, "reviews")
    if not os.path.isdir(reviews_dir):
        print(f"Error: '{reviews_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    target_files = sorted(glob.glob(os.path.join(reviews_dir, "_verified_*.json")))
    if not target_files:
        print(f"No _verified_*.json files in '{reviews_dir}' — nothing to validate.")
        sys.exit(0)

    total_valid = 0
    total_errors = 0
    all_issues = []

    for fpath in target_files:
        valid, errors, issues = validate_file(fpath)
        total_valid += valid
        total_errors += errors
        all_issues.extend(issues)

    if args.report:
        report = {
            "run_dir": run_dir,
            "files_checked": [os.path.basename(f) for f in target_files],
            "total_valid": total_valid,
            "total_errors": total_errors,
            "issues": all_issues,
            "passed": total_errors == 0,
        }
        print(json.dumps(report, indent=2))
    else:
        print(f"Validated {len(target_files)} verified file(s) in '{reviews_dir}':")
        print(f"  Valid entries: {total_valid}")
        print(f"  Errors:        {total_errors}")
        if all_issues:
            print()
            for issue in all_issues:
                print(f"  ! {issue}")
            print()

        if total_errors == 0:
            print("PASS: All verified entries pass schema validation.")
            update_progress(run_dir, "validate_verified")
        else:
            print(f"FAIL: {total_errors} error(s) found. Re-dispatch failed validation agents after their prior run finishes.")
        sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
    main()
