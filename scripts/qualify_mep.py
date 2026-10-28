"""Run canonical MEP qualification and bind its producer recheck for transfer.

Only the shared executable MCK adjudicates observations. This module verifies
tool/artifact identities and the trusted same-workflow producer handoff; it does
not replace canonical report-check or rewrite producer filesystem identities.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import ntpath
import os
import posixpath
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from scripts import extension_bundle as bundle
from scripts import mep_tool
from scripts.qualify_runtime import _descriptor


def argument_blob(value: str, *, windows: bool) -> dict[str, list[int]]:
    """Match the canonical runner's lossless serde OsString representation."""
    if not windows:
        return {"Unix": list(os.fsencode(value))}
    encoded = value.encode("utf-16-le", errors="surrogatepass")
    return {
        "Windows": [
            int.from_bytes(encoded[index : index + 2], "little")
            for index in range(0, len(encoded), 2)
        ]
    }


def _same_recorded_path(left: str, right: str, *, windows: bool) -> bool:
    # Rust canonicalization adds the Windows extended-length prefix. Never
    # resolve another producer's paths against the collector's filesystem.
    if windows:

        def normalize(value: str) -> str:
            value = value.replace("/", "\\")
            if value.startswith("\\\\?\\UNC\\"):
                value = "\\\\" + value[8:]
            elif value.startswith("\\\\?\\"):
                value = value[4:]
            return ntpath.normcase(ntpath.normpath(value))

        return normalize(left) == normalize(right)
    return posixpath.normpath(left) == posixpath.normpath(right)


def _bind_roles(
    roles: dict[str, dict[str, str]], identity: dict[str, Any]
) -> dict[str, dict[str, str]]:
    """Bind live producer files to the runner's own canonical identities."""
    bound = {}
    for name, expected in roles.items():
        matches = [
            record
            for record in identity["files"]
            if record["sha256"] == expected["sha256"]
            and os.path.samefile(record["path"], expected["path"])
        ]
        if len(matches) != 1:
            raise bundle.BundleError(f"MCK file identity differs for {name}")
        bound[name] = matches[0]
    return bound


def definition_hashes() -> dict[str, str]:
    """Identify the exact producer definition and pin configuration."""
    return {
        name: mep_tool.sha(bundle.ROOT / name)
        for name in (
            "scripts/qualify_mep.py",
            "scripts/mep_tool.py",
            "rust/extension.toml",
        )
    }


def case_set_sha(records: list[dict[str, Any]]) -> str:
    """Hash the complete required identity set, independently of record order."""
    identifiers = [record["caseId"] for record in records]
    if any(not isinstance(value, str) for value in identifiers) or len(
        set(identifiers)
    ) != len(identifiers):
        raise bundle.BundleError("MCK observation identities are invalid or duplicated")
    return hashlib.sha256(
        json.dumps(sorted(identifiers), separators=(",", ":")).encode()
    ).hexdigest()


def _tool(path: Path) -> dict[str, Any]:
    tool = mep_tool.object_file(path)
    pin = bundle.declaration()["mep"]
    if not (
        tool["kind"] == "source-built-shared-mck"
        and tool["revision"] == pin["rev"]
        and tool["tree"] == pin["tree"]
        and tool["corpusSha256"] == pin["corpus_sha256"]
        and tool["cargoLockSha256"] == pin["cargo_lock_sha256"]
        and tool["preparerSha256"] == mep_tool.sha(Path(mep_tool.__file__))
        and mep_tool.sha(Path(tool["executable"])) == tool["binarySha256"]
        and mep_tool.sha(Path(tool["kit"])) == pin["corpus_sha256"]
    ):
        raise bundle.BundleError("MCK tool receipt or available bytes differ")
    return tool


