"""Where outputs come from: the source commit, so every output traces back (Qualities)."""

from __future__ import annotations

import subprocess
from pathlib import Path


def source_version(root: Path) -> dict[str, object]:
    """The git commit of the library and whether it has uncommitted changes."""

    def git(*args: str) -> str | None:
        done = subprocess.run(
            ["git", "-C", str(root), *args], check=False, capture_output=True, text=True
        )
        return done.stdout.strip() if done.returncode == 0 else None

    commit = git("rev-parse", "HEAD")
    status = git("status", "--porcelain", "--", ".")
    return {"commit": commit, "uncommitted_changes": bool(status) if status is not None else None}
