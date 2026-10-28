"""Verify runtime selection and installed-byte integrity through the pinned CLI.

Use canonical WASM and process bundles from the same candidate. The process
bundle must include the current platform and a real foreign platform. This is
installed legacy-route qualification, independent of executable MEP conformance.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from scripts import extension_bundle as bundle


def _descriptor(directory: Path, runtime: str) -> dict[str, Any]:
    descriptor = json.loads((directory / "release.json").read_text())
    expected = {"release.json"}
    for entry in descriptor["artifacts"]:
        name = entry["filename"]
        if "/" in name or "\\" in name or name in {".", ".."}:
            raise bundle.BundleError("bundle artifact filename must be portable")
        path = directory / name
        if entry["runtime"] != runtime or path.is_symlink() or not path.is_file():
            raise bundle.BundleError("bundle runtime or artifact kind differs")
        digest = bundle.sha256(path.read_bytes())
        if entry["sha256"] != digest:
            raise bundle.BundleError("bundle artifact digest differs")
        if (directory / f"{name}.sha256").read_text() != f"{digest}  {name}\n":
            raise bundle.BundleError("bundle checksum differs")
        expected.update((name, f"{name}.sha256"))
    if {path.name for path in directory.iterdir()} != expected:
        raise bundle.BundleError("bundle inventory differs")
    return dict(descriptor)


def qualify(wasm: Path, process: Path) -> dict[str, Any]:
    """Exercise actual selected bytes in one home with fresh project caches."""
    wasm, process = wasm.resolve(), process.resolve()
    declarations = {
        "wasm": _descriptor(wasm, "wasm"),
        "process": _descriptor(process, "process"),
    }
    first, second = declarations.values()
    if not (
        first["extensionId"] == second["extensionId"] == "morphir-python"
        and first["version"] == second["version"] == bundle.crate_version()
        and first["gitCommit"] == second["gitCommit"]
    ):
        raise bundle.BundleError("runtime bundles are not the same candidate")
    platform = bundle._target()
    foreign = [entry for entry in second["artifacts"] if entry["platform"] != platform]
    if not foreign:
        raise bundle.BundleError("platform refusal check needs a real foreign artifact")
    cli, archive_digest = bundle.morphir_cli()
    cli = cli.resolve()
    switches: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="morphir-runtime-choice-") as temporary:
        root = Path(temporary)
        home, admin = root / "home", root / "admin"
        admin.mkdir()
        env = {**os.environ, "MORPHIR_HOME": str(home), "MORPHIR_NO_BANNER": "1"}
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
            env[name] = env[name.lower()] = bundle.OFFLINE
        env.pop("NO_PROXY", None)
        env.pop("no_proxy", None)

        def invoke(
            cwd: Path, *arguments: str, fail: bool = False
        ) -> subprocess.CompletedProcess[str]:
            result = subprocess.run(
                [str(cli), "--no-banner", *arguments],
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if (result.returncode != 0) != fail:
                raise bundle.BundleError(
                    f"runtime check {arguments}: {result.stdout} {result.stderr}"
                )
            return result

        def project(name: str) -> Path:
            directory = root / name
            shutil.copytree(bundle.SAMPLE, directory / "src")
            (directory / "morphir.toml").write_text(
                '[project]\nname = "acme/example"\nversion = "0.1.0"\n'
                'source_directory = "src"\n[frontend]\nlanguage = "python"\n'
                "emit_parse_stage = false\n"
            )
            return directory

        for runtime, directory in (("wasm", wasm), ("process", process)):
            repository = root / f"repository-{runtime}"
            name = f"python-{runtime}"
            invoke(admin, "extension", "repository", "init", str(repository))
            invoke(
                admin,
                "extension",
                "repository",
                "add",
                name,
                "--directory",
                str(repository),
            )
            invoke(
                admin,
                "extension",
                "repository",
                "publish",
                name,
                "--bundle",
                str(directory),
            )
            invoke(admin, "extension", "repository", "verify", name)

        for index, runtime in enumerate(("wasm", "process", "wasm")):
            current = project(f"project-{index}")
            invoke(
                current,
                "extension",
                "install",
                "morphir-python",
                "--repository",
                f"python-{runtime}",
                "--version",
                first["version"],
            )
            catalog = json.loads((home / "catalog/extensions.json").read_text())
            (installed,) = catalog["extensions"]
            entries = declarations[runtime]["artifacts"]
            (selected,) = [
                entry
                for entry in entries
                if runtime == "wasm" or entry["platform"] == platform
            ]
            if not (
                installed["runtime"] == runtime
                and installed["digest"] == selected["sha256"]
                and installed["version"] == first["version"]
                and installed["args"] == []
            ):
                raise bundle.BundleError(
                    "installed catalog differs from the selected runtime"
                )
            stored = home / installed["storePath"]
            if bundle.sha256(stored.read_bytes()) != selected["sha256"]:
                raise bundle.BundleError(
                    "installed bytes differ from selected artifact"
                )
            results: dict[str, dict[str, object]] = {}
            for version in ("3.0.0", "4") if index < 2 else ("4",):
                tag = version[0]
                invoke(
                    current,
                    "compile",
                    "--language",
                    "python",
                    "--input",
                    "src",
                    "--ir-version",
                    version,
                    "--output",
                    f"compiled-{tag}",
                )
                document = json.loads(
                    (current / f"compiled-{tag}/morphir-ir.json").read_text()
                )
                results[f"v{tag}"] = {
                    "ir_sha256": bundle.sha256(
                        json.dumps(
                            document, sort_keys=True, separators=(",", ":")
                        ).encode()
                    )
                }
                if index < 2:
                    generated = current / f"generated-{tag}"
                    invoke(
                        current,
                        "generate",
                        "--target",
                        "python",
                        "--input",
                        f"compiled-{tag}/morphir-ir.json",
                        "--output",
                        str(generated),
                    )
                    results[f"v{tag}"]["generated_sha256"] = {
                        file.relative_to(generated).as_posix(): bundle.sha256(
                            file.read_bytes()
                        )
                        for file in sorted(generated.rglob("*.py"))
                    }
            switches.append(
                {
                    "runtime": runtime,
                    "artifact_sha256": selected["sha256"],
                    "results": results,
                }
            )
            if index == 1 and switches[0]["results"] != results:
                raise bundle.BundleError("WASM and process installed results differ")
            if index == 2:
                if (
                    results["v4"]["ir_sha256"]
                    != switches[0]["results"]["v4"]["ir_sha256"]
                ):
                    raise bundle.BundleError(
                        "switching back to WASM changed the result"
                    )
                integrity = bundle.check_installed_integrity(cli, home, env)
            invoke(current, "extension", "uninstall", "morphir-python")

        # Publish only real non-current platform bytes into a separate local index.
        foreign_bundle = root / "foreign-bundle"
        foreign_bundle.mkdir()
        descriptor = copy.deepcopy(second)
        descriptor["artifacts"] = foreign
        for entry in foreign:
            for name in (entry["filename"], f"{entry['filename']}.sha256"):
                shutil.copyfile(process / name, foreign_bundle / name)
        (foreign_bundle / "release.json").write_text(
            json.dumps(descriptor, indent=2) + "\n"
        )
        foreign_repo = root / "repository-foreign"
        invoke(admin, "extension", "repository", "init", str(foreign_repo))
        invoke(
            admin,
            "extension",
            "repository",
            "add",
            "python-foreign",
            "--directory",
            str(foreign_repo),
        )
        invoke(
            admin,
            "extension",
            "repository",
            "publish",
            "python-foreign",
            "--bundle",
            str(foreign_bundle),
        )
        rejected = invoke(
            admin,
            "extension",
            "install",
            "morphir-python",
            "--repository",
            "python-foreign",
            "--version",
            first["version"],
            fail=True,
        )
        if "platform" not in (rejected.stdout + rejected.stderr).lower():
            raise bundle.BundleError("foreign-only bundle was not refused for platform")
        final_catalog = json.loads((home / "catalog/extensions.json").read_text())
        if final_catalog["extensions"]:
            raise bundle.BundleError("unsupported platform unexpectedly installed")
    return {
        "scope": "installed-legacy-runtime-selection",
        "sourceCommit": first["gitCommit"],
        "version": first["version"],
        "host": {
            "version": bundle.declaration()["host"]["version"],
            "archive_sha256": archive_digest,
            "binary_sha256": bundle.sha256(cli.read_bytes()),
        },
        "qualification_script_sha256": bundle.sha256(Path(__file__).read_bytes()),
        "descriptors": {
            runtime: bundle.sha256((directory / "release.json").read_bytes())
            for runtime, directory in (("wasm", wasm), ("process", process))
        },
        "integrity_checker_sha256": bundle.sha256(Path(bundle.__file__).read_bytes()),
        "installed_integrity": integrity,
        "switches": switches,
        "tampered_install_refused": True,
        "unsupported_platform_refused": True,
    }


def main(argv: list[str] | None = None) -> int:
    """Write actual runtime-choice evidence outside the supplied bundles."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wasm", type=Path, required=True)
    parser.add_argument("--process", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    if any(
        args.report.resolve().is_relative_to(path.resolve())
        for path in (args.wasm, args.process)
    ):
        parser.error("report must remain outside canonical input bundles")
    try:
        result = qualify(args.wasm, args.process)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + "\n")
    except (
        bundle.BundleError,
        OSError,
        KeyError,
        ValueError,
        subprocess.TimeoutExpired,
    ) as error:
        parser.exit(1, f"runtime qualification refused: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
