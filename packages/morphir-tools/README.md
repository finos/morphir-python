# Morphir Tools

CLI tools and extensions for [Morphir Python](https://github.com/finos/morphir-python).

This package provides:

- Command-line interface for Morphir operations
- Code generation backends
- File I/O utilities
- Development tools

## Installation

```bash
pip install morphir-tools
```

Or with uv:

```bash
uv add morphir-tools
```

This will also install the `morphir` core library as a dependency.

## Usage

The `morphir-tools` command inspects and converts versioned `morphir-ir.json`
files. It reads format 3.0.x (what morphir-elm writes) and draft IR 4.0.x, and
uses the `morphir` library for every read, write, and migration.

```bash
morphir-tools ir inspect morphir-ir.json
morphir-tools ir convert morphir-ir.json --to v4 -o out.json --package-version 1.2.0
morphir-tools ir convert v4.json --to v3 -o out.json --drop-source-locations
```

`inspect` prints the normalized format version, the distribution kind, and the
package name, and labels v4 as draft. `convert` writes through a temporary file
and renames it only on success, so a failed conversion leaves no output file.
Diagnostics go to standard error as `code at location: message`.

Exit codes are 0 for success (also with warnings), 1 for a diagnostic, and 2 for
a usage error. Formats 1 and 2 and IR 3.1.0 are rejected; see the
[morphir package README](../morphir/README.md#morphir-ir-versions) for the
format-version rules and the draft v4 status.

## Requirements

- Python 3.14+
- morphir (core library)

## License

Apache-2.0 - see the [LICENSE](../../LICENSE) file for details.

## Related Packages

- [morphir](https://pypi.org/project/morphir/) - Core library
