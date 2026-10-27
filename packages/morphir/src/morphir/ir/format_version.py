"""Reading, checking, and writing the ``formatVersion`` member of Morphir IR JSON.

The reader is deliberately more permissive than its sources:

- morphir-elm decodes ``formatVersion`` with ``Decode.int``, so it rejects the
  release string ``"3.0.0"``;
- the finos/morphir format-version contract accepts integer ``N`` and
  ``"N.minor.patch"`` but rejects the bare string ``"N"``.

This reader accepts all three spellings (``3``, ``"3"``, ``"3.0.0"``) so migration
tooling can read files written by older and newer tools. Writers stay canonical:
integer ``N`` for ``N.0.0`` and the exact release string otherwise, so this package
never produces a file that either source would reject.

The support table is ``[3.0.0,3.2.0),[4.0.0,4.1.0)``, the finos reference table
(finos/morphir decision record 0018). IR 3.1.0 added the v3 ``Specs``
distribution; `V3_1` names that release. v4 support is draft.

Formats 1 and 2 are legacy: the finos release grammar starts at major 3, so they
are in no support table, and `read_format_version` refuses them with
``unsupported_format_version_major``. `read_document_with_legacy` and
`read_legacy_document` recognize them, only as the integers morphir-elm wrote, for
the read-only decoders in `morphir.ir.v3.codec_v1` and `morphir.ir.v3.codec_v2`.
`write_format_version` never writes them.

Example:
    >>> read_format_version(3)
    FormatVersion(major=3, minor=0, patch=0)
    >>> read_format_version("3.0.0") == read_format_version("3")
    True
    >>> write_format_version(FormatVersion(3, 0, 0))
    3
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum

from . import diagnostics as d
from .diagnostics import DiagnosticError, fail

_U32_MAX = 4294967295
_COMPONENT = r"(0|[1-9][0-9]*)"
_RELEASE_RE = re.compile(rf"^{_COMPONENT}\.{_COMPONENT}\.{_COMPONENT}$")
_MAJOR_RE = re.compile(rf"^{_COMPONENT}$")
_CONSTRUCT = "formatVersion"


@dataclass(frozen=True, order=True)
class FormatVersion:
    """An exact, normalized format release such as 3.0.0."""

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class Interval:
    """A half-open release interval ``[lower, upper)``."""

    lower: FormatVersion
    upper: FormatVersion

    def __contains__(self, version: object) -> bool:
        return isinstance(version, FormatVersion) and (
            self.lower <= version < self.upper
        )

    def __str__(self) -> str:
        return f"[{self.lower},{self.upper})"


SupportTable = tuple[Interval, ...]

V3_INTERVAL = Interval(FormatVersion(3, 0, 0), FormatVersion(3, 2, 0))
V4_INTERVAL = Interval(FormatVersion(4, 0, 0), FormatVersion(4, 1, 0))
SUPPORT_TABLE: SupportTable = (V3_INTERVAL, V4_INTERVAL)
V3_TABLE: SupportTable = (V3_INTERVAL,)
V4_TABLE: SupportTable = (V4_INTERVAL,)

V3 = FormatVersion(3, 0, 0)
V3_1 = FormatVersion(3, 1, 0)
"""The release that introduced the v3 ``Specs`` distribution."""
V4 = FormatVersion(4, 0, 0)


def table_to_string(table: SupportTable) -> str:
    """Render a support table in canonical interval notation."""
    return ",".join(str(interval) for interval in table)


def _component(text: str, value: object) -> int:
    number = int(text)
    if number > _U32_MAX:
        raise fail(
            d.FORMAT_VERSION_OUT_OF_RANGE,
            _CONSTRUCT,
            (_CONSTRUCT,),
            f"formatVersion {value!r} has a component above {_U32_MAX}",
        )
    return number


def recognize_format_version(value: object) -> FormatVersion:
    """Recognize and normalize a ``formatVersion`` value without a support check.

    Historical integers 1 and 2 normalize to ``1.0.0`` and ``2.0.0`` so that the
    support check can report them as unsupported majors.

    Args:
        value: The decoded JSON value of the ``formatVersion`` member.

    Returns:
        The normalized release.

    Raises:
        DiagnosticError: With ``invalid_format_version_type``,
            ``invalid_format_version_syntax``, or ``format_version_out_of_range``.
    """
    loc: d.Location = (_CONSTRUCT,)
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise fail(
            d.INVALID_FORMAT_VERSION_TYPE,
            _CONSTRUCT,
            loc,
            f"formatVersion must be an integer or a release string, "
            f"not {type(value).__name__} {value!r}",
        )
    if isinstance(value, int):
        if value < 0:
            raise fail(
                d.INVALID_FORMAT_VERSION_TYPE,
                _CONSTRUCT,
                loc,
                f"formatVersion must be an unsigned integer, not {value}",
            )
        if value > _U32_MAX:
            raise fail(
                d.FORMAT_VERSION_OUT_OF_RANGE,
                _CONSTRUCT,
                loc,
                f"formatVersion {value} is above {_U32_MAX}",
            )
        if value == 0:
            raise fail(
                d.INVALID_FORMAT_VERSION_SYNTAX,
                _CONSTRUCT,
                loc,
                "formatVersion 0 is not a format family",
            )
        return FormatVersion(value, 0, 0)
    release = _RELEASE_RE.match(value)
    if release is not None:
        major, minor, patch = (_component(part, value) for part in release.groups())
        version = FormatVersion(major, minor, patch)
    else:
        bare = _MAJOR_RE.match(value)
        if bare is None:
            raise fail(
                d.INVALID_FORMAT_VERSION_SYNTAX,
                _CONSTRUCT,
                loc,
                f"formatVersion {value!r} is not N or N.minor.patch",
            )
        version = FormatVersion(_component(bare.group(1), value), 0, 0)
    if version.major < 3:
        raise fail(
            d.INVALID_FORMAT_VERSION_SYNTAX,
            _CONSTRUCT,
            loc,
            f"formatVersion {value!r} names a major below 3; "
            "formats 1 and 2 are written only as integers",
        )
    return version


def check_supported(
    version: FormatVersion, table: SupportTable = SUPPORT_TABLE
) -> FormatVersion:
    """Check a normalized release against a support table.

    Args:
        version: A release returned by `recognize_format_version`.
        table: The intervals the caller can process.

    Returns:
        The same release, when it is supported.

    Raises:
        DiagnosticError: With ``unsupported_format_version_major`` or
            ``unsupported_format_version_minor``.
    """
    if any(version in interval for interval in table):
        return version
    accepted = table_to_string(table)
    loc: d.Location = (_CONSTRUCT,)
    if not any(interval.lower.major == version.major for interval in table):
        if version.major in (1, 2):
            detail = _LEGACY_DETAIL
        else:
            detail = f"format family {version.major} is not supported"
        raise fail(
            d.UNSUPPORTED_FORMAT_VERSION_MAJOR,
            _CONSTRUCT,
            loc,
            f"format version {version} is not supported ({detail}); "
            f"this reader accepts only {_describe(table)} ({accepted})",
        )
    raise fail(
        d.UNSUPPORTED_FORMAT_VERSION_MINOR,
        _CONSTRUCT,
        loc,
        f"format version {version} is not supported; "
        f"this reader accepts only {_describe(table)} ({accepted})",
    )


def _families(interval: Interval) -> list[str]:
    lower, upper = interval.lower, interval.upper
    if upper.major == lower.major and upper.patch == 0:
        minors = range(lower.minor, max(upper.minor, lower.minor + 1))
    else:
        minors = range(lower.minor, lower.minor + 1)
    draft = "draft " if lower.major == 4 else ""
    return [f"{draft}{lower.major}.{minor}.x" for minor in minors]


def _describe(table: SupportTable) -> str:
    names = [name for interval in table for name in _families(interval)]
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])} and {names[-1]}"


def read_format_version(
    value: object, table: SupportTable = SUPPORT_TABLE
) -> FormatVersion:
    """Recognize, normalize, and support-check a ``formatVersion`` value.

    Args:
        value: The decoded JSON value of the ``formatVersion`` member.
        table: The intervals the caller can process.

    Returns:
        The normalized, supported release.

    Raises:
        DiagnosticError: With one of the finos format-version codes.
    """
    return check_supported(recognize_format_version(value), table)


def write_format_version(version: FormatVersion) -> int | str:
    """Return the canonical spelling: integer N for N.0.0, else the release string.

    Raises:
        ValueError: For a legacy major (1 or 2); legacy formats are never written.
    """
    if version.major < 3:
        raise ValueError(f"format {version.major} is legacy and is never written")
    if version.minor == 0 and version.patch == 0:
        return version.major
    return str(version)


class _Object(dict[str, object]):
    duplicates: frozenset[str] = frozenset()


def _object_pairs(pairs: list[tuple[str, object]], seen: list[str]) -> _Object:
    obj = _Object()
    dups: set[str] = set()
    for key, value in pairs:
        if key in obj:
            dups.add(key)
        obj[key] = value
    if dups:
        obj.duplicates = frozenset(dups)
        seen.extend(sorted(dups))
    return obj


def parse_json(text: str) -> object:
    """Parse JSON text, rejecting duplicate object members.

    ``json.loads`` silently keeps the last duplicate member, which the v4 JSON
    profile and the format-version contract both forbid.

    Raises:
        DiagnosticError: With ``invalid_json``, ``duplicate_format_version`` (root
            only), or ``duplicate_member``.
    """
    seen: list[str] = []
    try:
        root: object = json.loads(
            text, object_pairs_hook=lambda pairs: _object_pairs(pairs, seen)
        )
    except json.JSONDecodeError as error:
        raise fail(
            d.INVALID_JSON, "document", (), f"input is not valid JSON: {error}"
        ) from None
    if isinstance(root, _Object) and _CONSTRUCT in root.duplicates:
        raise fail(
            d.DUPLICATE_FORMAT_VERSION,
            _CONSTRUCT,
            (),
            "the document root contains formatVersion more than once",
        )
    if seen:
        raise fail(
            d.DUPLICATE_MEMBER,
            "object",
            (),
            f"an object contains member {seen[0]!r} more than once",
        )
    return root


def read_document(
    document: str | object, table: SupportTable = SUPPORT_TABLE
) -> tuple[FormatVersion, dict[str, object]]:
    """Read the root of a versioned IR document and check its format version.

    Recognition and the support check finish before any distribution decoder runs.

    Args:
        document: JSON text, or an already-decoded JSON value. Only text input can
            be checked for duplicate members.
        table: The intervals the caller can process.

    Returns:
        The supported release and the root object.

    Raises:
        DiagnosticError: With a format-version or JSON diagnostic.
    """
    obj = _versioned_root(document)
    return read_format_version(obj[_CONSTRUCT], table), obj


def _versioned_root(document: str | object) -> dict[str, object]:
    root = parse_json(document) if isinstance(document, str) else document
    if not isinstance(root, dict):
        raise fail(
            d.INVALID_JSON,
            "document",
            (),
            "the document root must be a JSON object",
        )
    if _CONSTRUCT not in root:
        raise fail(
            d.MISSING_FORMAT_VERSION,
            _CONSTRUCT,
            (),
            "the IR has no formatVersion member; it is in an old format. "
            "Please regenerate it!",
        )
    return dict(root)


def dump_json(value: object) -> str:
    """Serialize JSON compactly with members in insertion order."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


