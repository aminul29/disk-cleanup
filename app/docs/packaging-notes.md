# Packaging Notes

Packaging is deferred to a later milestone. The current MVP uses PyInstaller only for local build validation.

## Recommended Release Path

1. Stabilize the local Python MVP.
2. Add automated smoke tests.
3. Produce a PyInstaller one-folder build.
4. Wrap/package the app as MSIX for distribution.
5. Validate Store policy, privacy claims, and update behavior.

## Packaging Options

### MSIX Recommended

MSIX is the recommended distribution target for DiskWise AI because it aligns better with Windows app distribution:

- Microsoft Store distribution can provide Microsoft-managed signing for Store-delivered packages.
- Microsoft Store distribution can provide CDN hosting and update delivery.
- MSIX supports cleaner install/uninstall behavior than a loose executable.
- MSIX provides better Windows integration for identity, app lifecycle, and future Store readiness.

### PyInstaller Development Build

PyInstaller remains useful for local MVP development and smoke testing:

- Fast local executable validation.
- No Visual Studio, Windows App SDK, .NET SDK, or Rust requirement.
- Good enough for internal QA before Store packaging.

The PyInstaller output should be treated as a build artifact, not the final public distribution format.

Do not require Visual Studio, .NET SDK, Windows App SDK, Rust, or MSIX tools for current MVP development.

## Current Scripts

```powershell
.\scripts\run.ps1
.\scripts\test.ps1
.\scripts\build.ps1
```

`build.ps1` creates a PyInstaller one-folder build. It does not sign the app, create an installer, or produce MSIX.

Future MSIX work should be a separate milestone after the MVP UI, safety rules, and cleanup behavior are stable.

Future packaging should preserve:

- Local-first privacy claims.
- Clear cleanup preview.
- Conservative risk language.
- No fake performance claims.
- No payment or license secrets in the client.
