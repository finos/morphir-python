"""Keep timing fixtures within the supported Python/IR roundtrip subset."""

from __future__ import annotations

import pytest

from morphir_tools import python as api
from scripts.benchmark_extension import sources


@pytest.mark.parametrize("version", tuple(api.IrVersion))
@pytest.mark.parametrize("records,functions", [(1, 1), (200, 100)])
@pytest.mark.parametrize("with_values", [False, True])
def test_benchmark_fixtures_roundtrip_in_both_ir_versions(
    version: api.IrVersion, records: int, functions: int, with_values: bool
) -> None:
    """Numeric suffixes previously caused PY003 in classic v3 word arrays."""
    types, values = sources(records, functions)
    compiled = api.compile_sources(
        [api.SourceDocument("models.py", values if with_values else types)],
        package="acme",
        ir_version=version,
    )
    assert isinstance(compiled, (api.CompiledV3, api.CompiledV4)), compiled
    generated = api.generate_python(compiled.distribution)
    assert isinstance(generated, api.Generated), generated
    again = api.compile_sources(
        [api.SourceDocument(item.path, item.text) for item in generated.artifacts],
        package="acme",
        ir_version=version,
    )
    assert isinstance(again, (api.CompiledV3, api.CompiledV4)), again
    assert again.distribution == compiled.distribution
