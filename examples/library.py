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
