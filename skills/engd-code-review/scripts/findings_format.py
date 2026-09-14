#!/usr/bin/env python
"""findings_format.py -- Reference document for the 13-field finding format.

Usage:
  python scripts/findings_format.py          # print to stdout
  from findings_format import FINDINGS_FORMAT  # import as module
"""

FINDINGS_FORMAT = '''13-Field Finding Format
=====================================

Every finding MUST include ALL 13 fields. No field may be null, empty, or placeholder text.

## EXACT OUTPUT FORMAT (JSON EXAMPLE)

{
  "file": "src/main.c",
  "line": 42,
  "severity": "high",
  "category": "Security",
  "title": "Buffer overflow in memcpy",
  "description": "The memcpy call copies USER_COUNT bytes without checking the bound...",
  "suggested_fix": "Replace with memcpy_safe() and validate count < BUFFER_SIZE.",
  "original_code": "    if (count > BUFFER_SIZE) return -EINVAL;\\n    memcpy(buf, data, count);",
  "reviewed_code": "    if (count > BUFFER_SIZE) return -EINVAL;\\n    memcpy_safe(buf, data, count);",
  "architectural_comment": "Consider adding a bounds-checking wrapper for all memcpy calls.",
  "project": "kernel/common",
  "change_id": "1549963",
  "confidence_score": 95
}

## FIELD DEFINITIONS

| # | Field | Type | Rule |
|---|-------|------|------|
| 1 | file | string | Relative path from project root (as seen in diff) |
| 2 | line | integer | Line number where the issue occurs |
| 3 | severity | enum | MUST be lowercase: "high", "medium", "low", or "info" |
| 4 | category | string | Issue category (Security, Concurrency, Code Quality, Performance, Reliability, etc.) |
| 5 | title | string | Short, specific title (max 80 chars) |
| 6 | description | string | Detailed explanation of what the bug is and its impact |
| 7 | suggested_fix | string | Concrete, actionable fix -- 1-2 sentences. Must NOT duplicate description. |
| 8 | original_code | string | The CURRENT code at the reported line (3-5 lines of real source code). This is what\'s there NOW -- the buggy version. NEVER prose or placeholder. |
| 9 | reviewed_code | string | The PROPOSED FIX (3-5 lines of real source code). What the code SHOULD be after applying the fix. Must differ from original_code. |
| 10 | architectural_comment | string | Broader architectural concerns, or "" if none |
| 11 | project | string | Full project path (e.g., kernel/common) |
| 12 | change_id | string | The Gerrit change number |
| 13 | confidence_score | integer | Confidence score from 0-100 reflecting certainty that this is a real, impactful issue |

Cross-project findings (only for findings that span 2+ projects) add 2 extra fields:
| 14 | cross_project | boolean | Always true for cross-project findings |
| 15 | related_changes | array | List of impacted changes: [{"project": "...", "change_id": "...", "file": "...", "line": 0}] |

Code snippet extraction rules (MANDATORY, NO EXCEPTIONS):
- original_code = the CURRENT code at the reported line (what\'s there now, the buggy version). Extract from workspace source or diff NEW/+ side.
- reviewed_code = the PROPOSED FIX (what should replace it). Apply your fix to original_code.
- BOTH must be valid source code (3-5 lines)
- original_code must NOT equal reviewed_code
- suggested_fix must NOT be identical to description
- Extract code directly from the workspace/diff -- do NOT guess line numbers or fabricate code'''


if __name__ == "__main__":
    print(FINDINGS_FORMAT)
