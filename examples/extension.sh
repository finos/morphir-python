#!/usr/bin/env bash
set -euo pipefail
# MORPHIR_HOST is the verified finos/morphir 0.4.0-beta.10 executable.
# PYTHON_BUNDLE is the verified 0.4.2 bundle directory containing release.json.
: "${MORPHIR_HOST:?Set the verified Rust-host executable path}"
: "${PYTHON_BUNDLE:?Set the verified bundle directory}"
"$MORPHIR_HOST" --version
export MORPHIR_HOME="$PWD/.morphir-home"
"$MORPHIR_HOST" extension repository init .morphir/python-index
"$MORPHIR_HOST" extension repository add python-local --directory .morphir/python-index
"$MORPHIR_HOST" extension repository publish python-local --bundle "$PYTHON_BUNDLE"
"$MORPHIR_HOST" extension repository verify python-local
"$MORPHIR_HOST" extension install --repository python-local morphir-python
"$MORPHIR_HOST" extension list
cat > morphir.toml <<'TOML'
[project]
name = "acme/example"
version = "0.1.0"
source_directory = "src"

[frontend]
language = "python"
emit_parse_stage = false
TOML
"$MORPHIR_HOST" compile --language python --input src --ir-version 3.0.0 --output compiled
"$MORPHIR_HOST" generate --target python --input compiled/morphir-ir.json --output host-generated
"$MORPHIR_HOST" compile --language python --input host-generated --ir-version 3.0.0 --output host-rebuilt
