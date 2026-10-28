# Connect with the MoonBit-based CLI

The [MoonBit Morphir CLI](https://github.com/finos/morphir-moonbit/tree/bd3adc52e6b8f6368fdaee50f76535799732f8d6/apps/morphir)
and the Rust `finos/morphir` CLI share the executable name `morphir`. This guide
describes the MoonBit source at `bd3adc52e6b8f6368fdaee50f76535799732f8d6`.
It does not claim that the Python Extism bundle runs through this version.

## Current adapter limit

The Python bundle imports the Extism host ABI and speaks MEP 0.1. The MoonBit
portable `core-wasm-process` adapter expects a core-WASM guest using
`morphir_bytes_v1` callbacks, a binary Ion manifest and MEP 0.2 draft. The
`native-process` adapter is another explicit binding. Neither is an Extism host.
Renaming the Python `.wasm` to `model.wasm` does not supply a compatible ABI.

The separate [Extism proposal](https://github.com/finos/morphir-moonbit/tree/DamianReeves/propose-extism-python/openspec/changes/qualify-extism-python)
is tracked by `morphir-ukvn.5.98`. It proposes a pinned shared Rust host adapter,
protocol negotiation and qualification with the real Python bundle. The proposal does not establish released support. Until it is independently qualified, use
the [Rust-host recipe](python-extension.md) to invoke the Python extension or
use the [Python API](python-compiler.md) directly.

## File interchange limits

The portable MoonBit extension path generates from a MorphirModel envelope,
`model/model-envelope.json`, with a validated payload. Its current tuple uses
envelope `0.1.0-draft.1`, IR `4.0.0`, and either `morphir-model`/`ion-binary` or
`morphir-ir`/`morphir-json`. Compilation can refuse JSON if it would lose source
and naming provenance. Python's versioned `model.json` is a plain IR document.

The documentation qualification probes a plain Python v3/v4 Library at the
MoonBit portable generation boundary. The expected result is an explicit
envelope refusal before guest execution, with exit status 2 in this pinned CLI.
That is a checked incompatibility,
not a recipe for a successful conversion. No ad hoc envelope, undocumented
provenance drop, or automatic codec fallback is recommended.

To repeat a probe, use the pinned source's own CLI entry point and provide
the plain `model.json` from the [quickstart](quickstart.md) as the generation
input. Supply a syntactically valid portable pin as required by that CLI so
the check reaches model validation. The qualification runner records the exact
command, input and diagnostic; the upstream
[extension guide](https://github.com/finos/morphir-moonbit/blob/bd3adc52e6b8f6368fdaee50f76535799732f8d6/apps/morphir/docs/extension.md)
defines the full pin schema and invocation contract.

## Installation is not selection

The portable invocation requires an explicit extension pin. Local repository
commands and installed selection have separate constraints. Installed native
selection is tracked by `morphir-ukvn.5.64.30`. The site will add a working
Python connection only after the Extism adapter and the exact bundle/host pair
pass their own qualification.
