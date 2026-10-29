"""The mise qualification must install the identified candidate, never PyPI substitutes."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from scripts import qualify_mise as q


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


def test_installer_caches_are_private_to_each_qualification(tmp_path: Path) -> None:
    original = {
        key: str(tmp_path / "user-cache" / key)
        for key in ("PIP_CACHE_DIR", "UV_CACHE_DIR")
    }
    environments = {
        installer: q.isolated_environment(tmp_path / installer, original)
        for installer in ("uv", "pipx")
    }
    for key, user_cache in original.items():
        for installer, env in environments.items():
            assert env[key] != user_cache
            assert Path(env[key]).is_relative_to(tmp_path / installer)
        assert environments["uv"][key] != environments["pipx"][key]


def test_candidate_refuses_a_missing_native_input_before_resolving(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="core, native and CLI"):
        q.validate_candidates([tmp_path / "core.whl"] * 3)


@pytest.mark.parametrize("installer", ["uv", "pipx"])
def test_qualification_preserves_the_published_configuration(installer: str) -> None:
    original = tomllib.loads(
        (q.ROOT / "examples/install" / f"mise-{installer}.toml").read_text()
    )
    version = original["tools"][q.tool_name(installer)]["version"]
    assert tomllib.loads(q.configuration(installer, version)) == original
