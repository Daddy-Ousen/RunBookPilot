---
id: rb-18-raid-degraded-alert
title: Server RAID / Storage Spaces Degraded Array Alert
tags: [raid, degraded, storage-spaces, physical-disk, virtual-disk, drive-failure, smart, array]
---

## Symptoms
- Hardware iDRAC/iLO or Windows Storage Spaces monitoring raises a critical `Degraded` / `Predictive Failure` alert on storage host `srv-stor-01.corp.example.test`.
- Array remains online with reduced fault tolerance after one physical SAS/NVMe member disk enters `LostCommunication`, `PredictiveFailure`, or `Unhealthy` status.
- Common root cause: failing physical SAS/SSD drive media errors or backplane slot fault causing the virtual disk / RAID logical volume to run degraded without redundancy.

## Checks (Read-Only Commands)
Inspect all physical disks for `HealthStatus`, `OperationalStatus`, and slot location:
- `Get-PhysicalDisk | Select-Object FriendlyName, SerialNumber, MediaType, CanPool, OperationalStatus, HealthStatus, Size | Format-Table -AutoSize`
Check virtual disk / logical storage array resiliency and degraded operational status:
- `Get-VirtualDisk | Select-Object FriendlyName, ResiliencySettingName, OperationalStatus, HealthStatus, Size`
Inspect storage pool health and read-only state:
- `Get-StoragePool | Select-Object FriendlyName, OperationalStatus, HealthStatus, IsReadOnly`
Check disk reliability counters (read/write errors and wear):
- `Get-PhysicalDisk | Get-StorageReliabilityCounter | Select-Object DeviceId, ReadErrorsTotal, WriteErrorsTotal, Wear`

## Fixes (Change Commands)
After a spare physical disk is installed and verified, mark the failed physical disk as `Retired` and initiate virtual disk repair during an approved maintenance window:
- `Set-PhysicalDisk -FriendlyName "PhysicalDisk3" -Usage Retired`
- `Repair-VirtualDisk -FriendlyName "DataMirror01"`

## Escalation Rule
Escalate to Tier 2 Hardware/Storage Engineering if more than one physical drive shows predictive or media errors (risk of double-fault array loss), if no recent verified BCDR backup exists, or if a hardware RAID controller cache/battery fault is reported.
