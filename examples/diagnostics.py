"""Handle an unsupported model without exceptions or partial output."""

from morphir_tools.python import CompileFailure, SourceDocument, compile_sources

result = compile_sources(
    [SourceDocument("rules.py", "answer = 42\n")], package="acme/example"
)
assert isinstance(result, CompileFailure)
diagnostic = result.diagnostics[0]
assert diagnostic.code == "PY004"
assert diagnostic.source is not None
assert diagnostic.source.path == "rules.py"
print(diagnostic.code, diagnostic.severity.value, diagnostic.source.path)
