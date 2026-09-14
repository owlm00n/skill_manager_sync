"""generate_cross_project_validation_prompt.py -- Build validation prompt for cross-project findings.

This agent validates cross-project findings with access to ALL workspaces.

Usage:
  python scripts/generate_cross_project_validation_prompt.py <run_dir> [--output <path>]

Reads:
  <run_dir>/reviews/_cross_project_findings.json
  <run_dir>/change_summary.json
  <run_dir>/reviews/*.diff

Writes:
  Prompt to stdout or --output file.
  Agent writes results to <run_dir>/reviews/_verified_cross_project.json
"""

import sys
from pathlib import Path

CROSS_VALIDATION_TEMPLATE = r"""You are a cross-project validation agent.

You have access to ALL project workspaces under {{WORKSPACE_DIR}}/.
Use {{RUN_DIR}}/change_summary.json to resolve workspace paths for each project.

**FIRST: Read the cross-project findings to validate from `{{FINDINGS_FILE}}` using the Read tool.**

**SECOND: Read the cross-project index at `{{RUN_DIR}}/reviews/_cross_project_index.md`** (or `_cross_project_index.json` if the markdown index is missing). The index maps changed projects, files, signals, and likely provider/consumer edges. Use it to locate the relevant files for each finding.

**Do NOT read every raw diff upfront.** For each finding, open only the diffs and workspace source files needed to verify that specific interaction chain. Raw diffs are evidence files — open them after you identify which edge you are verifying.

**CROSS-PROJECT VALIDATION RULES (different from per-project rules):**

Cross-project findings are about the TOPIC's completeness across multiple projects, NOT about a single change's scope. The key question is: "Does the topic as a whole create a broken or incomplete state?"

Do NOT mark a finding INVALID just because:
- The gap "pre-existed" in a file not modified by any single change — the TOPIC may still be incomplete
- A change only modifies one platform's config — the topic may need to update other platforms too
- The finding references files outside any change's diff — cross-project bugs often involve files that SHOULD have been changed but weren't

DO mark a finding INVALID if:
- The interaction chain is contradicted by source code (e.g., the consumer does NOT actually depend on the provider)
- The provider scope actually covers the consumer scope (the finding misidentified a gap)
- The consumer and provider are in the same project with no cross-project aspect
- The finding is fabricated (the symbols/configs mentioned don't exist in the codebase)

DO mark a finding VALID if:
- The consumer project genuinely requires a dependency (module, config, API) that the provider project does not fully supply
- The topic changes the consumer to require something new, but the provider side is missing or incomplete
- The provider scope (platforms, build variants) does not cover the consumer scope

For each cross-project finding:
1. Verify the root cause exists in the root cause project's source code
2. Verify the impact exists in the related project's source code
3. Trace the interaction chain: does the root cause actually create a gap for the related code?
4. Check the PROVIDER scope vs CONSUMER scope: does the provider cover all platforms/variants the consumer needs?
5. Verify the finding is truly cross-project (spans 2+ projects)
6. **False positive filter — mark INVALID only if the interaction chain is contradicted by source, NOT if the gap is "pre-existing".**

Write results to {{RUN_DIR}}/reviews/_verified_cross_project.json as a pretty-printed JSON array.

**CRITICAL: Write to `_verified_cross_project.json`, NOT `verified_findings.json`.**

For each finding, output a dict with exactly these 10 fields:
- change_id: string, root cause change ID (copy from finding)
- file: string, root cause file (copy from finding)
- line: integer, root cause line number (copy from finding)
- title: string, finding title (copy from finding)
- cross_project: boolean, always true
- original_severity: string, severity from review agent
- verdict: string, one of VALID, PARTIAL, or INVALID
- confirmed_severity: string, your adjusted severity
- rationale: string, detailed explanation tracing the cross-project interaction chain
- related_changes: array, copy from finding

Verdicts:
- VALID: both root cause and impact verified, interaction chain confirmed
- PARTIAL: one side verified but the other is uncertain
- INVALID: root cause or impact not found, interaction chain contradicted, or false positive

**SELF-VALIDATION:** Verify all 10 fields present, cross_project is true, verdict is one of VALID/PARTIAL/INVALID.
"""


def build_cross_validation_prompt(run_dir: Path) -> str:
    """Build the cross-project validation prompt."""
    run_dir = run_dir.resolve()
    workspace_dir = str((run_dir.parent / "workspace").resolve())
    reviews_dir = run_dir / "reviews"

    findings_path = reviews_dir / "_cross_project_findings.json"

    prompt = CROSS_VALIDATION_TEMPLATE
    prompt = prompt.replace("{{WORKSPACE_DIR}}", workspace_dir)
    prompt = prompt.replace("{{RUN_DIR}}", str(run_dir))
    prompt = prompt.replace("{{FINDINGS_FILE}}", str(findings_path))

    return prompt


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_cross_project_validation_prompt.py <run_dir> [--output <path>]",
              file=sys.stderr)
        sys.exit(1)

    run_dir = Path(sys.argv[1]).resolve()
    output_path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--output" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]

    prompt = build_cross_validation_prompt(run_dir)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(prompt, encoding="utf-8")
        print(f"Cross-project validation prompt written to: {output_path}", file=sys.stderr)
    else:
        print(prompt)


if __name__ == "__main__":
    main()
