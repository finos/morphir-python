"""Compare framed legacy process diagnostics with the exact installed Python API.

This producer check supplements installed CLI checks, whose readable errors omit
language diagnostic codes. It is not canonical executable MEP conformance.
"""

from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from scripts import extension_bundle as bundle

SOURCE = "import os\n"


def _frame(message: dict[str, Any]) -> bytes:
    body = json.dumps(message, ensure_ascii=False).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode() + body


def _responses(data: bytes) -> list[dict[str, Any]]:
    responses: list[dict[str, Any]] = []
    offset = 0
    while offset < len(data):
        end = data.find(b"\r\n\r\n", offset, offset + 8192)
        if end < 0:
            raise bundle.BundleError("process diagnostic stdout has no bounded header")
        lengths: list[int] = []
        for line in data[offset:end].split(b"\r\n"):
            name, separator, value = line.partition(b":")
            if not separator:
                raise bundle.BundleError("process diagnostic stdout is not framed")
            if name.lower() == b"content-length":
                value = value.strip()
                if not value.isdigit():
                    raise bundle.BundleError(
                        "process diagnostic frame length is invalid"
                    )
                lengths.append(int(value))
        if len(lengths) != 1 or not 0 < lengths[0] <= 16 * 1024 * 1024:
            raise bundle.BundleError("process diagnostic frame length is not bounded")
        offset = end + 4
        body_end = offset + lengths[0]
        if body_end > len(data):
            raise bundle.BundleError("process diagnostic frame is truncated")
        message = json.loads(data[offset:body_end].decode("utf-8"))
        if not isinstance(message, dict) or len(responses) == 4:
            raise bundle.BundleError(
                "process diagnostic stdout has unexpected messages"
            )
        responses.append(message)
        offset = body_end
    return responses


def qualify(executable: Path) -> dict[str, Any]:
    """Check a real clean-environment session and retain structured parity proof."""
    from morphir_tools.python import (
        CompileFailure,
        IrVersion,
        SourceDocument,
        compile_sources,
        native_compiler,
    )

    native = native_compiler()
    if native.compiler_version != bundle.crate_version():
        raise bundle.BundleError("diagnostic API compiler does not match candidate")
    messages: list[dict[str, Any]] = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "morphir.initialize",
            "params": {
                "protocolVersions": ["0.1"],
                "host": {"name": "python-diagnostic-qualification", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "method": "morphir.initialized"},
    ]
    expected: dict[str, list[dict[str, Any]]] = {}
    for number, version in enumerate(IrVersion, 2):
        compiled = compile_sources(
            [SourceDocument("models.py", SOURCE)], package="acme", ir_version=version
        )
        if not isinstance(compiled, CompileFailure):
            raise bundle.BundleError("diagnostic fixture unexpectedly compiled")
        expected[version.value] = [
            {
                "code": item.code,
                "severity": item.severity.value,
                "message": item.message,
                "location": None
                if item.source is None
                else {
                    "uri": item.source.path,
                    "range": {
                        "start": dataclasses.asdict(item.source.start),
                        "end": dataclasses.asdict(item.source.end),
                    },
                },
            }
            for item in compiled.diagnostics
        ]
        messages.append(
            {
                "jsonrpc": "2.0",
                "id": number,
                "method": "morphir.frontend.compile",
                "params": {
                    "languageId": "python",
                    "sources": {
                        "documents": [
                            {
                                "uri": "models.py",
                                "languageId": "python",
                                "version": 1,
                                "text": SOURCE,
                            }
                        ]
                    },
                    "package": {"name": "acme"},
                    "dependencies": [],
                    "options": {"irVersion": version.value, "typesOnly": False},
                },
            }
        )
    messages.extend(
        [
            {"jsonrpc": "2.0", "id": 4, "method": "morphir.shutdown", "params": {}},
            {"jsonrpc": "2.0", "method": "morphir.exit"},
        ]
    )
    digest = bundle.sha256(executable.read_bytes())
    with tempfile.TemporaryDirectory(prefix="python-process-diagnostics-") as name:
        work = Path(name)
        owned = work / executable.name
        owned.write_bytes(executable.read_bytes())
        if bundle.sha256(owned.read_bytes()) != digest:
            raise bundle.BundleError("diagnostic artifact copy differs")
        if os.name != "nt":
            owned.chmod(0o700)
        result = subprocess.run(
            [str(owned)],
            input=b"".join(map(_frame, messages)),
            cwd=work,
            env={},
            capture_output=True,
            timeout=60,
        )
        if result.returncode or result.stderr:
            raise bundle.BundleError(f"diagnostic guest failed: {result.stderr!r}")
    replies = _responses(result.stdout)
    if [item.get("id") for item in replies] != [1, 2, 3, 4] or any(
        item.get("jsonrpc") != "2.0" or "error" in item for item in replies
    ):
        raise bundle.BundleError("diagnostic guest lifecycle/IDs differ")
    initialized = replies[0]["result"]
    if not (
        initialized["protocolVersion"] == "0.1"
        and initialized["extension"]["id"] == "morphir-python"
        and initialized["extension"]["version"] == native.compiler_version
    ):
        raise bundle.BundleError("diagnostic guest identity differs")
    cases: dict[str, Any] = {}
    for reply, version in zip(replies[1:3], IrVersion, strict=True):
        value = reply["result"]
        diagnostics = [
            {key: item.get(key) for key in ("code", "severity", "message", "location")}
            for item in value["diagnostics"]
        ]
        if (
            value["success"] is not False
            or value.get("ir") is not None
            or not diagnostics
            or diagnostics != expected[version.value]
        ):
            raise bundle.BundleError("process and Python API diagnostics differ")
        cases[version.value] = {
            "diagnostics": diagnostics,
            "pythonApi": expected[version.value],
        }
    if bundle.sha256(executable.read_bytes()) != digest:
        raise bundle.BundleError("diagnostic artifact changed during execution")
    return {
        "scope": "legacy-process-diagnostic-parity",
        "artifactSha256": digest,
        "checkerSha256": bundle.sha256(Path(__file__).read_bytes()),
        "inputSha256": bundle.sha256(SOURCE.encode()),
        "compilerVersion": native.compiler_version,
        "nativeVersion": native.version,
        "protocolVersion": "0.1",
        "cleanEnvironment": True,
        "exitCode": result.returncode,
        "stderr": result.stderr.decode(),
        "cases": cases,
    }
