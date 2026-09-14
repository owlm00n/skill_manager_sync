#!/usr/bin/env python
"""generate_validation_prompt.py -- Build the agent prompt for the adversarial validation agent.

Usage:
  python scripts/generate_validation_prompt.py \\
      --workspace-dir <path> \\
      --run-dir <path>

Prints the validation prompt to stdout.
"""

import argparse
import sys

from shared import VALIDATION_RULES

VALIDATION_PROMPT_TEMPLATE = r"""Read all_findings.json from {{RUN_DIR}}/all_findings.json.

**FIRST: Read the relevant diff files from {{RUN_DIR}}/reviews/*.diff using the Read tool.** You will need them to verify original_code snippets against the diff NEW (+) side.

For each finding:
1. Each finding includes a `file` (source file relative to its project root) and `change_id`. Use `change_summary.json` from {{RUN_DIR}} to look up the workspace_path for the change_id, then resolve the source file under {{WORKSPACE_DIR}}/<workspace_path>.
2. Verify the file exists and the line number is valid
3. Check that original_code snippet matches the diff NEW (+) side — the change author's version
4. Reason about the logic claim - trace lock operations, verify error paths, check API contracts
5. Verify whether each finding's claim holds against the real source.
6. Additionally verify: is this a bug introduced or exposed by the change? If the claim is about a pre-existing bug untouched by the change, mark it INVALID (out of scope).
7. """ + VALIDATION_RULES + """

Write your results to a file at {{RUN_DIR}}/reviews/_verified_{CHANGE_ID}.json as a pretty-printed JSON array (indent=2, one object per entry).

**You MUST use the Write tool to persist the file.**

For each finding, output a dict with exactly these 8 fields:
- change_id: string, the Gerrit change number (copy from the finding)
- file: string, source file path (copy from the finding)
- line: integer, line number (copy from the finding)
- title: string, title from the finding (copy from the finding)
- original_severity: string, severity from review agents (high/medium/low/info)
- verdict: string, one of VALID, PARTIAL, or INVALID
- confirmed_severity: string, high/medium/low/info — your adjusted severity, may be less than original
- rationale: string, detailed explanation with actual line numbers and code snippets

Verdicts:
- VALID: claim holds, file/line/snippet found, and the bug is change-related
- PARTIAL: partially supported by source code or subjective judgment
- INVALID: file not found, claim contradicted by source, out of scope, false positive per rules above, or confidence_score < 80

**SELF-VALIDATION:** Before writing, verify every result has ALL 8 fields present and non-null. The change_id, file, line, and title MUST exactly match the original finding."""


def build_prompt(workspace_dir: str, run_dir: str) -> str:
    """Build the fully-substituted validation prompt."""
    prompt = VALIDATION_PROMPT_TEMPLATE
    prompt = prompt.replace("{{WORKSPACE_DIR}}", workspace_dir)
    prompt = prompt.replace("{{RUN_DIR}}", run_dir)
    return prompt


def main():
    parser = argparse.ArgumentParser(description="Generate validation agent prompt")
    parser.add_argument("--workspace-dir", required=True, help="Shared workspace root")
    parser.add_argument("--run-dir", required=True, help="Per-run timestamped directory")
    parser.add_argument("--output", default=None, help="Write prompt to file instead of stdout")
    args = parser.parse_args()

    prompt = build_prompt(
        workspace_dir=args.workspace_dir,
        run_dir=args.run_dir,
    )

    if args.output:
        from pathlib import Path
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(prompt, encoding="utf-8")
        print(f"Prompt written to: {args.output}", file=sys.stderr)
    else:
        print(prompt)


if __name__ == "__main__":
    main()
