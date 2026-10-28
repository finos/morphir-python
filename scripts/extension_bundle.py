"""Package the morphir-python WASM extension and qualify it in a Morphir host.

Subcommands:

- ``package --wasm FILE --output DIR [--git-commit SHA]``: run finos/morphir-rust's
  canonical WASM packager, unchanged, at the revision pinned in
  ``rust/extension.toml``. The packager reads this repository's extension
  declaration and crate version, asks the exact guest bytes for their capability
  claims, and writes the WASM, its ``.sha256`` file and a version-2
  ``release.json``.
- ``host-check --bundle DIR``: download the pinned Morphir CLI, verify its
  digest, publish and install the bundle into a new Morphir home, delete the
  repository, block network access, then compile, generate and recompile a
  multi-module model in IR v3 and v4. The compiled IR must equal what the Python
  API produces for the same sources.

Each subcommand prints a JSON receipt and exits non-zero on the first failure.
"""

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
import tomllib
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DECLARATION = ROOT / "rust" / "extension.toml"
CRATE = ROOT / "rust" / "crates" / "morphir-python-binding" / "Cargo.toml"
SAMPLE = ROOT / "tests" / "fixtures" / "python" / "loans"
CACHE = ROOT / ".dev" / "tools"
# A closed local port: any attempted network access fails fast.
OFFLINE = "http://127.0.0.1:9"


class BundleError(Exception):
    """A packaging or qualification step failed."""


def declaration() -> dict[str, Any]:
    """Return the parsed ``rust/extension.toml``."""
    return tomllib.loads(DECLARATION.read_text())


def crate_version() -> str:
    """Return the binding crate version, which is the extension version."""
    return str(tomllib.loads(CRATE.read_text())["package"]["version"])


def sha256(data: bytes) -> str:
    """Return a hexadecimal SHA-256 digest."""
    return hashlib.sha256(data).hexdigest()


def registry_entry(extension: dict[str, Any]) -> str:
    """Render the extension as a morphir-rust ``.github/extensions.toml`` file."""
    short_id = extension["short_id"]
    lines = [f"[extensions.{short_id}]"]
    for key, value in extension.items():
        if key == "short_id":
            continue
        lines.append(f"{key} = {_toml(value)}")
    return "\n".join(lines) + "\n"


def _toml(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml(item) for item in value) + "]"
    if isinstance(value, dict):
        items = ", ".join(f"{k} = {_toml(v)}" for k, v in value.items())
        return "{ " + items + " }"
    raise BundleError(f"unsupported declaration value {value!r}")


def _run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, text=True, **kwargs)


def packager_checkout() -> Path:
    """Fetch the pinned morphir-rust revision and reset it to a clean state."""
    pin = declaration()["packager"]
    checkout = CACHE / f"morphir-rust-{pin['rev'][:12]}"
    if not (checkout / ".git").is_dir():
        checkout.mkdir(parents=True, exist_ok=True)
        _run(["git", "init", "--quiet"], cwd=checkout)
        _run(["git", "remote", "add", "origin", pin["repository"]], cwd=checkout)
    if (
        subprocess.run(
            ["git", "cat-file", "-e", f"{pin['rev']}^{{commit}}"],
            cwd=checkout,
            capture_output=True,
            check=False,
        ).returncode
        != 0
    ):
        _run(
            ["git", "fetch", "--quiet", "--depth", "1", "origin", pin["rev"]],
            cwd=checkout,
        )
    _run(["git", "checkout", "--quiet", "--force", pin["rev"]], cwd=checkout)
    _run(["git", "clean", "--quiet", "-fdx", "-e", "target"], cwd=checkout)
    head = _run(["git", "rev-parse", "HEAD"], cwd=checkout, capture_output=True)
    if head.stdout.strip() != pin["rev"]:
        raise BundleError(f"packager checkout is at {head.stdout.strip()}")
    return checkout


def prepare_packager(checkout: Path) -> None:
    """Point the pinned packager at this repository's declaration and version.

    The packager reads ``.github/extensions.toml`` and the registered crate's
    ``Cargo.toml``. Replace them with this repository's extension entry and a
    dependency-free stub crate carrying the binding's version, then update only
    the workspace members in ``Cargo.lock``.
    """
    extension = declaration()["extension"]
    (checkout / ".github" / "extensions.toml").write_text(registry_entry(extension))
    crate = checkout / "crates" / extension["package"]
    shutil.rmtree(crate, ignore_errors=True)
    (crate / "src").mkdir(parents=True)
    (crate / "src" / "lib.rs").write_text("")
    (crate / "Cargo.toml").write_text(
        f'[package]\nname = "{extension["package"]}"\n'
        f'version = "{crate_version()}"\nedition = "2024"\npublish = false\n'
    )
    _run(["cargo", "update", "--quiet", "--workspace"], cwd=checkout)
    changed = _run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=checkout,
        capture_output=True,
    ).stdout.split("\n")
    allowed = (
        ".github/extensions.toml",
        "Cargo.lock",
        f"crates/{extension['package']}/",
    )
    for line in filter(None, changed):
        path = line[3:]
        if not path.startswith(allowed):
            raise BundleError(f"preparing the packager changed {path}")


