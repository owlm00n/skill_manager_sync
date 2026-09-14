#!/usr/bin/env python3
"""
Create CODE_INDEX.md and Windows Junction for pulled code.

Usage:
  python create_shortcut.py --repo edk2 --branch sprdroid15_vnd_main --gerrit bsp/bootloader/edk2 [--target D:/06_Project/fixbug]

Creates:
  1. CODE_INDEX.md (or updates existing) in target directory
  2. Windows Junction: <target>/<repo> -> F:/05_Code/<branch>/<repo>
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_code_index_path(target_dir: str) -> str:
    """Get path to CODE_INDEX.md in target directory."""
    return os.path.join(target_dir, "CODE_INDEX.md")


def read_code_index(target_dir: str) -> tuple[list[str], list[dict]]:
    """Read existing CODE_INDEX.md. Returns (header_lines, entries)."""
    index_path = get_code_index_path(target_dir)
    if not os.path.exists(index_path):
        return [], []

    with open(index_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Split into header (before table) and parse table entries
    header = []
    entries = []
    in_table = False

    for line in lines:
        if line.strip().startswith("|") and not line.strip().startswith("|---"):
            parts = [p.strip() for p in line.strip("|\n").split("|")]
            if len(parts) >= 4 and parts[0] not in ("仓库", "Repo"):
                entries.append({
                    "repo": parts[0],
                    "branch": parts[1],
                    "local_path": parts[2],
                    "gerrit_path": parts[3],
                })
            in_table = True
        elif not in_table:
            header.append(line)

    return header, entries


def update_code_index(target_dir: str, repo: str, branch: str, gerrit_path: str) -> str:
    """Update CODE_INDEX.md with new entry."""
    index_path = get_code_index_path(target_dir)
    header, entries = read_code_index(target_dir)

    local_path = f"F:\\05_Code\\{branch}\\{repo}"

    # Check if entry already exists, update if so
    existing = False
    for entry in entries:
        if entry["repo"] == repo and entry["branch"] == branch:
            entry["local_path"] = local_path
            entry["gerrit_path"] = gerrit_path
            existing = True
            break

    if not existing:
        entries.append({
            "repo": repo,
            "branch": branch,
            "local_path": local_path,
            "gerrit_path": gerrit_path,
        })

    # Write updated index
    with open(index_path, "w", encoding="utf-8") as f:
        if header:
            f.writelines(header)
        else:
            f.write("# Code Index\n\n")
            f.write(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"> 生成工具: code-puller skill\n\n")

        f.write("| 仓库 | 分支 | 本地路径 | Gerrit 路径 |\n")
        f.write("|------|------|---------|-------------|\n")
        for entry in entries:
            f.write(f"| {entry['repo']} | {entry['branch']} | {entry['local_path']} | {entry['gerrit_path']} |\n")

    return index_path


def create_junction(target_dir: str, repo: str, branch: str) -> tuple[bool, str]:
    """Create a Windows Junction (directory symlink)."""
    source = f"F:\\05_Code\\{branch}\\{repo}"
    link = os.path.join(target_dir, repo)

    # Check if source exists
    if not os.path.exists(source):
        return False, f"Source directory does not exist: {source}"

    # Check if link already exists
    if os.path.exists(link):
        if os.path.islink(link) or _is_junction(link):
            return True, f"Junction already exists: {link} -> {source}"
        else:
            return False, f"Path exists but is not a junction: {link}"

    # Create junction using mklink /J
    try:
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", link, source],
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode == 0:
            return True, f"Junction created: {link} -> {source}"
        else:
            return False, f"mklink failed: {result.stderr.strip()}"
    except Exception as e:
        return False, f"Failed to create junction: {e}"


def _is_junction(path: str) -> bool:
    """Check if a path is a Windows Junction."""
    try:
        result = subprocess.run(
            ["cmd", "/c", "dir", "/AL", os.path.dirname(path)],
            capture_output=True,
            text=True,
            shell=False,
        )
        name = os.path.basename(path)
        return f"<JUNCTION>" in result.stdout and name in result.stdout
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Create CODE_INDEX.md and Windows Junction")
    parser.add_argument("--repo", required=True, help="Repository name (e.g. edk2)")
    parser.add_argument("--branch", required=True, help="Branch name (e.g. sprdroid15_vnd_main)")
    parser.add_argument("--gerrit", required=True, help="Gerrit repo path (e.g. bsp/bootloader/edk2)")
    parser.add_argument("--target", default=os.getcwd(), help="Target directory (default: current dir)")
    parser.add_argument("--no-junction", action="store_true", help="Skip junction creation")

    args = parser.parse_args()

    print(f"=== Code Puller: Creating Index & Shortcut ===")
    print(f"  Repo: {args.repo}")
    print(f"  Branch: {args.branch}")
    print(f"  Gerrit: {args.gerrit}")
    print(f"  Target: {args.target}")
    print()

    # 1. Update CODE_INDEX.md
    index_path = update_code_index(args.target, args.repo, args.branch, args.gerrit)
    print(f"[OK] CODE_INDEX.md updated: {index_path}")

    # 2. Create Junction
    if not args.no_junction:
        success, msg = create_junction(args.target, args.repo, args.branch)
        if success:
            print(f"[OK] {msg}")
        else:
            print(f"[WARN] {msg}")
            print(f"  You can manually access code at: F:\\05_Code\\{args.branch}\\{args.repo}")

    print()
    print(f"=== Done ===")


if __name__ == "__main__":
    main()