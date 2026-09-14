#!/usr/bin/env python
"""wait_for_dispatch.py — Block until dispatch outputs appear or timeout.

Prevents premature re-dispatch while subagents are still running.

On Claude Code, monitors subagents/*.jsonl mtimes in the parent session dir.
If no subagent has written for --subagent-idle-timeout seconds (default 300),
exits early so missing units can be re-dispatched instead of waiting the full
--timeout (default 7200s).

Usage:
  python scripts/wait_for_dispatch.py <run_dir> --type review
  python scripts/wait_for_dispatch.py <run_dir> --type review --timeout 7200 --interval 30
  python scripts/wait_for_dispatch.py <run_dir> --type review --claude-session-dir "C:/Users/.../session-id"

Exit codes:
  0 — all expected outputs exist
  1 — ledger/config error
  2 — timeout or stale subagents with outputs still missing (redispatch allowed)
"""

import argparse
import sys
import time
from pathlib import Path

from claude_code_utils import check_subagent_liveness, resolve_claude_session_dir
from dispatch_utils import DISPATCH_TYPES, check_outputs, load_ledger, mark_batch_complete


WAIT_BANNER = (
    "DO NOT spawn subagents, Continue/resume agents, or poll Task IDs while waiting. "
    "Missing files during in_flight is normal — agents may still be writing."
)


def _resolve_session_dir(run_dir: Path, ledger: dict | None, explicit: str | None) -> Path | None:
    if explicit:
        return resolve_claude_session_dir(explicit=explicit)
    if ledger and ledger.get("claude_session_dir"):
        return resolve_claude_session_dir(explicit=ledger["claude_session_dir"])
    return resolve_claude_session_dir()


def _exit_missing(
    run_dir: Path,
    dispatch_type: str,
    missing: list,
    *,
    reason: str,
    detail: str,
) -> None:
    mark_batch_complete(run_dir, dispatch_type)
    print(f"\n{reason}: Still missing {len(missing)} output file(s). {detail}")
    print(WAIT_BANNER)
    print("Redispatch is allowed ONLY for missing units:")
    print(f"  python scripts/prepare_redispatch.py \"{run_dir}\" --type {dispatch_type}")
    sys.exit(2)


def main():
    parser = argparse.ArgumentParser(description="Wait for dispatch output files")
    parser.add_argument("run_dir")
    parser.add_argument("--type", choices=DISPATCH_TYPES, required=True)
    parser.add_argument("--timeout", type=int, default=7200, help="Max wait seconds (default 7200)")
    parser.add_argument("--interval", type=int, default=30, help="Poll interval seconds (default 30)")
    parser.add_argument(
        "--subagent-idle-timeout",
        type=int,
        default=300,
        help="Claude Code: exit early if no subagent jsonl activity for N seconds (default 300; 0=disable)",
    )
    parser.add_argument(
        "--claude-session-dir",
        default=None,
        help="Claude Code parent session dir containing subagents/ (auto-detected when possible)",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        print(f"Error: '{args.run_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    ledger = load_ledger(run_dir).get(args.type)
    if not ledger:
        print(
            f"Warning: no ledger entry for {args.type}. "
            "Run record_dispatch.py --action start after spawning.",
            file=sys.stderr,
        )

    session_dir = _resolve_session_dir(run_dir, ledger, args.claude_session_dir)
    if session_dir:
        print(f"Claude Code subagent monitor: {session_dir / 'subagents'}")
    elif args.subagent_idle_timeout > 0:
        print(
            "Claude Code subagent monitor: disabled (session dir not found). "
            "Set CLAUDE_CODE_SESSION_ID, pass --claude-session-dir, or record dispatch from Claude Code.",
            file=sys.stderr,
        )

    deadline = time.time() + args.timeout
    attempt = 0
    print(WAIT_BANNER)
    print(f"Waiting for {args.type} outputs in {run_dir}/reviews/ ...")

    while True:
        attempt += 1
        found, missing = check_outputs(run_dir, args.type)
        total = len(found) + len(missing)
        print(f"[{attempt}] Found {len(found)}/{total} output file(s).")
        for unit in found:
            print(f"  ok: {unit['output_name']}")
        for unit in missing:
            print(f"  pending: {unit['output_name']}")

        if not missing:
            mark_batch_complete(run_dir, args.type)
            print(f"\nPASS: All {args.type} outputs present.")
            print(f"NEXT: python scripts/verify_dispatch.py \"{run_dir}\" --type {args.type}")
            sys.exit(0)

        if (
            session_dir
            and args.subagent_idle_timeout > 0
            and ledger
            and ledger.get("status") == "in_flight"
        ):
            live = check_subagent_liveness(
                session_dir,
                idle_seconds=args.subagent_idle_timeout,
                batch_started_at=ledger.get("started_at"),
            )
            if live["batch_jsonl_count"]:
                print(
                    f"  subagent activity: {live['batch_jsonl_count']} jsonl file(s), "
                    f"last update {live['seconds_since_activity']}s ago "
                    f"({live.get('latest_jsonl', '?')})"
                )
            else:
                print(f"  subagent activity: no batch jsonl yet ({live['reason']})")

            if not live["alive"]:
                idle = live.get("seconds_since_activity")
                idle_msg = f"{idle}s" if idle is not None else f">{args.subagent_idle_timeout}s"
                _exit_missing(
                    run_dir,
                    args.type,
                    missing,
                    reason="STALE_SUBAGENTS",
                    detail=(
                        f"No Claude Code subagent jsonl activity for {idle_msg} "
                        f"(threshold {args.subagent_idle_timeout}s). "
                        "Subagents likely exited without writing outputs."
                    ),
                )

        if time.time() >= deadline:
            _exit_missing(
                run_dir,
                args.type,
                missing,
                reason="TIMEOUT",
                detail=f"Waited {args.timeout}s.",
            )

        remaining = int(deadline - time.time())
        print(f"Sleeping {args.interval}s ({remaining}s remaining). {WAIT_BANNER}\n")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
