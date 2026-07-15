# Windows Packaging

DiskWise uses a PyInstaller one-folder build inside an MSIX package.

## Local Build

`scripts\build.ps1` installs dependencies, compiles the source, runs tests, generates Windows assets, and creates `dist\DiskWiseAI\DiskWiseAI.exe`.

## Store Build

`scripts\build-msix.ps1` stages the PyInstaller output, renders `AppxManifest.xml` with Partner Center identity values, and invokes the x64 `MakeAppx.exe` supplied by the Windows SDK.

Required build-machine components:

- Python 3.12 and project dependencies.
- Windows 10 or 11 SDK with MSIX Packaging Tools.
- Windows App Certification Kit only for an optional local precheck; Microsoft no longer maintains it, and Partner Center certification is authoritative.

Visual Studio, .NET, WinUI, Rust, Windows App SDK, and a local code-signing certificate are not required for Microsoft Store submission. The Store signs an accepted package.

The manifest template deliberately does not contain guessed identity values. A package must be built with the exact Identity Name and Publisher assigned in Partner Center.

Before packaging, run the Store preflight directly when needed:

```powershell
.\.venv\Scripts\python.exe .\scripts\validate-store-readiness.py --require-build
```

`scripts\build.ps1` and `scripts\build-msix.ps1` also run this validation. It checks manifest capabilities and placeholders, asset and screenshot dimensions, listing/privacy disclosures, version alignment, and the packaged files for mutable local data or embedded secrets.

## Store Screenshots

Generate listing screenshots without exposing local device data:

```powershell
.\.venv\Scripts\python.exe .\scripts\capture-store-screenshots.py
```

The script renders the real production pages at a 16:9 1440 x 810 logical viewport with a temporary SQLite database and synthetic `C:\Users\Demo` paths. It never reads the user's DiskWise database, API key, scan history, or disk usage for the captured values.
