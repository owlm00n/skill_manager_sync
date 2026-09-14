"""prepare_review_dispatch.py -- Generate a review dispatch manifest.

Reads change_summary.json, generates review prompts for ALL changes, and
writes a single manifest JSON file. The orchestrator reads this manifest
and dispatches ALL agents in one batch — no per-change decisions needed.

Usage:
  python scripts/prepare_review_dispatch.py <run_dir>

Output:
  <run_dir>/reviews/_review_manifest.json

The manifest contains short dispatch_prompt bootstraps plus prompt_file paths.
Full review instructions live in reviews/_review_prompt_<id>.txt (not inlined in JSON).
"""

import json
import sys
from pathlib import Path

from shared import (
    SUBAGENT_DISPATCH_FORBIDDEN,
    SUBAGENT_DISPATCH_RULES,
    SUBAGENT_REQUIRED_CAPABILITIES,
    SUBAGENT_SPAWN_OPTIONS,
    build_review_dispatch_prompt,
    load_json_safe,
    update_progress,
)


def prepare_dispatch(run_dir: Path):
    """Generate review prompts for all changes and write a dispatch manifest."""
    run_dir = run_dir.resolve()
    change_summary_path = run_dir / "change_summary.json"
    reviews_dir = run_dir / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)

    if not change_summary_path.is_file():
        print(f"Error: {change_summary_path} not found", file=sys.stderr)
        sys.exit(1)

    change_summary = load_json_safe(str(change_summary_path))

    workspace_dir = str((run_dir.parent / "workspace").resolve())
    run_dir_abs = str(run_dir)

    # Import the prompt builder
    from generate_review_prompt import build_prompt

    agents = []
    for entry in change_summary:
        project = entry["project"]
        change_id = str(entry["change_id"])
        workspace_path = entry["workspace_path"]

        diff_file = reviews_dir / f"{workspace_path}-{change_id}.diff"
        prompt = build_prompt(
            workspace_dir=workspace_dir,
            project_name=project,
            workspace_path=workspace_path,
            change_id=change_id,
            run_dir=run_dir_abs,
            diff_file=str(diff_file) if diff_file.is_file() else None,
        )

        # Also write individual prompt file for debugging
        prompt_file = reviews_dir / f"_review_prompt_{change_id}.txt"
        prompt_file.write_text(prompt, encoding="utf-8")

        findings_output = f"{workspace_path}-{change_id}_findings.json"
        output_path = reviews_dir / findings_output

        agents.append({
            "change_id": change_id,
            "project": project,
            "workspace_path": workspace_path,
            "description": f"Code review: change {change_id} ({project})",
            "dispatch_prompt": build_review_dispatch_prompt(str(prompt_file), str(output_path)),
            "findings_output": findings_output,
            "output_path": str(output_path),
            "prompt_file": str(prompt_file),
            "subagent_scope": "single_change",
        })

    # Count unique projects
    unique_projects = set(a["project"] for a in agents)
    project_count = len(unique_projects)

    verify_cmd = f"python scripts/verify_dispatch.py {run_dir_abs} --type review"

    manifest = {
        "run_dir": run_dir_abs,
        "workspace_dir": workspace_dir,
        "agent_count": len(agents),
        "change_count": len(agents),
        "one_subagent_per_change": True,
        "project_count": project_count,
        "subagent_role": "code_review",
        "worktree_isolation": False,
        "spawn_options": SUBAGENT_SPAWN_OPTIONS,
        "required_capabilities": SUBAGENT_REQUIRED_CAPABILITIES,
        "agents": agents,
        "dispatch_instruction": (
            f"Dispatch exactly {len(agents)} subagents — one per change, all in one parallel launch. "
            f"{SUBAGENT_DISPATCH_RULES}"
        ),
        "forbidden": SUBAGENT_DISPATCH_FORBIDDEN,
        "verify_command": verify_cmd,
    }

    manifest_path = reviews_dir / "_review_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    manifest_bytes = manifest_path.stat().st_size
    prompt_bytes = sum(
        Path(a["prompt_file"]).stat().st_size
        for a in agents
        if Path(a["prompt_file"]).is_file()
    )

    # Print prominent dispatch instruction as the LAST output
    print(f"Prepared review manifest with {len(agents)} agent(s)")
    print(f"Manifest: {manifest_path} ({manifest_bytes:,} bytes; prompts on disk: {prompt_bytes:,} bytes)")
    for a in agents:
        print(f"  Change #{a['change_id']} ({a['project']}) -> {a['findings_output']}")
    print()
    print(f"=" * 60)
    print(f"DISPATCH INSTRUCTION: {len(agents)} subagent(s) for {len(agents)} change(s) — 1:1 mapping.")
    print(f"SUBAGENT_ROLE=code_review")
    print(f"ISOLATION=omit  (do not pass isolation param — only 'worktree' is valid if set)")
    print(f"Read {manifest_path} and spawn exactly {len(agents)} subagents in parallel.")
    print(f"FORBIDDEN: merging multiple changes into one subagent.")
    print(f"Each subagent: one manifest entry, dispatch_prompt bootstrap, reads prompt_file, one output_path.")
    print(f"After spawn: python scripts/record_dispatch.py {run_dir_abs} --type review --action start")
    print(f"Then wait:  python scripts/wait_for_dispatch.py {run_dir_abs} --type review")
    print(f"Then verify: {verify_cmd}")
    print(f"On missing output: wait for batch to finish, then re-dispatch failed subagents only — do NOT redispatch while still running; do NOT review inline in parent.")
    print()
    print(f"PROJECT_COUNT={project_count}")
    if project_count > 1:
        print(f">>> MULTI-PROJECT: Run Step 3.1 (cross-project review) after dispatch.")
        print(f">>> Do NOT skip Step 3.1 even if per-project agents return 0 findings.")
        print(f">>> Cross-project bugs are invisible to per-project agents.")
    else:
        print(f">>> SINGLE PROJECT: Skip Step 3.1 (cross-project review).")
    print(f"=" * 60)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/prepare_review_dispatch.py <run_dir>", file=sys.stderr)
        sys.exit(1)

    run_dir = Path(sys.argv[1]).resolve()
    if not run_dir.is_dir():
        print(f"Error: '{sys.argv[1]}' is not a directory", file=sys.stderr)
        sys.exit(1)

    prepare_dispatch(run_dir)


if __name__ == "__main__":
    main()
