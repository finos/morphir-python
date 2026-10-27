"""Diagnostic codes reported by the Python compiler API.

Every code the API can report lives in this module, as `morphir.ir.diagnostics`
does for the IR readers and codecs.

- ``PY001`` to ``PY006`` come from the native ``morphir-python-binding`` compiler.
  They are the same codes its MEP extension reports, so Rust, WASM and Python
  callers see one vocabulary.
- ``unsupported_distribution`` is local to this API: generation accepts only a
  Library distribution.
- Decoding and encoding failures keep the `morphir.ir.diagnostics` code that the
  codec reported, such as ``unknown_node`` or ``no_v4_spelling``.
"""

from __future__ import annotations

# Native compiler (morphir-python-binding).
PY_REQUEST = "PY001"
"""Unsupported request or option."""
PY_SYNTAX = "PY002"
"""Python syntax error, with a source range."""
PY_NAME = "PY003"
"""Invalid name or naming collision."""
PY_UNSUPPORTED = "PY004"
"""Unsupported declaration, annotation or IR feature."""
PY_SERIALIZATION = "PY005"
"""IR decoding or serialization, or generated syntax failure."""
PY_PARSE_STAGE = "PY006"
"""Parse-stage output was requested but is unavailable."""

# Python API (morphir-python).
UNSUPPORTED_DISTRIBUTION = "unsupported_distribution"
"""Generation received a Specs or Application distribution."""
