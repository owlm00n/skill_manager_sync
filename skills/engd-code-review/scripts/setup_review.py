#!/usr/bin/env python
"""setup_review.py -- End-to-end setup for Gerrit code review.

Queries Gerrit, clones repos, cherry-picks changes, extracts diffs,
and writes change_summary.json.

Usage:
  python scripts/setup_review.py <topic:<name>|<id1>,<id2>,...> [resolved_cwd] [--dry-run] [--no-clone]

Examples:
  python scripts/setup_review.py topic:3300608
  python scripts/setup_review.py topic:my-feature --dry-run
  python scripts/setup_review.py 1536703
  python scripts/setup_review.py 1536703,1536704,1538349 --no-clone

Environment variables:
  GERRIT_HOST     Gerrit server (default: gerrit.unisoc.com)
  GERRIT_PORT     Gerrit SSH port (default: 29418)
  GERRIT_USER     SSH user (default: current user)
  GERRIT_HTTP_TIMEOUT  Web access check timeout in seconds (default: 3)
  GERRIT_HTTP_COOKIE   Optional browser session cookie for HTTPS access check
  BASE_DIR        Shared workspace base directory (default: ~/code-review/gerrit-cherry-pick-workspace)
  MIRROR_REF      Local mirror path (default: /space/mirror/cmtool/var/.c/sprd)
  MIRROR_URL      Mirror SSH URL (default: ssh://gitadmin@gitmirror.unisoc.com)
  MIRROR_ROOT     Mirror root prefix for kernel projects (default: kernel)
"""

import argparse
import getpass
import json
import os
import re
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from shared import update_progress


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GERRIT_HOST = os.environ.get("GERRIT_HOST", "gerrit.unisoc.com")
GERRIT_PORT = os.environ.get("GERRIT_PORT", "29418")
GERRIT_USER = os.environ.get("GERRIT_USER", getpass.getuser())
GERRIT_HTTP_TIMEOUT = float(os.environ.get("GERRIT_HTTP_TIMEOUT", "3"))
BASE_DIR_DEFAULT = os.environ.get("BASE_DIR", os.path.join(str(Path.home()), "code-review", "gerrit-cherry-pick-workspace"))
MIRROR_REF = Path(os.environ.get("MIRROR_REF", "/space/mirror/cmtool/var/.c/sprd"))
MIRROR_URL = os.environ.get("MIRROR_URL", "ssh://gitadmin@gitmirror.unisoc.com")
MIRROR_ROOT = os.environ.get("MIRROR_ROOT", "kernel")


# ---------------------------------------------------------------------------
# SSH helpers
# ---------------------------------------------------------------------------

def get_ssh_key() -> Path | None:
    """Find the user's default SSH key."""
    home = Path.home()
    for name in ["id_rsa", "id_ed25519", "id_ecdsa", "id_dsa"]:
        key = home / ".ssh" / name
        if key.is_file():
            return key
    return None


def ssh_gerrit(command: str, ssh_key: Path) -> tuple[str, str, int]:
    """Run a command on Gerrit via SSH. Returns (stdout, stderr, returncode)."""
    result = subprocess.run(
        [
            "ssh", "-p", GERRIT_PORT,
            "-i", str(ssh_key),
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
            f"{GERRIT_USER}@{GERRIT_HOST}",
            command,
        ],
        capture_output=True, text=True, timeout=60, encoding="utf-8",
    )
    return result.stdout, result.stderr.strip(), result.returncode


def _format_gerrit_error(stderr: str, returncode: int) -> str:
    """Summarize SSH/Gerrit failure for display."""
    if returncode != 0:
        if stderr:
            first = stderr.splitlines()[0].strip()
            if "Permission denied" in stderr or "permission denied" in stderr:
                return f"SSH permission denied ({first})"
            if "Connection refused" in stderr or "Connection timed out" in stderr:
                return f"Cannot reach Gerrit ({first})"
            return first
        return f"SSH command failed (exit {returncode})"
    return "No matching change (not found or no read permission)"


