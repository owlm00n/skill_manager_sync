#!/usr/bin/env python
"""generate_review_prompt.py -- Build the agent prompt for review agents.

Usage:
  python scripts/generate_review_prompt.py \\
      --workspace-dir <path> \\
      --project-name <project> \\
      --workspace-path <ws_path> \\
      --change-id <id> \\
      --run-dir <path> \\
      [--diff-file <path>] \\
      [--output <path>]

If --output is given, writes prompt to file. Otherwise prints to stdout.
"""

import argparse
import sys
from pathlib import Path

REVIEW_PROMPT_TEMPLATE = r"""You are an expert code reviewer. Review the diff below for project '{{PROJECT_NAME}}' (change {{CHANGE_ID}}). You have access to the full project workspace at {{WORKSPACE_DIR}}/{{WORKSPACE_PATH}}.

**SCOPE RULE: Only report bugs the change introduces, exposes, interacts with, or causes as regressions.**
- Do NOT report pre-existing bugs, style issues, spelling errors, or design choices unchanged by this diff.
- Do NOT report issues in unmodified files unless the change breaks a caller/callee relationship.
- Do NOT report issues on unmodified lines even in modified files.

**Core Responsibilities:**
- **Project Guidelines**: Verify CLAUDE.md compliance (imports, conventions, error handling, naming).
- **Bug Detection**: Logic errors, null handling, race conditions, memory leaks, security vulnerabilities, performance/power issues.
- **Code Quality**: Code duplication, missing critical error handling, inadequate test coverage for changed code.


**Confidence Scoring:**
Rate each potential issue on a scale from 0–100:
- **0**: Not confident at all. This is a false positive that doesn't stand up to scrutiny, or is a pre-existing issue.
- **25**: Somewhat confident. This might be a real issue, but may also be a false positive. If stylistic, it wasn't explicitly called out in project guidelines.
- **50**: Moderately confident. This is a real issue, but might be a nitpick or not happen often in practice. Not very important relative to the rest of the changes.
- **75**: Highly confident. Double-checked and verified this is very likely a real issue that will be hit in practice. The existing approach is insufficient. Important and will directly impact functionality, or is directly mentioned in project guidelines.
- **100**: Absolutely certain. Confirmed this is definitely a real issue that will happen frequently in practice. The evidence directly confirms this.

**Only report issues with confidence_score ≥ 80.** Focus on issues that truly matter — quality over quantity.

**Do NOT report:**
- Pre-existing issues, not-a-bug patterns, pedantic nitpicks
- Linter/typechecker/compiler violations (CI handles these)
- General code quality concerns unless explicitly required in CLAUDE.md
- Explicitly silenced issues (lint ignore comments)
- Likely intentional functionality changes

**FIRST: Read the diff file at `{{RUN_DIR}}/reviews/{{WORKSPACE_PATH}}-{{CHANGE_ID}}.diff` using the Read tool.** This is your primary input — review it thoroughly before proceeding to Phase 1.

**CHANGE PURPOSE (do this before reviewing):** After reading the diff, write a 1-2 sentence summary of what this change does and why it was made. Focus on the intent and scope, not individual line details. Use the Write tool to save it to `{{RUN_DIR}}/reviews/_purpose_{{CHANGE_ID}}.txt`. Example: "Introduces a serial_port_lock to fix a race condition between gserial connect/disconnect/suspend/resume paths. Also adds missing NULL pointer checks and corrects kernel log levels."

**Phase 1: Diff Review.** Review the diff you just read, identify changed lines. For each finding, read the actual source file from the workspace to verify context. Extract the code snippet at the reported line for both `original_code` and `reviewed_code`.

**Phase 2: Workspace Context Scan.** Only search within `{{WORKSPACE_DIR}}/{{WORKSPACE_PATH}}/` — never beyond. Only report where the change BREAKS existing callers. For concurrency, find all lock acquisitions but only report violations the change introduces.

**For large diffs (>2000 lines):** Focus on the most impactful and security-relevant files first.

**OUTPUT: Write findings to {{RUN_DIR}}/reviews/{{WORKSPACE_PATH}}-{{CHANGE_ID}}_findings.json using the Write tool.** Must also include a ```json code block in your response.

**Every finding MUST include ALL 13 fields. No field may be null, empty, or placeholder. change_id MUST be "{{CHANGE_ID}}" for EVERY finding.**

| # | Field | Type | Rule |
|---|-------|------|------|
| 1 | file | string | Relative path from project root (as seen in diff) |
| 2 | line | integer | Line number where the issue occurs |
| 3 | severity | enum | MUST be lowercase: "high", "medium", "low", or "info" |
| 4 | category | string | Security, Concurrency, Code Quality, Performance, Reliability |
| 5 | title | string | Short, specific title (max 80 chars) |
| 6 | description | string | Detailed explanation of the bug and its impact |
| 7 | suggested_fix | string | Concrete, actionable fix (1-2 sentences). Must NOT duplicate description. |
| 8 | original_code | string | The CURRENT code at the reported line (3-5 lines of real source code). This is what's there NOW — the code that has the bug. NEVER prose, description, or placeholder text. |
| 9 | reviewed_code | string | The PROPOSED FIX (3-5 lines of real source code). This is what the code SHOULD be after applying the fix. Must differ from original_code. |
| 10 | architectural_comment | string | Broader concerns, or "" if none |
| 11 | project | string | Full project path (e.g., kernel/common) |
| 12 | change_id | string | "{{CHANGE_ID}}" for EVERY finding |
| 13 | confidence_score | integer | 0-100 confidence score |

Example (note: both fields are real source code, 3-5 lines, showing current→fix):
{
  "file": "drivers/usb/gadget/udc.c", "line": 142, "severity": "high", "category": "Security",
  "title": "Buffer overflow in memcpy without bounds check",
  "description": "memcpy copies 'count' bytes without validating against BUFFER_SIZE, allowing a kernel heap overflow if count is attacker-controlled.",
  "suggested_fix": "Add a bounds check before memcpy and use the safe variant.",
  "original_code": "    if (!buf || !data)\n        return -EINVAL;\n    memcpy(buf, data, count);\n    return 0;",
  "reviewed_code": "    if (!buf || !data)\n        return -EINVAL;\n    if (count > BUFFER_SIZE)\n        return -EOVERFLOW;\n    memcpy(buf, data, count);\n    return 0;",
  "architectural_comment": "Consider a project-wide wrapper for bounded memcpy to prevent this class of bug.",
  "project": "kernel/common", "change_id": "1549963", "confidence_score": 95
}

**Code snippet rules (MANDATORY):**
- `original_code` = the CURRENT code at the reported line (what's there now, the buggy version). Extract from the workspace source file or diff NEW/+ side.
- `reviewed_code` = the PROPOSED FIX (what should replace it). Apply your fix to original_code.
- BOTH must be valid source code (3-5 lines). NEVER prose, descriptions, or placeholder text.
- They MUST differ from each other.
- `suggested_fix` MUST differ from `description`.
- Extract code directly from the workspace/diff — do NOT fabricate line numbers or code.

**SELF-VALIDATION (before output):** Verify all 13 fields are present, non-empty, correctly typed, original_code != reviewed_code, both look like real source code (not prose), and change_id/project match for every finding. Regenerate any failing finding before writing."""


