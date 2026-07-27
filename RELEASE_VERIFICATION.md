# Release Verification

Every official GitHub Release includes:

- `MarketingAnalytics-win-x64.zip` - the Windows x64 package;
- `SHA256SUMS.txt` - the SHA-256 checksum of that exact archive.

## Verify on Windows

After downloading both files into the same folder, run PowerShell:

```powershell
Get-FileHash .\MarketingAnalytics-win-x64.zip -Algorithm SHA256
Get-Content .\SHA256SUMS.txt
```

The hexadecimal SHA-256 values must match exactly. Do not run a downloaded
package if the checksum differs.

## What this confirms

The checksum detects accidental corruption or a changed archive after release.
It does not replace code signing. For public commercial distribution, publish a
future Authenticode-signed build and keep the signing identity stable.
