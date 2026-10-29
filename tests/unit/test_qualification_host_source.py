"""Qualification receipts must identify the host source actually built."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_qualification_receipt_matches_one_host_dependency_revision() -> None:
    """Prevent mixed host types and falsely attributed qualification reports."""
    tool = ROOT / "tools" / "extension-qualification"
    dependencies = tomllib.loads((tool / "Cargo.toml").read_text())["dependencies"]
    names = ("morphir-extension-sdk", "morphir-host", "morphir-host-native")
    sources = {(dependencies[name]["git"], dependencies[name]["rev"]) for name in names}
    assert len(sources) == 1, "Qualification host dependencies must share one source"
    _, revision = sources.pop()
    assert re.fullmatch(r"[0-9a-f]{40}", revision)
    source = (tool / "src" / "main.rs").read_text()
    declared = re.search(r'const HOST_SOURCE: &str = "([0-9a-f]{40})";', source)
    assert declared is not None
    assert declared.group(1) == revision, "Receipt source must match built dependencies"
