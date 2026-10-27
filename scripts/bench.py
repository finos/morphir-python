"""Measure the Python compiler's cost at each layer, with fixed inputs.

Stages, all on the same sources and IR version:

- ``rust_compile`` / ``rust_generate``: the Rust trait calls, release build;
- ``bridge_compile`` / ``bridge_generate``: the same work through the JSON
  bridge, in Rust, including request parsing and result serialization;
- ``native_compile`` / ``native_generate``: the CPython module calls;
- ``api_compile`` / ``api_generate``: the public API, including codec work;
- ``codec_decode`` / ``codec_encode``: the Python v3/v4 codecs alone;
- ``cli_compile`` / ``cli_generate``: ``morphir-python`` in a new process;
- ``cold_import``: a new interpreter importing and loading the compiler;
- ``ast_parse``: Python's ``ast.parse`` on the sources, a parsing-only baseline.

There is no pure-Python compiler, so no stage supports a Rust-versus-Python
compiler speed claim; ``ast_parse`` does far less work than compilation.

The command writes raw samples and metadata to ``results.json`` and a summary to
``report.html`` in a new directory under ``.dev/bench/``.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import html
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "tests" / "fixtures" / "python" / "loans"

MODEL_TEMPLATE = """\
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Pending{i}:
    pass

@dataclass(frozen=True)
class Approved{i}:
    amount: float
    count: int

type Decision{i} = Pending{i} | Approved{i}

type Point{i} = tuple[float, float]
"""

FUNCTION_TEMPLATE = """
def choose{i}{j}(flag: bool, first: Decision{i}, second: Decision{i}) -> Decision{i}:
    if flag:
        return first
    else:
        return second

def pair{i}{j}(left: float, right: float) -> Point{i}:
    return (left, right)

def limit{i}{j}(value: int, bound: int) -> int:
    return value if value < bound else bound
