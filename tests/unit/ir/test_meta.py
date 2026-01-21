import pytest
from morphir.ir.meta import FileMeta, SourceRange

def test_source_range():
    sr = SourceRange(start=(1, 1), end=(10, 5))
    assert sr.start == (1, 1)
    assert sr.end == (10, 5)

def test_file_meta_creation():
    sr = SourceRange(start=(1, 1), end=(10, 1))
    meta = FileMeta(
        source="src/main.elm",
        source_range=sr,
        compiler="morphir-elm 3.9.0",
        generated="2023-01-01T00:00:00Z",
        checksum="sha256:123456",
        edited_by="User",
        edited_at="2023-01-02T00:00:00Z",
        locked=True,
        is_generated=False,
        extensions={"my-tool": {"data": 123}}
    )
    
    assert meta.source == "src/main.elm"
    assert meta.source_range == sr
    assert meta.compiler == "morphir-elm 3.9.0"
    assert meta.extensions["my-tool"]["data"] == 123

def test_file_meta_defaults():
    meta = FileMeta()
    assert meta.source is None
    assert meta.extensions == {}
