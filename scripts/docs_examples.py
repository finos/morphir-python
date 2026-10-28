"""Synchronize and verify the documentation's canonical installed examples."""

from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MARKER = re.compile(
    r"<!-- example: ([\w/.-]+)(?:#([\w-]+))? -->.*?<!-- /example -->", re.S
)
REFERENCE = re.compile(r"<!-- reference: (\w+) -->.*?<!-- /reference -->", re.S)


def source_region(root: Path, name: str, region: str | None) -> str:
    """Read a contained example file or a named source region."""
    path = (root / name).resolve()
    if not path.is_relative_to((root / "examples").resolve()):
        raise ValueError(f"Example source escapes examples/: {name}")
    text = path.read_text()
    if region:
        match = re.search(
            rf"^# docs:start {re.escape(region)}\n"
            rf"(.*?)^# docs:end {re.escape(region)}$",
            text,
            re.M | re.S,
        )
        if match is None:
            raise ValueError(f"Missing region {name}#{region}")
        text = match[1]
    return text.rstrip() + "\n"


def reference(name: str) -> str:
    """Describe actual public exports and command options without rich wrapping."""
    if name == "api":
        from morphir_tools import python as api

        lines = []
        for symbol in api.__all__:
            value = getattr(api, symbol)
            if inspect.isfunction(value) or inspect.isclass(value):
                try:
                    rendered = str(inspect.signature(value))
                except ValueError:
                    rendered = ""
                lines.append(symbol + rendered)
            else:
                lines.append(symbol)
        return "\n".join(lines) + "\n"
    from typer.main import get_command

    from morphir_tools.cli import app

    root: Any = get_command(app)
    command = (
        root.commands[name]
        if name in ("compile", "generate")
        else root.commands["ir"].commands[name]
    )
    lines = [f"morphir-python {'ir ' if name in ('inspect', 'convert') else ''}{name}"]
    for param in command.params:
        flags = ", ".join(param.opts + getattr(param, "secondary_opts", []))
        required = " [required]" if param.required else ""
        default = f" [default: {param.default}]" if param.default is not None else ""
        lines.append(f"{flags}{required}{default}: {getattr(param, 'help', '') or ''}")
    return "\n".join(lines) + "\n"


def synchronize(root: Path = ROOT, *, write: bool = False) -> list[str]:
    """Update snippets/references, or report drift without modifying source pages."""
    changed = []
    for page in sorted((root / "docs").glob("*.md")):
        original = page.read_text()

        def snippet(match: re.Match[str]) -> str:
            name, region = match.groups()
            language = {".py": "python", ".toml": "toml"}.get(Path(name).suffix, "bash")
            key = name + (f"#{region}" if region else "")
            return (
                f"<!-- example: {key} -->\n```{language}\n"
                f"{source_region(root, name, region)}```\n<!-- /example -->"
            )

        updated = MARKER.sub(snippet, original)
        updated = REFERENCE.sub(
            lambda m: (
                f"<!-- reference: {m[1]} -->\n```text\n"
                f"{reference(m[1])}```\n<!-- /reference -->"
            ),
            updated,
        )
        if updated != original:
            changed.append(page.relative_to(root).as_posix())
            if write:
                page.write_text(updated)
    return changed


