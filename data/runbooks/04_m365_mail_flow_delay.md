---
id: rb-04-m365-mail-flow-delay
title: Microsoft 365 Exchange Online Mail Flow Delay
tags: [m365, exchange-online, mail-flow, email, delay, queue, connector, mx, smtp, deferred]
---

## Symptoms
- Inbound or outbound emails for tenant `tenant-alpha.test` are delayed by 20+ minutes or stuck in `Pending` / `Deferred` status in Exchange Online.
- Users report external messages arriving late or outbound partner mail queuing with `451 4.4.0 DNS query failed` or TLS connector validation errors.
- Common root cause: misconfigured or disabled Exchange Online mail flow connector, broken third-party mail gateway MX/SPF routing, or transport rule deferral loop.

## Checks (Read-Only Commands)
Run an Exchange Online message trace for affected recipient messages over the default 48-hour window:
- `Get-MessageTrace -RecipientAddress user02@tenant-alpha.test -PageSize 25 | Select-Object Received, SenderAddress, RecipientAddress, Subject, Status | Format-Table -AutoSize`
Inspect inbound and outbound Exchange Online connectors for disabled state or TLS certificate mismatch:
- `Get-InboundConnector | Select-Object Name, Enabled, ConnectorType, SenderDomains`
- `Get-OutboundConnector | Select-Object Name, Enabled, ConnectorType, SmartHosts`
Verify external MX record resolution for the tenant domain:
- `nslookup -type=MX tenant-alpha.test`

## Fixes (Change Commands)
Re-enable or update the affected Exchange Online outbound/inbound connector after change approval:
- `Set-OutboundConnector -Identity "Partner Gateway Outbound" -Enabled $true`

## Escalation Rule
Escalate to Tier 2 Cloud Messaging Engineering before modifying MX records, SPF/DKIM/DMARC DNS policy, or third-party smart-host routing, or if tenant-wide Exchange Online service advisories (`EX*`) are active.
