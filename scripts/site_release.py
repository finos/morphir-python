"""Bind the checked site bytes and required evidence to a deployable source revision."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.docs_hosts import verify_evidence  # noqa: E402


def tree_hashes(directory: Path) -> dict[str, str]:
    """Identify every published file except the manifest that contains these hashes."""
    hashes = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("Site artifact contains a symlink")
        if path.is_file() and path != directory / "site-evidence.json":
            hashes[path.relative_to(directory).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return hashes


def producer(run: dict[str, Any], repository: str) -> tuple[str, int]:
    """Accept artifacts only from successful CI runs of this repository's main."""
    if (
        run.get("conclusion") != "success"
        or run.get("event") not in ("push", "workflow_dispatch")
        or run.get("head_branch") != "main"
        or run.get("head_repository", {}).get("full_name") != repository
        or run.get("path") != ".github/workflows/ci.yml"
    ):
        raise ValueError("Untrusted or unsuccessful site artifact producer")
    source = str(run.get("head_sha", ""))
    if len(source) != 40 or any(c not in "0123456789abcdef" for c in source):
        raise ValueError("Invalid producer source revision")
    return source, int(run["id"])


def verify(directory: Path, source: str, *, deploy: bool) -> dict[str, Any]:
    """Reject altered bytes, mismatched candidates or absent deployment evidence."""
    report: dict[str, Any] = json.loads((directory / "site-evidence.json").read_text())
    if report.get("source") != source:
        raise ValueError("Site candidate does not match the selected source revision")
    if report.get("state") != "succeeded" or report.get("files") != tree_hashes(
        directory
    ):
        raise ValueError("Site artifact differs from the checked output")
    if deploy and report.get("eligible_for_deploy") is not True:
        raise ValueError("Site artifact lacks required deployment evidence")
    return report


def seal(directory: Path, examples: Path | None, hosts: Path | None) -> None:
    """Record the exact checked output and qualification results without rebuilding."""
    source = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    build = json.loads((directory / "telescope-build.json").read_text())
    pins = json.loads((ROOT / "site/toolchain.json").read_text())
    if build.get("toolkit_version") != pins["version"]:
        raise ValueError("Telescope output does not match the pinned tool")
    checks: dict[str, Any] = {}
    if examples:
        result = json.loads(examples.read_text())
        if result.get("state") != "succeeded" or result.get("source") != source:
            raise ValueError("Example evidence does not match the site candidate")
        for group in ("released", "candidate", "library"):
            if result.get(group, {}).get("state") != "succeeded":
                raise ValueError(f"Required example group did not succeed: {group}")
        checks["examples"] = result
    if hosts:
        result = json.loads(hosts.read_text())
        verify_evidence(result)
        checks["hosts"] = result
    report = {
        "schema_version": 1,
        "state": "succeeded",
        "source": source,
        "eligible_for_deploy": bool(examples and hosts),
        "tool": build,
        "checks": checks,
        "files": tree_hashes(directory),
    }
    (directory / "site-evidence.json").write_text(json.dumps(report, indent=2) + "\n")
    verify(directory, source, deploy=bool(examples and hosts))


def main() -> None:
    """Seal a checked build or verify an immutable candidate before promotion."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["seal", "verify", "producer"])
    parser.add_argument("--site", type=Path, default=ROOT / "_site")
    parser.add_argument("--source")
    parser.add_argument("--examples", type=Path)
    parser.add_argument("--hosts", type=Path)
    parser.add_argument("--deploy", action="store_true")
    parser.add_argument("--run-json", type=Path)
    parser.add_argument("--repository")
    args = parser.parse_args()
    try:
        if args.command == "producer":
            if not args.run_json or not args.repository:
                parser.error("producer requires --run-json and --repository")
            source, run_id = producer(
                json.loads(args.run_json.read_text()), args.repository
            )
            print(f"source={source}\nrun={run_id}")
            return
        if args.command == "seal":
            seal(args.site, args.examples, args.hosts)
        else:
            if not args.source:
                parser.error("verify requires --source")
            verify(args.site, args.source, deploy=args.deploy)
        print("Site artifact and evidence verified")
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"site publication: {exc}\n")


if __name__ == "__main__":
    main()
