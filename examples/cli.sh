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
