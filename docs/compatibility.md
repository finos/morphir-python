# Choose a Morphir CLI

Three independently packaged tools appear in these guides. Confirm the provider
as well as the version before copying an integration command.

| Tool | Qualified identity | Python compiler route | IR and artifacts |
| --- | --- | --- | --- |
| `morphir-python` | Python distribution 0.0.3, core 0.0.2, native 0.1.0 | In-process typed API and CLI | v3 Library by default; explicit draft v4; versioned JSON |
| `finos/morphir` | Rust product CLI 0.4.0-beta.10 | Python Extism bundle 0.4.1, MEP 0.1 | Explicit v3/v4 JSON; compile writes `morphir-ir.json` |
| MoonBit-based `morphir` | Source pin documented in the MoonBit guide | Current `core-wasm-process` and `native-process` adapters do not run the Python Extism guest | Portable MEP 0.2 draft, IR v4 model envelope; Ion default, explicit JSON tuple |

## Verify the provider

Use the `morphir-python` console script from your Python environment. For the
Rust host, use the exact executable path produced by the pinned download in
the [extension guide](python-extension.md), then verify `--version`. For the
MoonBit CLI, use its source/packaged entry point at the declared revision as
described in the [MoonBit guide](moonbit.md). A program named `morphir` somewhere
on `PATH` is insufficient evidence of its provider.

Installation and invocation are separate operations. A repository can contain
a bundle that an adapter cannot execute. Publisher capability claims also do
not prove that a particular host ran the guest successfully.

## File exchange is a separate contract

A shared format number does not imply that a plain IR file is a model envelope.
Each interchange recipe must name producer, consumer, IR release, encoding,
distribution kind and retained metadata. Python migration returns explicit
diagnostics and cannot invent a host envelope or source provenance.

The [finos/morphir workflow](python-extension.md) qualifies Python compile and
generation through the released bundle. The [MoonBit guide](moonbit.md) records
current adapter/envelope refusals and the separate Extism proposal. It makes no
direct Python-extension or successful portable file-exchange claim today.

## Requalify a claim

Run the host-recipe check described in the contributor guide whenever a host,
bundle, recipe or relevant contract changes. The evidence records exact input
hashes and versions. Missing downloads fail qualification. Reuse is permitted
only for the same relevant inputs and dependency identities; a stale green run
for another version does not establish support.
