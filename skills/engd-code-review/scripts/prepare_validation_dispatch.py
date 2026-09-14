"""prepare_validation_dispatch.py -- Prepare per-change validation prompts for parallel agents.

Reads all_findings.json and change_summary.json, groups non-cross-project findings
by change_id, and generates per-group prompt files + a manifest.

Cross-project findings (cross_project: true) are excluded here and validated
only in Step 4.1 via generate_cross_project_validation_prompt.py.

Usage:
  python scripts/prepare_validation_dispatch.py <run_dir>

Input files (from <run_dir>):
  all_findings.json
  change_summary.json

Output files:
  <run_dir>/reviews/_validation_findings_<CHANGE_ID>.json  -- findings per change
  <run_dir>/reviews/_validation_prompt_<CHANGE_ID>.txt     -- instructions only
  <run_dir>/reviews/_validation_manifest.json              -- slim dispatch manifest
"""

import json
import sys
from pathlib import Path

from shared import (
    SUBAGENT_DISPATCH_FORBIDDEN,
    SUBAGENT_DISPATCH_RULES,
    SUBAGENT_REQUIRED_CAPABILITIES,
    SUBAGENT_SPAWN_OPTIONS,
    VALIDATION_RULES,
    build_validation_dispatch_prompt,
    ensure_cross_project_review_done,
    update_progress,
)

VALIDATION_TEMPLATE = r"""You are a finding validation agent for one Gerrit change.

**FIRST: Read the findings to validate from `{{FINDINGS_FILE}}` using the Read tool** ({{FINDING_COUNT}} finding(s) expected).

**SECOND: Read the diff file at `{{RUN_DIR}}/reviews/{{WS_PATH}}-{{CHANGE_ID}}.diff` using the Read tool.** You will need it to verify original_code snippets against the diff NEW (+) side.

For each finding in the findings file:
1. Each finding includes a `file` (source file relative to its project root) and a `change_id`.
2. Use {{RUN_DIR}}/change_summary.json to look up the workspace_path for the change_id, then resolve the source file under {{WORKSPACE_DIR}}/<workspace_path>.
3. Verify the file exists and the line number is valid
4. Check that original_code snippet matches the diff NEW (+) side — the change author's version
5. Reason about the logic claim - trace lock operations, verify error paths, check API contracts
6. Verify whether each finding's claim holds against the real source.
7. Additionally verify: is this a bug introduced or exposed by the change? If the claim is about a pre-existing bug untouched by the change, mark it INVALID (out of scope).
8. """ + VALIDATION_RULES + """

Write your results to {{RUN_DIR}}/reviews/_verified_{{CHANGE_ID}}.json as a pretty-printed JSON array (indent=2, one object per entry). The file MUST be written to this exact path. Do NOT write to any other location. Do NOT modify this file after writing.

**CRITICAL: Each validation agent writes to a DIFFERENT file (`_verified_{{CHANGE_ID}}.json`). Do NOT write to `verified_findings.json` — that file is created by `merge_validation_results.py` AFTER all agents complete. Two agents writing to the same file will overwrite each other's work.**

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

**CRITICAL: verified_findings.json is the merged output created by `merge_validation_results.py` AFTER all agents complete. Each agent writes only to `_verified_{{CHANGE_ID}}.json`. Do NOT write to verified_findings.json.**

**SELF-VALIDATION:** Before writing, verify every result in your JSON array has ALL 8 fields present and non-null. The change_id, file, line, and title fields MUST exactly match the original finding. Your output must be valid JSON - no markdown wrappers other than the required ```json code block."""


