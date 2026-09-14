"""dispatch_utils.py — Shared dispatch status, ledger, and output checks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from claude_code_utils import resolve_claude_session_dir
from shared import load_json_safe

DISPATCH_TYPES = ("review", "validation", "cross-review", "cross-validation")

LEDGER_FILE = "_dispatch_ledger.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ledger_path(run_dir: Path) -> Path:
    return run_dir / "reviews" / LEDGER_FILE


def load_ledger(run_dir: Path) -> dict[str, Any]:
    path = ledger_path(run_dir)
    if not path.is_file():
        return {}
    return load_json_safe(str(path))


def save_ledger(run_dir: Path, ledger: dict[str, Any]) -> None:
    path = ledger_path(run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _review_units(run_dir: Path) -> list[dict[str, Any]]:
    manifest_path = run_dir / "reviews" / "_review_manifest.json"
    manifest = load_json_safe(str(manifest_path))
    reviews_dir = run_dir / "reviews"
    units = []
    for agent in manifest.get("agents", []):
        output_name = agent["findings_output"]
        units.append({
            "unit_id": str(agent["change_id"]),
            "change_id": str(agent["change_id"]),
            "project": agent.get("project", ""),
            "output_path": str(reviews_dir / output_name),
            "output_name": output_name,
            "dispatch_prompt": agent.get("dispatch_prompt", ""),
            "description": agent.get("description", ""),
            "prompt_file": agent.get("prompt_file", ""),
        })
    return units


def _validation_units(run_dir: Path) -> list[dict[str, Any]]:
    manifest_path = run_dir / "reviews" / "_validation_manifest.json"
    manifest = load_json_safe(str(manifest_path))
    reviews_dir = run_dir / "reviews"
    units = []
    for group in manifest.get("groups", []):
        cid = str(group["change_id"])
        output_name = f"_verified_{cid}.json"
        units.append({
            "unit_id": cid,
            "change_id": cid,
            "project": group.get("project", ""),
            "output_path": str(reviews_dir / output_name),
            "output_name": output_name,
            "dispatch_prompt": group.get("dispatch_prompt", ""),
            "description": group.get("description", ""),
            "prompt_file": group.get("prompt_file", ""),
            "findings_file": group.get("findings_file", ""),
        })
    return units


def _single_output_unit(run_dir: Path, output_name: str, unit_id: str, description: str) -> list[dict[str, Any]]:
    reviews_dir = run_dir / "reviews"
    output_path = reviews_dir / output_name
    return [{
        "unit_id": unit_id,
        "change_id": unit_id,
        "project": "",
        "output_path": str(output_path),
        "output_name": output_name,
        "description": description,
    }]


def get_units(run_dir: Path, dispatch_type: str) -> list[dict[str, Any]]:
    run_dir = run_dir.resolve()
    if dispatch_type == "review":
        return _review_units(run_dir)
    if dispatch_type == "validation":
        return _validation_units(run_dir)
    if dispatch_type == "cross-review":
        return _single_output_unit(
            run_dir,
            "_cross_project_findings.json",
            "cross_project_review",
            "Cross-project review",
        )
    if dispatch_type == "cross-validation":
        return _single_output_unit(
            run_dir,
            "_verified_cross_project.json",
            "cross_project_validation",
            "Cross-project validation",
        )
    raise ValueError(f"Unknown dispatch type: {dispatch_type}")


def check_outputs(run_dir: Path, dispatch_type: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (found_units, missing_units)."""
    found: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for unit in get_units(run_dir, dispatch_type):
        if Path(unit["output_path"]).is_file():
            found.append(unit)
        else:
            missing.append(unit)
    return found, missing


def start_batch(run_dir: Path, dispatch_type: str, batch_kind: str = "initial") -> dict[str, Any]:
    """Record a new in-flight dispatch batch. Raises if batch already in flight."""
    run_dir = run_dir.resolve()
    ledger = load_ledger(run_dir)
    entry = ledger.get(dispatch_type, {})
    if entry.get("status") == "in_flight":
        raise RuntimeError(
            f"{dispatch_type} batch #{entry.get('batch_id')} is still in_flight. "
            "Run wait_for_dispatch.py before starting another batch."
        )

    units = get_units(run_dir, dispatch_type)
    batch_id = int(entry.get("batch_id", 0)) + 1
    now = _utc_now()
    claude_session_dir = resolve_claude_session_dir()
    batch = {
        "batch_id": batch_id,
        "batch_kind": batch_kind,
        "status": "in_flight",
        "started_at": now,
        "completed_at": None,
        "expected_count": len(units),
        "claude_session_dir": str(claude_session_dir) if claude_session_dir else None,
        "units": [
            {
                "unit_id": u["unit_id"],
                "change_id": u.get("change_id", u["unit_id"]),
                "output_name": u["output_name"],
                "dispatched_at": now,
                "completed_at": None,
            }
            for u in units
        ],
    }
    ledger[dispatch_type] = batch
    save_ledger(run_dir, ledger)
    return batch


