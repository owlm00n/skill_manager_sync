"""shared.py -- Shared utilities for the engd-code-review skill.

Provides:
  - JSON loading with control-character auto-fix (deduplicates logic from 5 scripts)
  - Git subprocess helpers
  - SSH/Gerrit helpers
  - Validation prompt rules (deduplicates from 2 scripts)
  - Progress tracking for pipeline resume capability

Import from any script in the scripts/ directory:
  from shared import load_json_safe, fix_json_control_chars
"""

import getpass
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Gerrit configuration (from environment)
# ---------------------------------------------------------------------------

GERRIT_HOST = os.environ.get("GERRIT_HOST", "gerrit.unisoc.com")
GERRIT_PORT = os.environ.get("GERRIT_PORT", "29418")
GERRIT_USER = os.environ.get("GERRIT_USER", getpass.getuser())


# ---------------------------------------------------------------------------
# JSON loading with control-character auto-fix
# ---------------------------------------------------------------------------

# Build translation table once: replace control chars (0x00-0x08, 0x0B-0x0C,
# 0x0E-0x1F, 0x7F+) with spaces, preserving tab (0x09), LF (0x0A), CR (0x0D).
_CTRL_TABLE = bytes(
    b if 0x20 < b < 0x7F else (b if b in (0x09, 0x0A, 0x0D) else 0x20)
    for b in range(256)
)


def fix_json_control_chars(raw: bytes) -> str:
    """Remove invalid control characters from raw JSON bytes.

    Preserves valid whitespace (tab, LF, CR). Replaces other control chars
    with spaces. Uses bytes.translate for speed vs the old byte-by-byte loop.
    """
    return raw.translate(_CTRL_TABLE).decode("utf-8", errors="replace")


def load_json_safe(filepath):
    """Load a JSON file, auto-fixing control character issues from LLM output.

    Returns the parsed data on success.
    Prints error to stderr and calls sys.exit(1) on failure.
    """
    with open(filepath, "rb") as f:
        raw = f.read()
    try:
        return json.loads(raw, strict=True)
    except json.JSONDecodeError:
        pass
    fixed = fix_json_control_chars(raw)
    try:
        data = json.loads(fixed)
        print(
            f"Warning: auto-fixed control characters in {os.path.basename(filepath)}",
            file=sys.stderr,
        )
        return data
    except json.JSONDecodeError as e:
        print(
            f"Error: failed to parse {os.path.basename(filepath)}: {e}",
            file=sys.stderr,
        )
        sys.exit(1)


def try_load_json_safe(filepath):
    """Non-fatal variant of load_json_safe. Returns None on parse failure.

    Use when the caller needs to handle bad JSON gracefully (e.g., optional
    files like change_summary.json in _load_change_urls).
    """
    try:
        with open(filepath, "rb") as f:
            raw = f.read()
    except OSError:
        return None
    try:
        return json.loads(raw, strict=True)
    except json.JSONDecodeError:
        pass
    fixed = fix_json_control_chars(raw)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Git subprocess helpers
# ---------------------------------------------------------------------------


