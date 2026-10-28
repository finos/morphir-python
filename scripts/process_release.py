"""Assemble verified native platforms into a canonical process-only bundle.

This is artifact assembly, not MEP conformance or publication approval. Every
platform must have an exact-byte installed-host receipt matching the WASM
candidate's claims and supported legacy results. The release promotion gate
must additionally require independent executable MEP qualification.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

from scripts import extension_bundle as bundle
from scripts import process_extension as process
from scripts.qualify_native import tools_pin
from scripts.release_candidates import CandidateError, bundle_candidates


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise bundle.BundleError(f"expected an object in {path}")
    return value


def _windows_imports(root: Path, artifact_digest: str, commit: str) -> str:
    path = root / ".dev/qualification/windows-process-imports.json"
    proof = _read(path)
    try:
        dependencies = proof["dependencies"]
        if not (
            proof["sourceCommit"] == commit
            and proof["crt"] == "static"
            and proof["artifact"]["sha256"] == artifact_digest
            and proof["checkerSha256"]
            == bundle.sha256(
                (bundle.ROOT / ".github/scripts/check_process_windows.ps1").read_bytes()
            )
            and proof["tool"]["name"] == "dumpbin.exe"
            and re.fullmatch(r"[0-9a-f]{64}", proof["tool"]["sha256"])
            and proof["tool"]["version"]
            and isinstance(dependencies, list)
            and dependencies
            and all(
                isinstance(name, str) and re.fullmatch(r"(?i)[a-z0-9_.-]+\.dll", name)
                for name in dependencies
            )
            and not any(
                re.match(r"(?i)(vcruntime|msvcp|concrt|python)\d", name)
                for name in dependencies
            )
        ):
            raise bundle.BundleError("Windows process runtime dependency proof differs")
    except (KeyError, TypeError) as error:
        raise bundle.BundleError("incomplete Windows process runtime proof") from error
    return bundle.sha256(path.read_bytes())


def assemble(
    inputs: Path,
    output: Path,
    commit: str,
    wasm_claims: dict[str, Any],
    reference_results: dict[str, Any],
) -> dict[str, Any]:
    """Refuse mixed candidates and combine all canonical process entries."""
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    expected = {f"morphir-python-process-{target}" for target in process.PLATFORMS}
    if {path.name for path in inputs.iterdir()} != expected:
        raise bundle.BundleError("process set must contain exactly five platforms")
    if set(reference_results) != {"v3", "v4"} or not all(
        result.get("agrees_with_python_api") is True and result.get("modules")
        for result in reference_results.values()
    ):
        raise bundle.BundleError("WASM reference lacks successful v3/v4 results")
    version = bundle.crate_version()
    lock_digest = bundle.sha256((bundle.ROOT / "rust/Cargo.lock").read_bytes())
    source_files: list[Path] = []
    artifacts: list[dict[str, Any]] = []
    reports: dict[str, str] = {}
    windows_imports_digest = ""
    for target in process.PLATFORMS:
        root = inputs / f"morphir-python-process-{target}"
        directory = root / ".morphir/build/extensions/python-process"
        report_path = root / f".dev/qualification/process-{target}.json"
        report = _read(report_path)
        name = process.artifact_name(version, target)
        executable = directory / name
        # GitHub artifact ZIP transfer strips execute bits. Restore only the
        # declared raw executable; its bytes and original mode remain checked.
        if executable.is_symlink() or not executable.is_file():
            raise bundle.BundleError("process artifact is not a regular file")
        executable.chmod(0o700)
        checked = process.receipt(directory, commit, target)
        if target.endswith("windows-msvc"):
            windows_imports_digest = _windows_imports(
                root, checked["files"][name], commit
            )
        try:
            for field in (
                "sourceCommit",
                "runtime",
                "platform",
                "version",
                "files",
                "arguments",
                "explicitArguments",
                "executable",
                "claims",
            ):
                if report[field] != checked[field]:
                    raise bundle.BundleError(f"{target}: mismatched {field}")
            host = report["installedHost"]
            pin = bundle.declaration()["host"]
            if not (
                report["claims"] == wasm_claims
                and report["cargoLockSha256"] == lock_digest
                and report["bundler"]["version"] == pin["version"]
                and report["bundler"]["archiveSha256"] == pin["sha256"][target]
                and host["sourceCommit"] == commit
                and host["version"] == version
                and host["files"] == checked["files"]
                and host["installed_integrity"]["expected_sha256"]
                == checked["files"][name]
                and re.fullmatch(
                    r"[0-9a-f]{64}", host["installed_integrity"]["tampered_sha256"]
                )
                and host["installed_integrity"]["tampered_sha256"]
                != checked["files"][name]
                and host["installed_integrity"]["exit_code"] != 0
                and host["installed_integrity"]["fresh_project"] is True
                and bundle.is_digest_mismatch(
                    host["installed_integrity"]["stdout"]
                    + host["installed_integrity"]["stderr"],
                    checked["files"][name],
                    host["installed_integrity"]["tampered_sha256"],
                )
                and host["host"]["morphir"] == pin["version"]
                and host["host"]["sha256"] == pin["sha256"][target]
                and host["host"]["binary_sha256"] == report["bundler"]["binarySha256"]
                and host["qualification_script_sha256"]
                == bundle.sha256(
                    (bundle.ROOT / "scripts/extension_bundle.py").read_bytes()
                )
                and host["python_api"]["native_version"] == tools_pin()
                and host["python_api"]["compiler_version"] == version
                and host["offline_round_trips"] == reference_results
                and (target.endswith("windows-msvc") or report["mode"] == "0o700")
            ):
                raise bundle.BundleError(f"{target}: qualification evidence differs")
            descriptor = _read(directory / "release.json")
            artifacts.append(descriptor["artifacts"][0])
        except (KeyError, TypeError, IndexError) as error:
            raise bundle.BundleError(
                f"{target}: incomplete process evidence"
            ) from error
        source_files.extend([executable, directory / f"{name}.sha256"])
        reports[target] = bundle.sha256(report_path.read_bytes())
    descriptor = {
        "schemaVersion": "2.0.0-draft.2",
        "extensionId": "morphir-python",
        "shortId": "python",
        "version": version,
        "gitCommit": commit,
        "platformDifferences": "none",
        "artifacts": artifacts,
    }
    # mkdir is exclusive; a concurrent or existing destination is never replaced.
    output.mkdir()
    try:
        for path in source_files:
            shutil.copyfile(path, output / path.name)
            if not path.name.endswith(".sha256"):
                (output / path.name).chmod(0o700)
        (output / "release.json").write_text(json.dumps(descriptor, indent=2) + "\n")
    except BaseException:
        shutil.rmtree(output)
        raise
    return {
        "kind": "process-release-assembly",
        "sourceCommit": commit,
        "version": version,
        "platforms": list(process.PLATFORMS),
        "files": {
            path.name: bundle.sha256(path.read_bytes())
            for path in sorted(output.iterdir())
        },
        "inputReports": reports,
        "windowsImportsSha256": windows_imports_digest,
    }


def main(argv: list[str] | None = None) -> int:
    """Assemble a process candidate against source-bound WASM reference bytes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--wasm-bundle", type=Path, required=True)
    parser.add_argument("--wasm-report", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.report.resolve().is_relative_to(args.output.resolve()):
        parser.error("assembly report must remain outside the canonical bundle")
    try:
        bundle_candidates(args.wasm_bundle, bundle.crate_version(), args.commit)
        checked = bundle.receipt(args.wasm_bundle)
        reference = _read(args.wasm_report)
        if not (
            reference["git_commit"] == args.commit
            and reference["bundle"] == checked["bundle"]
            and reference["installed_integrity"]["expected_sha256"]
            == checked["wasm_sha256"]
            and reference["installed_integrity"]["exit_code"] != 0
            and reference["installed_integrity"]["fresh_project"] is True
            and bundle.is_digest_mismatch(
                reference["installed_integrity"]["stdout"]
                + reference["installed_integrity"]["stderr"],
                str(checked["wasm_sha256"]),
                reference["installed_integrity"]["tampered_sha256"],
            )
            and reference["qualification_script_sha256"]
            == bundle.sha256((bundle.ROOT / "scripts/extension_bundle.py").read_bytes())
            and reference["python_api"]["native_version"] == tools_pin()
            and reference["python_api"]["compiler_version"] == bundle.crate_version()
        ):
            raise bundle.BundleError("WASM reference is not this qualified candidate")
        claims = _read(args.wasm_bundle / "release.json")["artifacts"][0]["claims"]
        result = assemble(
            args.inputs,
            args.output,
            args.commit,
            claims,
            reference["offline_round_trips"],
        )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + "\n")
    except (
        bundle.BundleError,
        CandidateError,
        OSError,
        KeyError,
        ValueError,
        TypeError,
    ) as error:
        parser.exit(1, f"process release assembly refused: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
