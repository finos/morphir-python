# Install the Python process extension with the .NET CLI

Extension candidate `0.6.2` adds process packages for the .NET CLI, including
native Windows ARM64. This is a process-package release. Historical WASM bundles
and raw process assets remain available in their original releases. These
packages do not require CPython, a Rust toolchain or Wasmtime.
The published `0.6.0` release does not contain the new packages.

Morphirup installs the Morphir toolchain. Invoke its installed `morphir`
executable directly to install and run Python extensions. `morphirup run` uses
the selected generation's pinned F# providers and refuses Python with
`extension.not_selected`. Adding Python to that generation is separate work.

## Download the matching package

After `extension/python/v0.6.2` is published, download its matching `.zip`,
`.release.json` and `.manifest`, plus `SHA256SUMS`, from the
[extension releases](https://github.com/finos/morphir-python/releases).
Names start with `morphir-python-extension-0.6.2-<target>`.

| Machine | Target |
| --- | --- |
| Windows ARM64 | `aarch64-pc-windows-msvc` |
| Windows x64 | `x86_64-pc-windows-msvc` |
| Linux ARM64, glibc 2.39 or later | `aarch64-unknown-linux-gnu` |
| Linux x64, glibc 2.35 or later | `x86_64-unknown-linux-gnu` |
| macOS ARM64 | `aarch64-apple-darwin` |
| macOS x64 | `x86_64-apple-darwin` |

Verify each downloaded file against `SHA256SUMS`. Each archive contains one
executable. Leave it zipped for installation. Its descriptor uses the existing
`extensions/0.1.0-preview.1` contract and declares the archive's entry point,
executable file and extracted-tree digest.

The .NET CLI currently requires local files. Downloading release URLs during
`extension install` is tracked by
[morphir-dotnet#493](https://github.com/finos/morphir-dotnet/issues/493).

## Install and run

This PowerShell example uses a released .NET CLI at an explicit path and a
throwaway absolute Morphir Home. Substitute the paths and your platform target.
The existing installer requires explicit local-developer and no-probe flags.
Compilation and generation below exercise the installed process.

```powershell
$morphir = 'C:/tools/morphir/morphir.exe'
$env:MORPHIR_HOME = [IO.Path]::GetFullPath('.morphir-python-home')
Remove-Item Env:MORPHIR_EXTENSION_OVERLAY -ErrorAction SilentlyContinue
$packageDir = [IO.Path]::GetFullPath('python-package')
$stem = 'morphir-python-extension-0.6.2-aarch64-pc-windows-msvc'

& $morphir extension repository add python-local --directory $packageDir `
    --home $env:MORPHIR_HOME --local-developer
& $morphir extension install morphir-python --repository python-local `
    --local-release "$packageDir/$stem.release.json" `
    --local-archive "$packageDir/$stem.zip" `
    --home $env:MORPHIR_HOME --local-developer --no-probe

'def identity(value: int) -> int: return value' | Set-Content identity.py
& $morphir compile --language python --input identity.py --package-name acme/demo `
    --ir-version 4 --extension-id morphir-python --json
& $morphir generate --target python --output generated `
    --extension-id morphir-python --json
```

For the dotnet tool, use `dotnet-morphir` as the executable. Keep
`--extension-id morphir-python` explicit for both commands. `MORPHIR_HOME` must
be absolute and name the Home where the package was installed. This can be the
Home morphirup uses. Leave `MORPHIR_EXTENSION_OVERLAY` unset so the CLI reads
the Home's current catalog. A process extension has ordinary OS permissions.

The guest describes and negotiates only MEP `0.2.0-draft.1`. Hosts that offer
only the retired `0.1` protocol are refused. Historical packages are unchanged.

## Build a development package

From this checkout, build the process for your native target. On Windows, set
`RUSTFLAGS=-C target-feature=+crt-static` before building so the executable does
not require a separate Visual C++ runtime. For example, on Windows ARM64:

```powershell
$env:RUSTFLAGS = '-C target-feature=+crt-static'
cargo build --manifest-path rust/Cargo.toml --locked --release `
    -p morphir-python-extension --target aarch64-pc-windows-msvc
$commit = git rev-parse HEAD
python -m scripts.process_package `
    --executable rust/target/aarch64-pc-windows-msvc/release/morphir-python-extension.exe `
    --platform aarch64-pc-windows-msvc --commit $commit --output python-package
```

The packager reads the executable's actual MEP describe response, preserves its
claims, and removes only the `claimsVersion` wrapper for embedding in the
descriptor. It emits the archive, descriptor, canonical manifest and checksums
into a new directory. The process release workflow builds all six native targets
without adding a Python wheel platform. It runs the process tests and checks
installation, compile, generate and generated-code execution on Windows ARM64
against a pinned released .NET CLI. The retired Rust host is not a release gate.
