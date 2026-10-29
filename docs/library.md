# Work with IR and the SDK

**Released:** CPython 3.14 and `morphir==0.1.1`. These examples need neither the
CLI nor the native compiler. Install only `morphir` as described in
[installation](installation.md#use-only-the-library).

## Read, write and migrate IR

Use `morphir.ir.format_version` to identify a document before choosing a codec.
Use the explicit `v3` or `v4` namespace: `morphir.ir` re-exports draft-v4 types,
which differ from v3 types.

<!-- example: examples/library.py -->
```python
"""Read, write and migrate an IR document with the dependency-free library."""

import json

from morphir.ir import v3
from morphir.ir.format_version import read_document
from morphir.ir.migrate import Ok, v3_to_v4, v4_to_v3
from morphir.ir.v3 import codec

text = '{"formatVersion":3,"distribution":["Library",[["acme"]],[],{"modules":[]}]}'
version, _ = read_document(text)
library = codec.decode_versioned_distribution(text)
assert isinstance(library, v3.Library)
written = codec.encode_versioned_distribution(library)
assert codec.decode_versioned_distribution(json.dumps(written)) == library

upgraded = v3_to_v4(library, package_version="1.0.0")
downgraded = v4_to_v3(upgraded.value)
assert isinstance(downgraded, Ok) and downgraded.value == library
assert any(w.code == "package_version_dropped" for w in downgraded.warnings)
print("IR read/write and explicit migration succeeded")
```
<!-- /example -->

The fixture is an empty Library so every step is visible. The v3 writer emits
the lowest format version that fits. A package release version belongs to v4;
downgrading reports `package_version_dropped`. Migration returns immutable
`Ok` or `Err` values. Check diagnostics rather than assume every v4 construct
has a v3 representation.

The library reads legacy formats 1 and 2 through dedicated read-only codecs.
Format 3.1 adds Specs distributions. The compiler and Python generator accept
supported Library models, not Specs or Applications. Check the
[package reference](https://github.com/finos/morphir-python/blob/main/packages/morphir/README.md#morphir-ir-versions)
for the full version and loss policy.

## Use SDK values

The SDK contains pure functions and immutable values. Functions take arguments
in Morphir/Elm order; `Maybe` is a union of `Just` and `Nothing`.

<!-- example: examples/sdk.py -->
```python
"""Use immutable SDK values with pure Python functions."""

from morphir.sdk import maybe

present: maybe.Maybe[int] = maybe.Just(21)
missing: maybe.Maybe[int] = maybe.Nothing()
assert maybe.map(lambda n: n * 2, present) == maybe.Just(42)
assert maybe.with_default(0, missing) == 0
assert present == maybe.Just(21)
print("SDK Maybe: 42; missing value: 0")
```
<!-- /example -->

This prints `SDK Maybe: 42; missing value: 0`. Other modules include Basics,
Char, String, List, Dict, Set, Result, Tuple, Decimal, Int and Number. The SDK
is usable from ordinary Python, even where the compiler's source subset does
not yet accept a particular construct.

## Draft-v4 codec features

**Released in core 0.1.0:** the v4 writer emits compact canonical spellings
and exposes `morphir.ir.v4.codec.Spelling.EXPANDED` for explicit expanded output.
Core 0.0.2 predates this writer change. Both profiles describe draft v4; choosing
one does not establish compatibility with another tool's envelope or provenance
requirements. See [CLI compatibility](compatibility.md).
