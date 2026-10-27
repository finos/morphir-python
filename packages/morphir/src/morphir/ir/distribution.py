"""Compatibility shim: re-exports `morphir.ir.v4.distribution`."""

from morphir.ir.v4.distribution import (
    ApplicationDistribution,
    Distribution,
    EntryPoint,
    EntryPointKind,
    LibraryDistribution,
    PackageInfo,
    SpecsDistribution,
)

__all__ = [
    "ApplicationDistribution",
    "Distribution",
    "EntryPoint",
    "EntryPointKind",
    "LibraryDistribution",
    "PackageInfo",
    "SpecsDistribution",
]
