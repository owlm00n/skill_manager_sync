#!/usr/bin/env python
"""
generate_html_report.py - Generate an HTML code-review report from a Gerrit
cherry-pick workspace.

Usage:
    python3 generate_html_report.py \
        --workspace <gerrit-cherry-pick-workspace> \
        --branch <branch> \
        [--output <run_dir>/report-<timestamp>-<topic_prefix>.html] \
        [--issues issues.json] \
        [--title "Review Report"] \
        [--repo-name <gerrit_repo_name>]

When --issues is provided, all git repos in the workspace are auto-discovered.

The script auto-discovers all git repos in the workspace,
collects all git commit diffs, and renders a self-contained HTML report
with side-by-side diffs, collapsible file sections, syntax highlighting,
and issue cards.

The --issues flag accepts a JSON file of manually authored findings:
[
  {
    "file": "src/main.c",
    "line": 42,
    "severity": "high",     // high | medium | low | info
    "category": "Security",
    "title": "Buffer Overflow",
    "description": "...",
    "suggested_fix": "..."
  }
]
"""

import argparse
import difflib
import getpass
import html
import json
import os
import re
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from shared import default_report_path, load_json_safe, try_load_json_safe, update_progress

# ---------------------------------------------------------------------------
# Load template assets
# ---------------------------------------------------------------------------

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "assets"

_CSS_PATH = _TEMPLATE_DIR / "report.css"
try:
    REPORT_CSS = _CSS_PATH.read_text(encoding="utf-8")
except Exception:
    REPORT_CSS = ""

HTML_TAIL = "</body>\n</html>\n"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


# Minimal Prism-inspired syntax highlighting via CSS classes
# These are applied via <span class="token-*"> wrapping
_SYNTAX_PATTERNS: list[tuple[str, str]] = [
    # Comments (# in Python/shell, // in C/Java/JS)
    (
        "comment",
        r"(^[\t ]*(#.*)$|^[ \t]*(//.*)$)",
    ),
    # Strings (single and double quoted)
    ("string", r"""'[^'\\]*(?:\\.[^'\\]*)*'"""),
    ("string_dq", r""""[^"\\]*(?:\\.[^"\\]*)*" """),
    # Keywords (Python / shell)
    ("keyword", r"\b(def|class|import|from|return|if|else|elif|for|while|in|not|and|or|is|None|True|False|with|as|yield|try|except|finally|raise|pass|break|continue|lambda|global|nonlocal|assert|del)\b"),
    ("keyword_c", r"\b(function|var|let|const|if|else|for|while|do|switch|case|break|continue|return|try|catch|throw|new|this|class|extends|super|async|await|typeof|instanceof|interface|type|enum|public|private|protected|static|void|native|abstract|final|synchronized|volatile|transient|implements|import|package|struct|union|typedef|goto|register|inline|extern|auto|signed|unsigned)\b"),
    # Numbers
    ("number", r"\b(\d+\.?\d*(?:[eE][+-]?\d+)?|0x[0-9a-fA-F]+|0b[01]+)\b"),
    # Function calls
    ("function", r"\b([a-zA-Z_]\w*)\s*(?=\()"),
    # Preprocessor / include directives
    ("preprocessor", r"^(#include|#define|#ifdef|#ifndef|#endif|#pragma|#if)\b"),
]


# ---------------------------------------------------------------------------
# Change summary table
# ---------------------------------------------------------------------------


