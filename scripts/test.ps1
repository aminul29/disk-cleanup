$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$OriginalLocation = Get-Location

function Assert-NativeSuccess([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run scripts\run.ps1 first."
}

try {
    Set-Location $Root
    & $Python -m compileall -q app tests scripts
    Assert-NativeSuccess "Python compilation"
    & $Python -m ruff check app tests scripts
    Assert-NativeSuccess "Ruff"
    & $Python -m pytest -q
    Assert-NativeSuccess "Tests"
    & $Python scripts\validate-store-readiness.py
    Assert-NativeSuccess "Microsoft Store readiness validation"
} finally {
    Set-Location $OriginalLocation
}
