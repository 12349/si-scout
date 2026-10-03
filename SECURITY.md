# Security Policy

## Supported Versions

| Version | Supported |
| :--- | :--- |
| Release 1.0 (Current) | :white_check_mark: |

## Reporting a Vulnerability

SI Scout is designed to be run locally as an offline-first tool, strictly bound to `127.0.0.1`.
However, security reports regarding privacy leaks, accidental network requests, or input injection are taken seriously.

If you discover a security vulnerability:
1. **Do NOT open a public GitHub issue.**
2. Send a responsible disclosure email detailing:
   - Nature of the issue (e.g. unexpected socket connection, privacy leak, path traversal)
   - Steps to reproduce
   - Potential impact
3. A response and remediation timeline will be provided within 48 hours.

## Local Architecture Security Principles
- **Loopback Binding**: The dashboard binds exclusively to `127.0.0.1`. It never listens on `0.0.0.0` or external network interfaces.
- **Zero Remote Telemetry**: The application executes zero Google Analytics, CDN script tags, external fonts, or remote beacon tracking.
- **No Credential Storage**: No registrar login credentials, credit card details, or banking APIs are handled or stored by this software.