def _change_summary_table(issues: list[dict], files: list[dict], topic: str | None = None,
                          change_descriptions: list[str] | None = None) -> str:
    """Build a change summary table showing project, change ID, patchset, workspace.

    Reads change_summary.json (written by setup_review.sh).
    Exits with an error if the file is missing - no git log fallback.

    Optionally renders a change description paragraph if provided.
    """
    workspace = os.environ.get("WORKSPACE_PATH", os.path.expanduser("~/code-review/gerrit-cherry-pick-workspace"))
    gerrit_host = os.environ.get("GERRIT_HOST", "gerrit.unisoc.com")
    gerrit_user = os.environ.get("GERRIT_USER", "")

    # Resolve symlinks for paths
    workspace = os.path.realpath(workspace)
    # change_summary.json lives in the per-run directory. It may be reachable
    # from the explicit env var, but fallbacks: parent of workspace and CWD.
    change_summary_candidates = []
    if os.environ.get("EXPLICIT_CHANGE_SUMMARY"):
        change_summary_candidates.append(os.path.realpath(os.environ.get("EXPLICIT_CHANGE_SUMMARY")))
    change_summary_candidates.append(os.path.join(os.path.dirname(workspace), "change_summary.json"))
    change_summary_candidates.append(os.path.join(os.getcwd(), "change_summary.json"))
    change_summary_path = None
    for candidate in change_summary_candidates:
        if os.path.isfile(candidate):
            change_summary_path = candidate
            break
    if change_summary_path is None:
        print(f"ERROR: change_summary.json not found at:", file=sys.stderr)
        for c in change_summary_candidates:
            print(f"  - {c}", file=sys.stderr)
        print("The setup_review.sh script should have created this file.", file=sys.stderr)
        print("Run the cherry-pick script first, or pass --change-summary explicitly.", file=sys.stderr)
        sys.exit(1)

    changes = load_json_safe(change_summary_path)

    # Count findings per change_id from the issues list
    finding_counts: dict[str, int] = {}
    for iss in issues:
        cid = str(iss.get("change_id", ""))
        if cid:
            finding_counts[cid] = finding_counts.get(cid, 0) + 1

    rows = ""
    for idx, ch in enumerate(changes, 1):
        change_num = ch.get("change_id", "")
        gerrit_url = ch.get("gerrit_url")
        if not gerrit_url:
            gerrit_url = f"{gerrit_url_base}{change_num}"
        cid_url = html.escape(gerrit_url)
        cid_link = f'<a href="{cid_url}" target="_blank" rel="noopener" class="change-link">{html.escape(change_num)}</a>'
        proj_display = html.escape(ch.get("project", ""))
        patchset = ch.get("patchset", "")
        ws_dir = html.escape(ch.get("workspace_path", ""))
        branch = html.escape(ch.get("branch", ""))
        owner = html.escape(ch.get("owner", ""))
        fc = finding_counts.get(str(change_num), 0)
        raw_desc = (ch.get("description") or "").strip()
        desc = "<br>".join(html.escape(line) for line in raw_desc.split("\n") if line.strip())
        rows += f'''  <tr>
    <td>{idx}</td>
    <td>{proj_display}</td>
    <td>{cid_link}</td>
    <td>{html.escape(patchset)}</td>
    <td>{ws_dir}</td>
    <td>{branch}</td>
    <td>{desc}</td>
    <td>{fc}</td>
    <td>{owner}</td>
  </tr>'''

    # Build review summary: read purpose files from review agents
    review_summary = ""
    reviews_dir = os.path.join(os.path.dirname(change_summary_path), "reviews")
    purposes = []
    if os.path.isdir(reviews_dir):
        import glob as _glob
        for pf in sorted(_glob.glob(os.path.join(reviews_dir, "_purpose_*.txt"))):
            try:
                text = open(pf, encoding="utf-8").read().strip()
                if text:
                    cid = os.path.basename(pf).replace("_purpose_", "").replace(".txt", "")
                    proj = ""
                    for ch in changes:
                        if str(ch.get("change_id", "")) == cid:
                            proj = ch.get("project", "")
                            break
                    purposes.append((proj, cid, text))
            except OSError:
                pass

    # Fallback: use description from change_summary.json
    if not purposes:
        for ch in changes:
            desc = (ch.get("description") or "").strip()
            if desc:
                purposes.append((ch.get("project", ""), str(ch.get("change_id", "")), desc))

    # Build review comments block
    review_comments = ""
    if purposes:
        if len(purposes) == 1:
            proj, cid, text = purposes[0]
            label = f"{html.escape(proj)}({html.escape(cid)})" if proj else html.escape(cid)
            review_comments = f"""  <div class="review-summary-section">
    <strong>Review Comments:</strong> {label}: {html.escape(text)}
  </div>"""
        else:
            items = ""
            for proj, cid, text in purposes:
                label = f"{html.escape(proj)}({html.escape(cid)})" if proj else html.escape(cid)
                items += f"      <li><strong>{label}</strong>: {html.escape(text)}</li>\n"
            review_comments = f"""  <div class="review-summary-section">
    <strong>Review Comments:</strong>
    <ul>
{items}    </ul>
  </div>"""

    if review_comments:
        review_summary = f"""<div class="review-summary">
{review_comments}
</div>
"""

    return f"""<h2>Review Summary</h2>
<table class="summary-table">
  <tr>
    <th>#</th>
    <th>Project</th>
    <th>Change ID</th>
    <th>Patchset</th>
    <th>Workspace</th>
    <th>Branch</th>
    <th>Change Description</th>
    <th>Finding Count</th>
    <th>Owner</th>
  </tr>
{rows}
</table>
{review_summary}"""


# ---------------------------------------------------------------------------
# Syntax highlighting helpers
# ---------------------------------------------------------------------------

def _build_regex() -> re.Pattern:
    """Return one big regex that captures all token types."""
    parts: list[str] = []
    for _cls, pat in _SYNTAX_PATTERNS:
        # Use inline named group to avoid duplicate group-name issues
        parts.append(f"(?P<{_cls}>{pat})")
    return re.compile("|".join(parts), re.MULTILINE)


_LINE_RE = _build_regex()


_CSS_CLASS_MAP = {
    "string_dq": "string",
    "keyword_c": "keyword",
}

def _highlight_line(line: str) -> str:
    """Apply minimal syntax highlighting to a single line."""
    m = _LINE_RE.search(line)
    if not m:
        return line
    # Build result by walking all groups
    result: list[str] = []
    last_end = 0
    for gname in _LINE_RE.groupindex:
        grp = m.group(gname)
        if grp is None:
            continue
        start = m.start(gname)
        end = m.end(gname)
        if start < last_end:
            continue  # overlap, skip
        # Map internal group names to CSS classes used in the report
        css_class = _CSS_CLASS_MAP.get(gname, gname)
        result.append(html.escape(line[last_end:start]))
        result.append(f'<span class="token-{css_class}">{html.escape(grp)}</span>')
        last_end = end
    result.append(html.escape(line[last_end:]))
    return "".join(result)


def _highlight(text: str) -> str:
    """Highlight an entire block of text line by line."""
    return "\n".join(_highlight_line(l) for l in text.split("\n"))


# Heuristic: check if a string looks like source code rather than prose.
_SOURCE_CODE_INDICATORS = [
    # C keywords, control flow, types
    "void", "int", "char", "static", "const", "return", "if", "else",
    "for", "while", "do", "switch", "case", "break", "continue",
    "struct", "enum", "union", "typedef", "include",
    # C syntax
    "(", ")", "{", "}", ";", "=>", "!", "==", "!=", "<=", ">=",
    "#", "*/", "//",
    # Log macros (kernel/common)
    "pr_", "printk",
    # Python
    "def ", "class ", "import ", "from ", "yield",
]


def _source_code_like(text: str) -> bool:
    """Return True if *text* looks like source code (vs. a human description)."""
    if not text:
        return False
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return False
    score = 0
    # Code: lines ending with ; or { or starting with #
    for l in lines:
        if l.endswith(";") or l.endswith("{") or l.endswith("}"):
            score += 2
        if l.startswith("#") or l.startswith("/*") or l.startswith("*"):
            score += 2
        if l.startswith("//"):
            score += 1  # standalone comment line is weaker signal
    # Description prose: lines starting with common article/preposition patterns
    PROSE_STARTS = [
        "(no ", "the ", "a ", "two ", "there ", "this ", "that ",
        "missing ", "the missing", "adding ", "introduces ",
        "avoid ", "does ", "cannot ", "would ", "should ",
        "change ", "replace ", "remove ",
    ]
    for l in lines:
        low = l.lower().lstrip("*-")
        for prefix in PROSE_STARTS:
            if low.startswith(prefix):
                score -= 3
                break
    # Require at least 2 points to be "code" (single-line C statements like
    # `pr_info(...);` or `spin_lock(&x);` only score +2 for the trailing `;`)
    return score >= 2


