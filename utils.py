import os
import sys
import subprocess
from pathlib import Path

PS = "powershell.exe"

def run_ps(script, script_dir, args=None, timeout=15):
    cmd = [PS, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(Path(script_dir) / script)]
    if args:
        cmd.extend(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return {"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr, "code": r.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "timeout", "code": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}

# ── Open folder helper ────────────────────────────────
def open_folder(path_str):
    """Open a folder in Windows Explorer."""
    p = Path(path_str)
    if not p.exists():
        return False
    try:
        if sys.platform == "win32":
            os.startfile(str(p))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(p)])
        else:
            subprocess.run(["xdg-open", str(p)])
        return True
    except Exception:
        return False
