"""Compile source strings and generate typed artifacts in memory."""

from morphir_tools.python import (
    CompiledV3,
    CompileFailure,
    Generated,
    SourceDocument,
    compile_sources,
    generate_python,
)

models = SourceDocument(
    "acme/models.py",
    """\
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Pending:
    pass

@dataclass(frozen=True)
class Approved:
    amount: float

type Decision = Pending | Approved
""",
)
rules = SourceDocument(
    "acme/rules.py",
    """\
from __future__ import annotations
from .models import Decision

def choose(flag: bool, first: Decision, second: Decision) -> Decision:
    if flag:
        return first
    else:
        return second
""",
)

compiled = compile_sources([models, rules], package="acme/example")
if isinstance(compiled, CompileFailure):
    for diagnostic in compiled.diagnostics:
        print(diagnostic.severity.value, diagnostic.render())
    raise SystemExit(1)
assert isinstance(compiled, CompiledV3)

generated = generate_python(compiled.distribution)
assert isinstance(generated, Generated)
for artifact in generated.artifacts:
    print(artifact.path)
