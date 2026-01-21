from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceRange:
    start: tuple[int, int]
    end: tuple[int, int]


@dataclass(frozen=True)
class FileMeta:
    # Provenance
    source: str | None = None
    source_range: SourceRange | None = None
    compiler: str | None = None
    generated: str | None = None  # ISO 8601
    checksum: str | None = None

    # Tooling
    edited_by: str | None = None
    edited_at: str | None = None  # ISO 8601
    locked: bool | None = None
    is_generated: bool | None = None

    # Extensions
    extensions: dict[str, Any] = field(default_factory=dict)
