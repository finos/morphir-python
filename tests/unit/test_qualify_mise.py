"""The mise qualification must install the identified candidate, never PyPI substitutes."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import pytest

from scripts import qualify_mise as q

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("installer", ["uv", "pipx"])
def test_candidate_install_is_offline_and_uses_built_wheels(
    tmp_path: Path, installer: str
) -> None:
    house = tmp_path / "wheel house"
    config = tomllib.loads(q.configuration(installer, "9.8.7", house))
    tool = config["tools"][q.tool_name(installer)]
    assert tool["version"] == "9.8.7"
    args = tool["uvx_args" if installer == "uv" else "pipx_args"]
    assert "--no-index" in args
    assert house.as_uri() in args
    assert ("--no-build" if installer == "uv" else "--only-binary=:all:") in args
    if installer == "pipx":
        assert tool["uvx"] is False


def test_isolation_does_not_inherit_active_python_environment(tmp_path: Path) -> None:
    env = q.isolated_environment(
        tmp_path,
        {"PATH": "/usr/bin", "VIRTUAL_ENV": "wrong", "PYTHONPATH": "wrong"},
    )
    assert "VIRTUAL_ENV" not in env
    assert "PYTHONPATH" not in env
    assert env["MISE_DATA_DIR"] == str(tmp_path / "data")
    assert env["MISE_CONFIG_DIR"] == str(tmp_path / "config")


def test_candidate_refuses_a_missing_native_input_before_resolving(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="core, native and CLI"):
        q.validate_candidates([tmp_path / "core.whl"] * 3)
