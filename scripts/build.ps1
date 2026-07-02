$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "Creating Python 3.12 virtual environment..."
    uv venv --python 3.12 (Join-Path $Root ".venv")
}

Write-Host "Installing dependencies..."
uv pip install --python $Python -r (Join-Path $Root "requirements.txt")

Write-Host "Running tests before build..."
& $Python -m compileall app tests
& $Python -m pytest -q

Write-Host "Building PyInstaller one-folder app..."
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "DiskWiseAI" `
    --add-data "app\assets;app\assets" `
    app\main.py

Write-Host "Build complete: dist\DiskWiseAI\DiskWiseAI.exe"
