"""Select CI categories for a change set and gate on their results.

``select`` maps changed paths to the categories CI must run and prints
``key=value`` lines for ``$GITHUB_OUTPUT``. Unknown paths, workflow changes,
pushes and release qualification select every category, so selection can only
skip work it knows is unaffected.

``aggregate`` is the required check. Every selected job must have succeeded and
every unselected job must have been skipped. A failed, cancelled, missing or
unexpectedly skipped job fails the aggregate.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

CATEGORIES = ("python", "native", "rust", "bundle")
"""``python``: lint, type check and Python tests; ``native``: the native wheel and
its clean-install qualification; ``rust``: Rust format, lint, tests and the
independent consumer; ``bundle``: the WASM extension bundle and its host check."""

JOBS: Mapping[str, tuple[str, ...]] = {
    "lint": ("python",),
    "typecheck": ("python",),
    "native-wheel": ("python", "native", "bundle"),
    "test": ("python", "native"),
    "rust": ("rust",),
    "bundle": ("bundle",),
    "build": ("python", "native"),
}
"""Each job runs when any of its categories is selected."""

# First match wins. Each rule names the categories a matching path selects.
RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (".github/*", CATEGORIES),
    (".config/mise/*", CATEGORIES),
    ("rust/extension.toml", ("bundle",)),
    ("scripts/extension_bundle.py", ("bundle",)),
    ("rust/crates/morphir-python-binding/*", CATEGORIES),
    ("rust/crates/morphir-python-native/*", ("python", "native", "rust")),
    ("rust/*", CATEGORIES),
    ("packages/morphir-python-native/*", ("python", "native")),
    ("scripts/qualify_native.py", ("python", "native")),
    ("tests/fixtures/python/*", ("python", "native", "bundle")),
    ("packages/*", ("python", "native")),
    ("tests/*", ("python", "native")),
    ("features/*", ("python", "native")),
    ("scripts/*", ("python", "native")),
    ("pyproject.toml", ("python", "native")),
    ("uv.lock", ("python", "native")),
    ("behave.ini", ("python",)),
    (".pre-commit-config.yaml", ("python",)),
    ("docs/python-compiler.md", ("python",)),
    ("*.md", ()),
    ("docs/*", ()),
    ("openspec/*", ()),
    ("LICENSE", ()),
    ("LICENSE.spdx", ()),
    ("NOTICE", ()),
    ("renovate.json", ()),
    ("skills-lock.json", ()),
    (".beads/*", ()),
    (".gitignore", ()),
    (".gitattributes", ()),
)


@dataclass(frozen=True)
class Selection:
    """The categories a change set needs, and why."""

    categories: frozenset[str]
    reason: str

    def jobs(self) -> dict[str, bool]:
        """Return whether each job runs."""
        return {
            job: any(category in self.categories for category in categories)
            for job, categories in JOBS.items()
        }


def select(paths: Iterable[str], *, full: bool = False) -> Selection:
    """Select categories for changed paths; unknown paths select everything."""
    if full:
        return Selection(frozenset(CATEGORIES), "full run")
    selected: set[str] = set()
    for path in paths:
        for pattern, categories in RULES:
            if fnmatch.fnmatchcase(path, pattern):
                selected.update(categories)
                break
        else:
            return Selection(frozenset(CATEGORIES), f"unclassified path {path}")
    return Selection(frozenset(selected), "changed paths")


def aggregate(
    selected: Mapping[str, bool], results: Mapping[str, Mapping[str, str]]
) -> list[str]:
    """Return problems with the job results; empty when the gate passes.

    Args:
        selected: Whether each job was selected, from ``select``.
        results: The ``needs`` context: job name to ``{"result": ...}``.
    """
    problems: list[str] = []
    for job, required in sorted(selected.items()):
        result = results.get(job, {}).get("result")
        if result is None:
            problems.append(f"{job}: no result")
        elif required and result != "success":
            problems.append(f"{job}: selected but {result}")
        elif not required and result != "skipped":
            problems.append(f"{job}: not selected but {result}")
    for job in sorted(set(results) - set(selected) - {"changes"}):
        if results[job].get("result") != "success":
            problems.append(f"{job}: {results[job].get('result')}")
    changes = results.get("changes", {}).get("result")
    if changes != "success":
        problems.append(f"changes: {changes}")
    return problems


def changed_paths(base: str, head: str) -> list[str]:
    """Return paths changed between the merge base of ``base`` and ``head``."""
    output = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in output.splitlines() if line]


def main(argv: list[str] | None = None) -> None:
    """Run ``select`` or ``aggregate``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    chooser = commands.add_parser("select")
    chooser.add_argument("--base")
    chooser.add_argument("--head", default="HEAD")
    chooser.add_argument("--full", action="store_true")
    chooser.add_argument("paths", nargs="*")
    gate = commands.add_parser("aggregate")
    gate.add_argument("--selected", required=True, help="JSON from select")
    gate.add_argument("--needs", required=True, help="JSON of the needs context")
    args = parser.parse_args(argv)
    if args.command == "select":
        paths = list(args.paths)
        if args.base:
            paths += changed_paths(args.base, args.head)
        selection = select(paths, full=args.full or not (args.base or args.paths))
        print(f"jobs={json.dumps(selection.jobs(), sort_keys=True)}")
        for category in CATEGORIES:
            print(f"{category}={str(category in selection.categories).lower()}")
        print(f"reason={selection.reason}")
        return
    problems = aggregate(json.loads(args.selected), json.loads(args.needs))
    for problem in problems:
        print(f"::error::{problem}")
    if problems:
        raise SystemExit(1)
    print("all selected checks passed")


if __name__ == "__main__":
    main()
