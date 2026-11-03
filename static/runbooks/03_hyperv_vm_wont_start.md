---
id: rb-03-hyperv-vm-wont-start
title: Hyper-V Virtual Machine Will Not Start
tags: [hyper-v, hyperv, vm, virtualization, vhdx, vmms, power-on, checkpoint]
---

## Symptoms
- A guest virtual machine (`vm-erp-01`) on Hyper-V host `hv-host-01.corp.example.test` refuses to power on or stays stuck in `Off` / `Saved` state.
- Hyper-V Manager reports "Failed to change state", insufficient host memory, orphaned checkpoint `.avhdx` chain error, or depleted CSV/datastore disk space (`0x80070070`).
- Common root cause: exhausted host storage on the VHDX volume, insufficient available RAM on the Hyper-V host, or stalled `vmms` (Hyper-V Virtual Machine Management) service.

## Checks (Read-Only Commands)
Inspect the VM state, operational status, and memory assignment on the Hyper-V host:
- `Get-VM -Name vm-erp-01 | Select-Object Name, State, Status, MemoryAssigned, MemoryStartup`
Check free disk space on all host storage volumes hosting VHDX and checkpoint files:
- `Get-Volume | Select-Object DriveLetter, FileSystemLabel, HealthStatus, SizeRemaining, Size | Format-Table -AutoSize`
Verify the Hyper-V Virtual Machine Management service (`vmms`) status and recent Hyper-V-VMMS admin logs:
- `Get-Service -Name vmms, vhdsvc | Select-Object Name, Status, StartType`
- `Get-WinEvent -LogName "Microsoft-Windows-Hyper-V-VMMS-Admin" -MaxEvents 20 | Select-Object TimeCreated, Id, Message | Format-List`

## Fixes (Change Commands)
Delete saved state if corrupted (with approval), restart the Hyper-V management service (does not stop running VMs), and start the VM:
- `Restart-Service -Name vmms`
- `Start-VM -Name vm-erp-01`

## Escalation Rule
Escalate to Tier 2 Virtualization Engineering if VHDX or `.avhdx` checkpoint chain corruption is reported, if Cluster Shared Volume (CSV) ownership fails in Failover Cluster Manager, or if host hardware memory faults are logged.
