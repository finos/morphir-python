"""Morphir IR format 3, the format morphir-elm writes today, and its 3.1.0 revision.

morphir-elm (commit bc99af69) is normative for the 3.0.0 model and its JSON
shapes. What 3.1.0 adds, the `Specs` distribution, follows the finos/morphir v3
specification (decision record 0018). The classes here are distinct from
`morphir.ir.v4`; use `morphir.ir.migrate` to move between versions.

`morphir.ir.v3.codec_v1` and `morphir.ir.v3.codec_v2` read the legacy formats 1
and 2 into the 3.0.0 `Library` model, which upgrades them to format 3.0.0.
Nothing writes them.
"""

from . import (
    access_controlled,
    codec,
    codec_v1,
    codec_v2,
    distribution,
    documented,
    fqname,
    literal,
    module,
    name,
    package,
    path,
    qname,
    type,
    value,
)
from .access_controlled import Access, AccessControlled
from .distribution import Distribution, Library, Specs
from .documented import Documented
from .fqname import FQName
from .name import Name
from .path import Path
from .qname import QName

__all__ = [
    "Access",
    "AccessControlled",
    "Distribution",
    "Documented",
    "FQName",
    "Library",
    "Name",
    "Path",
    "QName",
    "Specs",
    "access_controlled",
    "codec",
    "codec_v1",
    "codec_v2",
    "distribution",
    "documented",
    "fqname",
    "literal",
    "module",
    "name",
    "package",
    "path",
    "qname",
    "type",
    "value",
]
