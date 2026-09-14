#!/usr/bin/env python
"""record_dispatch.py — Record that a dispatch batch was started (in-flight guard).

Run AFTER spawning subagents in a parallel batch, or immediately before if your
platform requires it — but never spawn a second batch while status is in_flight.

Usage:
  python scripts/record_dispatch.py <run_dir> --type review --action start
  python scripts/record_dispatch.py <run_dir> --type review --action complete
  python scripts/record_dispatch.py <run_dir> --type review --action status
"""

import argparse
import sys
from pathlib import Path

from dispatch_utils import DISPATCH_TYPES, check_outputs, mark_batch_complete, start_batch, load_ledger


def main():
    parser = argparse.ArgumentParser(description="Record dispatch batch state")
    parser.add_argument("run_dir")
    parser.add_argument("--type", choices=DISPATCH_TYPES, required=True)
    parser.add_argument(
        "--action",
        choices=("start", "complete", "status"),
        default="start",
    )
    parser.add_argument(
        "--batch-kind",
        choices=("initial", "redispatch"),
        default="initial",
        help="Label for this batch in the ledger",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        print(f"Error: '{args.run_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    if args.action == "status":
        ledger = load_ledger(run_dir).get(args.type, {})
        found, missing = check_outputs(run_dir, args.type)
        print(f"LEDGER_STATUS={ledger.get('status', 'none')}")
        print(f"BATCH_ID={ledger.get('batch_id', 0)}")
        print(f"FOUND={len(found)}")
        print(f"MISSING={len(missing)}")
        for unit in missing:
            print(f"  missing: {unit['output_name']} (change {unit.get('change_id', unit['unit_id'])})")
        sys.exit(0)

    if args.action == "complete":
        mark_batch_complete(run_dir, args.type)
        found, missing = check_outputs(run_dir, args.type)
        print(f"Marked {args.type} batch complete. Found {len(found)}, missing {len(missing)}.")
        sys.exit(0)

    try:
        batch = start_batch(run_dir, args.type, batch_kind=args.batch_kind)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Recorded {args.type} batch #{batch['batch_id']} ({args.batch_kind}) as in_flight.")
    print(f"Expected outputs: {batch['expected_count']}")
    print("NEXT: wait for subagents — do NOT spawn again until wait_for_dispatch.py exits.")
    print(f"  python scripts/wait_for_dispatch.py \"{run_dir}\" --type {args.type}")


if __name__ == "__main__":
    main()
