"""Exercise real installed runtime selection and byte-integrity refusals."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.mark.skipif(
    not (
        os.environ.get("MORPHIR_TEST_WASM_BUNDLE")
        and os.environ.get("MORPHIR_TEST_PROCESS_BUNDLE")
    ),
    reason="requires exact built WASM and process bundles plus the pinned host CLI",
)
def test_installed_runtime_choices_are_equivalent_and_tamper_is_refused() -> None:
    from scripts.qualify_runtime import qualify

    report = qualify(
        Path(os.environ["MORPHIR_TEST_WASM_BUNDLE"]),
        Path(os.environ["MORPHIR_TEST_PROCESS_BUNDLE"]),
    )
    assert [step["runtime"] for step in report["switches"]] == [
        "wasm",
        "process",
        "wasm",
    ]
    assert report["switches"][0]["results"] == report["switches"][1]["results"]
    assert (
        report["switches"][2]["results"]["v4"]["ir_sha256"]
        == report["switches"][0]["results"]["v4"]["ir_sha256"]
    )
    assert report["tampered_install_refused"] is True
    assert report["unsupported_platform_refused"] is True
