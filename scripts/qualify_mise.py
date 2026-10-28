"""Qualify wheel-only CLI installs through mise's uv and actual pipx installers.

Run without wheel arguments to check the released examples. With three wheels,
download their dependencies once, then install those exact candidates offline.
Every install uses fresh mise state outside the checkout and exercises v3/v4
compile, inspect, generate and recompile with no Rust toolchain on PATH.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, cast

from scripts.check_distributions import load_packages, validate_archive
from scripts.qualify_native import (
    ROOT,
    SAMPLE,
    WHEEL_NAME,
    rust_free_path,
    sha256,
    validate_wheel,
    venv_python,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

INSTALLERS = ("uv", "pipx")


def validate_candidates(wheels: Sequence[Path]) -> None:
    """Require identified core, native and CLI inputs before any dependency lookup."""
    core, tools = load_packages(ROOT)
    expected = [
        f"morphir-{core.version}-py3-none-any.whl",
        f"morphir_python-{tools.version}-py3-none-any.whl",
    ]
    if (
        len(wheels) != 3
        or wheels[0].name != expected[0]
        or wheels[2].name != expected[1]
        or not WHEEL_NAME.fullmatch(wheels[1].name)
    ):
        raise ValueError("expected the core, native and CLI candidate wheels, in order")
    validate_archive(core, wheels[0])
    validate_wheel(wheels[1])
    validate_archive(tools, wheels[2])


def tool_name(installer: str) -> str:
    """Return the explicit backend identity being qualified."""
    return f"{'pypi' if installer == 'uv' else 'pipx'}:morphir-python"


def configuration(installer: str, version: str, wheelhouse: Path | None = None) -> str:
    """Render the documented config, optionally restricted to candidate wheels."""
    template = ROOT / "examples" / "install" / f"mise-{installer}.toml"
    tools = tomllib.loads(template.read_text())["tools"]
    options = cast("dict[str, str | bool]", tools[tool_name(installer)])
    options["version"] = version
    if wheelhouse:
        location = f"--find-links={wheelhouse.as_uri()}"
        if installer == "uv":
            options["uvx_args"] = shlex.join(["--no-build", "--no-index", location])
        else:
            options["pipx_args"] = shlex.join(
                ["--pip-args", f"--only-binary=:all: --no-index {location}"]
            )
    lines = ["[tools]"]
    for name, value in tools.items():
        rendered = (
            "{ " + ", ".join(f"{k} = {json.dumps(v)}" for k, v in value.items()) + " }"
            if isinstance(value, dict)
            else json.dumps(value)
        )
        lines.append(f"{json.dumps(name)} = {rendered}")
    return "\n".join(lines) + "\n"


def isolated_environment(
    directory: Path, original: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Keep mise state and Python installer state separate from the user's."""
    env = dict(os.environ if original is None else original)
    for name in list(env):
        if name.startswith(("MISE_", "PYTHON", "UV_", "PIP_", "PIPX_")) or name in {
            "VIRTUAL_ENV",
            "CONDA_PREFIX",
        }:
            del env[name]
    env.update(
        {
            "MISE_DATA_DIR": str(directory / "data"),
            "MISE_CACHE_DIR": str(directory / "cache"),
            "MISE_CONFIG_DIR": str(directory / "config"),
            "MISE_STATE_DIR": str(directory / "state"),
            "MISE_YES": "1",
            "MISE_AUTO_INSTALL": "0",
            "PIP_CONFIG_FILE": os.devnull,
            "NO_COLOR": "1",
        }
    )
    return env


def run(command: Sequence[str], cwd: Path, env: Mapping[str, str]) -> str:
    """Run a required check, retaining stderr and refusing timeouts or failure."""
    print(shlex.join(command), file=sys.stderr, flush=True)
    result = subprocess.run(
        command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, timeout=600
    )
    result.check_returncode()
    return result.stdout.strip()


def exercise(cli: Path, python: Path, work: Path, env: dict[str, str]) -> None:
    """Exercise the installed CLI and execute its generated model."""
    env = {**env, "PATH": rust_free_path(python.parent.parent)}
    source = work / "source"
    shutil.copytree(SAMPLE, source)
    run([str(cli), "--help"], work, env)
    for target in ("v3", "v4"):
        model, again, output = (
            work / f"{target}.json",
            work / f"{target}-again.json",
            work / f"{target}-generated",
        )
        args = ["--package", "acme/example", "--ir-version", target]
        run([str(cli), "compile", str(source), *args, "-o", str(model)], work, env)
        run([str(cli), "ir", "inspect", str(model)], work, env)
        run([str(cli), "generate", str(model), "--output-dir", str(output)], work, env)
        run([str(cli), "compile", str(output), *args, "-o", str(again)], work, env)
        if json.loads(model.read_text()) != json.loads(again.read_text()):
            raise ValueError(
                f"{target} generated source did not compile to the same IR"
            )
        result = run(
            [
                str(python),
                "-I",
                "-c",
                "import sys; sys.path.insert(0, sys.argv[1]); from acme import rules; "
                "print(rules.choose(True, 1, 2), rules.twice_identity(7))",
                str(output),
            ],
            work,
            env,
        )
        if result != "1 7":
            raise ValueError(f"generated model returned {result!r}")


