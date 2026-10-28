"""Bind native OS arguments without rewriting canonical MCK report identities."""

import copy
import json
from typing import TYPE_CHECKING, Any

import pytest

from scripts import extension_bundle as bundle
from scripts import qualify_mep

if TYPE_CHECKING:
    from pathlib import Path


def test_native_argument_blobs_preserve_unicode_bytes_and_utf16_units() -> None:
    path = "guest-λ.wasm"
    assert qualify_mep.argument_blob(path, windows=False) == {
        "Unix": list(path.encode())
    }
    assert qualify_mep.argument_blob(path, windows=True) == {
        "Windows": [ord(character) for character in path]
    }
    assert qualify_mep.argument_blob("🙂", windows=True) == {
        "Windows": [0xD83D, 0xDE42]
    }


@pytest.fixture
def witness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A small transfer fixture, never a canonical conformance report."""
    declaration = copy.deepcopy(bundle.declaration())
    records = [
        {"caseId": "describe", "observed": {"result": {"fixture": "claims"}}},
        {"caseId": "opaque-request-id", "observed": {"id": "λ"}},
    ]
    declaration["mep"]["required_cases"] = len(records)
    declaration["mep"]["case_set_sha256"] = qualify_mep.case_set_sha(records)
    monkeypatch.setattr(bundle, "declaration", lambda: declaration)
    pin = declaration["mep"]
    roles = {
        "guest": {"path": "/producer/guest", "sha256": "a" * 64},
        "compilerLock": {
            "path": "/producer/rust/Cargo.lock",
            "sha256": qualify_mep.mep_tool.sha(bundle.ROOT / "rust/Cargo.lock"),
        },
    }
    identity = {
        "runner": {
            "name": "morphir",
            "version": pin["runner_version"],
            "commit": pin["rev"],
            "dirty": False,
        },
        "runnerBinary": {"path": "/producer/morphir", "sha256": "b" * 64},
        "host": roles["guest"],
        "arguments": [],
        "files": list(roles.values()),
    }
    report = {
        "contractVersion": "0.1.0-draft.1",
        "suite": "mep-guest",
        "profile": pin["profile"],
        "corpusSha256": pin["corpus_sha256"],
        "qualified": True,
        "error": None,
        "records": records,
        "identity": identity,
    }
    path = tmp_path / "mep-report.json"
    path.write_text(json.dumps(report))
    receipt = {
        "kind": "canonical-mep-producer-recheck",
        "sourceCommit": "c" * 40,
        "runtime": "process",
        "platform": "aarch64-apple-darwin",
        "artifactSha256": "a" * 64,
        "definitionInputs": qualify_mep.definition_hashes(),
        "reportSha256": qualify_mep.mep_tool.sha(path),
        "reportFilename": path.name,
        "recheck": {
            "exitCode": 0,
            "stdout": "MEP guest report: qualified\n",
            "stderr": "",
        },
        "checker": {
            "revision": pin["rev"],
            "tree": pin["tree"],
            "cargoLockSha256": pin["cargo_lock_sha256"],
            "binarySha256": "b" * 64,
            "executable": "/producer/morphir",
        },
        "checkedIdentity": copy.deepcopy(identity),
        "roles": copy.deepcopy(roles),
        "invocation": {"host": "/producer/guest", "arguments": [], "windows": False},
    }
    return {"receipt": receipt, "report": report, "path": path}


def verify(witness: dict[str, Any]) -> dict[str, Any]:
    return qualify_mep.verify_transfer(
        witness["receipt"],
        witness["path"],
        commit="c" * 40,
        runtime=witness["receipt"]["runtime"],
        platform=witness["receipt"]["platform"],
        artifact_sha="a" * 64,
        claims={"fixture": "claims"},
    )


def reseal(witness: dict[str, Any]) -> None:
    witness["path"].write_text(json.dumps(witness["report"]))
    witness["receipt"]["reportSha256"] = qualify_mep.mep_tool.sha(witness["path"])


def test_transfer_preserves_original_foreign_paths(witness: dict[str, Any]) -> None:
    assert verify(witness) == witness["report"]


@pytest.mark.parametrize(
    "field",
    [
        "sourceCommit",
        "artifactSha256",
        "definitionInputs",
        "reportSha256",
        "reportFilename",
        "recheck",
        "checker",
        "checkedIdentity",
        "roles",
        "invocation",
    ],
)
def test_missing_producer_evidence_blocks_transfer(
    witness: dict[str, Any],
    field: str,
) -> None:
    del witness["receipt"][field]
    with pytest.raises(bundle.BundleError):
        verify(witness)


@pytest.mark.parametrize(
    "mutation",
    [
        "source",
        "artifact",
        "definitions",
        "checker",
        "failed-recheck",
        "pending-recheck",
        "report-bytes",
        "corpus",
        "profile",
        "case-set",
        "duplicate-case",
        "missing-case",
        "claims",
        "lock",
        "extra-file",
        "arguments",
        "host",
        "dirty-runner",
    ],
)
def test_altered_evidence_blocks_transfer_even_when_qualified(
    witness: dict[str, Any],
    mutation: str,
) -> None:
    receipt, report = witness["receipt"], witness["report"]
    if mutation == "source":
        receipt["sourceCommit"] = "d" * 40
    elif mutation == "artifact":
        receipt["artifactSha256"] = "d" * 64
    elif mutation == "definitions":
        receipt["definitionInputs"] = {}
    elif mutation == "checker":
        receipt["checker"]["revision"] = "d" * 40
    elif mutation == "failed-recheck":
        receipt["recheck"]["exitCode"] = 1
    elif mutation == "pending-recheck":
        receipt["recheck"]["stdout"] = "pending"
    elif mutation == "report-bytes":
        witness["path"].write_text("{}")
        with pytest.raises(bundle.BundleError):
            verify(witness)
        return
    elif mutation == "corpus":
        report["corpusSha256"] = "d" * 64
    elif mutation == "profile":
        report["profile"] = "moonbit-rich-ion"
    elif mutation == "case-set":
        report["records"][1]["caseId"] = "unknown"
    elif mutation == "duplicate-case":
        report["records"][1]["caseId"] = "describe"
    elif mutation == "missing-case":
        report["records"].pop()
    elif mutation == "claims":
        report["records"][0]["observed"]["result"] = {}
    elif mutation == "lock":
        receipt["roles"]["compilerLock"]["sha256"] = "d" * 64
    elif mutation == "extra-file":
        report["identity"]["files"].append({"path": "/extra", "sha256": "d" * 64})
    elif mutation == "arguments":
        report["identity"]["arguments"] = [
            qualify_mep.argument_blob("x", windows=False)
        ]
    elif mutation == "host":
        report["identity"]["host"] = {"path": "/other", "sha256": "a" * 64}
    elif mutation == "dirty-runner":
        report["identity"]["runner"]["dirty"] = True
    reseal(witness)
    with pytest.raises(bundle.BundleError):
        verify(witness)


def test_live_roles_use_physical_files(tmp_path: Path) -> None:
    guest = tmp_path / "guest"
    guest.write_bytes(b"actual artifact")
    alias = tmp_path / "alias"
    alias.symlink_to(guest)
    record = {"path": str(alias), "sha256": qualify_mep.mep_tool.sha(guest)}
    assert qualify_mep._bind_roles(
        {"guest": {"path": str(guest), "sha256": record["sha256"]}},
        {"files": [record]},
    ) == {"guest": record}


def test_windows_paths_do_not_use_collector_filesystem() -> None:
    assert qualify_mep._same_recorded_path(
        "C:/runner/guest.exe",
        r"\\?\C:\runner\guest.exe",
        windows=True,
    )
    assert not qualify_mep._same_recorded_path(
        "C:/runner/guest.exe",
        "C:/other/guest.exe",
        windows=True,
    )


def wasm_witness(witness: dict[str, Any]) -> None:
    receipt, report = witness["receipt"], witness["report"]
    roles = receipt["roles"]
    roles["adapter"] = {"path": "/producer/adapter", "sha256": "d" * 64}
    for name, relative in (
        ("adapterLock", "tools/extension-qualification/Cargo.lock"),
        ("adapterSource", "tools/extension-qualification/src/bin/mep_wasm_host.rs"),
    ):
        roles[name] = {
            "path": f"/producer/{relative}",
            "sha256": qualify_mep.mep_tool.sha(bundle.ROOT / relative),
        }
    receipt["runtime"], receipt["platform"] = "wasm", "portable"
    receipt["invocation"] = {
        "host": roles["adapter"]["path"],
        "arguments": [roles["guest"]["path"]],
        "windows": False,
    }
    report["identity"]["host"] = roles["adapter"]
    report["identity"]["arguments"] = [
        qualify_mep.argument_blob(roles["guest"]["path"], windows=False)
    ]
    report["identity"]["files"] = list(roles.values())
    receipt["checkedIdentity"] = copy.deepcopy(report["identity"])
    reseal(witness)


def test_wasm_transfer_binds_adapter_and_guest_argument(
    witness: dict[str, Any],
) -> None:
    wasm_witness(witness)
    assert verify(witness) == witness["report"]
    # Even a matching receipt/report cannot substitute another argument for the
    # concrete guest whose bytes the producer checked.
    witness["receipt"]["invocation"]["arguments"] = ["/producer/other.wasm"]
    witness["report"]["identity"]["arguments"] = [
        qualify_mep.argument_blob("/producer/other.wasm", windows=False)
    ]
    witness["receipt"]["checkedIdentity"] = copy.deepcopy(witness["report"]["identity"])
    reseal(witness)
    with pytest.raises(bundle.BundleError):
        verify(witness)


def test_failed_saved_recheck_never_emits_a_receipt(
    witness: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess

    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "guest").write_bytes(b"guest")
    monkeypatch.setattr(
        qualify_mep,
        "_descriptor",
        lambda *_: {
            "gitCommit": "c" * 40,
            "version": bundle.crate_version(),
            "artifacts": [
                {
                    "platform": bundle._target(),
                    "filename": "guest",
                    "sha256": "a" * 64,
                    "claims": {"fixture": "claims"},
                }
            ],
        },
    )
    monkeypatch.setattr(
        qualify_mep,
        "_tool",
        lambda _: {
            "executable": "checker",
            "kit": "kit",
            "corpusSha256": "b" * 64,
        },
    )
    results = iter(
        [
            subprocess.CompletedProcess([], 0, "qualified", ""),
            subprocess.CompletedProcess([], 1, "", "identity no longer matches"),
        ]
    )
    monkeypatch.setattr(qualify_mep.subprocess, "run", lambda *_, **__: next(results))
    output = tmp_path / "recheck.json"
    with pytest.raises(bundle.BundleError, match="recheck failed"):
        qualify_mep.qualify(
            candidate,
            "process",
            tmp_path / "tool.json",
            witness["path"],
            output,
            "c" * 40,
        )
    assert not output.exists()


@pytest.mark.parametrize(
    "missing",
    [
        "x86_64-unknown-linux-gnu",
        "aarch64-unknown-linux-gnu",
        "aarch64-apple-darwin",
        "x86_64-apple-darwin",
        "x86_64-pc-windows-msvc",
        "portable",
    ],
)
def test_release_requires_every_platform_and_wasm_proof(
    witness: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    from scripts.process_extension import PLATFORMS

    inputs = tmp_path / "inputs"
    wasm_bundle, wasm_proofs = tmp_path / "wasm", tmp_path / "wasm-proofs"
    monkeypatch.setattr(
        qualify_mep,
        "_descriptor",
        lambda directory, _: (
            qualify_mep.mep_tool.object_file(directory / "release.json")
        ),
    )
    missing_path = None
    for target in (*PLATFORMS, "portable"):
        item = copy.deepcopy(witness)
        is_wasm = target == "portable"
        if is_wasm:
            wasm_witness(item)
            directory, evidence, prefix = wasm_bundle, wasm_proofs, "bundle-mep"
        else:
            root = inputs / f"morphir-python-process-{target}"
            directory = root / ".morphir/build/extensions/python-process"
            evidence = root / ".dev/qualification"
            prefix = f"mep-{target}"
        directory.mkdir(parents=True)
        evidence.mkdir(parents=True)
        guest = directory / "guest"
        guest.write_bytes(target.encode())
        digest = qualify_mep.mep_tool.sha(guest)
        receipt, report = item["receipt"], item["report"]
        receipt["platform"] = target
        receipt["artifactSha256"] = digest
        receipt["roles"]["guest"]["sha256"] = digest
        receipt["invocation"]["windows"] = target.endswith("windows-msvc")
        report["identity"]["files"] = list(receipt["roles"].values())
        report["identity"]["host"] = receipt["roles"]["adapter" if is_wasm else "guest"]
        receipt["checkedIdentity"] = copy.deepcopy(report["identity"])
        item["path"] = evidence / f"{prefix}-report.json"
        receipt["reportFilename"] = item["path"].name
        reseal(item)
        path = evidence / f"{prefix}-recheck.json"
        path.write_text(json.dumps(receipt))
        (directory / "release.json").write_text(
            json.dumps(
                {
                    "gitCommit": "c" * 40,
                    "artifacts": [
                        {
                            "platform": target,
                            "filename": "guest",
                            "sha256": digest,
                            "claims": {"fixture": "claims"},
                        }
                    ],
                }
            )
        )
        if target == missing:
            missing_path = path
    result = qualify_mep.verify_release(inputs, wasm_bundle, wasm_proofs, "c" * 40)
    assert len(result["producerRechecks"]) == 6
    assert missing_path is not None
    missing_path.unlink()
    with pytest.raises((bundle.BundleError, OSError)):
        qualify_mep.verify_release(inputs, wasm_bundle, wasm_proofs, "c" * 40)