def prepare_dispatch(run_dir: Path):
    """Group findings by change_id and generate per-group prompts + manifest."""
    ensure_cross_project_review_done(run_dir, "validation dispatch (Step 4b)")

    all_findings_path = run_dir / "all_findings.json"
    change_summary_path = run_dir / "change_summary.json"
    reviews_dir = run_dir / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)

    if not all_findings_path.is_file():
        print(f"Error: {all_findings_path} not found", file=sys.stderr)
        sys.exit(1)
    if not change_summary_path.is_file():
        print(f"Error: {change_summary_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(all_findings_path, encoding="utf-8") as f:
        all_findings = json.load(f)
    with open(change_summary_path, encoding="utf-8") as f:
        change_summary = json.load(f)

    change_map = {}
    for c in change_summary:
        change_map[str(c["change_id"])] = {
            "project": c["project"],
            "workspace_path": c["workspace_path"],
            "branch": c.get("branch", ""),
        }

    cross_project_findings = [f for f in all_findings if f.get("cross_project")]
    per_change_findings = [f for f in all_findings if not f.get("cross_project")]

    groups = {}
    for finding in per_change_findings:
        cid = str(finding.get("change_id", ""))
        if cid not in groups:
            groups[cid] = []
        groups[cid].append(finding)

    sorted_keys = sorted(
        groups.keys(),
        key=lambda x: int(x) if x.isdigit() else x,
    )

    workspace_dir = str((run_dir.parent / "workspace").resolve())
    run_dir_abs = str(run_dir.resolve())

    manifest_groups = []
    total_findings_bytes = 0
    total_prompt_bytes = 0

    for gi, cid in enumerate(sorted_keys):
        group_findings = groups[cid]
        cm = change_map.get(cid, {})
        ws_path = cm.get("workspace_path", "")
        project = cm.get("project", "")

        findings_file = reviews_dir / f"_validation_findings_{cid}.json"
        with open(findings_file, "w", encoding="utf-8") as f:
            json.dump(group_findings, f, indent=2, ensure_ascii=False)
            f.write("\n")
        total_findings_bytes += findings_file.stat().st_size

        prompt = VALIDATION_TEMPLATE
        prompt = prompt.replace("{{WORKSPACE_DIR}}", workspace_dir)
        prompt = prompt.replace("{{RUN_DIR}}", run_dir_abs)
        prompt = prompt.replace("{{CHANGE_ID}}", cid)
        prompt = prompt.replace("{{WS_PATH}}", ws_path)
        prompt = prompt.replace("{{FINDINGS_FILE}}", str(findings_file))
        prompt = prompt.replace("{{FINDING_COUNT}}", str(len(group_findings)))

        prompt_file = reviews_dir / f"_validation_prompt_{cid}.txt"
        prompt_file.write_text(prompt, encoding="utf-8")
        total_prompt_bytes += prompt_file.stat().st_size

        output_path = reviews_dir / f"_verified_{cid}.json"

        manifest_groups.append({
            "group_id": gi,
            "change_id": cid,
            "workspace_path": ws_path,
            "project": project,
            "description": f"Validate findings: change {cid} ({project})",
            "finding_count": len(group_findings),
            "findings_file": str(findings_file),
            "output_path": str(output_path),
            "prompt_file": str(prompt_file),
            "dispatch_prompt": build_validation_dispatch_prompt(str(prompt_file), str(output_path)),
        })

    verify_cmd = f"python scripts/verify_dispatch.py {run_dir_abs} --type validation"

    manifest = {
        "run_dir": run_dir_abs,
        "workspace_dir": workspace_dir,
        "groups": manifest_groups,
        "group_count": len(manifest_groups),
        "total_findings": len(all_findings),
        "per_change_findings": len(per_change_findings),
        "cross_project_findings": len(cross_project_findings),
        "subagent_role": "finding_validation",
        "worktree_isolation": False,
        "spawn_options": SUBAGENT_SPAWN_OPTIONS,
        "required_capabilities": SUBAGENT_REQUIRED_CAPABILITIES,
        "forbidden": SUBAGENT_DISPATCH_FORBIDDEN,
        "dispatch_instruction": (
            f"Dispatch ALL {len(manifest_groups)} validation subagents in one parallel batch. "
            "Pass each group's dispatch_prompt — subagents read prompt_file and findings_file on disk. "
            f"{SUBAGENT_DISPATCH_RULES}"
            if manifest_groups
            else "No per-change validation subagents needed. Cross-project findings are validated in Step 4.1."
        ),
        "verify_command": verify_cmd if manifest_groups else "",
    }

    manifest_file = reviews_dir / "_validation_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    manifest_bytes = manifest_file.stat().st_size

    print(f"Prepared {len(manifest_groups)} validation group(s) for {len(per_change_findings)} per-change finding(s)")
    if cross_project_findings:
        print(f"Excluded {len(cross_project_findings)} cross-project finding(s) — validated in Step 4.1 only")
    print(
        f"Manifest: {manifest_file} ({manifest_bytes:,} bytes; "
        f"prompts: {total_prompt_bytes:,} bytes; findings: {total_findings_bytes:,} bytes on disk)"
    )
    for g in manifest_groups:
        print(
            f"  Group {g['group_id']}: change #{g['change_id']} "
            f"({g['project']}) -- {g['finding_count']} finding(s)"
        )
    print()
    print(f"=" * 60)
    if manifest_groups:
        print(f"DISPATCH INSTRUCTION: {len(manifest_groups)} validation subagent(s) ready.")
        print(f"SUBAGENT_ROLE=finding_validation")
        print(f"ISOLATION=omit  (do not pass isolation param — only 'worktree' is valid if set)")
        print(f"Dispatch ALL {len(manifest_groups)} subagents in parallel — pass each group's dispatch_prompt.")
        print(f"After spawn: python scripts/record_dispatch.py {run_dir_abs} --type validation --action start")
        print(f"Then wait:  python scripts/wait_for_dispatch.py {run_dir_abs} --type validation")
        print(f"Then verify: {verify_cmd}")
        print(f"On timeout: python scripts/prepare_redispatch.py {run_dir_abs} --type validation")
    else:
        print("DISPATCH INSTRUCTION: Skip Step 4c (no per-change findings to validate).")
        if cross_project_findings:
            print(">>> Proceed to Step 4.1 for cross-project validation.")
    print(f"=" * 60)
    update_progress(run_dir, "validation_dispatch")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/prepare_validation_dispatch.py <run_dir>", file=sys.stderr)
        sys.exit(1)

    run_dir = Path(sys.argv[1]).resolve()
    if not run_dir.is_dir():
        print(f"Error: '{sys.argv[1]}' is not a directory", file=sys.stderr)
        sys.exit(1)

    prepare_dispatch(run_dir)


if __name__ == "__main__":
    main()
