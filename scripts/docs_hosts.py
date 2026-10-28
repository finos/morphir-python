"""Qualify the displayed host recipe and the pinned MoonBit envelope refusal."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import extension_bundle as bundle  # noqa: E402

PINS = ROOT / "site/integrations.json"
INPUTS: tuple[str, ...] = (
    "site/integrations.json",
    "rust/extension.toml",
    "scripts/docs_hosts.py",
    "scripts/extension_bundle.py",
    "examples/extension.sh",
    "examples/model/acme/models.py",
    "examples/model/acme/rules.py",
    "docs/python-extension.md",
    "docs/moonbit.md",
    "docs/compatibility.md",
)
INPUTS += tuple(
    p.relative_to(ROOT).as_posix() for p in sorted(bundle.SAMPLE.rglob("*.py"))
)


def sha(data: bytes) -> str:
    """Hash source or artifact bytes."""
    return hashlib.sha256(data).hexdigest()


def input_hashes(root: Path = ROOT) -> dict[str, str]:
    """Bind evidence to the recipe, pins, fixtures and checker implementation."""
    return {name: sha((root / name).read_bytes()) for name in INPUTS}


def verify_evidence(report: dict[str, Any], root: Path = ROOT) -> None:
    """Refuse missing, failed or stale qualification evidence."""
    if report.get("state") != "succeeded" or report.get("inputs") != input_hashes(root):
        raise ValueError(
            "Host evidence is missing, failed or stale; run docs_hosts.py qualify"
        )
    if not report.get("rust_recipe") or not report.get("moonbit_refusals"):
        raise ValueError("Host evidence lacks a required result")
    for version in ("3", "4"):
        result = report["moonbit_refusals"].get(version, {})
        if result.get("error") != "extension.unsupported_model_envelope":
            raise ValueError("Host evidence lacks the qualified envelope refusal")


def download(url: str, expected: str, destination: Path) -> bytes:
    """Cache only bytes that match the declared SHA-256."""
    if destination.is_file() and sha(destination.read_bytes()) == expected:
        return destination.read_bytes()
    with urllib.request.urlopen(url, timeout=120) as response:
        data: bytes = response.read()
    if sha(data) != expected:
        raise ValueError(f"SHA-256 mismatch: {url}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return data


def prepare() -> tuple[Path, Path]:
    """Acquire the declared Rust CLI and released Python bundle."""
    pins = json.loads(PINS.read_text())
    host, archive_digest = bundle.morphir_cli()
    version = pins["rust_host"]["version"]
    if bundle.declaration()["host"]["version"] != version:
        raise ValueError("Host declaration and documentation pins disagree")
    target = host.parent.name.removeprefix(f"morphir-{version}-")
    archive_name = f"morphir-{version}-{target}.tgz"
    data = download(
        bundle.declaration()["host"]["release"] + "/" + archive_name,
        archive_digest,
        ROOT / ".dev/docs-hosts" / archive_name,
    )
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        member = next(m for m in archive.getmembers() if Path(m.name).name == "morphir")
        stream = archive.extractfile(member)
        if stream is None or sha(stream.read()) != sha(host.read_bytes()):
            raise ValueError("Cached host does not match its verified release archive")
    identity = subprocess.check_output([str(host), "--version"], text=True)
    if f"morphir {version}" not in identity:
        raise ValueError("Wrong Morphir provider/version")
    spec = pins["python_bundle"]
    directory = ROOT / ".dev/docs-hosts" / f"python-{spec['version']}"
    for name, expected in spec["files"].items():
        destination = directory / (
            "release.json" if name.endswith(".release.json") else name
        )
        download(spec["release"] + "/" + name, expected, destination)
    bundle.receipt(directory, version=spec["version"])
    return host, directory


def qualify_rust(host: Path, directory: Path) -> dict[str, Any]:
    """Run the exact displayed installation recipe, then existing offline checks."""
    with tempfile.TemporaryDirectory(prefix="docs-rust-host-") as scratch:
        work = Path(scratch)
        shutil.copytree(ROOT / "examples/model", work / "src")
        result = subprocess.run(
            ["bash", str(ROOT / "examples/extension.sh")],
            cwd=work,
            env=os.environ
            | {"MORPHIR_HOST": str(host), "PYTHON_BUNDLE": str(directory)},
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        first = json.loads((work / "compiled/morphir-ir.json").read_text())
        again = json.loads((work / "host-rebuilt/morphir-ir.json").read_text())
        if first != again:
            raise ValueError("Displayed host recipe changed IR across its round trip")
        if not (work / "host-generated/acme/rules.py").is_file():
            raise ValueError(
                "Displayed host recipe did not generate its documented module"
            )
        return {
            "recipe": "examples/extension.sh",
            "exit_code": result.returncode,
            "host_sha256": sha(host.read_bytes()),
            "offline": bundle.host_check(
                directory,
                version=json.loads(PINS.read_text())["python_bundle"]["version"],
            ),
        }


def moonbit_source() -> Path:
    """Build the exact source-pinned CLI in this repository's disposable tool cache."""
    spec = json.loads(PINS.read_text())["moonbit"]
    cache = ROOT / ".dev/docs-hosts"
    data = download(
        f"https://codeload.github.com/finos/morphir-moonbit/tar.gz/{spec['revision']}",
        spec["archive_sha256"],
        cache / "moonbit-source.tar.gz",
    )
    source: Path = cache / ("moonbit-" + spec["revision"][:12])
    # Always extract fresh source; a cache of a compiled CLI is not source evidence.
    if source.exists():
        shutil.rmtree(source)
    source.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(source, filter="data")
    source = next(source.iterdir())
    subprocess.run(
        ["mise", "trust", ".config/mise/config.toml"],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    tool = "http:moonbit@" + str(spec["toolchain"])
    subprocess.run(
        ["mise", "install", tool],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )
    moon_home = Path(
        subprocess.check_output(["mise", "where", tool], cwd=source, text=True).strip()
    )
    moon = moon_home / "bin/moon"
    environment = os.environ | {
        "MOON_HOME": str(moon_home),
        "PATH": str(moon_home / "bin") + os.pathsep + os.environ["PATH"],
    }
    for arguments in (
        ["update"],
        ["build", "apps/morphir", "--target", "js", "--release"],
    ):
        subprocess.run(
            [str(moon), *arguments],
            cwd=source,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
    return source


def qualify_moonbit() -> dict[str, Any]:
    """Probe plain v3/v4 IR at the real portable CLI boundary before execution."""
    from morphir.ir.v3 import codec as v3_codec
    from morphir.ir.v4 import codec as v4_codec
    from morphir_tools.python import (
        CompiledV3,
        CompiledV4,
        IrVersion,
        SourceDocument,
        compile_sources,
    )

    source = moonbit_source()
    binary = source / "_build/js/release/build/morphir/morphir/morphir.js"
    modules = [
        "node-mep-cli.mjs",
        "node-mep-stdio.mjs",
        "node-mep-adapter.mjs",
        "node-mep-worker.mjs",
        "mep-adapter.mjs",
        "mep-frames.mjs",
        "wasm-memory.mjs",
        "node-artifacts.mjs",
        "artifacts.mjs",
        "assembly.mjs",
        "index.mjs",
        "dist/bridge.mjs",
    ]
    pin: dict[str, Any] = {
        "contractVersion": "0.1.0-draft.1",
        "binding": "core-wasm-process",
        "executionProfile": {
            "id": "morphir/mep-bytes-v1/v1-draft",
            "sha256": (
                "6ed5e96fa9c7f7dcaa179efc88e517307463cfeddc5e2eeae854f0395e7a4ec6"
            ),
        },
        "runtime": {
            "name": "node",
            "version": "v24.22.1",
            "executable": "/not-executed/node",
            "sha256": "0" * 64,
        },
        "host": {
            "root": "/not-executed/host",
            "modules": dict.fromkeys(modules, "0" * 64),
        },
        "artifact": {
            "directory": "/not-executed/guest",
            "wasmSha256": "0" * 64,
            "manifestSha256": "0" * 64,
        },
        "origin": "Negative envelope probe: execution must never start",
    }
    results = {}
    sources = [
        SourceDocument(p.relative_to(ROOT / "examples/model").as_posix(), p.read_text())
        for p in sorted((ROOT / "examples/model").rglob("*.py"))
    ]
    with tempfile.TemporaryDirectory(prefix="docs-moonbit-") as scratch:
        work = Path(scratch)
        (work / "pin.json").write_text(json.dumps(pin))
        for version in IrVersion:
            compiled = compile_sources(
                sources, package="acme/example", ir_version=version
            )
            if isinstance(compiled, CompiledV3):
                document = v3_codec.encode_versioned_distribution(compiled.distribution)
            elif isinstance(compiled, CompiledV4):
                document = v4_codec.encode_versioned_distribution(compiled.distribution)
            else:
                raise ValueError("Interchange fixture failed compilation")
            (work / "plain.json").write_text(json.dumps(document))
            command = [
                "node",
                str(binary),
                "extension",
                "generate",
                "plain.json",
                "--extension-pin",
                "pin.json",
                "--extension-helper",
                "/not-executed/helper.mjs",
                "--output",
                "generated",
                "--json",
            ]
            result = subprocess.run(
                command, cwd=work, text=True, capture_output=True, timeout=20
            )
            report = json.loads(result.stdout)
            if (
                result.returncode != 2
                or report.get("error") != "extension.unsupported_model_envelope"
                or (work / "generated").exists()
            ):
                raise ValueError(
                    f"MoonBit envelope refusal changed: {result.stdout} {result.stderr}"
                )
            results[version.value] = {
                "exit_code": result.returncode,
                "error": report["error"],
                "input_sha256": sha((work / "plain.json").read_bytes()),
                "command": [
                    arg.replace(str(source), "PINNED_SOURCE") for arg in command
                ],
            }
    return {
        "revision": json.loads(PINS.read_text())["moonbit"]["revision"],
        "cli_sha256": sha(binary.read_bytes()),
        "results": results,
    }


def main() -> None:
    """Prepare, qualify or verify reusable host compatibility evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "qualify", "verify"])
    parser.add_argument(
        "--report", type=Path, default=ROOT / ".dev/docs-hosts/report.json"
    )
    args = parser.parse_args()
    try:
        if args.command == "verify":
            verify_evidence(json.loads(args.report.read_text()))
            print("Host evidence matches all relevant inputs")
            return
        host, directory = prepare()
        if args.command == "prepare":
            print(f"MORPHIR_HOST={host}\nPYTHON_BUNDLE={directory}")
            return
        rust = qualify_rust(host, directory)
        moonbit = qualify_moonbit()
        report = {
            "schema_version": 1,
            "state": "succeeded",
            "inputs": input_hashes(),
            "platform": platform.platform(),
            "python": sys.version,
            "working_tree_dirty": bool(
                subprocess.check_output(
                    ["git", "status", "--porcelain"], cwd=ROOT, text=True
                )
            ),
            "git_head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "rust_recipe": rust,
            "moonbit_refusals": moonbit["results"],
            "moonbit": moonbit,
        }
        verify_evidence(report)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        print(args.report)
    except (ValueError, OSError, subprocess.SubprocessError, bundle.BundleError) as exc:
        parser.exit(1, f"host qualification: {exc}\n")


if __name__ == "__main__":
    main()
