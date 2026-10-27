"""Safe publication of generated files.

Generation writes a complete tree into a new sibling staging directory and only
then moves it into place, so a failure never leaves partial output or touches
existing user files.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


def umask() -> int:
    """Return the process umask without changing it."""
    mask = os.umask(0o022)
    os.umask(mask)
    return mask


class OutputError(Exception):
    """Output cannot be published safely; nothing was written."""


def validate_artifact_paths(paths: Iterable[str]) -> None:
    """Check that relative artifact paths stay inside one new directory tree.

    Each path must be a normalized relative POSIX path. No two paths may name the
    same file on a case-insensitive file system, and no path may be a parent
    directory of another.

    Raises:
        OutputError: For the first invalid path or collision.
    """
    seen: dict[str, str] = {}
    directories: dict[str, str] = {}
    for path in paths:
        pure = PurePosixPath(path)
        if (
            not path
            or "\\" in path
            or pure.is_absolute()
            or ":" in pure.parts[0]
            or any(part in {"", ".", ".."} for part in path.split("/"))
        ):
            raise OutputError(f"artifact path {path!r} is not a safe relative path")
        key = path.casefold()
        if key in seen:
            raise OutputError(f"artifact paths {seen[key]!r} and {path!r} collide")
        seen[key] = path
        for parent in pure.parents:
            if str(parent) != ".":
                directories.setdefault(str(parent).casefold(), path)
    for key, path in seen.items():
        if key in directories:
            raise OutputError(
                f"artifact path {path!r} is also a directory of {directories[key]!r}"
            )


def check_destination(directory: Path) -> None:
    """Require an absent directory, or an empty real directory.

    Raises:
        OutputError: When the destination is a symbolic link, a file or a
            nonempty directory.
    """
    if directory.is_symlink():
        raise OutputError(f"output directory {directory} is a symbolic link")
    if directory.exists():
        if not directory.is_dir():
            raise OutputError(f"output path {directory} is not a directory")
        if any(directory.iterdir()):
            raise OutputError(f"output directory {directory} is not empty")


def publish_tree(directory: Path, files: Sequence[tuple[str, str]]) -> None:
    """Write ``files`` to a staging directory, then move it to ``directory``.

    Args:
        directory: The absent or empty destination.
        files: Relative POSIX paths and their text, already validated.

    Raises:
        OutputError: When the destination is unsuitable.
        OSError: When writing or moving fails; the staging tree is removed and
            the destination is unchanged.
    """
    check_destination(directory)
    parent = directory.parent
    parent.mkdir(parents=True, exist_ok=True)
    # mkdtemp creates 0700; publish with the existing directory's mode, or the
    # mode an ordinary mkdir would give under the user's umask.
    mode = directory.stat().st_mode & 0o7777 if directory.exists() else 0o777 & ~umask()
    staging = Path(tempfile.mkdtemp(prefix=f".{directory.name}.", dir=parent))
    try:
        staging.chmod(mode)
        for relative, text in files:
            target = staging.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        check_destination(directory)
        if directory.exists():
            directory.rmdir()
        os.replace(staging, directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
