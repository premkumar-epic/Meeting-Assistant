from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path


def create_temp_dir(base_dir: str | None = None, prefix: str = "meeting_assistant_") -> Path:
    """Create and return an isolated temporary directory."""
    return Path(tempfile.mkdtemp(prefix=prefix, dir=base_dir))


def build_temp_file_path(temp_dir: str | Path, suffix: str, prefix: str = "artifact") -> Path:
    """Build a collision-safe temporary file path inside temp_dir."""
    directory = Path(temp_dir)
    directory.mkdir(parents=True, exist_ok=True)
    safe_suffix = suffix if suffix.startswith(".") else f".{suffix}"
    return directory / f"{prefix}_{uuid.uuid4().hex}{safe_suffix}"


def safe_unlink(path: str | Path) -> None:
    """Delete file if it exists."""
    try:
        Path(path).unlink(missing_ok=True)
    except IsADirectoryError:
        return


def safe_rmtree(path: str | Path) -> None:
    """Delete directory tree if it exists."""
    target = Path(path)
    if target.exists() and target.is_dir():
        shutil.rmtree(target, ignore_errors=True)


def ensure_parent_dir(path: str | Path) -> None:
    """Create parent directory for a target file path."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
