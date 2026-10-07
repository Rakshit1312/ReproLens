from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def _run(args: list[str], cwd: str | Path) -> str:
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=30)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "git command failed")
    return p.stdout.strip()


def repository_info(repo: str | Path) -> dict[str, Any]:
    repo = str(Path(repo).resolve())
    return {
        "root": repo,
        "commit": _run(["git", "rev-parse", "HEAD"], repo),
        "branch": _run(["git", "branch", "--show-current"], repo),
        "remote": _run(["git", "config", "--get", "remote.origin.url"], repo) if _has_remote(repo) else None,
    }


def _has_remote(repo: str) -> bool:
    p = subprocess.run(["git", "config", "--get", "remote.origin.url"], cwd=repo, capture_output=True, text=True)
    return p.returncode == 0 and bool(p.stdout.strip())
