#!/usr/bin/env python
"""prepare_redispatch.py — Build a manifest for ONLY missing dispatch units.

Usage:
  python scripts/prepare_redispatch.py <run_dir> --type review

Writes:
  <run_dir>/reviews/_redispatch_<type>_manifest.json

Only run after wait_for_dispatch.py exits (success or timeout) and ledger is not in_flight.
Does NOT mark the batch in_flight — run record_dispatch.py --action start after spawning.
"""

import argparse
import json
import sys
from pathlib import Path

from dispatch_utils import DISPATCH_TYPES, build_redispatch_manifest, check_outputs


def main():
    parser = argparse.ArgumentParser(description="Prepare redispatch manifest for missing units only")
    parser.add_argument("run_dir")
    parser.add_argument("--type", choices=DISPATCH_TYPES, required=True)
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        print(f"Error: '{args.run_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    found, missing = check_outputs(run_dir, args.type)
    if not missing:
        print(f"Nothing to redispatch for {args.type}: all {len(found)} output(s) exist.")
        print(f"Run: python scripts/verify_dispatch.py \"{run_dir}\" --type {args.type}")
        sys.exit(0)

    try:
        manifest = build_redispatch_manifest(run_dir, args.type)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print("Run wait_for_dispatch.py first. Do NOT redispatch while batch is in_flight.", file=sys.stderr)
        sys.exit(1)

    out_path = run_dir / "reviews" / f"_redispatch_{args.type.replace('-', '_')}_manifest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    count = manifest.get("agent_count") or manifest.get("group_count") or 1
    print(f"Redispatch manifest: {out_path}")
    print(f"Missing outputs: {len(missing)}")
    for unit in missing:
        print(f"  - {unit['output_name']} (change {unit.get('change_id', unit['unit_id'])})")
    print()
    print("=" * 60)
    print(f"REDISPATCH ONLY {count} subagent(s) from {out_path.name}")
    print("FORBIDDEN: Continue/resume in-flight agents; dispatch units that already succeeded")
    print(f"After spawning: python scripts/record_dispatch.py \"{run_dir}\" --type {args.type} --action start --batch-kind redispatch")
    print(f"Then: python scripts/wait_for_dispatch.py \"{run_dir}\" --type {args.type}")
    print("=" * 60)


if __name__ == "__main__":
    main()
