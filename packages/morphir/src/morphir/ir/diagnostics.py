"""Structured diagnostics shared by the IR readers, codecs, and migrations.

Every diagnostic code lives in this module so that an upstream rename is a single
edit. Codes reuse upstream vocabulary where it exists:

- format-version codes come from the finos/morphir format-version contract
  (``docs/spec/ir/format-version.md``);
- ``specs_before_3_1`` comes from the finos/morphir v3 specification
  (``docs/spec/ir/schemas/v3/whats-new.md``, decision record 0018);
- decoding codes come from the Morphir Compatibility Kit (morphir-rust
  ``ir/diagnostic.rs``);
- downgrade codes come from the finos CLI and morphir-moonbit
  ``migration/v3/migration.mbt``, and may be renamed when finos bead
  ``morphir-diwy`` settles;
- ``package_version_dropped``, ``source_location_dropped``,
  ``input_attributes_dropped``, and ``no_v4_spelling`` are local to
  morphir-python.
"""

from __future__ import annotations

from dataclasses import dataclass

# Format version (finos/morphir format-version contract).
MISSING_FORMAT_VERSION = "missing_format_version"
DUPLICATE_FORMAT_VERSION = "duplicate_format_version"
INVALID_FORMAT_VERSION_TYPE = "invalid_format_version_type"
INVALID_FORMAT_VERSION_SYNTAX = "invalid_format_version_syntax"
FORMAT_VERSION_OUT_OF_RANGE = "format_version_out_of_range"
UNSUPPORTED_FORMAT_VERSION_MAJOR = "unsupported_format_version_major"
UNSUPPORTED_FORMAT_VERSION_MINOR = "unsupported_format_version_minor"

# A v3 Specs distribution declared below 3.1.0 (finos/morphir decision record 0018).
SPECS_BEFORE_3_1 = "specs_before_3_1"

# Decoding (Morphir Compatibility Kit).
UNKNOWN_NODE = "unknown_node"
UNKNOWN_MEMBER = "unknown_member"
MISSING_MEMBER = "missing_member"
DUPLICATE_MEMBER = "duplicate_member"
INVALID_NAME = "invalid_name"
INVALID_LITERAL = "invalid_literal"
INVALID_JSON = "invalid_json"

# Encoding a v4 construct that has no spelling in the pinned draft profile.
NO_V4_SPELLING = "no_v4_spelling"

# Reverse migration (finos CLI, morphir-moonbit).
UNSUPPORTED_V4_DOWNGRADE = "unsupported_v4_downgrade"
UNSUPPORTED_ATTRIBUTES_DOWNGRADE = "unsupported_attributes_downgrade"
MISSING_INFERRED_TYPE = "missing_inferred_type"
UNSUPPORTED_DOCUMENTATION_DOWNGRADE = "unsupported_documentation_downgrade"

# Warnings (morphir-python).
PACKAGE_VERSION_DROPPED = "package_version_dropped"
SOURCE_LOCATION_DROPPED = "source_location_dropped"
INPUT_ATTRIBUTES_DROPPED = "input_attributes_dropped"

Location = tuple[str | int, ...]


@dataclass(frozen=True)
class Diagnostic:
    """A machine-readable problem found while reading, writing, or migrating IR.

    Attributes:
        code: Stable diagnostic code, one of the constants in this module.
        construct: Name of the IR construct involved, such as ``"Hole"``.
        location: Path from the document root to the construct.
        message: Human-readable explanation. Callers must not parse it.
    """

    code: str
    construct: str
    location: Location
    message: str

    def render(self) -> str:
        """Render as ``code at location: message`` for terminal output."""
        where = "/".join(str(part) for part in self.location) or "<root>"
        return f"{self.code} at {where}: {self.message}"


class DiagnosticError(Exception):
    """Raised by readers and codecs when input cannot be processed.

    Attributes:
        diagnostics: One or more diagnostics describing the failure.
    """

    def __init__(self, *diagnostics: Diagnostic) -> None:
        self.diagnostics: tuple[Diagnostic, ...] = diagnostics
        super().__init__("; ".join(d.render() for d in diagnostics))

    @property
    def codes(self) -> tuple[str, ...]:
        """The diagnostic codes, in order."""
        return tuple(d.code for d in self.diagnostics)


def fail(
    code: str, construct: str, location: Location, message: str
) -> DiagnosticError:
    """Build a `DiagnosticError` holding a single diagnostic."""
    return DiagnosticError(Diagnostic(code, construct, location, message))
