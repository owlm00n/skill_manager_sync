"""init_review.py -- Initialize the review base directory.

Takes the raw user input (topic:X or id1,id2) and outputs the correct
resolved_cwd path. Creates the directory if it doesn't exist.

Usage:
  python scripts/init_review.py <input>

Examples:
  python scripts/init_review.py topic:3300608
  python scripts/init_review.py topic:engd-code-review-test
  python scripts/init_review.py 1536703
  python scripts/init_review.py 1536703,1536704

Output (stdout): the absolute path to use as resolved_cwd.
The script prints ONLY the path on the last line (for easy capture).
"""

import os
import sys
from pathlib import Path


def compute_topic_prefix(user_input: str) -> str:
    """Derive the TOPIC_PREFIX from the raw user input.

    Rules (based SOLeLY on input format, never on value appearance):
      topic:X       -> review-topic-X
      single_id     -> review-<id>
      id1,id2,...   -> review-<id1>_<id2>_...
    """
    if user_input.startswith("topic:"):
        name = user_input[6:]  # strip "topic:"
        if not name:
            print("Error: topic name is empty (got 'topic:')", file=sys.stderr)
            sys.exit(1)
        return f"review-topic-{name}"

    # Comma-separated IDs
    ids = [x.strip() for x in user_input.split(",") if x.strip()]
    if not ids:
        print("Error: no change IDs provided", file=sys.stderr)
        sys.exit(1)

    if len(ids) == 1:
        return f"review-{ids[0]}"

    return f"review-{'_'.join(ids)}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/init_review.py <input>", file=sys.stderr)
        print("  input: topic:<name> or <id1>,<id2>,...", file=sys.stderr)
        sys.exit(1)

    user_input = sys.argv[1]
    prefix = compute_topic_prefix(user_input)

    base_dir = Path.home() / "code-review" / prefix
    base_dir.mkdir(parents=True, exist_ok=True)

    resolved = str(base_dir.resolve())
    print(f"Review directory: {resolved}", file=sys.stderr)
    print(resolved)


if __name__ == "__main__":
    main()
