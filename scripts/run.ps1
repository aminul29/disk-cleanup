$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$OriginalLocation = Get-Location

function Assert-NativeSuccess([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

try {
    Set-Location $Root
    $Uv = Get-Command uv -ErrorAction SilentlyContinue
    if (-not (Test-Path $Python)) {
        Write-Host "Creating Python 3.12 virtual environment..."
        if ($null -ne $Uv) {
            & $Uv.Source venv --python 3.12 (Join-Path $Root ".venv")
        } else {
            py -3.12 -m venv (Join-Path $Root ".venv")
        }
        Assert-NativeSuccess "Virtual environment creation"
    }

    Write-Host "Installing dependencies..."
    if ($null -ne $Uv) {
        & $Uv.Source pip install --python $Python -r (Join-Path $Root "requirements.txt")
    } else {
        & $Python -m pip install -r (Join-Path $Root "requirements.txt")
    }
    Assert-NativeSuccess "Dependency installation"

    Write-Host "Starting DiskWise AI..."
    & $Python -m app.main
    Assert-NativeSuccess "DiskWise AI"
} finally {
    Set-Location $OriginalLocation
}
