"""Use immutable SDK values with pure Python functions."""

from morphir.sdk import maybe

present: maybe.Maybe[int] = maybe.Just(21)
missing: maybe.Maybe[int] = maybe.Nothing()
assert maybe.map(lambda n: n * 2, present) == maybe.Just(42)
assert maybe.with_default(0, missing) == 0
assert present == maybe.Just(21)
print("SDK Maybe: 42; missing value: 0")