def package(wasm: Path, output: Path, git_commit: str | None) -> dict[str, object]:
    """Package the guest with the pinned canonical packager."""
    checkout = packager_checkout()
    prepare_packager(checkout)
    if output.exists():
        raise BundleError(f"bundle directory {output} already exists")
    args = [sys.executable, "-B", "scripts/package_extension.py", "--short-id"]
    args += [declaration()["extension"]["short_id"], "--wasm", str(wasm.resolve())]
    args += ["--output", str(output.resolve())]
    if git_commit:
        args += ["--git-commit", git_commit]
    _run(args, cwd=checkout)
    return receipt(output)


def receipt(bundle: Path, *, version: str | None = None) -> dict[str, object]:
    """Check a bundle's files, digest and claims, and describe them."""
    extension = declaration()["extension"]
    version = crate_version() if version is None else version
    artifact = f"{extension['artifact']}-{version}.wasm"
    names = sorted(p.name for p in bundle.iterdir())
    if names != sorted([artifact, f"{artifact}.sha256", "release.json"]):
        raise BundleError(f"unexpected bundle files {names}")
    wasm = (bundle / artifact).read_bytes()
    digest = sha256(wasm)
    if (bundle / f"{artifact}.sha256").read_text() != f"{digest}  {artifact}\n":
        raise BundleError("the .sha256 file does not match the WASM")
    descriptor = json.loads((bundle / "release.json").read_text())
    (entry,) = descriptor["artifacts"]
    claims = entry["claims"]
    if (
        descriptor["extensionId"] != extension["extension_id"]
        or descriptor["version"] != version
        or entry["sha256"] != digest
        or claims["extension"]["id"] != extension["extension_id"]
        or claims["extension"]["version"] != version
    ):
        raise BundleError("release.json disagrees with the declaration or WASM")
    capabilities = claims["capabilities"]
    frontend, backend = capabilities.get("frontend"), capabilities.get("backend")
    if not (
        isinstance(frontend, dict)
        and frontend.get("compile") is True
        and frontend.get("multiDocument") is True
        and frontend.get("irVersions") == extension["ir_versions"]
        and isinstance(backend, dict)
        and backend.get("generate") is True
        and backend.get("targets") == extension["targets"]
    ):
        raise BundleError("the claims lack the declared compile and generate support")
    return {
        "bundle": {name: sha256((bundle / name).read_bytes()) for name in names},
        "wasm_sha256": digest,
        "extension": descriptor["extensionId"],
        "version": version,
        "git_commit": descriptor.get("gitCommit"),
        "packager_rev": declaration()["packager"]["rev"],
        "capabilities": sorted(k for k, v in capabilities.items() if v),
        "multiDocument": frontend["multiDocument"],
    }


def _target() -> str:
    machine = platform.machine().lower()
    arch = {"arm64": "aarch64", "amd64": "x86_64"}.get(machine, machine)
    system = {"Darwin": "apple-darwin", "Linux": "unknown-linux-gnu"}.get(
        platform.system()
    )
    if system is None:
        raise BundleError(f"no pinned Morphir CLI for {platform.system()}")
    return f"{arch}-{system}"


def morphir_cli() -> tuple[Path, str]:
    """Download the pinned Morphir CLI for this platform and verify its digest."""
    host = declaration()["host"]
    target = _target()
    expected = host["sha256"].get(target)
    if expected is None:
        raise BundleError(f"no pinned Morphir CLI digest for {target}")
    directory = CACHE / f"morphir-{host['version']}-{target}"
    binary = directory / "morphir"
    archive_name = f"morphir-{host['version']}-{target}.tgz"
    if not binary.is_file():
        with urllib.request.urlopen(
            f"{host['release']}/{archive_name}", timeout=120
        ) as r:
            data = r.read()
        if sha256(data) != expected:
            raise BundleError(f"{archive_name} digest differs from the pin")
        directory.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            member = next(
                m for m in archive.getmembers() if Path(m.name).name == "morphir"
            )
            extracted = archive.extractfile(member)
            if extracted is None:
                raise BundleError(f"{archive_name} has no morphir executable")
            binary.write_bytes(extracted.read())
        binary.chmod(0o755)
    return binary, expected


