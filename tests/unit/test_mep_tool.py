"""Source-built checker identities must survive later Cargo rebuilds."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING, Any

import pytest

from scripts import extension_bundle as bundle
from scripts import mep_tool

if TYPE_CHECKING:
    from pathlib import Path


def test_frozen_checker_keeps_old_report_identity_when_build_output_changes(
    tmp_path: Path,
) -> None:
    executable = tmp_path / "morphir"
    executable.write_bytes(b"qualified checker")
    first = mep_tool.freeze_binary(executable, tmp_path / "cache")
    executable.write_bytes(b"a later compatible rebuild")
    second = mep_tool.freeze_binary(executable, tmp_path / "cache")
    assert first != second
    assert first.read_bytes() == b"qualified checker"
    assert second.read_bytes() == b"a later compatible rebuild"
    assert first.parent.name == mep_tool.sha(first)
    assert mep_tool.freeze_binary(executable, tmp_path / "cache") == second
    second.write_bytes(b"changed stored checker")
    with pytest.raises(bundle.BundleError, match="integrity"):
        mep_tool.freeze_binary(executable, tmp_path / "cache")


def test_unicode_report_does_not_depend_on_producer_locale(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_bytes('{"opaqueId":"λ雪🙂"}'.encode())
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pathlib import Path; import sys; "
            "from scripts.mep_tool import object_file; "
            "assert object_file(Path(sys.argv[1]))['opaqueId'] == "
            "'\\u03bb\\u96ea\\U0001f642'",
            str(report),
        ],
        env=os.environ
        | {
            "LC_ALL": "C",
            "PYTHONUTF8": "0",
            "PYTHONCOERCECLOCALE": "0",
        },
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_failed_build_exposes_diagnostics_and_retains_full_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnostic = (
        "earlier build output\n" * 100 + "error: missing Windows prerequisite λ\n"
    ).encode()

    def fail(arguments: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        kwargs["stdout"].write(diagnostic)
        return subprocess.CompletedProcess(arguments, 1)

    monkeypatch.setattr(mep_tool.subprocess, "run", fail)
    log = tmp_path / "build.log"
    with pytest.raises(bundle.BundleError, match="missing Windows prerequisite λ"):
        mep_tool.build_checker(tmp_path, tmp_path / "target", log)
    assert log.read_bytes() == diagnostic
