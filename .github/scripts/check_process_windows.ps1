param(
    [Parameter(Mandatory = $true)][string]$Executable,
    [Parameter(Mandatory = $true)][string]$Report
)
$ErrorActionPreference = "Stop"
$processBinary = (Resolve-Path -LiteralPath $Executable).Path
$vsWhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
$toolCandidates = @(& $vsWhere -latest -products "*" -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -find "VC\Tools\MSVC\**\bin\Hostx64\x64\dumpbin.exe")
$toolLocation = $toolCandidates | Select-Object -First 1
if ($LASTEXITCODE -ne 0 -or !$toolLocation) {
    throw "Cannot locate the MSVC dependency inspector"
}
$dependencyOutput = & $toolLocation /DEPENDENTS $processBinary
if ($LASTEXITCODE -ne 0) {
    throw "MSVC dependency inspection failed"
}
$dependencies = @(
    [regex]::Matches(($dependencyOutput -join "`n"), '(?i)\b[A-Za-z0-9_.-]+\.dll\b') |
        ForEach-Object { $_.Value.ToLowerInvariant() } |
        Sort-Object -Unique
)
if ($dependencies.Count -eq 0) {
    throw "Dependency inspection returned no Windows system DLLs"
}
if ($dependencies -match '^(vcruntime|msvcp|concrt|python)\d') {
    throw "Standalone process imports an external VC or Python runtime: $($dependencies -join ', ')"
}
$receipt = @{
    sourceCommit = $env:GITHUB_SHA
    crt = "static"
    artifact = @{
        sha256 = (Get-FileHash -LiteralPath $processBinary -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    checkerSha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
    tool = @{
        name = "dumpbin.exe"
        sha256 = (Get-FileHash -LiteralPath $toolLocation -Algorithm SHA256).Hash.ToLowerInvariant()
        version = (Get-Item -LiteralPath $toolLocation).VersionInfo.FileVersion
    }
    dependencies = $dependencies
}
$reportFile = [System.IO.Path]::GetFullPath($Report)
[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($reportFile)) | Out-Null
[System.IO.File]::WriteAllText($reportFile, ($receipt | ConvertTo-Json -Depth 5) + "`n", [System.Text.UTF8Encoding]::new($false))
$receipt | ConvertTo-Json -Depth 5
