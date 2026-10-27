"""The ``morphir-python`` command line.

Every IR operation goes through the `morphir` library: the shared format-version
reader, the v3 (3.0.x and 3.1.x) and draft v4 codecs, and `morphir.ir.migrate`.
The CLI adds file handling and reporting only.

Exit codes: 0 for success (including success with warnings), 1 when the library
reports a diagnostic, 2 for a usage error.
"""

from __future__ import annotations

import os
import tempfile
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from morphir.ir import format_version as fv
from morphir.ir.diagnostics import Diagnostic, DiagnosticError
from morphir.ir.migrate import Err, Ok, v3_to_v4, v4_to_v3
from morphir.ir.migrate import drop_input_attributes as drop_inputs
from morphir.ir.v3 import codec as v3_codec
from morphir.ir.v3 import codec_v1, codec_v2
from morphir.ir.v3 import distribution as v3_dist
from morphir.ir.v4 import codec as v4_codec
from morphir.ir.v4 import distribution as v4_dist
from morphir.ir.v4.name import Name as Name4
from morphir.ir.v4.path import Path as Path4

app = typer.Typer(
    name="morphir-python",
    help="Command-line tools for Morphir IR.",
    no_args_is_help=True,
)
ir_app = typer.Typer(
    help="Inspect and convert versioned morphir-ir.json files "
    "(format 3.0.x and 3.1.x, and draft 4.0.x; legacy formats 1 and 2 are read "
    "and upgraded).",
    no_args_is_help=True,
)
app.add_typer(ir_app, name="ir")


class Target(str, Enum):
    """The IR version to convert to."""

    V3 = "v3"
    V4 = "v4"


def _report(diagnostics: tuple[Diagnostic, ...], *, warning: bool = False) -> None:
    prefix = "warning" if warning else "error"
    for diagnostic in diagnostics:
        typer.echo(f"{prefix}: {diagnostic.render()}", err=True)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        typer.echo(f"error: cannot read {path}: {error.strerror}", err=True)
        raise typer.Exit(1) from None


def _write_atomically(target: Path, text: str) -> None:
    directory = target.parent if str(target.parent) else Path()
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=directory
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        Path(temp_name).replace(target)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def _kind(dist: v4_dist.Distribution | v3_dist.Distribution) -> str:
    match dist:
        case v3_dist.Library():
            return "Library"
        case v3_dist.Specs():
            return "Specs"
        case v4_dist.LibraryDistribution():
            return "Library"
        case v4_dist.SpecsDistribution():
            return "Specs"
        case v4_dist.ApplicationDistribution():
            return "Application"


def _read_v3_family(
    text: str, version: fv.FormatVersion | fv.LegacyFormat
) -> v3_dist.Distribution:
    """Decode a format 1, 2, or 3.x document into the v3 model.

    Legacy formats 1 and 2 always give a format 3.0.0 Library.
    """
    match version:
        case fv.LegacyFormat.V1:
            return codec_v1.decode_versioned_distribution(text)
        case fv.LegacyFormat.V2:
            return codec_v2.decode_versioned_distribution(text)
        case _:
            return v3_codec.decode_versioned_distribution(text)


def _is_v4(version: fv.FormatVersion | fv.LegacyFormat) -> bool:
    return isinstance(version, fv.FormatVersion) and version.major == 4


@ir_app.command()
def inspect(
    file: Annotated[Path, typer.Argument(help="A versioned morphir-ir.json file.")],
) -> None:
    """Report the format version, distribution kind, and package name."""
    text = _read(file)
    try:
        version, _ = fv.read_document_with_legacy(text)
        if _is_v4(version):
            dist = v4_codec.decode_versioned_distribution(text)
            kind = _kind(dist)
            package = v4_codec.encode_path(dist.package.name)
        else:
            classic = _read_v3_family(text, version)
            kind = _kind(classic)
            package = v4_codec.encode_path(
                Path4(tuple(Name4(tuple(n)) for n in classic.package_name))
            )
    except DiagnosticError as error:
        _report(error.diagnostics)
        raise typer.Exit(1) from None
    legacy = isinstance(version, fv.LegacyFormat)
    typer.echo(f"format: {version}{' (legacy)' if legacy else ''}")
    typer.echo(f"kind: {kind}")
    typer.echo(f"package: {package}")
    if _is_v4(version):
        typer.echo(f"note: {v4_codec.DRAFT_NOTICE}")
    if legacy:
        typer.echo(
            f"note: legacy format {version} is read-only; "
            "ir convert upgrades it to format 3.0.0 or draft v4"
        )


@ir_app.command()
def convert(
    file: Annotated[Path, typer.Argument(help="A versioned morphir-ir.json file.")],
    to: Annotated[Target, typer.Option("--to", help="The IR version to write.")],
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Where to write the result.")
    ],
    package_version: Annotated[
        str | None,
        typer.Option(help="Package release version to record when upgrading to v4."),
    ] = None,
    drop_source_locations: Annotated[
        bool,
        typer.Option(help="Drop value source locations when downgrading to v3."),
    ] = False,
    drop_input_attributes: Annotated[
        bool,
        typer.Option(
            help="Keep only the declared type of each value-definition input when "
            "writing v4, which spells an input as a bare type."
        ),
    ] = False,
) -> None:
    """Convert between format 3 (3.0.x and 3.1.x) and draft IR v4.

    A v3 Library is written as format 3 and a v3 Specs as format 3.1.0, the lowest
    version that holds each. Legacy formats 1 and 2 are read as a format 3.0.0
    Library and never written.

    The output is written to a temporary file and renamed only on success, so a
    failed conversion leaves no output file.
    """
    text = _read(file)
    try:
        version, _ = fv.read_document_with_legacy(text)
        if to is Target.V4:
            upgraded: Ok[v4_dist.Distribution]
            if _is_v4(version):
                upgraded = Ok(v4_codec.decode_versioned_distribution(text))
            else:
                migrated = v3_to_v4(
                    _read_v3_family(text, version),
                    package_version=package_version,
                )
                upgraded = Ok(migrated.value, migrated.warnings)
            if drop_input_attributes:
                upgraded = drop_inputs(upgraded.value)
            document = v4_codec.encode_versioned_distribution(upgraded.value)
            warnings: tuple[Diagnostic, ...] = upgraded.warnings
        else:
            if not _is_v4(version):
                classic = _read_v3_family(text, version)
                warnings = ()
            else:
                result = v4_to_v3(
                    v4_codec.decode_versioned_distribution(text),
                    drop_source_locations=drop_source_locations,
                )
                if isinstance(result, Err):
                    _report(result.diagnostics)
                    raise typer.Exit(1)
                classic, warnings = result.value, result.warnings
            document = v3_codec.encode_versioned_distribution(classic)
    except DiagnosticError as error:
        _report(error.diagnostics)
        raise typer.Exit(1) from None
    _write_atomically(output, fv.dump_json(document))
    _report(warnings, warning=True)
    typer.echo(f"wrote {output} (format {to.value})")


def main() -> None:
    """Run the ``morphir-python`` command line."""
    app()
