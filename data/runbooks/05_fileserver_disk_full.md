---
id: rb-05-fileserver-disk-full
title: Disk Full Alert on Windows File Server
tags: [disk-full, storage, file-server, low-disk-space, volume, quota, temp-files, smb]
---

## Symptoms
- RMM monitoring triggers a critical low-disk-space alert (< 5% or < 2 GB free) on system drive `C:` or data volume `D:` of `srv-file-01.corp.example.test`.
- Users cannot save documents to SMB network shares and receive "There is not enough space on the disk" (`0x80070070`).
- Common root cause: runaway IIS/CBS/application log accumulation, orphaned Windows Temp files, or oversized user share uploads/shadow copies consuming volume capacity.

## Checks (Read-Only Commands)
Check free capacity across all mounted volumes on the file server:
- `Get-Volume | Select-Object DriveLetter, FileSystemLabel, HealthStatus, SizeRemaining, Size | Format-Table -AutoSize`
Measure total size of files inside `C:\Windows\Temp` and `C:\Windows\Logs\CBS`:
- `Get-ChildItem -Path C:\Windows\Temp -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum`
- `Get-ChildItem -Path C:\Windows\Logs\CBS -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum`
List top-level folders on the data share volume to review directory layout:
- `Get-ChildItem -Path D:\Shares -Directory | Select-Object Name, LastWriteTime`

## Fixes (Change Commands)
Remove stale temporary files from `C:\Windows\Temp` and archived CBS logs (never delete user share files without written owner approval):
- `Remove-Item -Path "C:\Windows\Temp\*" -Recurse -Force -ErrorAction SilentlyContinue`
- `Stop-Service -Name TrustedInstaller -Force`
- `Remove-Item -Path "C:\Windows\Logs\CBS\CBS.log" -Force -ErrorAction SilentlyContinue`

## Escalation Rule
Escalate to Tier 2 Infrastructure Engineering if freeing temporary/log files leaves less than 10% free space, if volume expansion (VHDX/SAN LUN resize) is needed, or before deleting any business data or VSS shadow copies.
