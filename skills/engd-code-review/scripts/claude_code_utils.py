"""claude_code_utils.py — Claude Code subagent session discovery and liveness checks."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def encode_claude_project_dir(cwd: Path) -> str:
    """Encode a filesystem path the way Claude Code names ~/.claude/projects/<name>/ dirs."""
    resolved = str(cwd.resolve())
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in resolved)


def claude_projects_root() -> Path:
    return Path.home() / ".claude" / "projects"


def resolve_claude_session_dir(
    *,
    explicit: Path | str | None = None,
    session_id: str | None = None,
    cwd: Path | str | None = None,
) -> Path | None:
    """Resolve the Claude Code parent session directory containing subagents/.

    Resolution order:
      1. explicit path (--claude-session-dir or ledger value)
      2. CLAUDE_CODE_SESSION_DIR env var
      3. CLAUDE_CODE_SESSION_ID + encoded cwd under ~/.claude/projects/
    """
    if explicit:
        path = Path(explicit).expanduser().resolve()
        return path if path.is_dir() else None

    env_dir = os.environ.get("CLAUDE_CODE_SESSION_DIR", "").strip()
    if env_dir:
        path = Path(env_dir).expanduser().resolve()
        return path if path.is_dir() else None

    sid = (session_id or os.environ.get("CLAUDE_CODE_SESSION_ID", "")).strip()
    if not sid:
        return None

    work_cwd = Path(cwd or os.getcwd()).resolve()
    project_key = encode_claude_project_dir(work_cwd)
    candidate = claude_projects_root() / project_key / sid
    if candidate.is_dir():
        return candidate

    # Fallback: session id is unique — search all project buckets.
    root = claude_projects_root()
    if not root.is_dir():
        return None
    for project_dir in root.iterdir():
        if not project_dir.is_dir():
            continue
        candidate = project_dir / sid
        if candidate.is_dir():
            return candidate
    return None


def _parse_iso_epoch(iso_ts: str | None) -> float | None:
    if not iso_ts:
        return None
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return None


def check_subagent_liveness(
    session_dir: Path,
    *,
    idle_seconds: int = 300,
    batch_started_at: str | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Return liveness info based on subagents/*.jsonl mtimes.

    A subagent is considered alive when its jsonl file was modified within
    idle_seconds. If no batch jsonl has recent activity for idle_seconds while
    outputs are still missing, callers should allow early redispatch.
    """
    now = time.time() if now is None else now
    subagents_dir = session_dir / "subagents"
    if not subagents_dir.is_dir():
        return {
            "enabled": True,
            "session_dir": str(session_dir),
            "alive": True,
            "reason": "no_subagents_dir_yet",
            "jsonl_count": 0,
            "batch_jsonl_count": 0,
            "seconds_since_activity": None,
            "idle_seconds": idle_seconds,
        }

    batch_start = _parse_iso_epoch(batch_started_at)
    batch_grace = 30.0
    jsonl_files = sorted(subagents_dir.glob("agent-*.jsonl"))
    batch_files: list[Path] = []
    for path in jsonl_files:
        mtime = path.stat().st_mtime
        if batch_start is None or mtime >= batch_start - batch_grace:
            batch_files.append(path)

    if not batch_files:
        if batch_start is not None and (now - batch_start) >= idle_seconds:
            return {
                "enabled": True,
                "session_dir": str(session_dir),
                "alive": False,
                "reason": "no_batch_jsonl_after_idle",
                "jsonl_count": len(jsonl_files),
                "batch_jsonl_count": 0,
                "seconds_since_activity": int(now - batch_start),
                "idle_seconds": idle_seconds,
            }
        return {
            "enabled": True,
            "session_dir": str(session_dir),
            "alive": True,
            "reason": "waiting_for_batch_jsonl",
            "jsonl_count": len(jsonl_files),
            "batch_jsonl_count": 0,
            "seconds_since_activity": None,
            "idle_seconds": idle_seconds,
        }

    latest_mtime = max(path.stat().st_mtime for path in batch_files)
    seconds_since = now - latest_mtime
    alive = seconds_since < idle_seconds
    return {
        "enabled": True,
        "session_dir": str(session_dir),
        "alive": alive,
        "reason": "recent_jsonl_activity" if alive else "no_recent_jsonl_activity",
        "jsonl_count": len(jsonl_files),
        "batch_jsonl_count": len(batch_files),
        "seconds_since_activity": int(seconds_since),
        "idle_seconds": idle_seconds,
        "latest_jsonl": max(batch_files, key=lambda p: p.stat().st_mtime).name,
    }