"""


def tag(index: int) -> str:
    """Spell an index with two or more letters; v3 names cannot hold digits."""
    letters = ""
    index += 26
    while index:
        index, remainder = divmod(index, 26)
        letters = chr(ord("a") + remainder) + letters
    return letters


def generated_sources(modules: int, functions: int) -> dict[str, str]:
    """Return ``modules`` model and rules module pairs with ``functions`` each."""
    sources: dict[str, str] = {}
    for number in range(modules):
        i = tag(number)
        sources[f"scale/models{i}.py"] = MODEL_TEMPLATE.format(i=i)
        header = (
            "from __future__ import annotations\n"
            f"from .models{i} import Decision{i}, Point{i}\n"
        )
        body = "".join(
            FUNCTION_TEMPLATE.format(i=i, j=tag(j)) for j in range(functions)
        )
        sources[f"scale/rules{i}.py"] = header + body
    return sources


def sample_sources() -> dict[str, str]:
    """Return the checked-in two-module sample project."""
    return {
        p.relative_to(SAMPLE).as_posix(): p.read_text()
        for p in sorted(SAMPLE.rglob("*.py"))
    }


def summarize(samples: list[int]) -> dict[str, float]:
    """Return the median and spread of nanosecond samples, in milliseconds."""
    values = sorted(sample / 1e6 for sample in samples)
    quartiles = statistics.quantiles(values, n=4) if len(values) > 1 else values * 3
    return {
        "median_ms": statistics.median(values),
        "q1_ms": quartiles[0],
        "q3_ms": quartiles[-1],
        "min_ms": values[0],
        "max_ms": values[-1],
        "count": len(values),
    }


def timed(warmup: int, repetitions: int, operation: Callable[[], object]) -> list[int]:
    """Return nanosecond samples after warmup calls."""
    for _ in range(warmup):
        operation()
    samples = []
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        operation()
        samples.append(time.perf_counter_ns() - start)
    return samples


def _tool(*args: str) -> str:
    try:
        return subprocess.run(
            list(args), capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def environment() -> dict[str, object]:
    """Describe the hardware, toolchains and the loaded native module."""
    import morphir_python_native._native as native

    lock = tomllib.loads((ROOT / "rust" / "Cargo.lock").read_text())
    versions = {
        package["name"]: package["version"]
        for package in lock["package"]
        if package["name"] in {"pyo3", "morphir-core", "morphir-extension-sdk"}
    }
    module = Path(native.__file__)
    cpu = _tool("sysctl", "-n", "machdep.cpu.brand_string")
    if cpu == "unavailable" and Path("/proc/cpuinfo").exists():
        cpu = next(
            (
                line.split(":", 1)[1].strip()
                for line in Path("/proc/cpuinfo").read_text().splitlines()
                if line.startswith("model name")
            ),
            "unavailable",
        )
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": cpu,
        "cpu_count": os.cpu_count(),
        "python": sys.version,
        "rustc": _tool("rustc", "--version"),
        "cargo_profile": "release (lto, codegen-units=1, opt-level=3)",
        "crates": versions,
        "native_module": module.name,
        "native_module_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
        "native_version": native.__version__,
        "compiler_version": native.COMPILER_VERSION,
        "git_commit": _tool("git", "-C", str(ROOT), "rev-parse", "HEAD"),
        "git_dirty": bool(_tool("git", "-C", str(ROOT), "status", "--porcelain")),
    }


def rust_samples(
    request: dict[str, object], warmup: int, repetitions: int, work: Path
) -> dict[str, object]:
    """Run the release-build Rust benchmark example."""
    path = work / "request.json"
    path.write_text(json.dumps(request))
    output = subprocess.run(
        [
            "cargo", "run", "--quiet", "--locked", "--release",
            "-p", "morphir-python-native", "--example", "bench", "--",
            str(path), str(warmup), str(repetitions),
        ],
        cwd=ROOT / "rust", capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    return dict(json.loads(output))


def measure(
    name: str,
    sources: dict[str, str],
    version: str,
    warmup: int,
    repetitions: int,
    cli_repetitions: int,
) -> dict[str, object]:
    """Measure every stage for one input set and IR version."""
    import morphir_python_native._native as native
    from morphir.ir import format_version as fv
    from morphir.ir.v3 import codec as v3_codec
    from morphir.ir.v4 import codec as v4_codec
    from morphir_tools.python import (
        CompileFailure,
        Generated,
        IrVersion,
        SourceDocument,
        compile_sources,
        generate_python,
    )

    ir_version = IrVersion.V3 if version == "3" else IrVersion.V4
    codec = v3_codec if version == "3" else v4_codec
    documents = [SourceDocument(path, text) for path, text in sorted(sources.items())]
    request: dict[str, object] = {
        "package": "acme/bench",
        "sources": [{"path": d.path, "text": d.text} for d in documents],
        "exposedModules": None,
        "irVersion": version,
    }
    request_text = json.dumps(request)
    compiled = compile_sources(documents, package="acme/bench", ir_version=ir_version)
    if isinstance(compiled, CompileFailure):
        raise SystemExit(f"{name}: {compiled.diagnostics}")
    generated = generate_python(compiled.distribution)
    if not isinstance(generated, Generated):
        raise SystemExit(f"{name}: {generated}")
    ir_text = json.loads(native.compile(request_text))["ir"]
    encoded = fv.dump_json(codec.encode_versioned_distribution(compiled.distribution))

    samples: dict[str, list[int]] = {}
    with tempfile.TemporaryDirectory(prefix="morphir-bench-") as scratch:
        work = Path(scratch)
        rust = rust_samples(request, warmup, repetitions, work)
        for key in (
            "rust_compile",
            "rust_generate",
            "bridge_compile",
            "bridge_generate",
        ):
            samples[key] = [int(value) for value in rust[key]]  # type: ignore[attr-defined]
        samples["native_compile"] = timed(
            warmup, repetitions, lambda: native.compile(request_text)
        )
        samples["native_generate"] = timed(
            warmup, repetitions, lambda: native.generate(encoded)
        )
        samples["api_compile"] = timed(
            warmup,
            repetitions,
            lambda: compile_sources(
                documents, package="acme/bench", ir_version=ir_version
            ),
        )
        samples["api_generate"] = timed(
            warmup, repetitions, lambda: generate_python(compiled.distribution)
        )
        samples["codec_decode"] = timed(
            warmup, repetitions, lambda: codec.decode_versioned_distribution(ir_text)
        )
        samples["codec_encode"] = timed(
            warmup,
            repetitions,
            lambda: fv.dump_json(
                codec.encode_versioned_distribution(compiled.distribution)
            ),
        )
        samples["ast_parse"] = timed(
            warmup,
            repetitions,
            lambda: [ast.parse(text) for text in sources.values()],
        )
        source_root = work / "src"
        for path, text in sources.items():
            target = source_root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        cli = shutil.which("morphir-python", path=str(Path(sys.executable).parent))
        model = work / "model.json"
        flag = "v3" if version == "3" else "v4"
        compile_cli = [
            str(cli), "compile", str(source_root), "--package", "acme/bench",
            "--ir-version", flag, "--output", str(model),
        ]  # fmt: skip
        samples["cli_compile"] = timed(
            1,
            cli_repetitions,
            lambda: subprocess.run(compile_cli, check=True, capture_output=True),
        )
        counter = iter(range(10**6))

        def generate_cli() -> None:
            out = work / f"gen{next(counter)}"
            subprocess.run(
                [str(cli), "generate", str(model), "--output-dir", str(out)],
                check=True,
                capture_output=True,
            )

        samples["cli_generate"] = timed(1, cli_repetitions, generate_cli)
        cold = [
            sys.executable, "-c",
            "from morphir_tools.python import native_compiler; native_compiler()",
        ]  # fmt: skip
        samples["cold_import"] = timed(
            1, cli_repetitions, lambda: subprocess.run(cold, check=True)
        )
    return {
        "input": name,
        "ir_version": version,
        "modules": len(sources),
        "source_bytes": sum(len(t.encode()) for t in sources.values()),
        "ir_bytes_rust": rust["ir_bytes"],
        "ir_bytes_python_encoder": len(encoded.encode()),
        "generated_bytes": sum(len(a.text.encode()) for a in generated.artifacts),
        "warmup": warmup,
        "repetitions": repetitions,
        "process_repetitions": cli_repetitions,
        "samples_ns": samples,
        "summary": {stage: summarize(values) for stage, values in samples.items()},
    }


STAGE_NOTES = {
    "rust_compile": "Rust Frontend::compile on owned SDK values",
    "bridge_compile": "Rust bridge: parse request, compile, serialize IR text",
    "native_compile": "CPython call to _native.compile, GIL released",
    "api_compile": "compile_sources: request JSON, native call, codec decode",
    "codec_decode": "Python codec decode of the IR text alone",
    "cli_compile": "morphir-python compile in a new process",
    "rust_generate": "Rust Backend::generate on owned IR",
    "bridge_generate": "Rust bridge: parse IR text, generate, serialize",
    "native_generate": "CPython call to _native.generate",
    "api_generate": "generate_python: codec encode, native call, artifacts",
    "codec_encode": "Python codec encode of the model alone",
    "cli_generate": "morphir-python generate in a new process",
    "cold_import": "new interpreter: import API and load the native module",
    "ast_parse": "ast.parse of the sources (parsing only, no compilation)",
}


def report(results: dict[str, object], path: Path) -> None:
    """Write an HTML summary from the agent-document template."""
    env = results["environment"]
    runs = results["runs"]
    assert isinstance(env, dict) and isinstance(runs, list)
    assets = os.path.relpath(ROOT / "docs" / "templates" / "assets", path.parent)
    rows = []
    for run in runs:
        summary = run["summary"]
        for stage, note in STAGE_NOTES.items():
            s = summary[stage]
            rows.append(
                f"<tr><td>{html.escape(run['input'])}</td><td>v{run['ir_version']}</td>"
                f"<td>{stage}</td><td>{s['median_ms']:.3f}</td>"
                f"<td>{s['q1_ms']:.3f}&ndash;{s['q3_ms']:.3f}</td>"
                f"<td>{s['min_ms']:.3f}&ndash;{s['max_ms']:.3f}</td>"
                f"<td>{s['count']}</td><td>{html.escape(note)}</td></tr>"
            )
    inputs = "".join(
        f"<tr><td>{html.escape(r['input'])}</td><td>v{r['ir_version']}</td>"
        f"<td>{r['modules']}</td><td>{r['source_bytes']}</td>"
        f"<td>{r['ir_bytes_rust']}</td><td>{r['ir_bytes_python_encoder']}</td>"
        f"<td>{r['generated_bytes']}</td></tr>"
        for r in runs
    )
    environment_rows = "".join(
        f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>"
        for k, v in env.items()
    )
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Python compiler integration costs</title>
<link rel="stylesheet" href="{assets}/agent-document.css">
<link rel="stylesheet" href="{assets}/highlight/styles/github.min.css" media="(prefers-color-scheme: light)">
<link rel="stylesheet" href="{assets}/highlight/styles/github-dark.min.css" media="(prefers-color-scheme: dark)">
<script defer src="{assets}/highlight/highlight.min.js"></script>
<script defer src="{assets}/agent-document.js"></script>
</head>
<body>
<main>
<h1>Python compiler integration costs</h1>
<p class="meta">morphir-ukvn.1.6.6 · {html.escape(str(env["timestamp"]))} · measurement report</p>
<nav class="toc" aria-label="Contents">
<ul>
<li><a href="#limits">What these numbers show</a></li>
<li><a href="#inputs">Inputs</a></li>
<li><a href="#results">Results</a></li>
<li><a href="#environment">Environment</a></li>
</ul>
</nav>
<h2 id="limits">What these numbers show</h2>
<p>Each stage ran on the same sources and IR version. Values are milliseconds
per call: the median, the interquartile range and the full range. Raw samples are in
<code>results.json</code> next to this report. They are observations on one machine,
not thresholds.</p>
<p>The difference between the Rust, bridge, native and API stages is the cost of
JSON exchange, the CPython call and the Python codecs. The CLI and cold-import
stages include interpreter start-up.</p>
<p><code>ast_parse</code> only parses. It does not resolve names, check types or
build IR, so it is not a compiler. This repository has no pure-Python compiler, so
these results support no claim that Rust compiles faster or slower than an
equivalent Python implementation.</p>
<h2 id="inputs">Inputs</h2>
<table><thead><tr><th>Input</th><th>IR</th><th>Modules</th><th>Source bytes</th>
<th>IR bytes (Rust)</th><th>IR bytes (Python encoder)</th><th>Generated bytes</th></tr></thead>
<tbody>{inputs}</tbody></table>
<h2 id="results">Results</h2>
<table><thead><tr><th>Input</th><th>IR</th><th>Stage</th><th>Median ms</th><th>IQR ms</th>
<th>Range ms</th><th>Samples</th><th>Measures</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table>
<h2 id="environment">Environment</h2>
<table><tbody>{environment_rows}</tbody></table>
</main>
</body>
</html>
"""
    path.write_text(document)


def main(argv: list[str] | None = None) -> None:
    """Run the benchmark and write its results and report."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--modules", type=int, default=20)
    parser.add_argument("--functions", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--repetitions", type=int, default=30)
    parser.add_argument("--process-repetitions", type=int, default=10)
    parser.add_argument("--output", type=Path, default=ROOT / ".dev" / "bench")
    args = parser.parse_args(argv)
    inputs = {
        "sample": sample_sources(),
        f"scale-{args.modules}x{args.functions}": generated_sources(
            args.modules, args.functions
        ),
    }
    runs = [
        measure(
            name,
            sources,
            version,
            args.warmup,
            args.repetitions,
            args.process_repetitions,
        )  # fmt: skip
        for name, sources in inputs.items()
        for version in ("3", "4")
    ]
    results: dict[str, object] = {
        "environment": environment(),
        "parameters": vars(args) | {"output": str(args.output)},
        "runs": runs,
    }
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    directory = args.output / stamp
    directory.mkdir(parents=True)
    (directory / "results.json").write_text(json.dumps(results, indent=1))
    report(results, directory / "report.html")
    print(directory / "report.html")


if __name__ == "__main__":
    main()
