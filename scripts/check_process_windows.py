"""Refuse a Windows process guest that imports an external VC or Python runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from scripts.process_command import run


def sha256(path: Path) -> str:
    """Hash a file without reading the complete executable into memory."""
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def dependencies(output: str) -> list[str]:
    """Read dumpbin imports and reject external compiler or interpreter runtimes."""
    imported = sorted(
        {name.lower() for name in re.findall(r"(?i)\b[a-z0-9_.-]+\.dll\b", output)}
    )
    if not imported:
        raise RuntimeError("Dependency inspection returned no Windows system DLLs")
    if any(re.match(r"(vcruntime|msvcp|concrt|python)\d", name) for name in imported):
        raise RuntimeError(
            f"Standalone process imports an external runtime: {imported}"
        )
    return imported


def inspect(executable: Path) -> dict[str, Any]:
    """Use the installed MSVC inspector and retain exact artifact/tool identities."""
    binary = executable.resolve(strict=True)
    program_files = os.environ.get("PROGRAMFILES(X86)")
    if not program_files:
        raise RuntimeError("Cannot locate the Visual Studio installer")
    vswhere = Path(program_files) / "Microsoft Visual Studio/Installer/vswhere.exe"
    candidates = run(
        [
            str(vswhere),
            "-latest",
            "-products",
            "*",
            "-find",
            r"VC\Tools\MSVC\**\bin\Host*\*\dumpbin.exe",
        ]
    ).splitlines()
    if not candidates:
        raise RuntimeError("Cannot locate the MSVC dependency inspector")
    tool = Path(candidates[0].strip()).resolve(strict=True)
    output = run([str(tool), "/DEPENDENTS", str(binary)])
    version = re.search(r"(?i)\bVersion\s+([0-9.]+)", output)
    if version is None:
        raise RuntimeError("Cannot identify the MSVC dependency inspector version")
    return {
        "sourceCommit": os.environ.get("GITHUB_SHA"),
        "crt": "static",
        "artifact": {"sha256": sha256(binary)},
        "checkerSha256": sha256(Path(__file__)),
        "tool": {
            "name": "dumpbin.exe",
            "sha256": sha256(tool),
            "version": version[1],
        },
        "dependencies": dependencies(output),
    }


def main(argv: list[str] | None = None) -> int:
    """Check a Windows executable and write its dependency receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt = inspect(args.executable)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(receipt, indent=2) + "\n"
        args.report.write_text(text, encoding="utf-8", newline="\n")
        print(text, end="")
    except subprocess.CalledProcessError as error:
        parser.exit(
            1,
            f"Windows process dependency check failed: {error}\n"
            f"{error.stdout or ''}{error.stderr or ''}",
        )
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Windows process dependency check failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
