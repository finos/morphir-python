"""Morphir.SDK.UUID: universally unique identifiers.

A `UUID` is the standard library `uuid.UUID`. The reference behaviour is the Elm
runtime, which uses TSFoster/elm-uuid.

The name `compare` and the module name are also names in Python. Import the
module with an alias:

    >>> from morphir.sdk import uuid as UUID
    >>> UUID.parse("6ba7b810-9dad-11d1-80b4-00c04fd430c8") == Ok(UUID.dns_namespace)
    True
    >>> UUID.to_string(UUID.for_name("python.org", UUID.dns_namespace))
    '886313e1-3b8a-5372-9b90-0c9aee199e5d'
    >>> UUID.parse("not a uuid")
    Err(error=<Error.WrongLength: 'WrongLength'>)

`parse` and `from_string` read the same text forms as the Elm runtime. They
remove all spaces, tabs, line feeds and hyphens, and ignore the case. They then
accept 32 hexadecimal digits, optionally after the prefix `urn:uuid:` or
between `{` and `}`. They do not use the parser of `uuid.UUID`, which accepts
other forms (for example `{` with no `}`, or `urn:uuid:` with braces).

A UUID from `parse` is never the nil UUID, has the RFC 4122 variant and has a
version from 0 to 8. A `uuid.UUID` from a different source can break these
rules. All functions in this module accept such a value.

Departure from the Elm runtime: `parse` gives `NoVersion` for a version above
8, as TSFoster/elm-uuid 4.3.1 does. Release 4.2.0 of that package, which
morphir-elm also permits, gives `NoVersion` for a version above 5.
"""

import uuid as _uuid
from enum import Enum

from morphir.sdk._compare import Order
from morphir.sdk.maybe import Just, Maybe, Nothing
from morphir.sdk.result import Err, Ok, Result

__all__ = [
    "UUID",
    "Error",
    "compare",
    "dns_namespace",
    "for_name",
    "from_string",
    "is_nil_string",
    "nil_string",
    "oid_namespace",
    "parse",
    "to_string",
    "url_namespace",
    "version",
    "x500_namespace",
]

UUID = _uuid.UUID
"""The standard library UUID type."""


class Error(Enum):
    """The reason why `parse` did not accept a text."""

    WrongFormat = "WrongFormat"
    """The text has a character that is not a hexadecimal digit."""

    WrongLength = "WrongLength"
    """The text does not have 32 hexadecimal digits."""

    UnsupportedVariant = "UnsupportedVariant"
    """The UUID does not have the RFC 4122 variant."""

    IsNil = "IsNil"
    """The UUID is the nil UUID, which has only zeros."""

    NoVersion = "NoVersion"
    """The version of the UUID is not in the range 0 to 8."""


_HEX_DIGITS = frozenset("0123456789abcdef")
_MAX_VERSION = 8
_URN_PREFIX = "urn:uuid:"

nil_string: str = "00000000-0000-0000-0000-000000000000"
"""The text of the nil UUID. `parse` does not accept it."""

dns_namespace: UUID = _uuid.NAMESPACE_DNS
"""The namespace for domain names, `6ba7b810-9dad-11d1-80b4-00c04fd430c8`."""

url_namespace: UUID = _uuid.NAMESPACE_URL
"""The namespace for URLs, `6ba7b811-9dad-11d1-80b4-00c04fd430c8`."""

oid_namespace: UUID = _uuid.NAMESPACE_OID
"""The namespace for ISO object IDs, `6ba7b812-9dad-11d1-80b4-00c04fd430c8`."""

x500_namespace: UUID = _uuid.NAMESPACE_X500
"""The namespace for X.500 names, `6ba7b814-9dad-11d1-80b4-00c04fd430c8`."""


def _utf16_length(text: str) -> int:
    # Elm measures a string in UTF-16 code units.
    return sum(2 if ord(char) > 0xFFFF else 1 for char in text)


def _normalize(s: str) -> str:
    text = s
    for removed in ("\n", "\t", " ", "-"):
        text = text.replace(removed, "")
    text = text.lower()
    if text.startswith(_URN_PREFIX):
        return text[len(_URN_PREFIX) :]
    if text.startswith("{") and text.endswith("}"):
        return text[1:-1]
    return text


def parse(s: str) -> Result[Error, UUID]:
    """Read a UUID from text.

    The module docstring gives the accepted text forms.

    Args:
        s: The text to read.

    Returns:
        `Ok` with the UUID, or `Err` with the reason. The checks are in this
        order: `WrongLength`, `WrongFormat`, `IsNil`, `NoVersion`,
        `UnsupportedVariant`.
    """
    normalized = _normalize(s)
    if _utf16_length(normalized) != 32:
        return Err(Error.WrongLength)
    if not _HEX_DIGITS.issuperset(normalized):
        return Err(Error.WrongFormat)
    value = _uuid.UUID(int=int(normalized, 16))
    if value.int == 0:
        return Err(Error.IsNil)
    if version(value) > _MAX_VERSION:
        return Err(Error.NoVersion)
    if (value.int >> 62) & 0b11 != 0b10:
        return Err(Error.UnsupportedVariant)
    return Ok(value)


def from_string(s: str) -> Maybe[UUID]:
    """Read a UUID from text, as `parse` does, with no reason for a failure.

    Args:
        s: The text to read.

    Returns:
        `Just` the UUID, or `Nothing` when `parse` gives an error.
    """
    match parse(s):
        case Ok(value):
            return Just(value)
        case Err():
            return Nothing()


def for_name(s: str, uuid: UUID) -> UUID:
    """Make a version 5 UUID from a name and a namespace.

    The same name and namespace always give the same UUID. The result can be the
    namespace of other UUIDs.

    Args:
        s: The name. It is encoded as UTF-8.
        uuid: The namespace.

    Returns:
        The version 5 (SHA-1) UUID of RFC 4122.
    """
    return _uuid.uuid5(uuid, s)


def to_string(uuid: UUID) -> str:
    """Convert a UUID to the canonical text: lower case, with four hyphens."""
    return str(uuid)


def version(uuid: UUID) -> int:
    """Return the version number of a UUID.

    The result is the value of the four version bits. Unlike `uuid.UUID.version`,
    it is a number for a UUID of any variant.
    """
    return (uuid.int >> 76) & 0xF


def compare(uuid1: UUID, uuid2: UUID) -> Order:
    """Compare two UUIDs as unsigned 128-bit numbers.

    Args:
        uuid1: The first UUID.
        uuid2: The second UUID.

    Returns:
        `Order.LT`, `Order.EQ` or `Order.GT`.
    """
    if uuid1.int < uuid2.int:
        return Order.LT
    if uuid1.int > uuid2.int:
        return Order.GT
    return Order.EQ


def is_nil_string(s: str) -> bool:
    """Check that a text is the nil UUID in one of the forms that `parse` reads."""
    return parse(s) == Err(Error.IsNil)