def _diff_lines(original: str, reviewed: str) -> tuple[list[str], list[str]]:
    """Compute a line-level diff and render two lists of highlighted lines.

    Returns (left_lines, right_lines) where each entry is a <span> with
    appropriate .del/.add/.common classes.
    """
    from difflib import Differ

    orig_lines = original.split("\n")
    rev_lines = reviewed.split("\n")
    differ = Differ()
    tags = list(differ.compare(orig_lines, rev_lines))

    left_html: list[str] = []
    right_html: list[str] = []
    left_num = 0
    right_num = 0

    for tag in tags:
        kind = tag[0]
        line = tag[2:]  # strip ' ' prefix
        hl = _highlight(line)

        if kind == " ":
            # Context line - increment both, render without del/add
            left_num += 1
            right_num += 1
            left_html.append(f'<span class="line-num">{left_num}</span>{hl}')
            right_html.append(f'<span class="line-num">{right_num}</span>{hl}')
        elif kind == "-":
            # Only in original
            left_num += 1
            left_html.append(f'<span class="line-num">{left_num}</span><span class="del">{hl}</span>')
        elif kind == "+":
            # Only in reviewed
            right_num += 1
            right_html.append(f'<span class="line-num">{right_num}</span><span class="add">{hl}</span>')
        else:
            # Change (delete+insert) - treat as del + add
            left_num += 1
            right_num += 1
            left_html.append(f'<span class="line-num">{left_num}</span><span class="del">{hl}</span>')
            right_html.append(f'<span class="line-num">{right_num}</span><span class="add">{hl}</span>')

    return left_html, right_html


# ---------------------------------------------------------------------------
# Diff parsing
# ---------------------------------------------------------------------------

def _git_diff_for_workspace(workspace: str, commit_ref: str = "HEAD~1..HEAD") -> list[dict]:
    """Return diffs for ALL git repos in the workspace directory."""
    workspace = os.path.realpath(workspace)
    all_files: list[dict] = []
    if os.path.isdir(workspace):
        for entry in sorted(os.listdir(workspace)):
            sub = os.path.join(workspace, entry)
            if os.path.isdir(sub) and os.path.isdir(os.path.join(sub, ".git")):
                all_files.extend(_git_diff(sub, commit_ref))
    return all_files


