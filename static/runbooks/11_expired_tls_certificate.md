---
id: rb-11-expired-tls-certificate
title: Expired TLS/SSL Certificate on Windows IIS Web Server
tags: [certificate, ssl, tls, expired, iis, https, cert-store, thumbprint, x509]
---

## Symptoms
- Users connecting to internal portal `https://portal.tenant-alpha.test` on IIS server `srv-web-01.corp.example.test` receive browser warning `NET::ERR_CERT_DATE_INVALID` (`SEC_ERROR_EXPIRED_CERTIFICATE`).
- API integrations fail TLS handshake due to an expired X.509 certificate bound to TCP port 443.
- Common root cause: renewed TLS certificate was imported into `Cert:\LocalMachine\My` (or awaits import), while the IIS HTTPS site binding on port 443 still references the old expired certificate thumbprint.

## Checks (Read-Only Commands)
List all certificates in the LocalMachine Personal store with expiration dates and thumbprints:
- `Get-ChildItem -Path Cert:\LocalMachine\My | Select-Object Subject, FriendlyName, NotBefore, NotAfter, Thumbprint | Format-Table -AutoSize`
Inspect current IIS web bindings on port 443:
- `Get-WebBinding -Protocol "https" | Select-Object protocol, bindingInformation, certificateHash, certificateStoreName`
Test TCP port 443 connectivity to the web server:
- `Test-NetConnection -ComputerName srv-web-01.corp.example.test -Port 443`

## Fixes (Change Commands)
Import the renewed `.pfx` certificate (if not yet staged) and update the IIS HTTPS binding to the new valid certificate thumbprint during an approved change window:
- `New-WebBinding -Name "Default Web Site" -Protocol "https" -Port 443 -IPAddress "*"`
- `Remove-Item -Path "Cert:\LocalMachine\My\OLD_EXPIRED_THUMBPRINT"`

## Escalation Rule
Escalate to Tier 2 PKI/Security Engineering if the internal Enterprise Root/Issuing CA itself has expired, if private key material is missing for CSR renewal, or if wildcards span external load balancers/WAFs.