def build_prompt(workspace_dir: str, project_name: str, workspace_path: str,
                 change_id: str, run_dir: str, diff_file: str | None = None) -> str:
    """Build the fully-substituted review prompt.

    The diff is NOT inlined — the prompt tells the agent to read it from disk.
    The diff_file parameter is kept for backward compatibility but unused.
    """
    prompt = REVIEW_PROMPT_TEMPLATE
    prompt = prompt.replace("{{WORKSPACE_DIR}}", workspace_dir)
    prompt = prompt.replace("{{PROJECT_NAME}}", project_name)
    prompt = prompt.replace("{{WORKSPACE_PATH}}", workspace_path)
    prompt = prompt.replace("{{CHANGE_ID}}", change_id)
    prompt = prompt.replace("{{RUN_DIR}}", run_dir)

    return prompt


def main():
    parser = argparse.ArgumentParser(description="Generate review agent prompt")
    parser.add_argument("--workspace-dir", required=True, help="Shared workspace root")
    parser.add_argument("--project-name", required=True, help="Project path (e.g., kernel/common)")
    parser.add_argument("--workspace-path", required=True, help="Workspace subdirectory (e.g., kernel_common)")
    parser.add_argument("--change-id", required=True, help="Gerrit change number")
    parser.add_argument("--run-dir", required=True, help="Per-run timestamped directory")
    parser.add_argument("--diff-file", default=None, help="Path to extracted diff")
    parser.add_argument("--output", default=None, help="Write prompt to file instead of stdout")
    args = parser.parse_args()

    prompt = build_prompt(
        workspace_dir=args.workspace_dir,
        project_name=args.project_name,
        workspace_path=args.workspace_path,
        change_id=args.change_id,
        run_dir=args.run_dir,
        diff_file=args.diff_file,
    )

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(prompt, encoding="utf-8")
        print(f"Prompt written to: {args.output}", file=sys.stderr)
    else:
        print(prompt)


if __name__ == "__main__":
    main()
