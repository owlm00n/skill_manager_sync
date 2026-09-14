"""prepare_cross_project_dispatch.py -- Cross-project review prompt + dispatch manifest.

Step 3.1 must dispatch exactly ONE subagent that reviews ALL changes together.
Writes prompt file and _cross_project_manifest.json so the orchestrator cannot
split work into per-change or per-project batches.

Usage:
  python scripts/prepare_cross_project_dispatch.py <run_dir>
"""

import json
import sys
from pathlib import Path

from prepare_cross_project_index import write_cross_project_index
from generate_cross_project_prompt import build_cross_project_prompt
from shared import (
    CROSS_PROJECT_DISPATCH_FORBIDDEN,
    SUBAGENT_DISPATCH_FORBIDDEN,
    SUBAGENT_DISPATCH_RULES,
    SUBAGENT_REQUIRED_CAPABILITIES,
    SUBAGENT_SPAWN_OPTIONS,
    get_project_count,
    load_json_safe,
)


def prepare_cross_project_dispatch(run_dir: Path) -> None:
    run_dir = run_dir.resolve()
    change_summary_path = run_dir / "change_summary.json"
    reviews_dir = run_dir / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)

    if not change_summary_path.is_file():
        print(f"Error: {change_summary_path} not found", file=sys.stderr)
        sys.exit(1)

    changes = load_json_safe(str(change_summary_path))
    change_count = len(changes)
    project_count = get_project_count(run_dir)
    if project_count <= 1:
        print(f"SKIP: PROJECT_COUNT={project_count} — cross-project review not needed.")
        return

    workspace_dir = str((run_dir.parent / "workspace").resolve())
    run_dir_abs = str(run_dir)
    index_json_path, index_md_path = write_cross_project_index(run_dir)
    prompt = build_cross_project_prompt(run_dir)

    prompt_file = reviews_dir / "_cross_project_prompt.txt"
    prompt_file.write_text(prompt, encoding="utf-8")

    output_path = reviews_dir / "_cross_project_findings.json"
    record_cmd = f"python scripts/record_dispatch.py {run_dir_abs} --type cross-review --action start"
    wait_cmd = f"python scripts/wait_for_dispatch.py {run_dir_abs} --type cross-review"
    verify_cmd = f"python scripts/verify_dispatch.py {run_dir_abs} --type cross-review"

    change_ids = [str(c["change_id"]) for c in changes]
    manifest = {
        "run_dir": run_dir_abs,
        "workspace_dir": workspace_dir,
        "subagent_role": "cross_project_review",
        "agent_count": 1,
        "change_count": change_count,
        "project_count": project_count,
        "change_ids": change_ids,
        "worktree_isolation": False,
        "spawn_options": SUBAGENT_SPAWN_OPTIONS,
        "required_capabilities": SUBAGENT_REQUIRED_CAPABILITIES,
        "index_json": str(index_json_path),
        "index_markdown": str(index_md_path),
        "prompt_file": str(prompt_file),
        "output_path": str(output_path),
        "dispatch_instruction": (
            f"Dispatch exactly ONE cross-project review subagent for all {change_count} changes "
            f"across {project_count} projects. Do NOT split by change groups or projects. "
            f"{SUBAGENT_DISPATCH_RULES}"
        ),
        "forbidden": CROSS_PROJECT_DISPATCH_FORBIDDEN + SUBAGENT_DISPATCH_FORBIDDEN,
        "record_command": record_cmd,
        "wait_command": wait_cmd,
        "verify_command": verify_cmd,
    }

    manifest_path = reviews_dir / "_cross_project_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Cross-project prompt: {prompt_file}")
    print(f"Cross-project index JSON: {index_json_path}")
    print(f"Cross-project index Markdown: {index_md_path}")
    print(f"Manifest: {manifest_path}")
    print(f"Changes: {change_count} across {project_count} projects")
    print(f"Change IDs: {', '.join(change_ids)}")
    print()
    print("=" * 60)
    print("DISPATCH INSTRUCTION: exactly 1 cross-project subagent for ALL changes.")
    print("SUBAGENT_ROLE=cross_project_review")
    print("ISOLATION=omit  (do not pass isolation param)")
    print(f"Read {manifest_path} — use prompt_file, write to output_path only.")
    print("FORBIDDEN: review change A+B+C batches; one agent per project; multiple agents.")
    print(f"After spawn: {record_cmd}")
    print(f"Then wait:  {wait_cmd}")
    print(f"Then verify: {verify_cmd}")
    print("On missing output: wait for the cross-review batch to finish, then redispatch once only if needed.")
    print("=" * 60)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/prepare_cross_project_dispatch.py <run_dir>", file=sys.stderr)
        sys.exit(1)

    run_dir = Path(sys.argv[1]).resolve()
    if not run_dir.is_dir():
        print(f"Error: '{sys.argv[1]}' is not a directory", file=sys.stderr)
        sys.exit(1)

    prepare_cross_project_dispatch(run_dir)


if __name__ == "__main__":
    main()