def mark_batch_complete(run_dir: Path, dispatch_type: str) -> None:
    ledger = load_ledger(run_dir)
    entry = ledger.get(dispatch_type)
    if not entry:
        return
    now = _utc_now()
    entry["status"] = "complete"
    entry["completed_at"] = now
    found, missing = check_outputs(run_dir, dispatch_type)
    completed_ids = {u["unit_id"] for u in found}
    for unit in entry.get("units", []):
        if unit["unit_id"] in completed_ids:
            unit["completed_at"] = now
    entry["missing_count"] = len(missing)
    save_ledger(run_dir, ledger)


def redispatch_allowed(run_dir: Path, dispatch_type: str) -> tuple[bool, str]:
    """Return whether the orchestrator may spawn a redispatch batch."""
    ledger = load_ledger(run_dir)
    entry = ledger.get(dispatch_type)
    if not entry:
        return False, "No dispatch ledger entry — run record_dispatch.py --action start after spawning."
    if entry.get("status") == "in_flight":
        return False, (
            f"Batch #{entry.get('batch_id')} is still in_flight. "
            "Run wait_for_dispatch.py and do NOT spawn subagents."
        )
    found, missing = check_outputs(run_dir, dispatch_type)
    if not missing:
        return False, "All outputs already exist — run verify_dispatch.py instead of redispatching."
    return True, f"{len(missing)} unit(s) still missing after batch completed."


def build_redispatch_manifest(run_dir: Path, dispatch_type: str) -> dict[str, Any] | None:
    """Build a manifest containing ONLY units with missing outputs."""
    allowed, reason = redispatch_allowed(run_dir, dispatch_type)
    if not allowed:
        raise RuntimeError(reason)

    _, missing = check_outputs(run_dir, dispatch_type)
    missing_ids = {u["unit_id"] for u in missing}
    run_dir_abs = str(run_dir.resolve())

    if dispatch_type == "review":
        manifest = load_json_safe(str(run_dir / "reviews" / "_review_manifest.json"))
        agents = [a for a in manifest.get("agents", []) if str(a["change_id"]) in missing_ids]
        return {
            "run_dir": run_dir_abs,
            "dispatch_type": dispatch_type,
            "batch_kind": "redispatch",
            "agent_count": len(agents),
            "agents": agents,
            "forbidden": [
                "Dispatching units whose output files already exist",
                "Using Continue/resume on in-flight agents",
                "Spawning agents while ledger status is in_flight",
            ],
            "dispatch_instruction": (
                f"REDISPATCH ONLY: spawn exactly {len(agents)} subagent(s) listed below. "
                f"Do NOT touch units that already wrote output files."
            ),
        }

    if dispatch_type == "validation":
        manifest = load_json_safe(str(run_dir / "reviews" / "_validation_manifest.json"))
        groups = [g for g in manifest.get("groups", []) if str(g["change_id"]) in missing_ids]
        return {
            "run_dir": run_dir_abs,
            "dispatch_type": dispatch_type,
            "batch_kind": "redispatch",
            "group_count": len(groups),
            "groups": groups,
            "forbidden": [
                "Dispatching units whose output files already exist",
                "Using Continue/resume on in-flight agents",
                "Spawning agents while ledger status is in_flight",
            ],
            "dispatch_instruction": (
                f"REDISPATCH ONLY: spawn exactly {len(groups)} validation subagent(s) listed below."
            ),
        }

    if dispatch_type == "cross-review":
        manifest = load_json_safe(str(run_dir / "reviews" / "_cross_project_manifest.json"))
        manifest = dict(manifest)
        manifest["batch_kind"] = "redispatch"
        manifest["dispatch_instruction"] = "REDISPATCH ONLY: one cross-project review subagent."
        return manifest

    if dispatch_type == "cross-validation":
        return {
            "run_dir": run_dir_abs,
            "dispatch_type": dispatch_type,
            "batch_kind": "redispatch",
            "agent_count": 1,
            "prompt_file": str(run_dir / "reviews" / "_cross_project_validation_prompt.txt"),
            "output_path": str(run_dir / "reviews" / "_verified_cross_project.json"),
            "dispatch_instruction": "REDISPATCH ONLY: one cross-project validation subagent.",
        }

    raise ValueError(f"Unknown dispatch type: {dispatch_type}")
