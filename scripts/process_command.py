"""Run captured release-check commands without visible Windows child consoles."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path


def run(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float = 60,
) -> str:
    """Return stdout, raising on failure and terminating the tree on timeout."""
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW
    with subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=flags,
        start_new_session=sys.platform != "win32",
    ) as child:
        try:
            stdout, stderr = child.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                    check=False,
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                with suppress(ProcessLookupError):
                    os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate()
            raise subprocess.TimeoutExpired(
                command, timeout, output=stdout, stderr=stderr
            ) from None
        if child.returncode:
            raise subprocess.CalledProcessError(
                child.returncode, command, output=stdout, stderr=stderr
            )
    return stdout
