# Morphir Python

CLI tools and extensions for [Morphir Python](https://github.com/finos/morphir-python).

This package provides:

- Command-line interface for Morphir operations
- Code generation backends
- File I/O utilities
- Development tools

## Installation

```bash
pip install morphir-python
```

Or with uv:

```bash
uv add morphir-python
```

This will also install the `morphir` core library as a dependency.

## Usage

The `morphir-python` command inspects and converts versioned `morphir-ir.json`
files. It reads format 3.0.x (what morphir-elm writes), format 3.1.x (which adds
the v3 `Specs` distribution) and draft IR 4.0.x, reads the legacy formats 1 and 2
to upgrade them, and uses the `morphir` library for every read, write, and
migration.

```bash
morphir-python ir inspect morphir-ir.json
morphir-python ir convert morphir-ir.json --to v4 -o out.json --package-version 1.2.0
morphir-python ir convert v4.json --to v3 -o out.json --drop-source-locations
morphir-python ir convert old-format-1.json --to v3 -o out.json
```

`inspect` prints the normalized format version, the distribution kind
(`Library`, `Specs` or `Application`), and the package name, and labels v4 as
draft and formats 1 and 2 as legacy. `convert` handles `Library` and `Specs` in
both directions. It writes a v3 `Library` as format `3` and a v3 `Specs` as
`"3.1.0"`, the lowest version that holds each. A legacy format 1 or 2 file
converts to a format 3.0.0 `Library` or draft v4; nothing writes format 1 or 2.
`convert` writes through a temporary file and renames it only on success, so a
failed conversion leaves no output file.
Diagnostics go to standard error as `code at location: message`.

Exit codes are 0 for success (also with warnings), 1 for a diagnostic, and 2 for
a usage error. 3.x releases from 3.2.0 on are rejected; see the
[morphir package README](../morphir/README.md#morphir-ir-versions) for the
format-version rules and the draft v4 status.

## Requirements

- Python 3.14+
- morphir (core library)

## License

Apache-2.0 - see the [LICENSE](../../LICENSE) file for details.

## Related Packages

- [morphir](https://pypi.org/project/morphir/) - Core library