def run_examples(python: Path, group: str = "all") -> dict[str, object]:
    """Execute examples and CLI recipes outside the checkout with installed packages."""
    manifest = json.loads((ROOT / "examples/manifest.json").read_text())
    completed = []
    with tempfile.TemporaryDirectory(prefix="morphir-docs-") as scratch:
        for item in manifest["examples"]:
            if group != "all" and item["packages"] != group:
                continue
            result = subprocess.run(
                [str(python), "-I", str(ROOT / item["source"])],
                cwd=scratch,
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stdout != item["stdout"]:
                raise ValueError(
                    f"Unexpected output for {item['source']}: {result.stdout!r}"
                )
            if list(Path(scratch).iterdir()):
                raise ValueError(f"Example wrote unexpected files: {item['source']}")
            completed.append(item["source"])
        if group != "library":
            tools = Path(scratch) / "tools"
            tools.mkdir()
            for name in ("bash", "mkdir", "cat"):
                executable_path = shutil.which(name)
                if executable_path is None:
                    raise ValueError(f"Missing POSIX recipe tool: {name}")
                (tools / name).symlink_to(executable_path)
            environment = os.environ | {
                "PATH": str(python.parent) + os.pathsep + str(tools)
            }
            if shutil.which("rustc", path=environment["PATH"]) is not None:
                raise ValueError("Example environment must not expose Rust")
            subprocess.run(
                ["bash", str(ROOT / "examples/cli.sh")],
                cwd=scratch,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            for name in (
                "model.json",
                "rebuilt.json",
                "model-v4.json",
                "generated/acme/models.py",
                "generated/acme/rules.py",
            ):
                if not (Path(scratch) / name).is_file():
                    raise ValueError(f"CLI example did not create {name}")
            # Compare decoded IR, not JSON formatting or source spelling.
            compare = (
                "from pathlib import Path; "
                "from morphir.ir.v3.codec import decode_versioned_distribution as d; "
                "assert d(Path('model.json').read_text()) == "
                "d(Path('rebuilt.json').read_text())"
            )
            subprocess.run([str(python), "-I", "-c", compare], cwd=scratch, check=True)
            behavior = (
                "import sys; sys.path.insert(0, 'generated'); "
                "from acme.models import Approved, Pending; "
                "from acme.rules import choose; "
                "assert choose(True, Approved(3.0), Pending()) == Approved(3.0)"
            )
            subprocess.run([str(python), "-I", "-c", behavior], cwd=scratch, check=True)
            executable = python.parent / "morphir-python"
            protected = Path(scratch) / "generated/acme/models.py"
            before = protected.read_bytes()
            failure = subprocess.run(
                [
                    str(executable),
                    "generate",
                    "model.json",
                    "--output-dir",
                    "generated",
                ],
                cwd=scratch,
                capture_output=True,
                text=True,
            )
            if failure.returncode != 1 or protected.read_bytes() != before:
                raise ValueError("Nonempty generation directory did not fail safely")
            invalid = Path(scratch) / "invalid.py"
            invalid.write_text("answer = 42\n")
            model_before = (Path(scratch) / "model.json").read_bytes()
            failure = subprocess.run(
                [
                    str(executable),
                    "compile",
                    str(invalid),
                    "--package",
                    "acme/example",
                    "--output",
                    "model.json",
                ],
                cwd=scratch,
                capture_output=True,
                text=True,
            )
            if failure.returncode != 1 or "PY004" not in failure.stderr:
                raise ValueError("Unsupported-source diagnostic changed")
            if (Path(scratch) / "model.json").read_bytes() != model_before:
                raise ValueError("Failed compilation changed existing IR output")
            completed.append("examples/cli.sh")
    packages = json.loads(
        subprocess.check_output(
            [
                str(python),
                "-I",
                "-c",
                "import json,importlib.metadata as m; "
                "print(json.dumps({d.metadata['Name']:d.version "
                "for d in m.distributions()}))",
            ],
            text=True,
        )
    )
    return {"state": "succeeded", "examples": completed, "packages": packages}


def archive_examples() -> None:
    """Create a deterministic download from the same checked example files."""
    output = ROOT / "site/downloads/examples.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((ROOT / "examples").rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                info = zipfile.ZipInfo(
                    path.relative_to(ROOT).as_posix(), (2026, 1, 1, 0, 0, 0)
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())


def main() -> None:
    """Synchronize source snippets or run installed learning workflows."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["sync", "check", "test", "archive"])
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument(
        "--group", choices=["all", "compiler", "library"], default="all"
    )
    args = parser.parse_args()
    if args.command in ("sync", "check"):
        changed = synchronize(write=args.command == "sync")
        if changed:
            print("\n".join(changed))
            if args.command == "check":
                parser.exit(
                    1,
                    "Run scripts/docs_examples.py sync and review the snippets.\n",
                )
    elif args.command == "archive":
        archive_examples()
    else:
        print(json.dumps(run_examples(args.python.absolute(), args.group), indent=2))


if __name__ == "__main__":
    main()
