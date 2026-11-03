---
id: rb-12-server-high-cpu
title: Sustained High CPU Utilization on Windows Server
tags: [high-cpu, cpu, performance, process, runaway-process, wmi, server-slow]
---

## Symptoms
- RMM monitoring alerts that total CPU usage on `srv-app-02.corp.example.test` has exceeded 95% continuously for over 15 minutes.
- Application responses time out and interactive console sessions feel sluggish.
- Common root cause: runaway application worker process (`w3wp.exe`, reporting worker, or stuck monitoring agent), hung `WmiPrvSE.exe` query loop, or unscheduled full antivirus scan during business hours.

## Checks (Read-Only Commands)
Sample overall processor utilization across 3 intervals to verify active saturation:
- `Get-Counter -Counter "\Processor(_Total)\% Processor Time" -SampleInterval 2 -MaxSamples 3`
Inspect running processes with cumulative CPU time and memory footprint:
- `Get-Process | Select-Object Name, Id, CPU, WorkingSet, StartTime | Format-Table -AutoSize`
Check Windows Defender scan status and running application services:
- `Get-MpComputerStatus | Select-Object AntivirusEnabled, FullScanAge, QuickScanAge`
- `Get-Service | Select-Object Name, DisplayName, Status | Format-Table -AutoSize`

## Fixes (Change Commands)
Restart the runaway non-critical application pool/service or terminate an identified hung worker PID after change approval (never kill OS critical processes or database engines):
- `Restart-Service -Name W3SVC`
- `Stop-Process -Id 4812 -Force`

## Escalation Rule
Escalate to Tier 2 Systems/Database Engineering if high CPU is driven by `sqlservr.exe`, `lsass.exe` (Domain Controller), or kernel `System` interrupts, or if CPU saturation recurs immediately after service restart requiring VM vCPU right-sizing.
