# A Python model round trip

**Released:** CPython 3.14, `morphir-python==0.1.0`, `morphir==0.1.0`, native
compiler `0.1.1`. Follow [installation](installation.md) first. This recipe uses
a POSIX shell such as Bash. The CLI commands themselves also work on Windows;
create the same source files in your editor there.

## Compile, inspect, generate and recompile

Start in a new directory. This complete example defines an immutable decision
type and a pure function in another module. It uses local imports and annotated
function arguments.

<!-- example: examples/cli.sh -->
```bash
#!/usr/bin/env bash
set -euo pipefail
mkdir -p src/acme
cat > src/acme/models.py <<'PYTHON'
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Pending:
    pass

@dataclass(frozen=True)
class Approved:
    amount: float

type Decision = Pending | Approved
PYTHON
cat > src/acme/rules.py <<'PYTHON'
from __future__ import annotations
from .models import Decision

def choose(flag: bool, first: Decision, second: Decision) -> Decision:
    if flag:
        return first
    else:
        return second
PYTHON
morphir-python compile src --package acme/example --output model.json
morphir-python ir inspect model.json
morphir-python generate model.json --output-dir generated
morphir-python compile generated --package acme/example --output rebuilt.json
morphir-python ir convert model.json --to v4 --output model-v4.json
```
<!-- /example -->

`model.json` is a format-3 Library. `ir inspect` reports its format and module
summary. Generation creates `generated/acme/models.py` and
`generated/acme/rules.py`. Recompilation writes `rebuilt.json` with equivalent
supported definitions. Conversion explicitly writes draft v4 to `model-v4.json`.
Conversion diagnostics report information a format cannot retain. Generated
Python needs no Morphir runtime dependency.

The example keeps semantics rather than comments or source formatting. Running
generation again into the same nonempty directory fails and preserves those
files. Choose a new output directory for another generation.

## Change the version or module access

`compile --ir-version v4` requests draft-v4 compiler output directly. With no
`--expose`, every module is public. Repeat `--expose acme/models` to select public
modules. Recompile with the same exposure/package/version options when comparing
models. See [command reference](cli-reference.md) for diagnostics and options.

To perform the same work without files, use the
[in-memory compiler API](python-compiler.md#use-the-python-api).
The [example sources](https://github.com/finos/morphir-python/tree/main/examples)
are also available as an [archive](/assets/downloads/examples.zip).
