$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "Creating Python 3.12 virtual environment..."
    uv venv --python 3.12 (Join-Path $Root ".venv")
}

Write-Host "Installing dependencies..."
uv pip install --python $Python -r (Join-Path $Root "requirements.txt")

Write-Host "Starting DiskWise AI..."
& $Python -m app.main
