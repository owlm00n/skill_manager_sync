"""verify_dispatch.py -- Verify all dispatched agents produced output files.

Checks that every agent listed in the manifest produced its expected output file.
Prints a clear pass/fail report.

Usage:
  python scripts/verify_dispatch.py <run_dir> [--type review|validation]

Examples:
  python scripts/verify_dispatch.py <run_dir> --type review
  python scripts/verify_dispatch.py <run_dir> --type validation
"""

import json
import os
import sys
from pathlib import Path

from shared import get_project_count, cross_project_review_path, update_progress
from dispatch_utils import check_outputs, load_ledger


def verify_review_dispatch(run_dir: Path) -> tuple[bool, list[str]]:
    """Check all review agents produced findings files."""
    manifest_path = run_dir / "reviews" / "_review_manifest.json"
    if not manifest_path.is_file():
        return False, [f"Manifest not found: {manifest_path}"]

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    reviews_dir = run_dir / "reviews"
    expected = manifest.get("agent_count", 0)
    missing = []
    found = []

    for agent in manifest.get("agents", []):
        output_file = reviews_dir / agent["findings_output"]
        if output_file.is_file():
            found.append(agent["findings_output"])
        else:
            missing.append(agent["findings_output"])

    errors = []
    if missing:
        errors.append(f"Missing {len(missing)}/{expected} findings file(s):")
        for m in missing:
            errors.append(f"  - {m}")
    if found:
        errors.insert(0, f"Found {len(found)}/{expected} findings file(s)")

    return len(missing) == 0, errors


def verify_validation_dispatch(run_dir: Path) -> tuple[bool, list[str]]:
    """Check all validation agents produced verified files."""
    manifest_path = run_dir / "reviews" / "_validation_manifest.json"
    if not manifest_path.is_file():
        return False, [f"Manifest not found: {manifest_path}"]

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    reviews_dir = run_dir / "reviews"
    groups = manifest.get("groups", [])
    expected = len(groups)
    missing = []
    found = []

    for group in groups:
        cid = group["change_id"]
        output_file = reviews_dir / f"_verified_{cid}.json"
        if output_file.is_file():
            found.append(f"_verified_{cid}.json")
        else:
            missing.append(f"_verified_{cid}.json")

    errors = []
    if missing:
        errors.append(f"Missing {len(missing)}/{expected} verified file(s):")
        for m in missing:
            errors.append(f"  - {m}")
    if found:
        errors.insert(0, f"Found {len(found)}/{expected} verified file(s)")

    return len(missing) == 0, errors


def verify_cross_review(run_dir: Path) -> tuple[bool, list[str]]:
    """Check that the cross-project review agent produced output."""
    output = run_dir / "reviews" / "_cross_project_findings.json"
    if output.is_file():
        return True, ["Cross-project findings found: _cross_project_findings.json"]
    return False, ["Missing: _cross_project_findings.json"]


def verify_cross_validation(run_dir: Path) -> tuple[bool, list[str]]:
    """Check that the cross-project validation agent produced output."""
    output = run_dir / "reviews" / "_verified_cross_project.json"
    if output.is_file():
        return True, ["Cross-project verified results found: _verified_cross_project.json"]
    return False, ["Missing: _verified_cross_project.json"]


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_dispatch.py <run_dir> [--type review|validation|cross-review|cross-validation]",
              file=sys.stderr)
        sys.exit(1)

    run_dir = Path(sys.argv[1]).resolve()
    dispatch_type = "review"
    for i, arg in enumerate(sys.argv):
        if arg == "--type" and i + 1 < len(sys.argv):
            dispatch_type = sys.argv[i + 1]

    if dispatch_type == "review":
        ok, messages = verify_review_dispatch(run_dir)
    elif dispatch_type == "validation":
        ok, messages = verify_validation_dispatch(run_dir)
    elif dispatch_type == "cross-review":
        ok, messages = verify_cross_review(run_dir)
    elif dispatch_type == "cross-validation":
        ok, messages = verify_cross_validation(run_dir)
    else:
        print(f"Unknown type: {dispatch_type}. Use 'review', 'validation', 'cross-review', or 'cross-validation'.", file=sys.stderr)
        sys.exit(1)

    for msg in messages:
        print(msg)

    if ok:
        print(f"\nPASS: All {dispatch_type} agents completed successfully.")
        if dispatch_type == "review":
            project_count = get_project_count(run_dir)
            if project_count > 1 and not cross_project_review_path(run_dir).is_file():
                print()
                print("!" * 60)
                print(f"NEXT REQUIRED: Step 3.1 — cross-project review (PROJECT_COUNT={project_count})")
                print("Missing: reviews/_cross_project_findings.json")
                print("Do NOT run consolidate (Step 3.5) or validation (Step 4) yet.")
                print("!" * 60)
        elif dispatch_type == "cross-review":
            update_progress(run_dir, "cross_project_review")
    else:
        print(f"\nFAIL: Some {dispatch_type} agents did not produce output.")
        ledger = load_ledger(run_dir).get(dispatch_type, {})
        if ledger.get("status") == "in_flight":
            print(f"Ledger: batch #{ledger.get('batch_id')} is IN_FLIGHT — subagents may still be running.")
            print("DO NOT re-dispatch. DO NOT use Continue/resume agents.")
            print("Task polling errors (e.g. 'No task found with ID') mean WAIT, not re-dispatch.")
            print(f"NEXT: python scripts/wait_for_dispatch.py \"{run_dir}\" --type {dispatch_type}")
        else:
            print("Wait until every subagent from the original batch has finished.")
            print(f"NEXT: python scripts/wait_for_dispatch.py \"{run_dir}\" --type {dispatch_type}")
            print("If wait times out: python scripts/prepare_redispatch.py "
                  f"\"{run_dir}\" --type {dispatch_type}")
        print("Then re-dispatch ONLY missing units from the redispatch manifest (never duplicates).")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
