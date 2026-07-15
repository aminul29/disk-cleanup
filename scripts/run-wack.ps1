param(
    [Parameter(Mandatory = $true)]
    [string]$PackagePath
)

$ErrorActionPreference = "Stop"
$ResolvedPackage = (Resolve-Path -LiteralPath $PackagePath).Path
$Root = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$ReportDirectory = Join-Path $Root "build\wack"
$ReportPath = Join-Path $ReportDirectory "DiskWiseAI-WACK.xml"
New-Item -ItemType Directory -Path $ReportDirectory -Force | Out-Null

$AppCert = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\App Certification Kit" `
    -Filter "appcert.exe" -Recurse -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($null -eq $AppCert) {
    throw "Windows App Certification Kit was not found. Install it from the Windows SDK installer."
}

& $AppCert.FullName test -appxpackagepath $ResolvedPackage -reportoutputpath $ReportPath
if ($LASTEXITCODE -ne 0) {
    throw "Windows App Certification Kit reported a failure. Review $ReportPath."
}

Write-Host "WACK report: $ReportPath"
