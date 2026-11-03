---
id: rb-06-windows-update-stuck
title: Windows Update Stuck Downloading or Installing
tags: [windows-update, patching, wuauserv, bits, softwaredistribution, kb, stuck, 0x8024001e]
---

## Symptoms
- Monthly cumulative update on workstation or server stays stuck at `Downloading - 0%` or `Pending Install` for several hours, or fails with `0x80070020`, `0x8024001e`, or `0x800f081f`.
- Patch compliance report flags endpoint `wks-acct-04.corp.example.test` as overdue for security updates.
- Common root cause: corrupted local Windows Update cache (`C:\Windows\SoftwareDistribution`), hung Background Intelligent Transfer Service (`BITS`), or stalled `wuauserv` service.

## Checks (Read-Only Commands)
Inspect the status of Windows Update, BITS, Cryptographic, and Windows Installer services:
- `Get-Service -Name wuauserv, bits, cryptsvc, msiserver | Select-Object Name, Status, StartType | Format-Table -AutoSize`
Check recently installed hotfixes to confirm patch history:
- `Get-HotFix | Select-Object HotFixID, Description, InstalledOn | Format-Table -AutoSize`
Review recent WindowsUpdateClient operational errors:
- `Get-WinEvent -LogName "Microsoft-Windows-WindowsUpdateClient/Operational" -MaxEvents 20 | Select-Object TimeCreated, Id, Message | Format-List`

## Fixes (Change Commands)
Stop Windows Update and BITS services, rename the corrupted `SoftwareDistribution` cache folder, and restart the services:
- `Stop-Service -Name wuauserv, bits -Force`
- `Rename-Item -Path "C:\Windows\SoftwareDistribution" -NewName "SoftwareDistribution.bak"`
- `Start-Service -Name bits, wuauserv`

## Escalation Rule
Escalate to Tier 2 Systems Engineering if servicing stack / Component-Based Servicing (`DISM` / `CBS`) corruption persists (`0x800f081f` / `0x800f0922`), or if a server is stuck at "Getting Windows ready — Don't turn off your computer" during reboot for over 60 minutes.
