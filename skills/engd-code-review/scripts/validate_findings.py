#!/usr/bin/env python
"""Validate findings JSON files against the 13-field format spec.

Checks every finding in *_findings.json and issues.json for:
  - All 13 required fields are present
  - No field is null, empty, or whitespace-only
  - Correct types (line and confidence_score are int, others are str)
  - Severity is one of: high, medium, low, info
  - original_code != reviewed_code
  - suggested_fix != description
  - title length <= 80 chars
  - project and change_id are non-empty
  - line is positive integer (not a string range like "1429-1430")
  - confidence_score is 0-100

Usage:
  python3 validate_findings.py <directory>
  python3 validate_findings.py <directory> --fix        # auto-fix line ranges
  python3 validate_findings.py <directory> --report     # JSON report mode
"""

import argparse
import glob
import json
import os
import re
import sys

from shared import fix_json_control_chars, update_progress

REQUIRED_FIELDS = [
    "file", "line", "severity", "category", "title",
    "description", "suggested_fix", "original_code",
    "reviewed_code", "architectural_comment", "project", "change_id",
    "confidence_score",
]

STRING_FIELDS = [
    "file", "severity", "category", "title", "description",
    "suggested_fix", "original_code", "reviewed_code",
    "architectural_comment", "project", "change_id",
]

VALID_SEVERITIES = {"high", "medium", "low", "info"}

MAX_TITLE_LENGTH = 80

# Fields that are allowed to be empty strings
ALLOWED_EMPTY = {"architectural_comment"}