def run_git(
    args: list[str],
    cwd: "Path | str | None" = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a git command with SSH options that skip host key verification."""
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = (
        "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    )
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=check,
        env=env,
    )


# ---------------------------------------------------------------------------
# SSH / Gerrit helpers
# ---------------------------------------------------------------------------


def get_ssh_key() -> "Path | None":
    """Find the user's default SSH key."""
    home = Path.home()
    for name in ["id_rsa", "id_ed25519", "id_ecdsa", "id_dsa"]:
        key = home / ".ssh" / name
        if key.is_file():
            return key
    return None


def ssh_gerrit(command: str, ssh_key: Path) -> str:
    """Run a command on Gerrit via SSH. Returns stdout."""
    result = subprocess.run(
        [
            "ssh",
            "-p",
            GERRIT_PORT,
            "-i",
            str(ssh_key),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "ConnectTimeout=10",
            f"{GERRIT_USER}@{GERRIT_HOST}",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.stdout


# ---------------------------------------------------------------------------
# Validation rules (shared between generate_validation_prompt.py and
# prepare_validation_dispatch.py)
# ---------------------------------------------------------------------------

VALIDATION_RULES = """**False positive filter — mark INVALID any finding that falls into these categories:**
   - **Pre-existing issues**: The code has a problem but it predates the change and is not touched by it.
   - **Not-a-bug patterns**: Something that looks like a bug but is actually correct (intentional workaround, platform quirk, documented behavior).
   - **Pedantic nitpicks**: Issues a senior engineer would not call out in a code review.
   - **Compiler/linter/typechecker violations**: Missing imports, type errors, broken tests, formatting, pedantic style (newlines, trailing whitespace). These are handled by CI tooling — mark INVALID.
   - **General code quality**: Lack of test coverage, general security concerns, poor documentation. Unless explicitly required in CLAUDE.md, mark INVALID.
   - **Explicitly silenced issues**: The claim is flagged in CLAUDE.md but the code has an intentional ignore comment or override. Mark INVALID.
   - **Intentional changes**: Functionality changes that are likely deliberate or directly part of the broader PR goal.
   - **Unmodified lines**: Real issues that exist only on lines the user did NOT modify in their PR.
   - **Low confidence**: Any finding where `confidence_score` (field 13 of all_findings.json) is less than 80. These are uncertain or weak findings — mark INVALID."""


# ---------------------------------------------------------------------------
# Subagent dispatch (platform-agnostic; used by prepare_*_dispatch.py)
# ---------------------------------------------------------------------------

SUBAGENT_DISPATCH_RULES = (
    "Dispatch exactly one subagent per manifest entry — 10 changes means 10 subagents, never fewer. "
    "'Parallel batch' means launch all subagents in one message, NOT merge multiple changes into one subagent. "
    "Do not pass isolation or worktree params — omit them entirely (default runs in shared cwd). "
    "Each subagent must receive its dispatch_prompt from the manifest (bootstrap only); "
    "the subagent reads the full instructions from prompt_file. "
    "Write to the specified output_path. "
    "Wait for the entire batch to finish before running verify_dispatch.py. "
    "On missing output: re-dispatch only the failed subagents after the original batch completes — "
    "never re-dispatch while a previous run for the same unit is still in progress. "
    "The parent orchestrator must NOT perform review or validation inline."
)

SUBAGENT_DISPATCH_FORBIDDEN = [
    "Combining multiple changes into one subagent",
    "Grouping manifest entries into fewer agents for efficiency",
    "One subagent writing multiple *_findings.json files",
    "Parent performing review because dispatch seemed too large",
    "Re-dispatching a subagent while its previous run is still in progress",
    "Using Continue/resume on in-flight subagents (creates duplicate workers)",
    "Polling Task/agent by numeric ID — wait for background completion instead",
    "Running verify_dispatch.py before wait_for_dispatch.py on an in-flight batch",
    "Running verify_dispatch.py before all subagents in the batch have finished",
    "Passing isolation: worktree, --worktree, or EnterWorktree",
    "Passing isolation: none (invalid on many platforms — omit the parameter instead)",
]

# Do not pass an isolation field when spawning subagents. Many Agent APIs only accept
# isolation="worktree"; omitting the parameter runs in the parent cwd (what we want).
SUBAGENT_SPAWN_OPTIONS = {
    "omit_isolation": True,
    "use_worktree": False,
}

SUBAGENT_REQUIRED_CAPABILITIES = [
    "read_files",
    "write_files",
    "multi_step_reasoning",
]


def build_review_dispatch_prompt(prompt_file: str, output_path: str) -> str:
    """Short bootstrap prompt for review subagents — full instructions live in prompt_file."""
    return (
        "You are a code review subagent for one Gerrit change.\n"
        "1. Read the full review instructions from this file using the Read tool "
        "and follow them exactly (do not summarize or truncate):\n"
        f"   {prompt_file}\n"
        "2. Write findings to this exact path using the Write tool:\n"
        f"   {output_path}\n"
        "Execute every step in the prompt file, including diff read, purpose summary, "
        "workspace verification, and self-validation."
    )


def build_validation_dispatch_prompt(prompt_file: str, output_path: str) -> str:
    """Short bootstrap prompt for per-change validation subagents."""
    return (
        "You are a finding validation subagent for one Gerrit change.\n"
        "1. Read the full validation instructions from this file using the Read tool "
        "and follow them exactly (do not summarize or truncate):\n"
        f"   {prompt_file}\n"
        "2. Write verified results to this exact path using the Write tool:\n"
        f"   {output_path}\n"
        "The prompt file references a separate findings JSON file — read that file "
        "as instructed before validating."
    )


def build_cross_validation_dispatch_prompt(prompt_file: str, output_path: str) -> str:
    """Short bootstrap prompt for cross-project validation subagent."""
    return (
        "You are a cross-project finding validation subagent.\n"
        "1. Read the full validation instructions from this file using the Read tool "
        "and follow them exactly (do not summarize or truncate):\n"
        f"   {prompt_file}\n"
        "2. Write verified results to this exact path using the Write tool:\n"
        f"   {output_path}\n"
        "The prompt file references _cross_project_findings.json — read that file "
        "as instructed before validating."
    )


CROSS_PROJECT_DISPATCH_FORBIDDEN = [
    "Splitting cross-project review into multiple subagents",
    "Grouping changes like 1541988+1562265+1549280 into one agent",
    "One subagent per project or per change subset",
    "Multiple outputs — only _cross_project_findings.json is valid",
]

def get_project_count(run_dir: "str | Path") -> int:
    """Return unique project count from review manifest or change_summary."""
    run_dir = Path(run_dir)
    manifest_path = run_dir / "reviews" / "_review_manifest.json"
    if manifest_path.is_file():
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        if "project_count" in manifest:
            return int(manifest["project_count"])

    change_summary_path = run_dir / "change_summary.json"
    if change_summary_path.is_file():
        changes = load_json_safe(str(change_summary_path))
        if isinstance(changes, list) and changes:
            return len({c.get("project", "") for c in changes})

    return 1


def cross_project_review_path(run_dir: "str | Path") -> Path:
    """Path to the cross-project review agent output file."""
    return Path(run_dir) / "reviews" / "_cross_project_findings.json"


def ensure_cross_project_review_done(run_dir: "str | Path", step_label: str) -> None:
    """Exit with code 1 if a multi-project run skipped Step 3.1."""
    project_count = get_project_count(run_dir)
    cross_file = cross_project_review_path(run_dir)

    if project_count <= 1 or cross_file.is_file():
        return

    print(
        f"Error: PROJECT_COUNT={project_count} but {cross_file.name} is missing.",
        file=sys.stderr,
    )
    print(
        f">>> Step 3.1 (cross-project review) must complete before {step_label}.",
        file=sys.stderr,
    )
    print(
        ">>> CROSS_PROJECT_FINDINGS=0 from consolidate does NOT mean review ran — "
        "it means no _cross_project_findings.json was found.",
        file=sys.stderr,
    )
    print(
        ">>> Run: python scripts/generate_cross_project_prompt.py <run_dir> "
        "--output <run_dir>/reviews/_cross_project_prompt.txt",
        file=sys.stderr,
    )
    print(">>> Then dispatch ONE cross-project review agent.", file=sys.stderr)
    print(
        ">>> Verify: python scripts/verify_dispatch.py <run_dir> --type cross-review",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------

def default_report_path(run_dir: str | Path) -> Path:
    """Build the default HTML report path from a per-run review directory.

    Pattern: <run_dir>/report-<timestamp>-<topic_prefix>.html

    Examples:
      .../review-topic-foo/review-20260629232928
        -> .../review-20260629232928/report-20260629232928-review-topic-foo.html
      .../review-1569504/review-20260628003845
        -> .../review-20260628003845/report-20260628003845-review-1569504.html
    """
    run_dir = Path(run_dir).resolve()
    run_name = run_dir.name
    parent_name = run_dir.parent.name
    stamp = run_name.removeprefix("review-") if run_name.startswith("review-") else run_name
    return run_dir / f"report-{stamp}-{parent_name}.html"


PIPELINE_STEPS = [
    "setup",
    "review",
    "cross_project_review",
    "validate_findings",
    "consolidate",
    "validation_dispatch",
    "validate_verified",
    "merge_validation",
    "build_issues",
    "report",
]


def update_progress(run_dir: "str | Path", step_name: str):
    """Record a completed pipeline step in <run_dir>/progress.json.

    Creates or updates the file. Safe to call multiple times.
    """
    run_dir = Path(run_dir)
    progress_file = run_dir / "progress.json"

    if progress_file.is_file():
        with open(progress_file, encoding="utf-8") as f:
            progress = json.load(f)
    else:
        progress = {"completed": [], "pending": list(PIPELINE_STEPS)}

    if step_name not in progress["completed"]:
        progress["completed"].append(step_name)
    progress["pending"] = [
        s for s in PIPELINE_STEPS if s not in progress["completed"]
    ]
    progress["step"] = progress["pending"][0] if progress["pending"] else "done"
    progress["timestamp"] = datetime.now(timezone.utc).isoformat()

    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)
        f.write("\n")
