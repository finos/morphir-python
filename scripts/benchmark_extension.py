"""Measure fresh guests and ordered v3/v4 operations using the real Rust host.

The executable checker verifies outputs and diagnostics before accepting a sample.
This is a local performance observation, not canonical MEP conformance evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    """Hash retained input, checker, artifact or result bytes."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def sources(records: int, functions: int) -> tuple[str, str]:
    """Create frozen records and typed conditional functions deterministically."""

    def suffix(index: int) -> str:
        # Classic v3 word arrays cannot preserve numeric identifier parts.
        result = ""
        while True:
            result = chr(ord("a") + index % 26) + result
            index = index // 26 - 1
            if index < 0:
                return result

    types = "from dataclasses import dataclass\n" + "".join(
        f"\n@dataclass(frozen=True)\nclass Item{suffix(index).capitalize()}:\n"
        "    value: int\n"
        for index in range(records)
    )
    values = types + "".join(
        f"\ndef choose_{suffix(index)}(flag: bool, first: int, second: int) -> int:\n"
        "    return first if flag else second\n"
        for index in range(functions)
    )
    return types, values


def summarize(observations: dict[str, list[int]]) -> dict[str, Any]:
    """Retain raw nanoseconds with descriptive statistics and no speed claim."""
    return {
        name: {
            "samplesNs": values,
            "minNs": min(values),
            "medianNs": statistics.median(values),
            "maxNs": max(values),
        }
        for name, values in observations.items()
    }


def benchmark(
    checker: Path, wasm: Path, process: Path, output: Path, samples: int
) -> None:
    """Run fresh checker processes, verify identities, and save all raw results."""
    checker, wasm, process = (
        path.resolve(strict=True) for path in (checker, wasm, process)
    )
    output.mkdir(parents=True, exist_ok=False)
    expected = {"wasmSha256": sha(wasm), "processSha256": sha(process)}
    definitions = {
        name: sha(ROOT / "tools/extension-qualification" / name)
        for name in ("Cargo.toml", "Cargo.lock", "build.rs", "src/main.rs")
    }
    checker_digest = sha(checker)
    host_metadata: dict[str, Any] = {}
    reports: list[dict[str, Any]] = []
    measurements: dict[str, list[int]] = {}
    for name, record_count, function_count in (("small", 1, 1), ("medium", 200, 100)):
        directory = output / name
        directory.mkdir()
        types, values = sources(record_count, function_count)
        type_path, value_path = directory / "types.py", directory / "values.py"
        type_path.write_text(types)
        value_path.write_text(values)
        inputs = {
            "typesOnlySha256": sha(type_path),
            "typesAndValuesSha256": sha(value_path),
        }
        for index in range(samples):
            report = directory / f"sample-{index}.json"
            started = time.perf_counter_ns()
            result = subprocess.run(
                [
                    str(checker),
                    str(wasm),
                    str(process),
                    str(report),
                    str(type_path),
                    str(value_path),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            elapsed = time.perf_counter_ns() - started
            (directory / f"sample-{index}.log").write_text(
                result.stdout + result.stderr
            )
            if result.returncode:
                raise RuntimeError(f"Checker failed: {result.stderr}")
            raw = json.loads(report.read_text())
            if (
                raw.get("scope") != "source-pinned-legacy-host-interoperability"
                or raw.get("checkerBinarySha256") != checker_digest
                or raw.get("inputs") != inputs
                or raw.get("definitionInputs") != definitions
                or any(raw.get(key) != value for key, value in expected.items())
            ):
                raise ValueError(
                    "Checker report does not match the measured inputs/bytes"
                )
            observed_host = {key: raw[key] for key in ("hostSource", "rustc", "build")}
            if host_metadata and host_metadata != observed_host:
                raise ValueError(
                    "Measured host or build settings changed between samples"
                )
            host_metadata = observed_host
            measurements.setdefault(f"{name}/checker-wall", []).append(elapsed)
            for runtime in raw["results"]:
                prefix = f"{name}/{runtime['runtime']}"
                measurements.setdefault(prefix + "/fresh-guest-initialize", []).append(
                    runtime["startupNs"]
                )
                for operation in runtime["operations"]:
                    kind = "types" if operation["typesOnly"] else "values"
                    key = f"{prefix}/v{operation['irVersion']}/{kind}"
                    for phase in ("compile", "generate"):
                        measurements.setdefault(key + "/" + phase, []).append(
                            operation[phase + "Ns"]
                        )
            reports.append(
                {
                    "path": report.relative_to(output).as_posix(),
                    "sha256": sha(report),
                    "stdout": result.stdout,
                }
            )
    if sha(checker) != checker_digest or any(
        sha(path) != expected[key]
        for path, key in ((wasm, "wasmSha256"), (process, "processSha256"))
    ):
        raise ValueError("Measured checker or artifact changed during execution")
    summary = {
        "scope": "local-legacy-runtime-timings",
        "state": "succeeded",
        "samplesPerWorkload": samples,
        "method": {
            "host": "Fresh checker process per sample; WASM then process, sequentially",
            "startup": (
                "Fresh guest creation and MEP initialization; "
                "WASM includes module compilation"
            ),
            "operations": (
                "One session per runtime: v3 types, v3 values, v4 types, v4 values; "
                "no guest restart between operations"
            ),
            "cache": (
                "OS filesystem caches are not cleared; "
                "no persistent Wasmtime module cache is configured"
            ),
            "validation": (
                "Every sample checks compile/generate/recompile semantics, runtime "
                "diagnostic parity, orderly shutdown and process timeout cleanup"
            ),
            "limits": (
                "One machine/toolchain and fixed runtime order; "
                "descriptive measurements only, not a general speed claim"
            ),
        },
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "logicalCpus": os.cpu_count(),
            "python": platform.python_version(),
        },
        "checkerBinarySha256": checker_digest,
        **host_metadata,
        "artifacts": expected,
        "definitionInputs": {
            name: sha(ROOT / name)
            for name in (
                "scripts/benchmark_extension.py",
                "tools/extension-qualification/Cargo.toml",
                "tools/extension-qualification/Cargo.lock",
                "tools/extension-qualification/build.rs",
                "tools/extension-qualification/src/main.rs",
            )
        },
        "reports": reports,
        "measurements": summarize(measurements),
    }
    (output / "timings.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        f"Measured {samples} samples of each workload; report {output / 'timings.json'}"
    )


def main() -> None:
    """Accept exact built artifacts and a new destination for retained evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("checker", "wasm", "process", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--samples", type=int, default=5, choices=range(3, 31))
    args = parser.parse_args()
    benchmark(args.checker, args.wasm, args.process, args.output, args.samples)


if __name__ == "__main__":
    main()