def _git_diff(project_dir: str, commit_ref: str = "HEAD~1..HEAD") -> list[dict]:
    """Return a list of {'file': ..., 'old': [...], 'new': [...]} dicts.

    Uses a multi-strategy approach to extract diffs, handling the common case
    where cherry-picked commits have divergent parent chains:

    1.  Standard ``git diff <commit_ref>`` - works when the commit graph is linear.
    2.  ``git diff HEAD`` - fallback when the standard ref yields nothing.
    3.  Walk each commit in the range with ``git show --format=""`` and extract
        the patch via ``diff-tree``.  This works for cherry-picked commits whose
        original parents may not exist in the local branch graph.
    """
    # Resolve symlinks (e.g., /home -> /home2) to match git's realpath
    project_dir = os.path.realpath(project_dir)
    # Find the git repo root
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=project_dir,
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        root = None

    if root is None:
        return []

    rel_project = os.path.relpath(project_dir, root)

    def _parse_diff(raw: str) -> list[dict]:
        """Parse a unified diff string into structured file lists."""
        all_files: list[dict] = []
        current_file: dict | None = None
        current_lines: list[tuple[int, int, str]] = []
        current_line_no: dict[str, int] | None = None

        for line in raw.splitlines():
            if line.startswith("diff --git"):
                if current_file is not None and current_lines:
                    current_file["lines"] = current_lines
                    all_files.append(current_file)
                m = re.search(r"b/(.+)", line)
                fname = m.group(1) if m else "?"
                # Quick filter: skip files outside project before allocating
                if rel_project != "." and not fname.startswith(rel_project + os.sep):
                    current_file = None
                    current_lines = []
                    current_line_no = None
                    continue
                current_file = {"file": fname, "old": [], "new": [], "lines": []}
                current_lines = []
                current_line_no = None
            elif current_file is not None and line.startswith("@@"):
                current_line_no = {}
                old_match = re.search(r"\-(\d+)", line)
                new_match = re.search(r"\+(\d+)", line)
                old_start = int(old_match.group(1)) if old_match else 0
                new_start = int(new_match.group(1)) if new_match else 0
                current_line_no["old"] = old_start
                current_line_no["new"] = new_start
            elif current_file is not None and line.startswith("---"):
                current_file["old"] = line.replace("--- ", "").strip()
            elif current_file is not None and line.startswith("+++"):
                # Strip the "+++ b/" prefix to get the real path
                val = re.sub(r"^\+\+\+ b/", "", line).rstrip()
                if val == "/dev/null":
                    val = ""
                current_file["new"] = val
            elif current_file is not None and line and line[0] in ("+", "-", " "):
                if current_line_no is None:
                    current_line_no = {}
                if line[0] == "+":
                    current_lines.append((1, current_line_no.get("new", 0), line[1:]))
                    current_line_no["new"] = current_line_no.get("new", 0) + 1
                elif line[0] == "-":
                    current_lines.append((-1, current_line_no.get("old", 0), line[1:]))
                    current_line_no["old"] = current_line_no.get("old", 0) + 1
                else:  # " " (context line)
                    current_lines.append((0, current_line_no.get("old", 0), line[1:]))
                    current_line_no["old"] = current_line_no.get("old", 0) + 1
                    current_line_no["new"] = current_line_no.get("new", 0) + 1

        if current_file is not None and current_lines:
            current_file["lines"] = current_lines
            all_files.append(current_file)

        return all_files

    # Strategy 1: standard git diff
    raw = subprocess.check_output(
        ["git", "diff", commit_ref, "--"],
        cwd=root,
        text=True,
    )
    if raw.strip():
        return _parse_diff(raw)

    # Strategy 2: git diff HEAD
    try:
        raw = subprocess.check_output(
            ["git", "diff", "HEAD", "--"],
            cwd=root,
            text=True,
        )
    except subprocess.CalledProcessError:
        raw = ""
    if raw.strip():
        return _parse_diff(raw)

    # Strategy 3: walk each commit in the range and use git show (diff-tree)
    # This handles cherry-picked commits whose parents diverge from the local graph.
    try:
        # git rev-list gives us commit SHAs in the range; for a single-commit
        # cherry-pick (HEAD~1..HEAD) this yields one SHA.
        range_str = commit_ref
        if ".." not in range_str:
            range_str = f"{range_str}..HEAD"
        result = subprocess.run(
            ["git", "rev-list", range_str],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            for sha in result.stdout.strip().split("\n"):
                sha = sha.strip()
                if not sha:
                    continue
                # git show --format="" produces the full patch for this commit
                # using its actual parent(s), regardless of graph position.
                show_result = subprocess.run(
                    ["git", "show", "--format=", "--", "."],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if show_result.returncode == 0 and show_result.stdout.strip():
                    all_files = _parse_diff(show_result.stdout)
                    if all_files:
                        return all_files
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        pass

    return []


def _build_side_by_side(lines: list[tuple[int, int, str]]) -> tuple[list[tuple[int | None, str]], list[tuple[int | None, str]]]:
    """Build two columns (left/old, right/new) for side-by-side diff."""
    left: list[tuple[int | None, str]] = []
    right: list[tuple[int | None, str]] = []

    i = 0
    # Group consecutive changes into hunks for context
    while i < len(lines):
        op, lnum, text = lines[i]

        if op == 0:  # context
            # Take up to 3 lines of context before a change
            ctx_lines = []
            while i < len(lines) and lines[i][0] == 0:
                ctx_lines.append(lines[i])
                i += 1
            for _, n, t in ctx_lines:
                left.append((n, t))
                right.append((n, t))
        elif op == -1:  # removed
            # Collect consecutive removals
            removed = []
            while i < len(lines) and lines[i][0] == -1:
                removed.append(lines[i])
                i += 1
            # Add 1 line of context after (if next is context)
            ctx_after = []
            while i < len(lines) and lines[i][0] == 0:
                ctx_after.append(lines[i])
                i += 1
            for _, n, t in removed:
                left.append((n, t))
                right.append((None, ""))
            for _, nl, nt in ctx_after:
                left.append((nl, nt))
                right.append((nl, nt))
        elif op == 1:  # added
            added = []
            while i < len(lines) and lines[i][0] == 1:
                added.append(lines[i])
                i += 1
            for _, n, t in added:
                left.append((None, ""))
                right.append((n, t))

    # Trailing context
    while i < len(lines) and lines[i][0] == 0:
        _, n, t = lines[i]
        left.append((n, t))
        right.append((n, t))
        i += 1

    return left, right


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _findings_html(
    issues: list[dict],
    gerrit_change_url_template: str = "",
    change_urls: dict[str, str] | None = None,
) -> str:
    """Generate finding cards in the reference style (side-by-side comparison blocks)."""
    cards = ""
    for idx, iss in enumerate(issues, 1):
        # Normalize severity (handle both uppercase and lowercase)
        sev = iss.get("severity", "info").lower()
        sev_cls = sev if sev in ("high", "medium", "low", "info") else "info"
        sev_label = sev.upper()

        file_ref = html.escape(iss.get("file", ""))
        line_ref = iss.get("line")
        if line_ref:
            file_ref += f":{line_ref}"
        fix_file = iss.get("fix_file", "").strip()
        is_cross_file = bool(fix_file)
        if is_cross_file:
            fix_esc = html.escape(fix_file)
            file_ref += f" (fix: {fix_esc})"
        cat = html.escape(iss.get("category", "General"))
        # Support both 13-field format (finding/explanation/fix) and template format (title/description/suggested_fix)
        title_esc = html.escape(iss.get("finding", iss.get("title", iss.get("summary", ""))))
        desc = iss.get("explanation", iss.get("description", iss.get("detail", "")))
        suggested_fix = iss.get("fix", iss.get("suggested_fix", ""))
        architectural_comment = iss.get("architectural_comment", "")
        original_code = iss.get("original_code", "")
        reviewed_code = iss.get("reviewed_code", "")
        change_id = iss.get("change_id", "")
        if isinstance(change_id, int):
            change_id = str(change_id)
        project = iss.get("project", "")
        owner = iss.get("owner", "")

        # Build change/project header line
        meta_parts = ""
        if project:
            meta_parts += f'<span class="finding-project">{html.escape(project)}</span> '
        if change_id:
            esc = html.escape(change_id)
            if change_urls and str(change_id) in change_urls:
                url = change_urls[str(change_id)]
            else:
                url = f"{gerrit_change_url_template}{esc}"
            meta_parts += f'<span class="change-ref">Change <a href="{html.escape(url)}" class="change-link" target="_blank">{esc}</a></span>'
        if owner:
            meta_parts += f' <span class="change-ref">Owner: {html.escape(owner)}</span>'
        if is_cross_file:
            fix_esc = html.escape(fix_file)
            meta_parts += f' <span class="change-ref">Fix in: {fix_esc}</span>'
        meta_html = f'<div class="finding-meta">{meta_parts}</div>\n' if meta_parts else ""

        # Build description paragraphs
        desc_parts = desc.split("\n\n") if desc else [desc]
        desc_blocks = ""
        for part in desc_parts:
            if part.strip():
                escaped = html.escape(part)
                # Replace escaped code markers like <code>...</code> from JSON
                # Users may have already HTML-escaped their code
                desc_blocks += f'<div class="description"><strong>Description:</strong> {escaped}</div>\n\n'

        # Side-by-side code comparison (diff view - unified context)
        comparison_block = ""
        if original_code or reviewed_code:
            _orig_ok = _source_code_like(original_code) if original_code else False
            _rev_ok = _source_code_like(reviewed_code) if reviewed_code else False
            if not _orig_ok or not _rev_ok:
                # Emit a visible warning in the report so the reviewer knows the
                # diff view is unreliable for this finding.
                comparison_block = f"""
      <div class="code-comparison" style="border:2px solid #f85149;">
        <div style="padding:6px 10px;background:#f85149;color:#fff;font-size:13px;grid-column:1/-1;">
          <strong>Warning:</strong> {'original_code' if not _orig_ok else 'reviewed_code'} contains non-source text - the side-by-side diff below may be misleading.
        </div>
        <div class="code-original">
          <div class="code-header">Original Code - {file_ref}</div>
          <div class="code-body"><pre>{_highlight(html.escape(original_code))}</pre></div>
        </div>
        <div class="code-fixed">
          <div class="code-header">Corrected Code - Proposed Fix</div>
          <div class="code-body"><pre>{_highlight(html.escape(reviewed_code or ''))}</pre></div>
        </div>
      </div>"""
            else:
                left_lines, right_lines = _diff_lines(original_code, reviewed_code)
                left_html = "\n".join(left_lines) if left_lines else "<span class='del'>// (removed)</span>"
                right_html = "\n".join(right_lines) if right_lines else "<span class='add'>// (added)</span>"

                comparison_block = f"""
      <h4>Side-by-Side Code Review</h4>
      <div class="code-comparison">
        <div class="code-original">
          <div class="code-header">Original Code - {file_ref}</div>
          <div class="code-body"><pre>{left_html}</pre></div>
        </div>
        <div class="code-fixed">
          <div class="code-header">Corrected Code - Proposed Fix</div>
          <div class="code-body"><pre>{right_html}</pre></div>
        </div>
      </div>"""

        # No code comparison for findings without original/reviewed code
        # Omit side-by-side code blocks when snippets are not real source code

        # Additional architectural comment
        extra_block = ""
        if architectural_comment:
            extra_block = f'''
      <div class="description"><strong>Architecture Comment:</strong> {html.escape(architectural_comment)}</div>'''

        # Suggested Fix section
        suggested_fix_block = ""
        if suggested_fix:
            suggested_fix_block = f'''
      <div class="description"><strong>Suggested Fix:</strong> {html.escape(suggested_fix)}</div>'''

        # Cross-project indicator
        is_cross_project = iss.get("cross_project", False)
        cross_badge = ""
        cross_block = ""
        cross_cls = " cross-project" if is_cross_project else ""
        if is_cross_project:
            cross_badge = '<span class="cross-project-badge">CROSS-PROJECT</span>'
            related = iss.get("related_changes", [])
            if related:
                rel_items = ""
                for rc in related:
                    rp = html.escape(rc.get("project", ""))
                    rcid = html.escape(str(rc.get("change_id", "")))
                    rf = html.escape(rc.get("file", ""))
                    rl = rc.get("line", 0)
                    rel_items += f'      <li><strong>{rp}</strong>({rcid}): {rf}:{rl}</li>\n'
                cross_block = f'''
      <div class="description cross-project-related">
        <strong>Related changes:</strong>
        <ul>
{rel_items}        </ul>
      </div>'''

        cards += f"""
    <!-- Finding {idx} -->
    <div class="finding risk-{sev_cls}{cross_cls}" id="finding-f{idx}">
      <div class="finding-header">
        <a href="#summary-f{idx}" class="finding-id" title="Back to Executive Summary">F{idx}</a>
        <span class="finding-file">{file_ref}</span>
        <span class="risk-badge {sev_cls}">{sev_label}</span>
        {cross_badge}
      </div>
      {meta_html}
      <h3>{title_esc}</h3>
      {desc_blocks}
      {suggested_fix_block}
      {extra_block}
      {comparison_block}
      {cross_block}
    </div>"""
    return cards


def _summary_table(issues: list[dict]) -> str:
    """Build the compact findings summary table."""
    rows = ""
    for idx, iss in enumerate(issues, 1):
        # Normalize severity (handle both uppercase and lowercase)
        sev = iss.get("severity", "info").lower()
        sev_cls = f"risk-{sev}" if sev in ("high", "medium", "low", "info") else "risk-info"
        sev_upper = sev.upper()
        file_ref = html.escape(iss.get("file", ""))
        line_ref = iss.get("line")
        if line_ref:
            file_ref += f":{line_ref}"
        fix_file = iss.get("fix_file", "").strip()
        if fix_file:
            file_ref += f" (fix: {html.escape(fix_file)})"
        cat = html.escape(iss.get("category", "General"))
        change_id = iss.get("change_id", "")
        if isinstance(change_id, int):
            change_id = str(change_id)
        project = iss.get("project", "")
        title_esc = html.escape(iss.get("finding", iss.get("title", iss.get("summary", ""))))
        owner = iss.get("owner", "")
        # Cross-project: show project chain in project column
        is_cp = iss.get("cross_project", False)
        cp_cls = " cross-project" if is_cp else ""
        proj_display = html.escape(project)
        if is_cp:
            related = iss.get("related_changes", [])
            related_projs = [html.escape(rc.get("project", "")) for rc in related]
            if related_projs:
                proj_display = f"{proj_display} &rarr; {' &rarr; '.join(related_projs)}"
        rows += f'''  <tr id="summary-table-f{idx}"{cp_cls}>
    <td><a href="#finding-f{idx}" class="finding-jump" title="Jump to finding details">F{idx}</a></td>
    <td class="{sev_cls}">{sev_upper}</td>
    <td>{file_ref}</td>
    <td>{cat}</td>
    <td>{proj_display}</td>
    <td>{html.escape(change_id)}</td>
    <td>{html.escape(owner)}</td>
    <td>{title_esc}</td>
  </tr>'''
    return rows


def _arch_diagram() -> str:
    """Generate architecture diagram if present in issues (from architectural_comment or a special key)."""
    return ""


def _executive_summary(
    issues: list[dict],
    change_description: str = "",
    gerrit_change_url_template: str = "",
    change_urls: dict[str, str] | None = None,
) -> str:
    """Build executive summary with stats table and findings overview."""
    high = sum(1 for i in issues if i.get("severity", "info").lower() == "high")
    medium = sum(1 for i in issues if i.get("severity", "info").lower() == "medium")
    low = sum(1 for i in issues if i.get("severity", "info").lower() == "low")
    info = sum(1 for i in issues if i.get("severity", "info").lower() == "info")

    parts = []
    if high:
        parts.append(f"{high} High")
    if medium:
        parts.append(f"{medium} Medium")
    if low:
        parts.append(f"{low} Low")
    if info:
        parts.append(f"{info} Info")

    summary_text = ", ".join(parts) if parts else "none"

    findings_list = ""
    for idx, iss in enumerate(issues, 1):
        sev = iss.get("severity", "info").lower()
        sev_cls = f"risk-{sev}" if sev in ("high", "medium", "low", "info") else "risk-info"
        sev_label = sev.capitalize()
        file_ref = html.escape(iss.get("file", ""))
        line_ref = iss.get("line")
        if line_ref:
            file_ref += f":{line_ref}"
        fix_file = iss.get("fix_file", "").strip()
        if fix_file:
            file_ref += f" (fix: {html.escape(fix_file)})"
        cat = html.escape(iss.get("category", "General"))
        change_id = iss.get("change_id", "")
        if isinstance(change_id, int):
            change_id = str(change_id)
        project = iss.get("project", "")
        owner = iss.get("owner", "")
        sev_display = f'<td class="{sev_cls}">{sev_label}</td>'
        title_esc = html.escape(iss.get("finding", iss.get("title", iss.get("summary", ""))))
        # Build Change column with clickable gerrit link
        if change_id:
            if change_urls and str(change_id) in change_urls:
                gerrit_change_url = change_urls[str(change_id)]
            else:
                gerrit_change_url = f'{gerrit_change_url_template}{change_id}'
            findings_list += f'''  <tr id="summary-f{idx}"><td><a href="#finding-f{idx}" class="finding-jump" title="Jump to finding details">F{idx}</a></td>{sev_display}<td>{file_ref}</td><td>{cat}</td><td>{html.escape(project)}</td><td><a href="{html.escape(gerrit_change_url)}" target="_blank" rel="noopener" class="change-link">{html.escape(change_id)}</a></td><td>{html.escape(owner)}</td><td>{title_esc}</td></tr>
'''
        else:
            findings_list += f'''  <tr id="summary-f{idx}"><td><a href="#finding-f{idx}" class="finding-jump" title="Jump to finding details">F{idx}</a></td>{sev_display}<td>{file_ref}</td><td>{cat}</td><td>{html.escape(project)}</td><td>{html.escape(change_id)}</td><td>{html.escape(owner)}</td><td>{title_esc}</td></tr>
'''

    return f"""<h2>Executive Summary</h2>
<p>Cross-layer code review identified <strong>{len(issues)} findings</strong>: {summary_text}.</p>

<table class="summary-table">
  <tr><th>Severity</th><th>Count</th><th>Summary</th></tr>
  <tr><td class="risk-high">High</td><td>{high}</td><td>Security and correctness issues requiring immediate action</td></tr>
  <tr><td class="risk-medium">Medium</td><td>{medium}</td><td>Significant issues that should be fixed before release</td></tr>
  <tr><td class="risk-low">Low</td><td>{low}</td><td>Code quality and maintainability concerns</td></tr>
  <tr><td class="risk-info">Info</td><td>{info}</td><td>Minor improvements and best-practice suggestions</td></tr>
</table>

<table class="summary-table">
  <tr><th>#</th><th>Severity</th><th>File</th><th>Category</th><th>Project</th><th>Change</th><th>Owner</th><th>Summary</th></tr>
{findings_list}</table>"""


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_change_urls(change_summary_path: str | None) -> dict[str, str] | None:
    """Load explicit gerrit URLs from change_summary.json, keyed by change_id."""
    if not change_summary_path or not os.path.isfile(change_summary_path):
        return None
    _changes = try_load_json_safe(change_summary_path)
    if _changes is None:
        return None
    urls: dict[str, str] = {}
    for ch in _changes:
        cid = str(ch.get("change_id", ""))
        gurl = ch.get("gerrit_url", "")
        if cid and gurl:
            urls[cid] = gurl
    return urls if urls else None


# Report generation
# ---------------------------------------------------------------------------


def generate_html(
    files: list[dict],
    issues: list[dict],
    title: str = "Code Review Report",
    branch: str = "unknown",
    project: str = "unknown",
    repo_name: str = "",
    review_date: str | None = None,
    architecture_diagram: str = "",
    topic: str | None = None,
    change_summary_json: str | None = None,
    change_description: str | None = None,
    change_descriptions: list[str] | None = None,
    gerrit_user: str | None = None,
    gerrit_host: str | None = None,
    gerrit_change_url_template: str | None = None,
    change_summary_urls: dict[str, str] | None = None,
) -> str:
    """Generate the full HTML string."""
    now = review_date or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    gerrit_user = gerrit_user or os.environ.get("GERRIT_USER", "")
    gerrit_host = gerrit_host or os.environ.get("GERRIT_HOST", "gerrit.unisoc.com")
    gerrit_change_url_template = gerrit_change_url_template or f"https://{gerrit_host}/c/"

    # Count stats
    total_files = len(files)
    high_issues = sum(1 for i in issues if i.get("severity", "info").lower() == "high")
    medium_issues = sum(1 for i in issues if i.get("severity", "info").lower() == "medium")
    low_issues = sum(1 for i in issues if i.get("severity", "info").lower() == "low")
    total_issues = len(issues)

    # Build issue cards in reference style
    gerrit_change_url_template_for_findings = f"{gerrit_change_url_template}"
    issue_cards = _findings_html(issues, gerrit_change_url_template_for_findings, change_summary_urls) if issues else ""

    # Build executive summary
    exec_desc = change_description or ""
    exec_summary = _executive_summary(issues, exec_desc, gerrit_change_url_template_for_findings, change_summary_urls) if issues else ""

    # Build change summary table (grouped by project/change_id)
    # If change_summary_json was passed as CLI arg, save to workspace for use
    change_summary_from_cli = change_summary_json
    change_descs = change_descriptions or []
    change_summary = _change_summary_table(issues, files, topic, change_descs)

    # Build summary table
    summary_table = _summary_table(issues) if issues else ""

    # Finding sections: only show when there are issues
    finding_sections = ""
    if issues:
        finding_sections = f"""
<h2>Finding Details</h2>

{issue_cards}
"""

    # Architecture diagram
    arch_diagram = ""
    if architecture_diagram:
        arch_diagram = f'''
  <div class="diagram">
    <h2 style="color:#00d4ff;border:none;padding:0;margin-bottom:0.5rem;">Architecture &amp; Flow</h2>
    <pre>{html.escape(architecture_diagram)}</pre>
  </div>'''

    # Compute review verdict
    high = sum(1 for i in issues if i.get("severity", "info").lower() == "high")
    medium = sum(1 for i in issues if i.get("severity", "info").lower() == "medium")
    low = sum(1 for i in issues if i.get("severity", "info").lower() == "low")
    info = sum(1 for i in issues if i.get("severity", "info").lower() == "info")
    if high > 0:
        verdict = "Denied"
        verdict_color = "#ff4444"
    elif medium > 0:
        verdict = "Changes Requested"
        verdict_color = "#ffcc00"
    else:
        verdict = "Approved"
        verdict_color = "#88cc44"

    # Extract review date from run directory name (e.g., review-20260621123456 -> 2026-06-21)
    review_date_str = ""
    if change_summary_json:
        import re as _re
        run_dir_name = os.path.basename(os.path.dirname(os.path.realpath(change_summary_json)))
        _ts_match = _re.search(r'(\d{4})(\d{2})(\d{2})\d{6}', run_dir_name)
        if _ts_match:
            review_date_str = f"{_ts_match.group(1)}-{_ts_match.group(2)}-{_ts_match.group(3)}"
    if not review_date_str:
        review_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    html_str = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{html.escape(title)} - {verdict} - Code Review Report</title>
<style>
{REPORT_CSS}
.verdict-badge {{
  display: inline-block;
  padding: 2px 10px;
  border: 2px solid {verdict_color};
  border-radius: 4px;
  color: {verdict_color};
  font-weight: bold;
  font-size: 0.9rem;
  margin-left: 0.5rem;
}}
</style>
</head>
<body>

<h1>{html.escape(title)} <span class="verdict-badge">{verdict}</span></h1>
<p class="review-date">{review_date_str}</p>

{change_summary}

{exec_summary}

{arch_diagram}
{finding_sections}

<script>
function toggleFilter(btn) {{
  const sev = btn.dataset.filter;
  const isActive = btn.classList.toggle('active');
  document.querySelectorAll('.finding').forEach(card => {{
    if (!sev) {{
      card.style.display = '';
      return;
    }}
    // Map filter to severity class
    const map = {{'high': 'risk-high', 'medium': 'risk-medium', 'low': 'risk-low', 'info': 'risk-info'}};
    if (map[sev]) {{
      const show = !isActive; // active = show this severity
      card.style.display = show ? '' : 'none';
    }}
  }});
}}
function showAll() {{
  document.querySelectorAll('.filter-btn[data-filter]').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.finding').forEach(c => c.style.display = '');
}}
</script>

{HTML_TAIL.strip()}
"""
    return html_str


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _resolve_run_dir(issues: str | None, change_summary: str | None) -> Path | None:
    """Infer per-run review dir from issues.json or change_summary.json path."""
    for path_arg in (issues, change_summary):
        if not path_arg:
            continue
        p = Path(path_arg).resolve()
        if p.is_file():
            return p.parent
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an HTML code-review report from a Gerrit cherry-pick workspace.",
    )
    parser.add_argument("--workspace", required=True, help="Shared workspace directory (e.g. ~/code-review/review-XXX/workspace, or the per-run review-<timestamp>/ dir)")
    parser.add_argument("--branch", required=True, help="Branch name (e.g., android14L-release)")
    parser.add_argument("--topic", default=None, help="Gerrit topic name (e.g., 3300608) for change discovery")
    parser.add_argument(
        "--output",
        default=None,
        help="Output HTML file path (default: <run_dir>/report-<timestamp>-<topic_prefix>.html)",
    )
    parser.add_argument("--issues", default=None, help="JSON file with authored findings")
    parser.add_argument("--title", default="Code Review Report", help="Report title")
    parser.add_argument("--repo-name", default="", help="Gerrit repository name for display")
    parser.add_argument("--review-date", default=None, help="Review date string (default: now)")
    parser.add_argument("--commit-ref", default="HEAD~1..HEAD", help="Git commit range for diff (default: HEAD~1..HEAD)")
    parser.add_argument("--change-summary", default=None, help="Path to change_summary.json (pre-built change list to avoid slow git log scans)")
    parser.add_argument("--change-description", default=None, action="append", help="Substantive description of the change (from commit message). Can be repeated for multiple changes.")

    args = parser.parse_args()

    # Auto-discover workspace subdirectories containing git repos
    ws_real = os.path.realpath(args.workspace) if args.workspace else "."
    project_names = []
    for entry in sorted(os.listdir(ws_real)):
        sub = os.path.join(ws_real, entry)
        if os.path.isdir(os.path.join(sub, ".git")):
            project_names.append(entry)
    if not project_names:
        print(f"ERROR: No git repos found in workspace: {ws_real}")
        print(f"  Ensure the workspace contains git repos with .git dirs")
        sys.exit(1)
    print(f"  Auto-discovered projects: {', '.join(project_names)}", file=sys.stderr)

    # Resolve project dir(s)
    # Resolve symlinks (e.g., /home -> /home2) so git paths match git paths
    args.workspace = os.path.realpath(args.workspace)

    # Normalize project names: "kernel/common" -> "kernel_common"
    normalized_projects = [p.replace("/", "_") for p in project_names]

    # Collect diffs from ALL discovered projects
    project_dirs: list[str] = []
    files: list[dict] = []
    for np in normalized_projects:
        pd = os.path.join(args.workspace, np)
        if os.path.isdir(pd) and os.path.isdir(os.path.join(pd, ".git")):
            project_dirs.append(pd)
            files.extend(_git_diff(pd, args.commit_ref))
            print(f"  OK: Collected diffs from {pd}", file=sys.stderr)

    if not files:
        print("WARNING: No diffs found in any of the discovered project directories.")
        for np in normalized_projects:
            pd = os.path.join(args.workspace, np)
            print(f"  Checked: {pd}  exists={os.path.isdir(pd)}  .git={os.path.isdir(os.path.join(pd, '.git'))}")

    # Load issues (defensive: auto-fix control characters from LLM output)
    issues: list[dict] = []
    if args.issues and os.path.isfile(args.issues):
        issues = load_json_safe(args.issues)

    # Validate and normalize line fields (must be int, not range strings like "1429-1430")
    for i, iss in enumerate(issues):
        raw = iss.get("line")
        if not raw:
            continue
        # Handle range strings like "1429-1430"
        if isinstance(raw, str) and "-" in raw.replace(" ", ""):
            try:
                parts = raw.split("-", 1)
                iss["line"] = int(parts[0].strip())
            except ValueError:
                print(f"WARNING: Invalid line range at issues[{i}]: {raw!r} - keeping as-is", file=sys.stderr)
        elif not isinstance(raw, int):
            try:
                iss["line"] = int(raw)
            except (ValueError, TypeError):
                print(f"WARNING: Invalid line number at issues[{i}]: {raw!r} - keeping as-is", file=sys.stderr)

    # Load change summary JSON (written by setup_review.sh)
    change_summary_json = args.change_summary
    # Resolve to workspace copy if not explicitly provided
    if not change_summary_json:
        for candidate in [
            # Parent of workspace = per-run directory (new structure)
            os.path.join(os.path.dirname(os.path.realpath(args.workspace)), "change_summary.json"),
            os.path.join(os.getcwd(), "change_summary.json"),
        ]:
            if os.path.isfile(candidate):
                change_summary_json = candidate
                break

    issue_owner_map: dict[str, str] = {}
    if change_summary_json and os.path.isfile(change_summary_json):
        # Copy change_summary.json into the same dir as the report output
        # for the template to find it.
        ws_real = os.path.realpath(args.workspace) if args.workspace else "."

        # If --change-summary was explicitly provided, use its directory (the per-run dir)
        # as the destination, so the copy lands next to the input file rather than
        # potentially in the wrong parent of workspace.
        if args.change_summary:
            dest_dir = os.path.dirname(os.path.realpath(change_summary_json))
        else:
            # Fallback: parent of workspace = per-run directory
            dest_dir = os.path.dirname(ws_real)
        dest = os.path.join(dest_dir, "change_summary.json")
        src_real = os.path.realpath(change_summary_json)
        try:
            dest_real = os.path.realpath(dest)
            is_same = os.path.samefile(src_real, dest_real)
        except FileNotFoundError:
            is_same = False
        if not is_same:
            import shutil
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(change_summary_json, dest)

        # Build change_id -> owner mapping (defensive JSON parsing)
        _cs = load_json_safe(change_summary_json)
        for ch in _cs:
            cid = str(ch.get("change_id", ""))
            ow = ch.get("owner", "")
            if cid and ow:
                issue_owner_map[cid] = ow

    # Enrich issues with owner from change_summary.json
    for iss in issues:
        cid = str(iss.get("change_id", ""))
        if cid and cid in issue_owner_map and not iss.get("owner"):
            iss["owner"] = issue_owner_map[cid]

    # Generate report - use real project path in display
    os.environ["WORKSPACE_PATH"] = args.workspace
    os.environ["EXPLICIT_CHANGE_SUMMARY"] = os.path.realpath(args.change_summary) if args.change_summary else ""
    # Gather change descriptions from CLI args
    change_descs = list(args.change_description) if args.change_description else []
    change_desc = change_descs[0] if change_descs else ""

    report = generate_html(
        files=files,
        issues=issues,
        title=args.title,
        branch=args.branch,
        project=normalized_projects[0] if normalized_projects else "unknown",
        repo_name=args.repo_name or (normalized_projects[0] if normalized_projects else ""),
        review_date=args.review_date,
        topic=args.topic,
        change_summary_json=args.change_summary,
        change_description=change_desc,
        change_descriptions=change_descs,
        change_summary_urls=_load_change_urls(args.change_summary),
    )

    # Write output
    out_path = args.output
    run_dir = _resolve_run_dir(args.issues, args.change_summary)
    if not out_path:
        if run_dir is not None:
            out_path = str(default_report_path(run_dir))
        else:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            parent = Path(args.workspace).resolve().parent.name
            out_path = str(
                Path(args.workspace).resolve().parent / f"report-{ts}-{parent}.html"
            )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report written to: {out_path}")
    print(f"  Files changed:    {len(files)}")
    print(f"  Issues recorded:  {len(issues)}")

    _run_dir = run_dir or Path(out_path).resolve().parent
    update_progress(_run_dir, "report")


if __name__ == "__main__":
    main()