@dataclass
class GerritFetchRow:
    """One row in the Gerrit access check table."""

    query: str
    status: str  # OK | FAILED
    change_id: str = ""
    project: str = ""
    branch: str = ""
    patchset: str = ""
    owner: str = ""
    gerrit_url: str = ""
    error: str = ""
    raw: dict | None = None


def gerrit_change_url(project: str, change_id: str) -> str:
    """Build the Gerrit web URL for a change (project path uses literal slashes)."""
    return f"https://{GERRIT_HOST}/gerrit/c/{project}/+/{change_id}"


def check_gerrit_web_access(url: str, timeout: float | None = None) -> bool:
    """Fast HTTP check: can this environment open the Gerrit change page?"""
    if timeout is None:
        timeout = GERRIT_HTTP_TIMEOUT

    headers = {"User-Agent": "engd-code-review/1.0"}
    cookie = os.environ.get("GERRIT_HTTP_COOKIE", "").strip()
    if cookie:
        headers["Cookie"] = cookie

    for method, extra_headers in (("HEAD", {}), ("GET", {"Range": "bytes=0-0"})):
        req = urllib.request.Request(url, headers={**headers, **extra_headers}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status not in (200, 206):
                    if method == "HEAD":
                        continue
                    return False
                final_url = resp.geturl().lower()
                if "login" in final_url or "signin" in final_url:
                    return False
                return True
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in (405, 501):
                continue
            return False
        except (urllib.error.URLError, TimeoutError, OSError):
            return False
    return False


def _row_from_gerrit_json(data: dict, query: str) -> GerritFetchRow:
    ps = data.get("currentPatchSet", {}) or {}
    change_id = str(data.get("number", ""))
    project = data.get("project", "")
    return GerritFetchRow(
        query=query,
        status="OK",
        change_id=change_id,
        project=project,
        branch=data.get("branch", ""),
        patchset=str(ps.get("number", "")).strip(),
        owner=(data.get("owner", {}) or {}).get("name", ""),
        gerrit_url=gerrit_change_url(project, change_id) if project and change_id else "",
        raw=data,
    )


def _verify_row_web_access(row: GerritFetchRow) -> GerritFetchRow:
    """Set row.status from HTTP access to the Gerrit change page."""
    if not row.gerrit_url:
        row.status = "FAILED"
        row.error = "Missing project or change ID"
        return row
    if check_gerrit_web_access(row.gerrit_url):
        row.status = "OK"
        row.error = ""
    else:
        row.status = "FAILED"
        row.error = f"No web access: {row.gerrit_url}"
    return row


def _parse_gerrit_query_lines(output: str) -> list[dict]:
    changes = []
    for line in output.strip().split("\n"):
        if not line or '"type":"stats"' in line:
            continue
        try:
            data = json.loads(line)
            if "number" in data:
                changes.append(data)
        except json.JSONDecodeError:
            continue
    return changes


def _print_box_table(headers: tuple[str, ...], rows: list[list[str]], indent: str = "  ") -> None:
    """Print a table with Unicode box-drawing borders."""
    if not headers:
        return

    all_rows = [list(headers)] + rows
    widths = [max(len(r[i]) for r in all_rows) for i in range(len(headers))]

    def border(left: str, mid: str, right: str) -> str:
        return indent + left + mid.join("─" * (w + 2) for w in widths) + right

    def line(cells: list[str]) -> str:
        return indent + "│" + "".join(f" {cells[i].ljust(widths[i])} │" for i in range(len(cells)))

    print(border("┌", "┬", "┐"))
    print(line(list(headers)))
    for row in rows:
        print(border("├", "┼", "┤"))
        print(line(row))
    print(border("└", "┴", "┘"))


def print_gerrit_fetch_table(rows: list[GerritFetchRow], host: str) -> None:
    """Print a box-drawing summary table of Gerrit access checks."""
    ok_count = sum(1 for r in rows if r.status == "OK")
    fail_count = len(rows) - ok_count

    print(f"\n=== Gerrit access check ({host}) ===")
    print(f"OK: {ok_count}  FAILED: {fail_count}  TOTAL: {len(rows)}\n")

    headers = ("Status", "Change ID", "Project", "Branch", "PS", "Owner")
    data = [
        [
            row.status,
            row.change_id or "-",
            row.project or "-",
            row.branch or "-",
            row.patchset or "-",
            row.owner or "-",
        ]
        for row in rows
    ]
    _print_box_table(headers, data)
    print()


def all_gerrit_fetches_succeeded(rows: list[GerritFetchRow]) -> bool:
    return bool(rows) and all(r.status == "OK" for r in rows)


def run_git(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command with SSH options that skip host key verification."""
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd) if cwd else None,
        capture_output=True, text=True, encoding="utf-8",
        check=check,
        env=env,
    )


# ---------------------------------------------------------------------------
# Mirror resolution
# ---------------------------------------------------------------------------

def resolve_mirror_path(project: str) -> str | None:
    """Resolve the mirror path for a given Gerrit project.

    Handles:
      kernel/common -> MIRROR_REF/kernel/common.git
      device/sprd/mpool -> MIRROR_REF/device/sprd/mpool.git (non-kernel fallback)
    """
    mirror_proj = f"{MIRROR_ROOT}/{project.split('/', 1)[1] if '/' in project else project}"

    if (MIRROR_REF / f"{mirror_proj}.git").is_dir():
        return mirror_proj

    if (MIRROR_REF / f"{project}.git").is_dir():
        return project

    parts = project.split("/", 1)
    if len(parts) > 1:
        proj_path = parts[1]
        if (MIRROR_REF / f"{proj_path}.git").is_dir():
            return proj_path

        if (MIRROR_REF / proj_path).is_dir():
            for subdir in sorted((MIRROR_REF / proj_path).glob("*.git")):
                if subdir.is_dir():
                    return f"{proj_path}/{subdir.name}"

    return None


# ---------------------------------------------------------------------------
# Clone
# ---------------------------------------------------------------------------

def git_clone_project(project: str, branch: str, proj_dir: Path, dry_run: bool) -> bool:
    """Clone a project with mirror --reference fallback chain."""
    mirror_proj = resolve_mirror_path(project)
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

    print(f"  Cloning {project} (branch: {branch}) ...")

    # Strategy 1: mirror --reference
    if mirror_proj and (MIRROR_REF / f"{mirror_proj}.git").is_dir():
        if dry_run:
            print(f"  [DRY-RUN] git clone --reference {MIRROR_REF}/{mirror_proj}.git {MIRROR_URL}/{mirror_proj} -b {branch} {proj_dir}")
            return True
        result = subprocess.run(
            [
                "git", "clone", "--reference", str(MIRROR_REF / f"{mirror_proj}.git"),
                f"{MIRROR_URL}/{mirror_proj}",
                "-b", branch, str(proj_dir),
            ],
            capture_output=True, text=True, env=env,
        )
        if result.returncode == 0:
            print("  [OK] Cloned from mirror")
            return True
        print("  WARNING: Mirror clone failed, falling back to mirror admin SSH...")

    # Strategy 2: mirror admin SSH (no --reference)
    if dry_run:
        print(f"  [DRY-RUN] git clone {MIRROR_URL}/{project} -b {branch} {proj_dir}")
        return True
    result = subprocess.run(
        ["git", "clone", f"{MIRROR_URL}/{project}", "-b", branch, str(proj_dir)],
        capture_output=True, text=True, env=env,
    )
    if result.returncode == 0:
        print("  [OK] Cloned from mirror admin SSH")
        return True
    print("  WARNING: Mirror admin SSH clone failed, falling back to Gerrit SSH...")

    # Strategy 3: Gerrit SSH
    ssh_url = f"ssh://{GERRIT_USER}@{GERRIT_HOST}:{GERRIT_PORT}/{project}"
    if dry_run:
        print(f"  [DRY-RUN] git clone {ssh_url} -b {branch} {proj_dir}")
        return True
    result = subprocess.run(
        ["git", "clone", ssh_url, "-b", branch, str(proj_dir)],
        capture_output=True, text=True, env=env,
    )
    return result.returncode == 0


def update_existing_clone(proj_dir: Path, branch: str, dry_run: bool):
    """Reset + clean + pull an existing clone."""
    print(f"  Already cloned — updating ...")
    if dry_run:
        print(f"  [DRY-RUN] Update existing clone in {proj_dir}")
        return
    run_git(["fetch", "origin", branch], cwd=proj_dir, check=False)
    run_git(["reset", "--hard", f"origin/{branch}"], cwd=proj_dir, check=False)
    run_git(["clean", "-df"], cwd=proj_dir, check=False)

    result = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=proj_dir, check=False)
    current = result.stdout.strip()
    if current != branch:
        print(f"  Updating to branch {branch} ...")
        run_git(["fetch", "origin", branch], cwd=proj_dir, check=False)
        run_git(["checkout", branch], cwd=proj_dir, check=False)
        run_git(["reset", "--hard", f"origin/{branch}"], cwd=proj_dir, check=False)


# ---------------------------------------------------------------------------
# Gerrit query + parsing
# ---------------------------------------------------------------------------

def fetch_gerrit_topic(ssh_key: Path, topic: str) -> list[GerritFetchRow]:
    """Query topic via SSH, then verify web access per change (fail-fast)."""
    query_label = f"topic:{topic}"
    print(f"=== Querying Gerrit (topic): {topic} ===")
    stdout, stderr, rc = ssh_gerrit(
        f"gerrit query --format JSON --current-patch-set 'topic:{topic}'",
        ssh_key,
    )
    if rc != 0:
        return [GerritFetchRow(query=query_label, status="FAILED", error=_format_gerrit_error(stderr, rc))]
    if not stdout.strip():
        return [GerritFetchRow(
            query=query_label,
            status="FAILED",
            error="Empty SSH response (check network, VPN, or SSH access)",
        )]

    changes = _parse_gerrit_query_lines(stdout)
    if not changes:
        return [GerritFetchRow(
            query=query_label,
            status="FAILED",
            error="No changes found for this topic",
        )]

    rows: list[GerritFetchRow] = []
    for data in changes:
        change_id = str(data.get("number", ""))
        row = _row_from_gerrit_json(data, change_id)
        print(f"  Checking web access: {row.gerrit_url}")
        _verify_row_web_access(row)
        rows.append(row)
        if row.status != "OK":
            return rows
    return rows


def fetch_gerrit_ids(ssh_key: Path, ids: list[str]) -> list[GerritFetchRow]:
    """Query each change ID via SSH, verify web access, stop on first failure."""
    print(f"=== Querying Gerrit (id): {len(ids)} change(s) {', '.join(ids)} ===")
    rows: list[GerritFetchRow] = []
    for num in ids:
        print(f"  Fetching change #{num} ...")
        stdout, stderr, rc = ssh_gerrit(
            f"gerrit query --format JSON --current-patch-set change:{num}",
            ssh_key,
        )
        if rc != 0:
            rows.append(GerritFetchRow(
                query=num,
                status="FAILED",
                error=_format_gerrit_error(stderr, rc),
            ))
            return rows

        found = _parse_gerrit_query_lines(stdout)
        if not found:
            rows.append(GerritFetchRow(
                query=num,
                status="FAILED",
                error=_format_gerrit_error(stderr, 0),
            ))
            return rows

        row = _row_from_gerrit_json(found[0], num)
        print(f"  Checking web access: {row.gerrit_url}")
        _verify_row_web_access(row)
        rows.append(row)
        if row.status != "OK":
            return rows
    return rows


def parse_changes(raw_changes: list[dict]) -> list[dict]:
    """Extract structured info from raw Gerrit JSON."""
    parsed = []
    for d in raw_changes:
        ps = d.get("currentPatchSet", {}) or {}
        parsed.append({
            "project": d.get("project", ""),
            "branch": d.get("branch", ""),
            "number": str(d.get("number", "")),
            "subject": d.get("subject", ""),
            "patchset": str(ps.get("number", "")).strip(),
            "owner": (d.get("owner", {}) or {}).get("name", ""),
        })
    return parsed


# ---------------------------------------------------------------------------
# Cherry-pick
# ---------------------------------------------------------------------------

class CherryPickConflictError(RuntimeError):
    """Fetch or cherry-pick failed for a Gerrit change."""


def abort_in_progress_cherry_pick(proj_dir: Path) -> None:
    """Best-effort: leave repo out of a conflicted cherry-pick state."""
    run_git(["cherry-pick", "--abort"], cwd=proj_dir, check=False)


def cherry_pick_change(proj_dir: Path, ssh_url: str, fetch_ref: str, dry_run: bool) -> str:
    """Fetch + cherry-pick a single change. Returns the commit SHA."""
    if dry_run:
        print(f"  [DRY-RUN] cd {proj_dir} && git fetch {ssh_url} {fetch_ref} && git cherry-pick FETCH_HEAD")
        return "dry-run-sha"

    fetch_result = run_git(["fetch", ssh_url, fetch_ref], cwd=proj_dir, check=False)
    if fetch_result.returncode != 0:
        raise CherryPickConflictError(f"Fetch failed: {fetch_result.stderr.strip()}")

    cp_result = run_git(["cherry-pick", "FETCH_HEAD"], cwd=proj_dir, check=False)
    if cp_result.returncode != 0:
        abort_in_progress_cherry_pick(proj_dir)
        raise CherryPickConflictError(f"Cherry-pick failed: {cp_result.stderr.strip()}")

    sha_result = run_git(["log", "-1", "--format=%H"], cwd=proj_dir, check=False)
    return sha_result.stdout.strip()


# ---------------------------------------------------------------------------
# Commit description extraction
# ---------------------------------------------------------------------------

GERRIT_TRAILERS = re.compile(
    r"^(Reviewed-on:|Reviewed-by:|Commit-Queue:|Change-Id:|Signed-off-by:|---$).*$",
    re.MULTILINE,
)


def extract_commit_description(proj_dir: Path, commit_sha: str) -> str:
    """Get commit message, strip Gerrit trailers, return first 3 non-empty lines."""
    result = run_git(["log", "-1", "--format=%B", commit_sha], cwd=proj_dir, check=False)
    msg = result.stdout.strip()
    if not msg:
        # Fallback: stat-based description
        stat_result = run_git(["log", "-1", "--stat", commit_sha], cwd=proj_dir, check=False)
        files = re.findall(r'\S+\.(?:c|h|py|mk|sh)', stat_result.stdout)
        if files:
            return f"Changes to {', '.join(files[:5])}"
        return ""

    cleaned = GERRIT_TRAILERS.sub("", msg)
    lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
    return "\n".join(lines[:3])


# ---------------------------------------------------------------------------
# Diff extraction
# ---------------------------------------------------------------------------

def extract_diff(proj_dir: Path, parent_sha: str, commit_sha: str, output_file: Path, dry_run: bool):
    """Extract git diff parent..commit to a file."""
    if dry_run:
        print(f"  [DRY-RUN] git diff {parent_sha}..{commit_sha} > {output_file}")
        return

    result = run_git(["diff", f"{parent_sha}..{commit_sha}"], cwd=proj_dir, check=False)
    if result.returncode == 0 and result.stdout:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(result.stdout, encoding="utf-8")
    else:
        # Fallback: per-file diff
        print(f"  [FALLBACK] Using --name-only diff extraction")
        names = run_git(["diff", "--name-only", f"{parent_sha}..{commit_sha}"], cwd=proj_dir, check=False)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            for fname in names.stdout.strip().split("\n"):
                if fname:
                    file_diff = run_git(["diff", f"{parent_sha}..{commit_sha}", "--", fname], cwd=proj_dir, check=False)
                    f.write(file_diff.stdout)


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Setup Gerrit code review: query, clone, cherry-pick, extract diffs",
    )
    parser.add_argument("input", help="topic:<name> or comma-separated change IDs")
    parser.add_argument("resolved_cwd", nargs="?", default=None,
                        help="Resolved output directory (default: BASE_DIR)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--no-clone", action="store_true", help="Skip git clone step")
    args = parser.parse_args()

    ssh_key = get_ssh_key()
    if ssh_key is None:
        print(f"ERROR: No SSH key found in {Path.home() / '.ssh'}")
        print("Generate one with: ssh-keygen -t ed25519")
        sys.exit(1)

    # Resolve base directory
    if args.resolved_cwd:
        base_dir = Path(args.resolved_cwd).resolve()
    else:
        base_dir = Path(BASE_DIR_DEFAULT).resolve()

    workspace_dir = base_dir / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Per-run timestamped directory
    run_ts = datetime.now().strftime("%Y%m%d%H%M%S")
    run_dir = base_dir / f"review-{run_ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    reviews_dir = run_dir / "reviews"
    reviews_dir.mkdir(exist_ok=True)

    # ─── Phase 1: Fetch all Gerrit metadata (must all succeed before clone) ──
    if args.input.startswith("topic:"):
        topic_name = args.input[6:]
        if not topic_name:
            print("ERROR: Topic name is empty (got 'topic:').")
            sys.exit(1)
        fetch_rows = fetch_gerrit_topic(ssh_key, topic_name)
    else:
        ids = [x.strip() for x in args.input.split(",") if x.strip()]
        if not ids:
            print("ERROR: No change IDs provided.")
            sys.exit(1)
        fetch_rows = fetch_gerrit_ids(ssh_key, ids)

    print_gerrit_fetch_table(fetch_rows, GERRIT_HOST)

    if not all_gerrit_fetches_succeeded(fetch_rows):
        failed = next(r for r in fetch_rows if r.status != "OK")
        print("ERROR: Gerrit access check failed — setup stopped before clone/cherry-pick.")
        if failed.gerrit_url:
            print(f"  Cannot access: {failed.gerrit_url}")
        elif failed.error:
            print(f"  {failed.error}")
        print("  Connect VPN or switch to a network with Gerrit web access.")
        print("  If you are logged in via browser, export your session cookie to GERRIT_HTTP_COOKIE.")
        print("  Then re-run:")
        print(f"    python scripts/setup_review.py \"{args.input}\" \"{base_dir}\"")
        sys.exit(1)

    raw_changes = [r.raw for r in fetch_rows if r.raw]
    changes = parse_changes(raw_changes)
    total = len(changes)
    print(f"=== All {total} change(s) accessible — continuing setup ===\n")

    # Group by branch (for display)
    by_branch: dict[str, list[int]] = {}
    for i, c in enumerate(changes):
        by_branch.setdefault(c["branch"], []).append(i)
    print("=== Changes by branch ===")
    for branch, indices in by_branch.items():
        print(f"  {branch}: {len(indices)} change(s)")
    print()

    # Unique (project, branch) pairs
    unique_pb: dict[str, dict] = {}
    for c in changes:
        key = f"{c['project']}|||{c['branch']}"
        if key not in unique_pb:
            unique_pb[key] = c

    # Assign workspace paths
    ws_paths: dict[str, str] = {}
    cloned_dirs: dict[str, Path] = {}
    ws_index: dict[str, int] = {}

    for key, c in unique_pb.items():
        ws_name = c["project"].replace("/", "_")
        if ws_name in ws_index:
            ws_index[ws_name] += 1
            ws_name = f"{ws_name}{ws_index[ws_name]}"
        else:
            ws_index[ws_name] = 1
        ws_paths[key] = ws_name
        cloned_dirs[key] = workspace_dir / ws_name

    # ─── Step 1: Clone all unique projects (parallel) ─────────────────
    def clone_one(key: str, c: dict) -> tuple[str, bool]:
        proj_dir = cloned_dirs[key]
        if args.no_clone:
            print(f"  [SKIP CLONE] {c['project']} @ {c['branch']}")
            return key, True
        if (proj_dir / ".git").is_dir():
            update_existing_clone(proj_dir, c["branch"], args.dry_run)
            return key, True
        ok = git_clone_project(c["project"], c["branch"], proj_dir, args.dry_run)
        return key, ok

    if not args.no_clone:
        workers = min(len(unique_pb), 8)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(clone_one, key, c): key
                for key, c in unique_pb.items()
            }
            for future in as_completed(futures):
                key, ok = future.result()
                if not ok:
                    print(f"  [WARN] Clone failed for {unique_pb[key]['project']}")

    # Ensure correct branches
    for key, c in unique_pb.items():
        proj_dir = cloned_dirs[key]
        if not (proj_dir / ".git").is_dir():
            continue
        result = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=proj_dir, check=False)
        current = result.stdout.strip()
        if current != c["branch"]:
            if args.dry_run:
                print(f"  [DRY-RUN] cd {proj_dir} && git checkout {c['branch']}")
            else:
                print(f"  Updating {c['project']} to branch {c['branch']} ...")
                run_git(["fetch", "origin", c["branch"]], cwd=proj_dir, check=False)
                run_git(["checkout", c["branch"]], cwd=proj_dir, check=False)
                run_git(["reset", "--hard", f"origin/{c['branch']}"], cwd=proj_dir, check=False)

    # ─── Step 2: Cherry-pick all changes (parallel across projects, serial within) ──
    print(f"\nCherry-picking {total} change(s)...")

    from collections import defaultdict
    project_groups: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for i, c in enumerate(changes):
        key = f"{c['project']}|||{c['branch']}"
        project_groups[key].append((i, c))

    last_cp_sha: dict[int, str] = {}
    cp_abort = threading.Event()

    def _cherry_pick_group(key: str, group: list[tuple[int, dict]]) -> dict[int, str]:
        """Cherry-pick a group of changes for one project serially."""
        group_shas: dict[int, str] = {}
        for i, c in group:
            if cp_abort.is_set():
                raise CherryPickConflictError(
                    f"Aborted after conflict elsewhere (skipped #{c['number']})"
                )
            proj_dir = cloned_dirs[key]
            ref_subdir = f"{int(c['number']) % 100:02d}"
            fetch_ref = f"refs/changes/{ref_subdir}/{c['number']}/{c['patchset']}"
            ssh_url = f"ssh://{GERRIT_USER}@{GERRIT_HOST}:{GERRIT_PORT}/{c['project']}"

            print(f"\n  --- Change #{c['number']}: {c['subject']} ---")

            try:
                sha = cherry_pick_change(proj_dir, ssh_url, fetch_ref, args.dry_run)
            except CherryPickConflictError:
                cp_abort.set()
                raise
            print(f"  [OK] Cherry-picked #{c['number']}")
            group_shas[i] = sha
        return group_shas

    try:
        if len(project_groups) == 1:
            for key, group in project_groups.items():
                last_cp_sha.update(_cherry_pick_group(key, group))
        else:
            workers = min(len(project_groups), 8)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(_cherry_pick_group, key, group): key
                    for key, group in project_groups.items()
                }
                try:
                    for future in as_completed(futures):
                        last_cp_sha.update(future.result())
                except CherryPickConflictError:
                    cp_abort.set()
                    for future in futures:
                        future.cancel()
                    raise
    except CherryPickConflictError as exc:
        print(f"\nERROR: Cherry-pick conflict — setup aborted immediately.")
        print(f"  {exc}")
        print("  No change_summary.json, no diffs, no further review steps.")
        sys.exit(1)

    # ─── Step 3: Write change_summary.json ────────────────────────────
    print("\n=== Generating change_summary.json ===")
    summary_file = run_dir / "change_summary.json"

    # Get branch head SHAs (pre-cherry-pick state)
    branch_head_sha: dict[str, str] = {}
    for i, c in enumerate(changes):
        key = f"{c['project']}|||{c['branch']}"
        if key in branch_head_sha:
            continue
        sha = last_cp_sha.get(i, "")
        proj_dir = cloned_dirs[key]
        if sha and (proj_dir / ".git").is_dir():
            result = run_git(["log", "-1", "--format=%P", sha], cwd=proj_dir, check=False)
            parent = result.stdout.strip().split()[0] if result.stdout.strip() else ""
            if parent:
                branch_head_sha[key] = parent

    summary_entries = []
    for i, c in enumerate(changes):
        key = f"{c['project']}|||{c['branch']}"
        ws_short = ws_paths[key]
        proj_dir = cloned_dirs[key]
        sha = last_cp_sha.get(i, "")

        desc = ""
        if sha and (proj_dir / ".git").is_dir() and not args.dry_run:
            desc = extract_commit_description(proj_dir, sha)

        gerrit_url = f"https://{GERRIT_HOST}/gerrit/c/{c['project']}/+/{c['number']}"

        entry = {
            "change_id": c["number"],
            "project": c["project"],
            "workspace_path": ws_short,
            "branch": c["branch"],
            "owner": c["owner"],
            "patchset": f"ps{c['patchset']}",
            "gerrit_url": gerrit_url,
        }
        if desc:
            entry["description"] = desc
        summary_entries.append(entry)

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_entries, f, indent=2)
        f.write("\n")
    print(f"  Saved: {summary_file}")

    # ─── Step 4: Extract precise diffs per change ─────────────────────
    print("\n=== Extracting precise diffs ===")
    reviews_dir.mkdir(exist_ok=True)

    pre_change_sha: dict[str, str] = {}

    for i, c in enumerate(changes):
        key = f"{c['project']}|||{c['branch']}"
        proj_dir = cloned_dirs[key]
        cp_sha = last_cp_sha.get(i, "")

        if not (proj_dir / ".git").is_dir() or not cp_sha:
            print(f"  [SKIP] {c['number']}: no workspace or SHA for {c['project']}")
            continue

        if key in pre_change_sha:
            parent = pre_change_sha[key]
        else:
            result = run_git(["log", "-1", "--format=%P", cp_sha], cwd=proj_dir, check=False)
            parent = result.stdout.strip().split()[0] if result.stdout.strip() else ""

        if not parent:
            print(f"  [SKIP] {c['number']}: could not find parent for {cp_sha}")
            continue

        pre_change_sha[key] = cp_sha

        commit_count_result = run_git(
            ["log", "--oneline", f"{parent}..{cp_sha}"], cwd=proj_dir, check=False
        )
        commit_count = len(commit_count_result.stdout.strip().split("\n")) if commit_count_result.stdout.strip() else 0
        if commit_count != 1:
            print(f"  [WARN] {c['number']}: expected 1 commit, got {commit_count}")

        diff_stat = run_git(["diff", "--stat", f"{parent}..{cp_sha}"], cwd=proj_dir, check=False)
        stat_lines = diff_stat.stdout.strip().split("\n")
        print(f"  [{c['number']}] {stat_lines[-1] if stat_lines else '(empty)'}")

        proj_path = c["project"].replace("/", "_")
        diff_file = reviews_dir / f"{proj_path}-{c['number']}.diff"
        extract_diff(proj_dir, parent, cp_sha, diff_file, args.dry_run)
        print(f"  Saved: {diff_file}")

    # ─── Done ──────────────────────────────────────────────────────────
    print(f"\n=== Setup complete ===")
    print(f"Shared base:    {base_dir}")
    print(f"Workspace:      {workspace_dir}")
    print(f"Per-run dir:    {run_dir}")
    print(f"Change summary: {summary_file}")
    print(f"Diff files:     {reviews_dir}/*.diff")
    print(f"\nNext step: dispatch code review agents using the diff files.")
    update_progress(run_dir, "setup")


if __name__ == "__main__":
    main()
