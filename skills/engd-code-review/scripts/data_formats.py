#!/usr/bin/env python
"""data_formats.py -- Reference docs for intermediate data formats.

Usage:
  python scripts/data_formats.py          # print to stdout
  from data_formats import DATA_FORMATS   # import as module
"""

DATA_FORMATS = '''Data Formats Reference
======================

## change_summary.json
Location: <resolved_cwd>/review-<timestamp>/change_summary.json
Written by: setup_review.py (per-run subdirectory)
Required by: generate_html_report.py (mandatory -- exits with error if missing)

Format: JSON array of objects

Example:
[
  {
    "change_id": "1549963",
    "project": "kernel/common",
    "workspace_path": "kernel_common",
    "branch": "msm-ms-4.19",
    "owner": "John Doe",
    "patchset": "ps12",
    "gerrit_url": "https://gerrit.unisoc.com/gerrit/c/kernel/common/+/1549963",
    "description": "Addresses a race condition between sprd_gserial_connect/disconnect/resume/suspend by introducing serial_port_lock to protect gser->ioport access, adds missing NULL checks, and corrects kernel log levels."
  }
]

Fields:
- change_id: Gerrit change number
- project: Full project path (e.g., kernel/common)
- workspace_path: Subdirectory name within the workspace (project path with / replaced by _)
- branch: Gerrit branch (e.g., msm-ms-4.19)
- owner: Gerrit change owner name
- patchset: Patchset identifier (e.g., ps12)
- gerrit_url: Full URL to the Gerrit change page
- description: First 3 non-empty lines of the commit message (after stripping Gerrit trailers like Reviewed-on, Signed-off-by, Change-Id), separated by newlines. Falls back to changed filenames if commit message is empty.

Multiple changes in the same project share one workspace_path directory.
workspace_path naming: replace / with _ (kernel/common -> kernel_common).

## findings JSON
Each agent writes findings to: <resolved_cwd>/review-<timestamp>/reviews/<workspace_path>-<change_id>_findings.json
Format: JSON array of finding objects (see findings_format.py for the 13-field specification).

## all_findings.json
Location: <resolved_cwd>/review-<timestamp>/all_findings.json
Created by: Step 3.5 consolidation step
Contents: Combined + deduplicated findings from all *_findings.json files

## verified_findings.json
Location: <resolved_cwd>/review-<timestamp>/verified_findings.json
Created by: Step 4 validation agent (NEVER overwritten by Step 5)
Format: JSON array of objects (pretty-printed, indent=2)

Each entry contains the validation result:
- change_id: Gerrit change number (string, copied from original finding)
- file: Source file path (string, copied from original finding)
- line: Line number (integer, copied from original finding)
- title: Finding title (string, copied from original finding)
- original_severity: Severity from review agents (high/medium/low/info)
- verdict: VALID | PARTIAL | INVALID
- confirmed_severity: Severity after validation (same or adjusted)
- rationale: Detailed explanation with actual line numbers and code snippets

Findings are matched by stable key (change_id, file, line, title) rather than
array position, so the order of entries does not affect correctness.

Step 5 MUST NOT overwrite this file. It reads from this file to build issues.json.

## issues.json
Location: <resolved_cwd>/review-<timestamp>/issues.json (output)
Created by: Step 5 -- built from validated findings
Contents: Subset of all_findings.json (VALID and PARTIAL only) with severity adjustments from validator
Format: Identical 13-field format as all_findings.json (file, line, severity, category, title, description, suggested_fix, original_code, reviewed_code, architectural_comment, project, change_id, confidence_score).
Cross-project findings additionally include: cross_project (boolean, true) and related_changes (array of {project, change_id, file, line}).
Do NOT rename, remove, or add fields. Use confirmed_severity from the validator for VALID/PARTIAL findings.
change_id must be non-null for every finding.
line field must be integer (not string like "1429-1430").'''


if __name__ == "__main__":
    print(DATA_FORMATS)
