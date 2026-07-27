# Security Policy

## Supported releases

Only the latest published release is supported with fixes. Install releases
only from the official GitHub Releases page and verify their SHA-256 checksum.

## Reporting a vulnerability

Do not publish exploit details, customer exports, access tokens, or personal
data in a public issue. Use GitHub's private security advisory reporting for
this repository when available. If it is unavailable, open a minimal issue
requesting a private contact channel without including sensitive details.

## Release safety

- Download only the official `MarketingAnalytics-win-x64.zip` asset.
- Verify the SHA-256 value against `SHA256SUMS.txt`.
- Keep Windows and Microsoft Defender current.
- Treat an unsigned build from any other location as untrusted.

Windows reputation warnings can occur for newly published unsigned EXE files.
Future releases should be Authenticode-signed through a trusted publisher
identity before broad distribution.
