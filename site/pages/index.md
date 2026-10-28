# Morphir Python

Write a small domain model in Python, compile it to Morphir IR, and generate
Python from that model. Use the library directly from your application or run
the same compiler through the CLI.

## Start with a model

Follow the [CLI quickstart](../../docs/quickstart.md) for a complete
compile, inspect, generate and recompile workflow. The
[Python API guide](../../docs/python-compiler.md) performs compilation in memory
and returns typed results and diagnostics.

## Work with existing IR

The dependency-free [library](../../docs/library.md) reads and writes Morphir IR,
migrates supported formats, and supplies the Morphir SDK.
[Installation](../../docs/installation.md) explains which package you need.

## Connect an extension

The Python compiler also ships as a WASM extension. Start with the
[compatibility table](../../docs/compatibility.md), then follow the guide for
[finos/morphir](../../docs/python-extension.md) or the
[MoonBit-based CLI](../../docs/moonbit.md). Each guide states what its qualified
version can do.

## Help improve the guides

These examples are checked against installed packages. The
[contributor guide](../../docs/site.md) explains how to run those checks and
preview this site with Telescope.