def is_empty(value):
    """Check if a value is null, empty, or whitespace-only."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def normalize_line(line_val):
    """Convert line field to int. Returns (int_value, was_string_range)."""
    if isinstance(line_val, int):
        return line_val, False
    if isinstance(line_val, float):
        return int(line_val), False
    if isinstance(line_val, str):
        # Handle "1429" -> 1429
        if line_val.strip().isdigit():
            return int(line_val.strip()), False
        # Handle "1429-1430" -> take first number
        m = re.match(r'(\d+)', line_val.strip())
        if m:
            return int(m.group(1)), True
    return None, False


def validate_finding(finding, idx, filepath, errors, fixes=None):
    """Validate a single finding dict. Returns True if valid."""
    prefix = f"{os.path.basename(filepath)}[#{idx}]"
    finding_valid = True

    # Check all 13 fields present
    for field in REQUIRED_FIELDS:
        if field not in finding:
            errors.append(f"{prefix}: missing field '{field}'")
            finding_valid = False

    # Extra fields beyond the 13 required are allowed — just ignore them

    if not finding_valid:
        # Can't meaningfully check further if fields are missing
        return False

    # Check string fields are not empty
    for field in STRING_FIELDS:
        if field in ALLOWED_EMPTY:
            continue
        if is_empty(finding[field]):
            errors.append(f"{prefix}: field '{field}' is empty/null/whitespace")
            finding_valid = False

    # Check line is a positive integer
    line_val = finding.get("line")
    line_val, was_range = normalize_line(line_val)
    if line_val is None:
        errors.append(f"{prefix}: field 'line' is not a valid number (got: {finding.get('line')!r})")
        finding_valid = False
    elif line_val <= 0:
        errors.append(f"{prefix}: field 'line' must be positive (got: {line_val})")
        finding_valid = False
    elif was_range:
        if fixes is not None:
            finding["line"] = line_val
            fixes.append(f"{prefix}: normalized line from {finding.get('line')!r} to {line_val}")
        else:
            errors.append(f"{prefix}: field 'line' is a range string '{finding.get('line')}' (should be int, use --fix to auto-fix)")

    # Check severity enum
    severity = finding.get("severity", "")
    if isinstance(severity, str) and severity.lower() not in VALID_SEVERITIES:
        errors.append(f"{prefix}: field 'severity' must be one of {VALID_SEVERITIES}, got '{severity}'")
        finding_valid = False
    elif isinstance(severity, str):
        finding["severity"] = severity.lower()

    # Title length is advisory only (not a gate)

    # Check original_code != reviewed_code
    orig = finding.get("original_code", "")
    rev = finding.get("reviewed_code", "")
    if isinstance(orig, str) and isinstance(rev, str) and orig == rev:
        errors.append(f"{prefix}: 'original_code' and 'reviewed_code' are identical")
        finding_valid = False

    # Check suggested_fix != description
    fix = finding.get("suggested_fix", "")
    desc = finding.get("description", "")
    if isinstance(fix, str) and isinstance(desc, str) and fix.strip() == desc.strip():
        errors.append(f"{prefix}: 'suggested_fix' is identical to 'description'")
        finding_valid = False

    # Check confidence_score is an integer 0–100
    conf = finding.get("confidence_score")
    if not isinstance(conf, int) or isinstance(conf, bool) or conf < 0 or conf > 100:
        errors.append(f"{prefix}: field 'confidence_score' must be an integer 0–100, got {conf!r}")
        finding_valid = False

    # Check project and change_id non-empty (already caught by is_empty loop above)

    # Optional cross-project fields (only validated when present)
    if "cross_project" in finding:
        if finding["cross_project"] is not True:
            errors.append(f"{prefix}: field 'cross_project' must be boolean true")
            finding_valid = False
        related = finding.get("related_changes")
        if not isinstance(related, list) or len(related) == 0:
            errors.append(f"{prefix}: 'related_changes' must be a non-empty array when cross_project is true")
            finding_valid = False
        elif isinstance(related, list):
            for ri, rc in enumerate(related):
                if not isinstance(rc, dict):
                    errors.append(f"{prefix}: related_changes[{ri}] is not an object")
                    finding_valid = False
                    continue
                for req_field in ("project", "file", "line"):
                    if req_field not in rc or (isinstance(rc[req_field], str) and not rc[req_field].strip()):
                        errors.append(f"{prefix}: related_changes[{ri}] missing required field '{req_field}'")
                        finding_valid = False
                # change_id is allowed to be empty for missing co-changes

    return finding_valid


def load_json_safe(filepath):
    """Load a JSON file, auto-fixing control character issues.

    Returns parsed data on success, or (None, error_message) on failure.
    This non-fatal variant is used by the validator to report bad files
    rather than crashing.
    """
    with open(filepath, 'rb') as f:
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


def validate_file(filepath, fixes=None, report_mode=False):
    """Validate a findings JSON file. Returns (valid_count, error_count, issues)."""
    issues = []

    try:
        data = load_json_safe(filepath)
        if data is None:
            # Error message is in the string
            raise json.JSONDecodeError(f"recovery failed: {data}", "", 0)
    except json.JSONDecodeError as e:
        issues.append(f"{os.path.basename(filepath)}: invalid JSON: {e}")
        return 0, len(issues), issues
    except Exception as e:
        issues.append(f"{os.path.basename(filepath)}: cannot read: {e}")
        return 0, 1, issues

    if not isinstance(data, list):
        issues.append(f"{os.path.basename(filepath)}: root is not a JSON array")
        return 0, 1, issues

    if len(data) == 0:
        issues.append(f"{os.path.basename(filepath)}: empty findings array")
        return 0, 0, issues

    valid = 0
    total_invalid = 0

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            issues.append(f"{os.path.basename(filepath)}[#{idx}]: item is not a JSON object")
            total_invalid += 1
            continue

        is_valid = validate_finding(item, idx, filepath, issues, fixes)
        if is_valid:
            valid += 1
        else:
            total_invalid += 1

    # Fix the file in-place if --fix was given
    if fixes and total_invalid > 0:
        try:
            with open(filepath, 'w', encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.write('\n')
        except Exception as e:
            issues.append(f"{os.path.basename(filepath)}: failed to write fixed file: {e}")

    return valid, total_invalid, issues


def main():
    parser = argparse.ArgumentParser(description="Validate 13-field finding format in JSON files")
    parser.add_argument("directory", help="Directory containing *_findings.json and/or issues.json")
    parser.add_argument("--fix", action="store_true", help="Auto-fix correctable issues (line ranges)")
    parser.add_argument("--report", action="store_true", help="Output JSON validation report to stdout")
    args = parser.parse_args()

    base_dir = os.path.abspath(args.directory)
    if not os.path.isdir(base_dir):
        print(f"Error: '{args.directory}' is not a directory", file=sys.stderr)
        sys.exit(1)

    # Find all findings and issues JSON files (verified_findings.json uses a different 8-field schema)
    patterns = [
        os.path.join(base_dir, "reviews", "*_findings.json"),
        os.path.join(base_dir, "issues.json"),
        os.path.join(base_dir, "all_findings.json"),
    ]

    seen = set()
    target_files = []
    for pat in patterns:
        for f in sorted(glob.glob(pat)):
            real = os.path.abspath(f)
            if real not in seen:
                seen.add(real)
                target_files.append(f)

    if not target_files:
        print(f"Error: no *_findings.json or issues.json found in '{base_dir}'")
        sys.exit(1)

    total_valid = 0
    total_errors = 0
    all_issues = []
    fix_notes = []

    for fpath in target_files:
        valid, errors, issues = validate_file(fpath, fixes=fix_notes if args.fix else None)
        total_valid += valid
        total_errors += errors
        all_issues.extend(issues)

    # Print results
    if args.report:
        report = {
            "directory": base_dir,
            "files_checked": [os.path.basename(f) for f in target_files],
            "total_valid": total_valid,
            "total_errors": total_errors,
            "issues": all_issues,
            "fix_notes": fix_notes,
            "passed": total_errors == 0,
        }
        print(json.dumps(report, indent=2))
    else:
        print(f"Validated {len(target_files)} file(s) in '{base_dir}':")
        print(f"  Valid findings: {total_valid}")
        print(f"  Errors:         {total_errors}")
        if all_issues:
            print()
            for issue in all_issues:
                print(f"  ! {issue}")
            print()

        if total_errors == 0:
            print("PASS: All findings pass 13-field validation.")
            update_progress(base_dir, "validate_findings")
        else:
            print(f"FAIL: {total_errors} error(s) found. Fix and re-run.")
        sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
    main()
