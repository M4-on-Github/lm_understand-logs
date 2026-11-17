"""Log writing for the Claude re-runs. Nothing here overwrites an existing run."""

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_text(path, text):
    """Write UTF-8 with the line endings exactly as given (no CRLF conversion on Windows)."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path, obj):
    write_text(path, json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def append_line(path, line):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write(line + "\n")


def code_commit(repo_dir):
    """The current git commit, with '+dirty' if tracked or untracked files under test-claude differ from it."""
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True, check=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", "test-claude/common", "test-claude/exp01/code"],
            cwd=repo_dir, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return head + ("+dirty" if status else "")
    except Exception:
        return None


def new_run_dir(runs_dir, model, item_id):
    """Create runs/<model>/<item>/runN with the next free N. Never reuses a folder."""
    base = Path(runs_dir) / model / item_id
    n = 1
    while (base / f"run{n}").exists():
        n += 1
    run_dir = base / f"run{n}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def python_version():
    return sys.version.split()[0]
