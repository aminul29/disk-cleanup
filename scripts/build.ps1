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

    Write-Host "Running release checks..."
    & $Python -m compileall -q app tests scripts\generate-store-assets.py
    Assert-NativeSuccess "Python compilation"
    & $Python -m ruff check app tests scripts\generate-store-assets.py
    Assert-NativeSuccess "Ruff"
    & $Python -m pytest -q
    Assert-NativeSuccess "Tests"

    Write-Host "Generating Windows assets..."
    & $Python (Join-Path $PSScriptRoot "generate-store-assets.py")
    Assert-NativeSuccess "Windows asset generation"

    Write-Host "Building PyInstaller one-folder app..."
    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --windowed `
        --name "DiskWiseAI" `
        --icon "app\assets\app-icon.ico" `
        --version-file "packaging\windows\version_info.txt" `
        --collect-data "lucide" `
        --add-data "app\assets;app\assets" `
        app\main.py
    Assert-NativeSuccess "PyInstaller"

    Write-Host "Build complete: dist\DiskWiseAI\DiskWiseAI.exe"
} finally {
    Set-Location $OriginalLocation
}
