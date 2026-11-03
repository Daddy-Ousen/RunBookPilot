---
id: rb-10-intune-enrollment-fail
title: Microsoft Intune Automatic MDM Enrollment Failure
tags: [intune, mdm, enrollment, autopilot, entra-id, azure-ad, 0x80180014, device-management]
---

## Symptoms
- Windows 11 corporate laptop fails automatic Microsoft Intune MDM enrollment during Entra join or GPO enrollment task with error `0x80180014`, `0x80180002`, or `0x8018002b`.
- Device appears in Entra ID without an Intune compliance state or Company Portal reports device cannot enroll.
- Common root cause: missing Intune MDM license assignment on the enrolling user, Windows MDM enrollment disabled/blocked by tenant device restriction (e.g. personal Windows device block or 15-device limit), or stale `EnterpriseMgmt` scheduled tasks/registry enrollment entries.

## Checks (Read-Only Commands)
Inspect recent DeviceManagement-Enterprise-Diagnostics-Provider Admin event log errors on the Windows 11 endpoint:
- `Get-WinEvent -LogName "Microsoft-Windows-DeviceManagement-Enterprise-Diagnostics-Provider/Admin" -MaxEvents 25 | Select-Object TimeCreated, Id, Message | Format-List`
Check existing EnterpriseMgmt enrollment scheduled tasks:
- `Get-ScheduledTask -TaskPath "\Microsoft\Windows\EnterpriseMgmt\*" | Select-Object TaskName, TaskPath, State`
Verify device hostname and MDM service status (`dmwappushservice`):
- `hostname`
- `Get-Service -Name dmwappushservice | Select-Object Name, Status, StartType`

## Fixes (Change Commands)
Enable and start `dmwappushservice` and trigger the Windows MDM enrollment scheduled task / deviceenroller re-registration after verifying user Intune licensing:
- `Set-Service -Name dmwappushservice -StartupType Automatic`
- `Start-Service -Name dmwappushservice`

## Escalation Rule
Escalate to Tier 2 Modern Workplace / Endpoint Admin if tenant MDM Mobility scope, Autopilot hardware hash registration, or Enrollment Restrictions policy (`0x80180014`) blocks corporate devices across the tenant.