def host_check(bundle: Path, *, version: str | None = None) -> dict[str, object]:
    """Install the bundle with the pinned CLI and round trip offline."""
    from morphir_tools.python import native_compiler

    bundle = bundle.resolve()
    described = receipt(bundle, version=version)
    cli, cli_digest = morphir_cli()
    with tempfile.TemporaryDirectory(prefix="python-bundle-host-") as scratch:
        work = Path(scratch)
        project, home, repository = work / "project", work / "home", work / "repo"
        shutil.copytree(SAMPLE, project / "src")
        (project / "morphir.toml").write_text(
            '[project]\nname = "acme/example"\nversion = "0.1.0"\n'
            'source_directory = "src"\n[frontend]\nlanguage = "python"\n'
            "emit_parse_stage = false\n"
        )
        base = {**os.environ, "MORPHIR_HOME": str(home)}

        def morphir(*args: str, offline: bool = False) -> str:
            env = dict(base)
            if offline:
                for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
                    env[name] = env[name.lower()] = OFFLINE
                env.pop("NO_PROXY", None)
                env.pop("no_proxy", None)
            result = subprocess.run(
                [str(cli), *args],
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise BundleError(f"morphir {' '.join(args)}: {result.stderr}")
            return result.stdout

        morphir("extension", "repository", "init", str(repository))
        morphir(
            "extension", "repository", "add", "local", "--directory", str(repository)
        )
        morphir("extension", "repository", "publish", "local", "--bundle", str(bundle))
        morphir("extension", "repository", "verify", "local")
        morphir("extension", "install", "morphir-python", "--repository", "local")
        shutil.rmtree(repository)
        listed = morphir("extension", "list", offline=True)
        if "morphir-python" not in listed:
            raise BundleError(f"morphir-python is not installed: {listed}")
        results: dict[str, object] = {}
        for version in ("3.0.0", "4"):
            tag = version.split(".")[0]
            compiled, generated = f"compiled-{tag}", f"generated-{tag}"
            morphir(
                "compile", "--language", "python", "--input", "src",
                "--ir-version", version, "--output", compiled, offline=True,
            )  # fmt: skip
            morphir(
                "generate", "--target", "python", "--input",
                f"{compiled}/morphir-ir.json", "--output", generated, offline=True,
            )  # fmt: skip
            morphir(
                "compile", "--language", "python", "--input", generated,
                "--ir-version", version, "--output", f"re{compiled}", offline=True,
            )  # fmt: skip
            first = json.loads((project / compiled / "morphir-ir.json").read_text())
            again = json.loads(
                (project / f"re{compiled}" / "morphir-ir.json").read_text()
            )
            if first != again:
                raise BundleError(f"IR v{tag} changed across a host round trip")
            files = sorted(
                p.relative_to(project / generated).as_posix()
                for p in (project / generated).rglob("*.py")
            )
            results[f"v{tag}"] = {
                "modules": files,
                "agrees_with_python_api": agrees_with_api(first, tag),
            }
    return {
        **described,
        "host": {"morphir": declaration()["host"]["version"], "sha256": cli_digest},
        "python_api": {
            "native_version": native_compiler().version,
            "compiler_version": native_compiler().compiler_version,
        },
        "offline_round_trips": results,
    }


def agrees_with_api(document: dict[str, Any], tag: str) -> bool:
    """Compare host output with the Python API's model for the same sources."""
    from morphir.ir.v3 import codec as v3_codec
    from morphir.ir.v4 import codec as v4_codec
    from morphir_tools.python import (
        CompileFailure,
        IrVersion,
        SourceDocument,
        compile_sources,
        native_compiler,
    )

    compiler = native_compiler()
    if compiler.compiler_version != crate_version():
        raise BundleError(
            f"API compiler {compiler.compiler_version} differs from "
            f"bundle {crate_version()}"
        )
    sources = [
        SourceDocument(p.relative_to(SAMPLE).as_posix(), p.read_text())
        for p in sorted(SAMPLE.rglob("*.py"))
    ]
    version = IrVersion.V3 if tag == "3" else IrVersion.V4
    compiled = compile_sources(sources, package="acme/example", ir_version=version)
    if isinstance(compiled, CompileFailure):
        raise BundleError(f"the Python API failed: {compiled.diagnostics}")
    codec = v3_codec if tag == "3" else v4_codec
    host_model = codec.decode_versioned_distribution(json.dumps(document))
    if host_model != compiled.distribution:
        raise BundleError(f"host and Python API models differ for IR v{tag}")
    return True


def main() -> None:
    """Run one subcommand and print its receipt."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    pack = commands.add_parser("package")
    pack.add_argument("--wasm", type=Path, required=True)
    pack.add_argument("--output", type=Path, required=True)
    pack.add_argument("--git-commit")
    check = commands.add_parser("host-check")
    check.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "package":
            result = package(args.wasm, args.output, args.git_commit)
        else:
            result = host_check(args.bundle)
    except (BundleError, subprocess.CalledProcessError, OSError, KeyError) as error:
        print(f"bundle check failed: {error}", file=sys.stderr)
        raise SystemExit(1) from None
    print(json.dumps({"check": args.command, **result}, indent=2))


if __name__ == "__main__":
    main()
