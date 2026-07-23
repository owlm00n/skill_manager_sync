import subprocess
from pathlib import Path


class GitManager:
    def __init__(self, repo_dir: Path):
        self.repo_dir = repo_dir

    def run(self, args):
        try:
            r = subprocess.run(["git"] + args, capture_output=True, text=True,
                               cwd=str(self.repo_dir), encoding="utf-8", errors="replace")
            return {"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr}
        except Exception as e:
            return {"ok": False, "stdout": "", "stderr": str(e)}
