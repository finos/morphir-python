#!/usr/bin/env bash
set -euo pipefail
VERSION=0.5.0
gh release download "extension/python/v$VERSION" \
  --repo finos/morphir-python --dir python-extension-assets
(cd python-extension-assets && shasum -a 256 -c SHA256SUMS)
mkdir python-wasm python-process
cp "python-extension-assets/morphir-python-binding-$VERSION.wasm" \
  "python-extension-assets/morphir-python-binding-$VERSION.wasm.sha256" python-wasm/
cp "python-extension-assets/morphir-python-binding-$VERSION.release.json" \
  python-wasm/release.json
tar -xzf "python-extension-assets/morphir-python-extension-$VERSION.tar.gz" \
  -C python-process
export WASM_BUNDLE="$(cd python-wasm && pwd)"
export PROCESS_BUNDLE="$(cd python-process && pwd)"
