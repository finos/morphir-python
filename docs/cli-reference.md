# CLI reference

The Python CLI executable is `morphir-python`, supplied by the `morphir-python`
distribution. It is independent of the two executables called `morphir` in the
[integration guides](compatibility.md). Use [installation](installation.md)
and the [round-trip quickstart](quickstart.md) to begin.

## Compile Python

`compile` reads one `.py` file or a directory tree. A directory's relative file
paths establish module identity. Hidden directories, caches and symlinks are
skipped. Compilation defaults to format 3.0.0; choosing v4 prints a draft notice.
Without exposure options, every module is public.

<!-- reference: compile -->
```text
morphir-python compile
source [required]: A Python file, or a directory of Python files.
--package [required]: Morphir package name, such as acme/example.
--output, -o [required]: Where to write the IR document.
--ir-version [default: Target.V3]: The IR version to write.
--expose: Module to make public, such as acme/models. Repeat for more. Without it every module is public.
```
<!-- /reference -->

## Generate Python

`generate` reads a supported Library document and creates relative module paths.
The output directory must be new or empty. The CLI validates and stages all
files before publishing them; errors leave existing data intact.

<!-- reference: generate -->
```text
morphir-python generate
file [required]: A versioned morphir-ir.json file.
--output-dir [required]: A new or empty directory for the Python modules.
```
<!-- /reference -->

## Inspect IR

Inspection reports the document's format/distribution and summary without
loading the native compiler. It does not imply the model is supported by the
Python compiler or every ecosystem host.

<!-- reference: inspect -->
```text
morphir-python ir inspect
file [required]: A versioned morphir-ir.json file.
```
<!-- /reference -->

## Convert IR

Conversion is explicit. Legacy formats 1/2 can be upgraded, and supported v3/v4
models can be migrated. Inspect diagnostics before permitting a documented loss
policy. No implicit conversion runs during generation.

<!-- reference: convert -->
```text
morphir-python ir convert
file [required]: A versioned morphir-ir.json file.
--to [required]: The IR version to write.
--output, -o [required]: Where to write the result.
--package-version: Package release version to record when upgrading to v4.
--drop-source-locations, --no-drop-source-locations [default: False]: Drop value source locations when downgrading to v3.
--drop-input-attributes, --no-drop-input-attributes [default: False]: Keep only the declared type of each value-definition input when writing v4, which spells an input as a bare type.
--v4-spelling [default: V4Spelling.COMPACT]: The v4 JSON spelling to write: compact, the canonical form, or expanded. Ignored when writing v3.
```
<!-- /reference -->

## Exit status and diagnostics

Successful operations exit zero. Model, format and output errors exit 1 and
write diagnostics to stderr, including stable codes and available locations.
Argument syntax errors use the CLI parser's nonzero status. Warnings remain
distinct from errors and do not make success fail. A failed compilation
preserves an existing output file. See [compiler diagnostics](python-compiler.md#diagnostics)
for codes and [library guidance](library.md) for migration diagnostics.
