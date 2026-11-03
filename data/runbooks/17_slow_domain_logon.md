---
id: rb-17-slow-domain-logon
title: Slow Windows Domain Logon and Group Policy Processing Delay
tags: [slow-logon, logon, group-policy, gpo, profile, roam, sysvol, ldap, login-slow]
---

## Symptoms
- Users on domain workstations (`wks-ops-09.corp.example.test`) wait 4–10 minutes at "Applying user settings" or "Please wait for the Group Policy Client" during morning sign-in.
- Group Policy operational log shows high elapsed processing time (`Event ID 5312`, `5326`, or `4001`) or unreachable mapped drive / network printer UNC targets.
- Common root cause: GPO drive-map or printer preference pointing to a decommissioned file/print server UNC path causing SMB timeout during synchronous logon, or slow Domain Controller LDAP/SYSVOL site affinity.

## Checks (Read-Only Commands)
Inspect recent Group Policy Operational events to identify which CSE extension or GPO hung during logon:
- `Get-WinEvent -LogName "Microsoft-Windows-GroupPolicy/Operational" -MaxEvents 30 | Select-Object TimeCreated, Id, Message | Format-List`
Verify low-latency TCP 389 (LDAP) and TCP 445 (SYSVOL SMB) connectivity to the local site Domain Controller (`dc-01.corp.example.test`):
- `Test-NetConnection -ComputerName dc-01.corp.example.test -Port 389`
- `Test-NetConnection -ComputerName dc-01.corp.example.test -Port 445`
Measure size of the user's local profile directory to rule out bloated profile caches:
- `Get-ChildItem -Path C:\Users\user09 -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum`

## Fixes (Change Commands)
Remove stale unreachable mapped network drives on the session or refresh Group Policy cache after remediating the broken GPO link:
- `Remove-SmbMapping -RemotePath "\\srv-legacy-01\archive" -Force`

## Escalation Rule
Escalate to Tier 2 Active Directory Engineering before editing or unlinking domain-wide Group Policy Objects, if AD Sites and Services subnet mappings are missing (causing cross-WAN DC authentication), or if FSLogix/roaming profile VHD containers fail to attach.
