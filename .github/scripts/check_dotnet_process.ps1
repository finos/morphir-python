param(
    [Parameter(Mandatory = $true)][string]$HostExecutable,
    [Parameter(Mandatory = $true)][string]$PackageDirectory,
    [Parameter(Mandatory = $true)][string]$WorkDirectory
)
$ErrorActionPreference = 'Stop'
$morphir = (Resolve-Path -LiteralPath $HostExecutable).Path
$packages = (Resolve-Path -LiteralPath $PackageDirectory).Path
$work = [IO.Path]::GetFullPath($WorkDirectory)
if (Test-Path -LiteralPath $work) { throw 'Smoke test needs a new working directory' }
[IO.Directory]::CreateDirectory($work) | Out-Null
$oldHome = $env:MORPHIR_HOME
$oldOverlay = $env:MORPHIR_EXTENSION_OVERLAY
$env:MORPHIR_HOME = Join-Path $work 'home'
Remove-Item Env:MORPHIR_EXTENSION_OVERLAY -ErrorAction SilentlyContinue
Push-Location -LiteralPath $work
try {
    $release = @(Get-ChildItem -LiteralPath $packages -Filter '*.release.json')
    if ($release.Count -ne 1) { throw 'Expected exactly one package declaration' }
    $descriptor = Get-Content -LiteralPath $release[0].FullName -Raw | ConvertFrom-Json
    $artifact = $descriptor.artifacts[0]
    & $morphir extension repository add python-local --directory $packages --home $env:MORPHIR_HOME --local-developer
    if ($LASTEXITCODE -ne 0) { throw 'Repository registration failed' }
    & $morphir extension install morphir-python --repository python-local --local-release $release[0].FullName --local-archive (Join-Path $packages $artifact.filename) --home $env:MORPHIR_HOME --local-developer --no-probe
    if ($LASTEXITCODE -ne 0) { throw 'Package installation failed' }
    [IO.File]::WriteAllText((Join-Path $work 'identity.py'), "def identity(value: int) -> int: return value`n", [Text.UTF8Encoding]::new($false))
    $compile = & $morphir compile --language python --input identity.py --package-name acme/demo --ir-version 4 --output compiled --extension-id morphir-python --json
    if ($LASTEXITCODE -ne 0) { throw "Installed compile failed: $compile" }
    $compiled = $compile | ConvertFrom-Json
    if (!$compiled.success -or $compiled.provider.version -ne $descriptor.version -or $compiled.provider.mepVersion -ne '0.2.0-draft.1') { throw 'Compile did not use the installed package and protocol' }
    $generate = & $morphir generate --input compiled/morphir-ir.json --target python --output generated --extension-id morphir-python --json
    if ($LASTEXITCODE -ne 0) { throw "Installed generate failed: $generate" }
    $generated = $generate | ConvertFrom-Json
    if (!$generated.success -or $generated.provider.version -ne $descriptor.version) { throw 'Generate did not use the installed package' }
    python -c "import runpy; assert runpy.run_path('generated/identity.py')['identity'](42) == 42"
    if ($LASTEXITCODE -ne 0) { throw 'Generated Python did not execute correctly' }
    $compile | Set-Content -LiteralPath compile.json -Encoding utf8
    $generate | Set-Content -LiteralPath generate.json -Encoding utf8
    Write-Output "Installed Python $($descriptor.version): compile, generate and generated code passed."
}
finally {
    Pop-Location
    $env:MORPHIR_HOME = $oldHome
    $env:MORPHIR_EXTENSION_OVERLAY = $oldOverlay
}