def _verify_transfer(
    receipt: dict[str, Any],
    report_path: Path,
    *,
    commit: str,
    runtime: str,
    platform: str,
    artifact_sha: str,
    claims: dict[str, Any],
) -> dict[str, Any]:
    """Verify exact evidence from successful producers in this workflow run.

    Canonical report-check already ran on the producer with the original
    checker and identity paths. Those paths can be Windows/macOS-specific;
    they are never rewritten or falsely rechecked on the Linux collector.
    Workflow needs, source/checker definitions, complete records and byte-bound
    receipts form the explicit transfer contract. This accepts no standalone
    'qualified' boolean as conformance evidence.
    """
    pin = bundle.declaration()["mep"]
    report = mep_tool.object_file(report_path)
    identity = report["identity"]
    invocation = receipt["invocation"]
    windows = invocation["windows"]
    roles = receipt["roles"]
    expected_roles = {"guest", "compilerLock"}
    if runtime == "wasm":
        expected_roles |= {"adapter", "adapterLock", "adapterSource"}
    if not (
        receipt["kind"] == "canonical-mep-producer-recheck"
        and receipt["sourceCommit"] == commit
        and receipt["runtime"] == runtime
        and receipt["platform"] == platform
        and receipt["artifactSha256"] == artifact_sha
        and receipt["definitionInputs"] == definition_hashes()
        and receipt["reportSha256"] == mep_tool.sha(report_path)
        and receipt["reportFilename"] == report_path.name
        and receipt["recheck"]["exitCode"] == 0
        and receipt["recheck"]["stdout"].strip() == "MEP guest report: qualified"
        and receipt["recheck"]["stderr"] == ""
        and report["contractVersion"] == "0.1.0-draft.1"
        and report["suite"] == "mep-guest"
        and report["profile"] == pin["profile"]
        and report["corpusSha256"] == pin["corpus_sha256"]
        and report["qualified"] is True
        and report["error"] is None
        and len(report["records"]) == pin["required_cases"]
        and case_set_sha(report["records"]) == pin["case_set_sha256"]
        and identity["runner"]
        == {
            "name": "morphir",
            "version": pin["runner_version"],
            "commit": pin["rev"],
            "dirty": False,
        }
        and identity["runnerBinary"]["sha256"] == receipt["checker"]["binarySha256"]
        and receipt["checker"]["revision"] == pin["rev"]
        and receipt["checker"]["tree"] == pin["tree"]
        and receipt["checker"]["cargoLockSha256"] == pin["cargo_lock_sha256"]
        and identity == receipt["checkedIdentity"]
        and set(roles) == expected_roles
        and len(identity["files"]) == len(roles)
        and all(role in identity["files"] for role in roles.values())
        and len({role["path"] for role in roles.values()}) == len(roles)
        and isinstance(windows, bool)
        and windows == platform.endswith("windows-msvc")
        and identity["arguments"]
        == [argument_blob(value, windows=windows) for value in invocation["arguments"]]
        and _same_recorded_path(
            invocation["host"], identity["host"]["path"], windows=windows
        )
        and _same_recorded_path(
            receipt["checker"]["executable"],
            identity["runnerBinary"]["path"],
            windows=windows,
        )
        and receipt["roles"]["guest"] in identity["files"]
        and receipt["roles"]["guest"]["sha256"] == artifact_sha
        and receipt["roles"]["compilerLock"] in identity["files"]
        and receipt["roles"]["compilerLock"]["sha256"]
        == mep_tool.sha(bundle.ROOT / "rust/Cargo.lock")
    ):
        raise bundle.BundleError(
            "MCK producer transfer is missing, stale or mismatched"
        )
    describes = [
        record for record in report["records"] if record["caseId"] == "describe"
    ]
    if len(describes) != 1 or describes[0]["observed"]["result"] != claims:
        raise bundle.BundleError("MCK discovery differs from staged artifact claims")
    if runtime == "process":
        if identity["host"] != receipt["roles"]["guest"] or identity["arguments"]:
            raise bundle.BundleError(
                "MCK process host is not the actual bare executable"
            )
    elif runtime == "wasm":
        if not (
            len(identity["arguments"]) == 1
            and _same_recorded_path(
                invocation["arguments"][0], roles["guest"]["path"], windows=windows
            )
            and identity["host"] == receipt["roles"]["adapter"]
            and receipt["roles"]["adapterLock"] in identity["files"]
            and receipt["roles"]["adapterLock"]["sha256"]
            == mep_tool.sha(bundle.ROOT / "tools/extension-qualification/Cargo.lock")
            and receipt["roles"]["adapterSource"] in identity["files"]
            and receipt["roles"]["adapterSource"]["sha256"]
            == mep_tool.sha(
                bundle.ROOT / "tools/extension-qualification/src/bin/mep_wasm_host.rs"
            )
        ):
            raise bundle.BundleError("MCK WASM adapter identity differs")
    else:
        raise bundle.BundleError("unsupported MCK runtime")
    return report