# --- Legacy formats 1 and 2 (read-only) ---

_LEGACY_DETAIL = (
    "formats 1 and 2 are legacy formats outside the support table; "
    "morphir.ir.v3.codec_v1 and codec_v2 read them as format 3.0.0"
)


class LegacyFormat(Enum):
    """A morphir-elm format from before the release grammar, which starts at 3.

    morphir-elm wrote formats 1 and 2 only as the JSON integers ``1`` and ``2``.
    They are in no support table: the legacy readers decode them into the
    format 3.0.0 model, and no writer emits them.
    """

    V1 = 1
    V2 = 2

    def __str__(self) -> str:
        return str(self.value)


def recognize_legacy_format(value: object) -> LegacyFormat | None:
    """Return the legacy format for the JSON integer ``1`` or ``2``, else ``None``.

    Example:
        >>> recognize_legacy_format(1)
        <LegacyFormat.V1: 1>
        >>> recognize_legacy_format("1") is None
        True
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return {1: LegacyFormat.V1, 2: LegacyFormat.V2}.get(value)


def read_document_with_legacy(
    document: str | object, table: SupportTable = SUPPORT_TABLE
) -> tuple[FormatVersion | LegacyFormat, dict[str, object]]:
    """Read a document root like `read_document`, but report legacy formats.

    The integers ``1`` and ``2`` give a `LegacyFormat`; every other value goes
    through `read_format_version` with ``table`` and fails as it does there.

    Raises:
        DiagnosticError: With a format-version or JSON diagnostic.
    """
    obj = _versioned_root(document)
    legacy = recognize_legacy_format(obj[_CONSTRUCT])
    if legacy is not None:
        return legacy, obj
    return read_format_version(obj[_CONSTRUCT], table), obj


def read_legacy_document(
    document: str | object, accepted: LegacyFormat
) -> dict[str, object]:
    """Read the root of a legacy document and check that it is ``accepted``.

    Args:
        document: JSON text, or an already-decoded JSON value.
        accepted: The one legacy format the caller decodes.

    Returns:
        The root object.

    Raises:
        DiagnosticError: With ``unsupported_format_version_major`` for any other
            format, or with the recognition diagnostic for a malformed version.
    """
    obj = _versioned_root(document)
    value = obj[_CONSTRUCT]
    found: FormatVersion | LegacyFormat | None = recognize_legacy_format(value)
    if found is accepted:
        return obj
    if found is None:
        found = recognize_format_version(value)
    raise fail(
        d.UNSUPPORTED_FORMAT_VERSION_MAJOR,
        _CONSTRUCT,
        (_CONSTRUCT,),
        f"format version {found} is not supported; "
        f"this reader accepts only legacy format {accepted}",
    )


__all__ = [
    "SUPPORT_TABLE",
    "V3",
    "V3_1",
    "V3_TABLE",
    "V4",
    "V4_TABLE",
    "DiagnosticError",
    "FormatVersion",
    "Interval",
    "LegacyFormat",
    "SupportTable",
    "check_supported",
    "dump_json",
    "parse_json",
    "read_document",
    "read_document_with_legacy",
    "read_format_version",
    "read_legacy_document",
    "recognize_format_version",
    "recognize_legacy_format",
    "table_to_string",
    "write_format_version",
]
