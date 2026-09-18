"""Morphir.SDK.Key: helpers for composite keys.

Elm needs this module because only tuples of comparables are comparable, a tuple
has at most three elements, and the unit value is not comparable. `key2` to
`key16` build a composite key from a row with one getter function for each
element:

    >>> from dataclasses import dataclass
    >>> from morphir.sdk import key as Key
    >>> @dataclass(frozen=True)
    ... class Trade:
    ...     desk: str
    ...     product: str
    ...     quantity: int
    >>> Key.key2(lambda t: t.desk, lambda t: t.product, Trade("fx", "spot", 10))
    ('fx', 'spot')

A composite key is a tuple, so `basics.compare` gives it a structural order and
it works as a `Dict` key or a `Set` member when its elements are comparable.

Elm nests the tuples of `Key4` and larger (`( k1, k2, ( k3, k4 ) )`), because an
Elm tuple has at most three elements. Python has no such limit, so every key
here is one flat tuple. The order of two keys is the same in the two forms.

`Key0` is the key with zero elements. It is the integer 0, as in Elm, so that it
stays comparable. `no_key` and `key0` yield it.

The functions are not curried. To get a key function of one argument, for
example for `aggregate.by_key`, use a `lambda` or `functools.partial`:

    >>> from functools import partial
    >>> desk_and_product = partial(Key.key2, lambda t: t.desk, lambda t: t.product)
    >>> desk_and_product(Trade("fx", "swap", 5))
    ('fx', 'swap')
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "Key0",
    "Key2",
    "Key3",
    "Key4",
    "Key5",
    "Key6",
    "Key7",
    "Key8",
    "Key9",
    "Key10",
    "Key11",
    "Key12",
    "Key13",
    "Key14",
    "Key15",
    "Key16",
    "key0",
    "key2",
    "key3",
    "key4",
    "key5",
    "key6",
    "key7",
    "key8",
    "key9",
    "key10",
    "key11",
    "key12",
    "key13",
    "key14",
    "key15",
    "key16",
    "no_key",
]

type Key0 = int
"""A key with zero elements. The only value is 0."""

type Key2[K1, K2] = tuple[K1, K2]
"""A composite key with 2 elements."""

type Key3[K1, K2, K3] = tuple[K1, K2, K3]
"""A composite key with 3 elements."""

type Key4[K1, K2, K3, K4] = tuple[K1, K2, K3, K4]
"""A composite key with 4 elements."""

type Key5[K1, K2, K3, K4, K5] = tuple[K1, K2, K3, K4, K5]
"""A composite key with 5 elements."""

type Key6[K1, K2, K3, K4, K5, K6] = tuple[K1, K2, K3, K4, K5, K6]
"""A composite key with 6 elements."""

type Key7[K1, K2, K3, K4, K5, K6, K7] = tuple[K1, K2, K3, K4, K5, K6, K7]
"""A composite key with 7 elements."""

type Key8[K1, K2, K3, K4, K5, K6, K7, K8] = tuple[K1, K2, K3, K4, K5, K6, K7, K8]
"""A composite key with 8 elements."""

type Key9[K1, K2, K3, K4, K5, K6, K7, K8, K9] = tuple[
    K1, K2, K3, K4, K5, K6, K7, K8, K9
]
"""A composite key with 9 elements."""

type Key10[K1, K2, K3, K4, K5, K6, K7, K8, K9, K10] = tuple[
    K1, K2, K3, K4, K5, K6, K7, K8, K9, K10
]
"""A composite key with 10 elements."""

type Key11[K1, K2, K3, K4, K5, K6, K7, K8, K9, K10, K11] = tuple[
    K1, K2, K3, K4, K5, K6, K7, K8, K9, K10, K11
]
"""A composite key with 11 elements."""

type Key12[K1, K2, K3, K4, K5, K6, K7, K8, K9, K10, K11, K12] = tuple[
    K1, K2, K3, K4, K5, K6, K7, K8, K9, K10, K11, K12
]
"""A composite key with 12 elements."""

type Key13[K1, K2, K3, K4, K5, K6, K7, K8, K9, K10, K11, K12, K13] = tuple[
    K1, K2, K3, K4, K5, K6, K7, K8, K9, K10, K11, K12, K13
]
"""A composite key with 13 elements."""

type Key14[K1, K2, K3, K4, K5, K6, K7, K8, K9, K10, K11, K12, K13, K14] = tuple[
    K1, K2, K3, K4, K5, K6, K7, K8, K9, K10, K11, K12, K13, K14
]
"""A composite key with 14 elements."""

type Key15[K1, K2, K3, K4, K5, K6, K7, K8, K9, K10, K11, K12, K13, K14, K15] = tuple[
    K1, K2, K3, K4, K5, K6, K7, K8, K9, K10, K11, K12, K13, K14, K15
]
"""A composite key with 15 elements."""

type Key16[K1, K2, K3, K4, K5, K6, K7, K8, K9, K10, K11, K12, K13, K14, K15, K16] = (
    tuple[K1, K2, K3, K4, K5, K6, K7, K8, K9, K10, K11, K12, K13, K14, K15, K16]
)
"""A composite key with 16 elements."""


def no_key(a: object) -> Key0:
    """Create a key with zero elements. The row is ignored; the key is always 0."""
    return 0


def key0(a: object) -> Key0:
    """Create a key with zero elements. The row is ignored; the key is always 0."""
    return 0


def key2[A, B1, B2](
    get_key1: Callable[[A], B1],
    get_key2: Callable[[A], B2],
    a: A,
) -> Key2[B1, B2]:
    """Create a composite key with 2 elements from a row."""
    return (get_key1(a), get_key2(a))


def key3[A, B1, B2, B3](
    get_key1: Callable[[A], B1],
    get_key2: Callable[[A], B2],
    get_key3: Callable[[A], B3],
    a: A,
) -> Key3[B1, B2, B3]:
    """Create a composite key with 3 elements from a row."""
    return (get_key1(a), get_key2(a), get_key3(a))


def key4[A, B1, B2, B3, B4](
    get_key1: Callable[[A], B1],
    get_key2: Callable[[A], B2],
    get_key3: Callable[[A], B3],
    get_key4: Callable[[A], B4],
    a: A,
) -> Key4[B1, B2, B3, B4]:
    """Create a composite key with 4 elements from a row."""
    return (get_key1(a), get_key2(a), get_key3(a), get_key4(a))


def key5[A, B1, B2, B3, B4, B5](
    get_key1: Callable[[A], B1],
    get_key2: Callable[[A], B2],
    get_key3: Callable[[A], B3],
    get_key4: Callable[[A], B4],
    get_key5: Callable[[A], B5],
    a: A,
) -> Key5[B1, B2, B3, B4, B5]:
    """Create a composite key with 5 elements from a row."""
    return (get_key1(a), get_key2(a), get_key3(a), get_key4(a), get_key5(a))


def key6[A, B1, B2, B3, B4, B5, B6](
    get_key1: Callable[[A], B1],
    get_key2: Callable[[A], B2],
    get_key3: Callable[[A], B3],
    get_key4: Callable[[A], B4],
    get_key5: Callable[[A], B5],
    get_key6: Callable[[A], B6],
    a: A,
) -> Key6[B1, B2, B3, B4, B5, B6]:
    """Create a composite key with 6 elements from a row."""
    return (
        get_key1(a),
        get_key2(a),
        get_key3(a),
        get_key4(a),
        get_key5(a),
        get_key6(a),
    )


def key7[A, B1, B2, B3, B4, B5, B6, B7](
    get_key1: Callable[[A], B1],
    get_key2: Callable[[A], B2],
    get_key3: Callable[[A], B3],
    get_key4: Callable[[A], B4],
    get_key5: Callable[[A], B5],
    get_key6: Callable[[A], B6],
    get_key7: Callable[[A], B7],
    a: A,
) -> Key7[B1, B2, B3, B4, B5, B6, B7]:
    """Create a composite key with 7 elements from a row."""
    return (
        get_key1(a),
        get_key2(a),
        get_key3(a),
        get_key4(a),
        get_key5(a),
        get_key6(a),
        get_key7(a),
    )


def key8[A, B1, B2, B3, B4, B5, B6, B7, B8](
    get_key1: Callable[[A], B1],
    get_key2: Callable[[A], B2],
    get_key3: Callable[[A], B3],
    get_key4: Callable[[A], B4],
    get_key5: Callable[[A], B5],
    get_key6: Callable[[A], B6],
    get_key7: Callable[[A], B7],
    get_key8: Callable[[A], B8],
    a: A,
) -> Key8[B1, B2, B3, B4, B5, B6, B7, B8]:
    """Create a composite key with 8 elements from a row."""
    return (
        get_key1(a),
        get_key2(a),
        get_key3(a),
        get_key4(a),
        get_key5(a),
        get_key6(a),
        get_key7(a),
        get_key8(a),
    )


def key9[A, B1, B2, B3, B4, B5, B6, B7, B8, B9](
    get_key1: Callable[[A], B1],
    get_key2: Callable[[A], B2],
    get_key3: Callable[[A], B3],
    get_key4: Callable[[A], B4],
    get_key5: Callable[[A], B5],
    get_key6: Callable[[A], B6],
    get_key7: Callable[[A], B7],
    get_key8: Callable[[A], B8],
    get_key9: Callable[[A], B9],
    a: A,
) -> Key9[B1, B2, B3, B4, B5, B6, B7, B8, B9]:
    """Create a composite key with 9 elements from a row."""
    return (
        get_key1(a),
        get_key2(a),
        get_key3(a),
        get_key4(a),
        get_key5(a),
        get_key6(a),
        get_key7(a),
        get_key8(a),
        get_key9(a),
    )


def key10[A, B1, B2, B3, B4, B5, B6, B7, B8, B9, B10](
    get_key1: Callable[[A], B1],
    get_key2: Callable[[A], B2],
    get_key3: Callable[[A], B3],
    get_key4: Callable[[A], B4],
    get_key5: Callable[[A], B5],
    get_key6: Callable[[A], B6],
    get_key7: Callable[[A], B7],
    get_key8: Callable[[A], B8],
    get_key9: Callable[[A], B9],
    get_key10: Callable[[A], B10],
    a: A,
) -> Key10[B1, B2, B3, B4, B5, B6, B7, B8, B9, B10]:
    """Create a composite key with 10 elements from a row."""
    return (
        get_key1(a),
        get_key2(a),
        get_key3(a),
        get_key4(a),
        get_key5(a),
        get_key6(a),
        get_key7(a),
        get_key8(a),
        get_key9(a),
        get_key10(a),
    )


def key11[A, B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11](
    get_key1: Callable[[A], B1],
    get_key2: Callable[[A], B2],
    get_key3: Callable[[A], B3],
    get_key4: Callable[[A], B4],
    get_key5: Callable[[A], B5],
    get_key6: Callable[[A], B6],
    get_key7: Callable[[A], B7],
    get_key8: Callable[[A], B8],
    get_key9: Callable[[A], B9],
    get_key10: Callable[[A], B10],
    get_key11: Callable[[A], B11],
    a: A,
) -> Key11[B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11]:
    """Create a composite key with 11 elements from a row."""
    return (
        get_key1(a),
        get_key2(a),
        get_key3(a),
        get_key4(a),
        get_key5(a),
        get_key6(a),
        get_key7(a),
        get_key8(a),
        get_key9(a),
        get_key10(a),
        get_key11(a),
    )


def key12[A, B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12](
    get_key1: Callable[[A], B1],
    get_key2: Callable[[A], B2],
    get_key3: Callable[[A], B3],
    get_key4: Callable[[A], B4],
    get_key5: Callable[[A], B5],
    get_key6: Callable[[A], B6],
    get_key7: Callable[[A], B7],
    get_key8: Callable[[A], B8],
    get_key9: Callable[[A], B9],
    get_key10: Callable[[A], B10],
    get_key11: Callable[[A], B11],
    get_key12: Callable[[A], B12],
    a: A,
) -> Key12[B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12]:
    """Create a composite key with 12 elements from a row."""
    return (
        get_key1(a),
        get_key2(a),
        get_key3(a),
        get_key4(a),
        get_key5(a),
        get_key6(a),
        get_key7(a),
        get_key8(a),
        get_key9(a),
        get_key10(a),
        get_key11(a),
        get_key12(a),
    )


def key13[A, B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12, B13](
    get_key1: Callable[[A], B1],
    get_key2: Callable[[A], B2],
    get_key3: Callable[[A], B3],
    get_key4: Callable[[A], B4],
    get_key5: Callable[[A], B5],
    get_key6: Callable[[A], B6],
    get_key7: Callable[[A], B7],
    get_key8: Callable[[A], B8],
    get_key9: Callable[[A], B9],
    get_key10: Callable[[A], B10],
    get_key11: Callable[[A], B11],
    get_key12: Callable[[A], B12],
    get_key13: Callable[[A], B13],
    a: A,
) -> Key13[B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12, B13]:
    """Create a composite key with 13 elements from a row."""
    return (
        get_key1(a),
        get_key2(a),
        get_key3(a),
        get_key4(a),
        get_key5(a),
        get_key6(a),
        get_key7(a),
        get_key8(a),
        get_key9(a),
        get_key10(a),
        get_key11(a),
        get_key12(a),
        get_key13(a),
    )


def key14[A, B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12, B13, B14](
    get_key1: Callable[[A], B1],
    get_key2: Callable[[A], B2],
    get_key3: Callable[[A], B3],
    get_key4: Callable[[A], B4],
    get_key5: Callable[[A], B5],
    get_key6: Callable[[A], B6],
    get_key7: Callable[[A], B7],
    get_key8: Callable[[A], B8],
    get_key9: Callable[[A], B9],
    get_key10: Callable[[A], B10],
    get_key11: Callable[[A], B11],
    get_key12: Callable[[A], B12],
    get_key13: Callable[[A], B13],
    get_key14: Callable[[A], B14],
    a: A,
) -> Key14[B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12, B13, B14]:
    """Create a composite key with 14 elements from a row."""
    return (
        get_key1(a),
        get_key2(a),
        get_key3(a),
        get_key4(a),
        get_key5(a),
        get_key6(a),
        get_key7(a),
        get_key8(a),
        get_key9(a),
        get_key10(a),
        get_key11(a),
        get_key12(a),
        get_key13(a),
        get_key14(a),
    )


def key15[A, B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12, B13, B14, B15](
    get_key1: Callable[[A], B1],
    get_key2: Callable[[A], B2],
    get_key3: Callable[[A], B3],
    get_key4: Callable[[A], B4],
    get_key5: Callable[[A], B5],
    get_key6: Callable[[A], B6],
    get_key7: Callable[[A], B7],
    get_key8: Callable[[A], B8],
    get_key9: Callable[[A], B9],
    get_key10: Callable[[A], B10],
    get_key11: Callable[[A], B11],
    get_key12: Callable[[A], B12],
    get_key13: Callable[[A], B13],
    get_key14: Callable[[A], B14],
    get_key15: Callable[[A], B15],
    a: A,
) -> Key15[B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12, B13, B14, B15]:
    """Create a composite key with 15 elements from a row."""
    return (
        get_key1(a),
        get_key2(a),
        get_key3(a),
        get_key4(a),
        get_key5(a),
        get_key6(a),
        get_key7(a),
        get_key8(a),
        get_key9(a),
        get_key10(a),
        get_key11(a),
        get_key12(a),
        get_key13(a),
        get_key14(a),
        get_key15(a),
    )


def key16[A, B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12, B13, B14, B15, B16](
    get_key1: Callable[[A], B1],
    get_key2: Callable[[A], B2],
    get_key3: Callable[[A], B3],
    get_key4: Callable[[A], B4],
    get_key5: Callable[[A], B5],
    get_key6: Callable[[A], B6],
    get_key7: Callable[[A], B7],
    get_key8: Callable[[A], B8],
    get_key9: Callable[[A], B9],
    get_key10: Callable[[A], B10],
    get_key11: Callable[[A], B11],
    get_key12: Callable[[A], B12],
    get_key13: Callable[[A], B13],
    get_key14: Callable[[A], B14],
    get_key15: Callable[[A], B15],
    get_key16: Callable[[A], B16],
    a: A,
) -> Key16[B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12, B13, B14, B15, B16]:
    """Create a composite key with 16 elements from a row."""
    return (
        get_key1(a),
        get_key2(a),
        get_key3(a),
        get_key4(a),
        get_key5(a),
        get_key6(a),
        get_key7(a),
        get_key8(a),
        get_key9(a),
        get_key10(a),
        get_key11(a),
        get_key12(a),
        get_key13(a),
        get_key14(a),
        get_key15(a),
        get_key16(a),
    )