def qualify(wheels: Sequence[Path], installers: Sequence[str]) -> dict[str, object]:
    """Install and exercise released packages or the three supplied candidates."""
    mise = shutil.which("mise")
    if mise is None:
        raise ValueError("mise is required; see docs/installation.md")
    released = json.loads((ROOT / "examples/manifest.json").read_text())["released"]
    version = str(released["morphir-python"])
    if wheels:
        validate_candidates(wheels)
        project = ROOT / "packages/morphir-tools/pyproject.toml"
        version = str(tomllib.loads(project.read_text())["project"]["version"])
    reports = []
    dependencies: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="morphir-mise-") as scratch:
        base = Path(scratch)
        wheelhouse = base / "wheels" if wheels else None
        if wheelhouse:
            wheelhouse.mkdir()
            constraints = base / "constraints.txt"
            run(
                [
                    "uv",
                    "export",
                    "--frozen",
                    "--all-packages",
                    "--no-default-groups",
                    "--no-emit-workspace",
                    "--no-hashes",
                    "--output-file",
                    str(constraints),
                ],
                ROOT,
                isolated_environment(base / "download"),
            )
            run(
                [
                    "uvx",
                    "--from",
                    "pip==26.2.2",
                    "pip",
                    "download",
                    "--only-binary=:all:",
                    "--dest",
                    str(wheelhouse),
                    "--constraint",
                    str(constraints),
                    *[str(w.resolve()) for w in wheels],
                    # pipx bootstraps its shared pip from the same offline index.
                    "pip==26.2.2",
                ],
                base,
                isolated_environment(base / "download"),
            )
            for wheel in wheels:
                if sha256(wheel) != sha256(wheelhouse / wheel.name):
                    raise ValueError(f"wheel download changed {wheel.name}")
            dependencies = {p.name: sha256(p) for p in sorted(wheelhouse.glob("*.whl"))}
        for installer in installers:
            work = base / installer
            work.mkdir()
            env = isolated_environment(work)
            (work / "mise.toml").write_text(
                configuration(installer, version, wheelhouse)
            )
            start = time.monotonic()
            run([mise, "trust"], work, env)
            run([mise, "install"], work, env)
            tool = tool_name(installer)
            installed = Path(run([mise, "where", f"{tool}@{version}"], work, env))
            cli = Path(run([mise, "which", "morphir-python"], work, env))
            environment = (
                installed / "morphir-python"
                if installer == "uv"
                else installed / "venvs/morphir-python"
            )
            python = venv_python(environment)
            if not python.is_file():
                raise ValueError(f"the installed tool environment is missing: {python}")
            versions = json.loads(
                run(
                    [
                        str(python),
                        "-I",
                        "-c",
                        "import json; from importlib.metadata import version; "
                        "print(json.dumps({p:version(p) for p in "
                        "['morphir','morphir-python','morphir-python-native']}))",
                    ],
                    work,
                    env,
                )
            )
            expected = dict(released)
            if wheels:
                from scripts.release_candidates import source_versions

                source = source_versions()
                expected = {
                    "morphir": source["morphir"],
                    "morphir-python": source["python"],
                    "morphir-python-native": source["native"],
                }
            if versions != expected:
                raise ValueError(
                    f"installed versions {versions} differ from {expected}"
                )
            exercise(cli, python, work, env)
            reports.append(
                {
                    "installer": installer,
                    "versions": versions,
                    "seconds": round(time.monotonic() - start, 3),
                }
            )
    return {
        "state": "succeeded",
        "installs": reports,
        "wheels": {w.name: sha256(w) for w in wheels},
        "wheelhouse": dependencies,
        "check_sha256": sha256(Path(__file__)),
    }


def main() -> None:
    """Run installed mise qualification and retain its receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheels", nargs="*", type=Path)
    parser.add_argument("--installer", choices=(*INSTALLERS, "both"), default="both")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if len(args.wheels) not in (0, 3):
        parser.error("supply no wheels, or exactly the core, native and CLI wheels")
    installers = INSTALLERS if args.installer == "both" else (args.installer,)
    receipt = qualify(args.wheels, installers)
    rendered = json.dumps(receipt, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
