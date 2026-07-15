param(
    [Parameter(Mandatory = $true)]
    [string]$IdentityName,

    [Parameter(Mandatory = $true)]
    [string]$Publisher,

    [Parameter(Mandatory = $true)]
    [string]$PublisherDisplayName,

    [string]$Version = "0.1.0.0",
    [switch]$SkipAppBuild
)

$ErrorActionPreference = "Stop"

if ($Version -notmatch '^\d+\.\d+\.\d+\.\d+$') {
    throw "Version must contain four numeric parts, for example 0.1.0.0."
}
if (($Version.Split('.') | Where-Object { [int]$_ -gt 65535 }).Count) {
    throw "Each MSIX version part must be between 0 and 65535."
}
foreach ($Value in @($IdentityName, $Publisher, $PublisherDisplayName)) {
    if ([String]::IsNullOrWhiteSpace($Value) -or $Value -match '(?i)PARTNER_CENTER|^YOUR_|REPLACE|__') {
        throw "Use the exact package identity values assigned in Partner Center; placeholders are not allowed."
    }
}

$Root = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$StageRoot = [IO.Path]::GetFullPath((Join-Path $Root "build\msix\root"))
$BuildRoot = [IO.Path]::GetFullPath((Join-Path $Root "build\msix"))
$DistApp = Join-Path $Root "dist\DiskWiseAI"
$OutputDirectory = Join-Path $Root "dist\msix"
$OutputPackage = Join-Path $OutputDirectory "DiskWiseAI_${Version}_x64.msix"
$ManifestTemplate = Join-Path $Root "packaging\msix\AppxManifest.template.xml"
$Assets = Join-Path $Root "packaging\msix\Assets"

if (-not $SkipAppBuild) {
    & (Join-Path $PSScriptRoot "build.ps1")
}
if (-not (Test-Path (Join-Path $DistApp "DiskWiseAI.exe"))) {
    throw "PyInstaller output was not found at $DistApp. Run scripts\build.ps1 first."
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
& $Python (Join-Path $PSScriptRoot "generate-store-assets.py")
if ($LASTEXITCODE -ne 0) {
    throw "Store asset generation failed with exit code $LASTEXITCODE."
}
& $Python (Join-Path $PSScriptRoot "validate-store-readiness.py") --require-build
if ($LASTEXITCODE -ne 0) {
    throw "Microsoft Store readiness validation failed with exit code $LASTEXITCODE."
}

$MakeAppx = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin" `
    -Filter "makeappx.exe" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match '\\x64\\makeappx\.exe$' } |
    Sort-Object FullName -Descending |
    Select-Object -First 1
if ($null -eq $MakeAppx) {
    throw "MakeAppx.exe was not found. Install the Windows 10/11 SDK, including MSIX Packaging Tools."
}

if (-not $StageRoot.StartsWith($BuildRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to replace an MSIX staging path outside $BuildRoot."
}
if (Test-Path $StageRoot) {
    Remove-Item -LiteralPath $StageRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $StageRoot | Out-Null
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

Copy-Item -LiteralPath $DistApp -Destination (Join-Path $StageRoot "DiskWiseAI") -Recurse
Copy-Item -LiteralPath $Assets -Destination (Join-Path $StageRoot "Assets") -Recurse

$Manifest = Get-Content -LiteralPath $ManifestTemplate -Raw
$Manifest = $Manifest.Replace("__IDENTITY_NAME__", [Security.SecurityElement]::Escape($IdentityName))
$Manifest = $Manifest.Replace("__PUBLISHER__", [Security.SecurityElement]::Escape($Publisher))
$Manifest = $Manifest.Replace(
    "__PUBLISHER_DISPLAY_NAME__",
    [Security.SecurityElement]::Escape($PublisherDisplayName)
)
$Manifest = $Manifest.Replace("__VERSION__", $Version)
if ($Manifest -match '__[A-Z0-9_]+__') {
    throw "The rendered AppxManifest.xml still contains an unresolved placeholder."
}
try {
    [xml]$Manifest | Out-Null
} catch {
    throw "The rendered AppxManifest.xml is invalid: $($_.Exception.Message)"
}
Set-Content -LiteralPath (Join-Path $StageRoot "AppxManifest.xml") -Value $Manifest -Encoding utf8

& $MakeAppx.FullName pack /d $StageRoot /p $OutputPackage /o
if ($LASTEXITCODE -ne 0) {
    throw "MakeAppx failed with exit code $LASTEXITCODE."
}

Write-Host "MSIX created: $OutputPackage"
Write-Host "The Microsoft Store signs the package during submission."
