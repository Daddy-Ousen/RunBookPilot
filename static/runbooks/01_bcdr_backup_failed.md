---
id: rb-01-bcdr-backup-failed
title: Failed BCDR Image Backup (VSS Writer / Agent Stall)
tags: [backup, bcdr, vss, shadow-copy, snapshot, image-backup, agent]
---

## Symptoms
- Scheduled block-level BCDR appliance backup job fails overnight with snapshot timeout or Volume Shadow Copy Service (VSS) writer error (`0x800423f4` / `VSS Event ID 8193` or `12289`).
- Backup portal alerts that incremental image snapshot for protected Windows Server (`srv-app-01.corp.example.test`) could not complete.
- Common root cause: stuck VSS writers or a hung BCDR backup agent service (`BackupAgentService` / `VSS`).

## Checks (Read-Only Commands)
Verify the status of the backup agent and Volume Shadow Copy services:
- `Get-Service -Name BackupAgentService, VSS, swprv | Select-Object Name, Status, StartType | Format-Table -AutoSize`
Inspect recent VSS errors in the Windows Application event log:
- `Get-WinEvent -LogName Application -MaxEvents 25 | Select-Object TimeCreated, Id, ProviderName, Message | Format-List`
Confirm adequate free space exists on volumes for shadow copy storage:
- `Get-Volume | Select-Object DriveLetter, FileSystemLabel, SizeRemaining, Size | Format-Table -AutoSize`

## Fixes (Change Commands)
Restart the Volume Shadow Copy service and the BCDR backup agent service during an approved window:
- `Restart-Service -Name VSS -Force`
- `Restart-Service -Name BackupAgentService -Force`

## Escalation Rule
Escalate to Tier 2 Storage/Backup Engineering if VSS writers remain in a failed state after restarting the services, if `NTDS` or `SqlServerWriter` fails repeatedly, or if backups have failed for more than 48 consecutive hours.