def verify_transfer(
    receipt: dict[str, Any],
    report_path: Path,
    *,
    commit: str,
    runtime: str,
    platform: str,
    artifact_sha: str,
    claims: dict[str, Any],
) -> dict[str, Any]:
    """Reject incomplete evidence as well as mismatched evidence."""
    try:
        return _verify_transfer(
            receipt,
            report_path,
            commit=commit,
            runtime=runtime,
            platform=platform,
            artifact_sha=artifact_sha,
            claims=claims,
        )
    except (KeyError, TypeError, ValueError, IndexError, OSError) as error:
        raise bundle.BundleError(
            "incomplete canonical MCK producer evidence"
        ) from error


def qualify(
    directory: Path,
    runtime: str,
    tool_path: Path,
    output: Path,
    receipt_path: Path,
    commit: str,
    adapter: Path | None = None,
) -> dict[str, Any]:
    """Execute the canonical suite and saved recheck while all identities exist."""
    directory = directory.resolve()
    if output.resolve().is_relative_to(
        directory
    ) or receipt_path.resolve().is_relative_to(directory):
        raise bundle.BundleError("MCK evidence must remain outside canonical bundles")
    descriptor = _descriptor(directory, runtime)
    if (
        descriptor["gitCommit"] != commit
        or descriptor["version"] != bundle.crate_version()
    ):
        raise bundle.BundleError("MCK candidate source/version differs")
    platform = bundle._target() if runtime == "process" else "portable"
    selected = [
        entry
        for entry in descriptor["artifacts"]
        if runtime == "wasm" or entry["platform"] == platform
    ]
    if len(selected) != 1:
        raise bundle.BundleError("MCK needs exactly the selected runtime artifact")
    entry = selected[0]
    guest = (directory / entry["filename"]).resolve()
    roles: dict[str, dict[str, str]] = {
        "guest": {"path": str(guest), "sha256": mep_tool.sha(guest)},
        "compilerLock": {
            "path": str(bundle.ROOT / "rust/Cargo.lock"),
            "sha256": mep_tool.sha(bundle.ROOT / "rust/Cargo.lock"),
        },
    }
    host, arguments = guest, []
    if runtime == "wasm":
        if adapter is None:
            raise bundle.BundleError(
                "WASM MCK qualification needs its concrete adapter"
            )
        host = adapter.resolve(strict=True)
        arguments = [str(guest)]
        for name, path in (
            ("adapter", host),
            ("adapterLock", bundle.ROOT / "tools/extension-qualification/Cargo.lock"),
            (
                "adapterSource",
                bundle.ROOT / "tools/extension-qualification/src/bin/mep_wasm_host.rs",
            ),
        ):
            roles[name] = {"path": str(path), "sha256": mep_tool.sha(path)}
    tool = _tool(tool_path)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        tool["executable"],
        "--no-banner",
        "mck",
        "mep",
        "guest-run",
        "--kit",
        tool["kit"],
        "--expect-kit-sha256",
        tool["corpusSha256"],
        "--host",
        str(host),
        "--report",
        str(output),
    ]
    for argument in arguments:
        command.extend(("--host-arg", argument))
    for role in roles.values():
        command.extend(("--identity-file", role["path"]))
    with tempfile.TemporaryDirectory(prefix="canonical-python-mep-") as scratch:
        environment = os.environ | {"MORPHIR_HOME": scratch, "MORPHIR_NO_BANNER": "1"}
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
            environment[name] = environment[name.lower()] = bundle.OFFLINE
        environment.pop("NO_PROXY", None)
        environment.pop("no_proxy", None)
        first = subprocess.run(
            command, env=environment, capture_output=True, text=True, timeout=300
        )
        if first.returncode:
            raise bundle.BundleError(
                f"canonical MCK run failed: {first.stdout} {first.stderr}; "
                f"report {output}"
            )
        recheck_command = [
            tool["executable"],
            "--no-banner",
            "mck",
            "mep",
            "report-check",
            "--kit",
            tool["kit"],
            str(output),
        ]
        recheck = subprocess.run(
            recheck_command, env=environment, capture_output=True, text=True, timeout=60
        )
        if recheck.returncode:
            raise bundle.BundleError(
                f"canonical MCK recheck failed: {recheck.stdout} {recheck.stderr}"
            )
    report = mep_tool.object_file(output)
    if report["identity"]["arguments"] != [
        argument_blob(value, windows=os.name == "nt") for value in arguments
    ]:
        raise bundle.BundleError("MCK invocation arguments differ")
    roles = _bind_roles(roles, report["identity"])
    receipt = {
        "kind": "canonical-mep-producer-recheck",
        "sourceCommit": commit,
        "runtime": runtime,
        "platform": platform,
        "artifactSha256": entry["sha256"],
        "definitionInputs": definition_hashes(),
        "checker": tool,
        "reportFilename": output.name,
        "reportSha256": mep_tool.sha(output),
        "roles": roles,
        "invocation": {
            "host": str(host),
            "arguments": arguments,
            "windows": os.name == "nt",
        },
        "checkedIdentity": report["identity"],
        "recheck": {
            "exitCode": recheck.returncode,
            "stdout": recheck.stdout,
            "stderr": recheck.stderr,
        },
    }
    verify_transfer(
        receipt,
        output,
        commit=commit,
        runtime=runtime,
        platform=platform,
        artifact_sha=entry["sha256"],
        claims=entry["claims"],
    )
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def verify_release(
    inputs: Path, wasm_bundle: Path, wasm_proofs: Path, commit: str
) -> dict[str, Any]:
    """Require all six producer rechecks before the existing release assembly."""
    from scripts.process_extension import PLATFORMS

    proofs = []
    for target in PLATFORMS:
        root = inputs / f"morphir-python-process-{target}"
        proofs.append(
            (
                root / ".morphir/build/extensions/python-process",
                root / ".dev/qualification",
                "process",
                target,
                f"mep-{target}",
            )
        )
    proofs.append((wasm_bundle, wasm_proofs, "wasm", "portable", "bundle-mep"))
    results = []
    for directory, evidence, runtime, platform, prefix in proofs:
        descriptor = _descriptor(directory, runtime)
        if descriptor["gitCommit"] != commit:
            raise bundle.BundleError("MCK release source differs")
        (entry,) = descriptor["artifacts"]
        if runtime == "process" and entry["platform"] != platform:
            raise bundle.BundleError("MCK release platform differs")
        report_path = evidence / f"{prefix}-report.json"
        receipt_path = evidence / f"{prefix}-recheck.json"
        receipt = mep_tool.object_file(receipt_path)
        verify_transfer(
            receipt,
            report_path,
            commit=commit,
            runtime=runtime,
            platform=platform,
            artifact_sha=mep_tool.sha(directory / entry["filename"]),
            claims=entry["claims"],
        )
        results.append(
            {
                "runtime": runtime,
                "platform": platform,
                "artifactSha256": entry["sha256"],
                "reportFilename": report_path.name,
                "reportSha256": mep_tool.sha(report_path),
                "receiptFilename": receipt_path.name,
                "receiptSha256": mep_tool.sha(receipt_path),
                "checkerBinarySha256": receipt["checker"]["binarySha256"],
            }
        )
    pin = bundle.declaration()["mep"]
    return {
        "sourceCommit": commit,
        "profile": pin["profile"],
        "checkerRevision": pin["rev"],
        "corpusSha256": pin["corpus_sha256"],
        "requiredCasesPerArtifact": pin["required_cases"],
        "producerRechecks": results,
    }


def main() -> None:
    """Qualify one producer's canonical bundle using an explicitly prepared tool."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--runtime", choices=("process", "wasm"), required=True)
    parser.add_argument("--tool", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--adapter", type=Path)
    args = parser.parse_args()
    qualify(
        args.bundle,
        args.runtime,
        args.tool,
        args.report,
        args.receipt,
        args.commit,
        args.adapter,
    )


if __name__ == "__main__":
    main()
