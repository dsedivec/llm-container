"""llmbox package."""

from __future__ import annotations

import subprocess
from typing import Final

__all__ = ["__version__", "version_with_commit"]

# Keep this simple assignment so Hatch's regex version source can parse it.
__version__ = "0.1.0"
VERSION: Final[str] = __version__


def _commit_hash() -> str | None:
    """Return the short git commit hash if available, otherwise None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() or None
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def version_with_commit() -> str:
    """Return version string including commit hash when available."""
    commit = _commit_hash()
    return f"{__version__} ({commit})" if commit else __version__
