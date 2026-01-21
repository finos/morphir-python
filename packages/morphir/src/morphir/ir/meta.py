from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple

@dataclass(frozen=True)
class SourceRange:
    start: Tuple[int, int]
    end: Tuple[int, int]

@dataclass(frozen=True)
class FileMeta:
    # Provenance
    source: Optional[str] = None
    source_range: Optional[SourceRange] = None
    compiler: Optional[str] = None
    generated: Optional[str] = None # ISO 8601
    checksum: Optional[str] = None

    # Tooling
    edited_by: Optional[str] = None
    edited_at: Optional[str] = None # ISO 8601
    locked: Optional[bool] = None
    is_generated: Optional[bool] = None

    # Extensions
    extensions: Dict[str, Any] = field(default_factory=dict)
