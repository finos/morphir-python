"""Refusal cases of the native distribution qualification script."""

from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING

import pytest

from scripts import qualify_native as q

if TYPE_CHECKING:
    from pathlib import Path

VERSION = q.crate_version()
STEM = f"morphir_python_native-{VERSION}"
METADATA = (
    "Metadata-Version: 2.4\nName: morphir-python-native\nVersion: {version}\n"
    "License-Expression: Apache-2.0\nRequires-Python: >=3.14\n{extra}\n"
)


def make_wheel(
    tmp_path: Path,
    *,
    tag: str = "cp314-abi3-manylinux_2_28_x86_64",
    version: str = VERSION,
    extra: str = "",
    omit: str = "",
    purelib: bool = False,
) -> Path:
    path = tmp_path / f"morphir_python_native-{version}-{tag}.whl"
    stem = f"morphir_python_native-{version}"
    files = {
        "morphir_python_native/__init__.py": "",
        "morphir_python_native/_native.abi3.so": "",
        "morphir_python_native/_native.pyi": "",
        "morphir_python_native/py.typed": "",
        f"{stem}.dist-info/licenses/LICENSE": "Apache",
        f"{stem}.dist-info/METADATA": METADATA.format(version=version, extra=extra),
        f"{stem}.dist-info/WHEEL": f"Root-Is-Purelib: {str(purelib).lower()}\n",
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, text in files.items():
            if name != omit:
                archive.writestr(name, text)
    return path


def test_versions_agree_across_crate_pin_and_constant() -> None:
    q.check_versions(VERSION)
    assert q.tools_pin() == VERSION


def test_accepts_a_complete_wheel(tmp_path: Path) -> None:
    assert q.validate_wheel(make_wheel(tmp_path))["version"] == VERSION


@pytest.mark.parametrize(
    "options",
    [
        {"tag": "cp314-cp314-manylinux_2_28_x86_64"},
        {"tag": "py3-none-any"},
        {"version": "9.9.9"},
        {"extra": "Requires-Dist: typer"},
        {"omit": "morphir_python_native/_native.pyi"},
        {"omit": "morphir_python_native/py.typed"},
        {"omit": "morphir_python_native/_native.abi3.so"},
        {"omit": f"{STEM}.dist-info/licenses/LICENSE"},
        {"purelib": True},
    ],
)
def test_refuses_incomplete_or_mismatched_wheels(
    tmp_path: Path, options: dict[str, object]
) -> None:
    with pytest.raises(q.QualificationError):
        q.validate_wheel(make_wheel(tmp_path, **options))  # type: ignore[arg-type]


def test_refuses_an_sdist_without_rust_inputs() -> None:
    names = [f"{STEM}/{name}" for name in q.REQUIRED_SDIST_FILES]
    q.validate_sdist_names(names, VERSION)
    with pytest.raises(q.QualificationError, match=r"Cargo\.lock"):
        q.validate_sdist_names(
            [n for n in names if not n.endswith("Cargo.lock")], VERSION
        )
    with pytest.raises(q.QualificationError, match="unsafe"):
        q.validate_sdist_names([*names, f"{STEM}/../escape"], VERSION)


def test_rust_free_path_excludes_cargo(tmp_path: Path) -> None:
    path = q.rust_free_path(tmp_path / "venv")
    import shutil

    assert shutil.which("cargo", path=path) is None
