"""Release checks reject external runtimes and use the installed Python guest."""

from __future__ import annotations

import copy
import os
from typing import TYPE_CHECKING

import pytest

from scripts import check_dotnet_process as dotnet
from scripts import check_process_windows as windows

if TYPE_CHECKING:
    from pathlib import Path


def test_windows_dependencies_are_sorted_case_insensitively() -> None:
    assert windows.dependencies(
        "Image has the following dependencies:\n KERNEL32.dll\n ntdll.dll\n kernel32.DLL"
    ) == ["kernel32.dll", "ntdll.dll"]


@pytest.mark.parametrize(
    "output", ["no imports", "VCRUNTIME140.dll", "MSVCP140.dll", "python314.dll"]
)
def test_windows_check_refuses_missing_or_external_runtime_imports(output: str) -> None:
    with pytest.raises(RuntimeError):
        windows.dependencies(output)


def test_smoke_environment_is_isolated_without_changing_the_callers_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MORPHIR_HOME", "original-home")
    monkeypatch.setenv("MORPHIR_EXTENSION_OVERLAY", "fsharp-generation")
    env = dotnet.environment(tmp_path)
    assert env["MORPHIR_HOME"] == str(tmp_path.resolve() / "home")
    assert "MORPHIR_EXTENSION_OVERLAY" not in env
    assert os.environ["MORPHIR_HOME"] == "original-home"
    assert os.environ["MORPHIR_EXTENSION_OVERLAY"] == "fsharp-generation"


@pytest.mark.parametrize(
    "change", [None, "success", "extensionId", "version", "mepVersion"]
)
def test_smoke_check_requires_the_selected_installed_provider(
    change: str | None,
) -> None:
    report = {
        "success": True,
        "provider": {
            "extensionId": "morphir-python",
            "version": "0.6.2",
            "mepVersion": "0.2.0-draft.1",
        },
    }
    changed = copy.deepcopy(report)
    if change == "success":
        changed["success"] = False
    elif change is not None:
        changed["provider"][change] = "other"
    if change is None:
        dotnet.validate_operation(changed, "0.6.2")
    else:
        with pytest.raises(RuntimeError):
            dotnet.validate_operation(changed, "0.6.2")
